"""Band-wise spread-gated autoregressive ensemble rollout (inference only).

Mechanism: FlowCast's chunked rollout feeds each chunk's raw prediction back
as the next chunk's condition (``rf_stdit.autoregressive_sample``).  This
module rolls the *whole ensemble* forward chunk-synchronously and, at every
chunk boundary, decides per radial frequency band how much of the generated
detail is trustworthy enough to condition on.  The trust signal is the
cross-member band spread (an internal, per-sample estimate of scale-dependent
predictability); low-spread bands pass through, high-spread bands are
attenuated so the condition falls back to that member's own low-pass.

Three design rules are frozen here on purpose (they came out of the
adversarial review that admitted this candidate, 2026-08-10):

1.  **Per-member content only.**  The gate's alpha is an ensemble statistic,
    but the *content* fed back for member ``m`` is always derived from member
    ``m`` alone.  No cross-member consensus in the condition: consensus
    feedback would collapse ensemble spread exactly where uncertainty is
    largest and damage CRPS.
2.  **Inference only.**  Nothing here trains or backpropagates; the generator
    stays frozen.  ``gate=None`` is bit-identical to per-member
    ``autoregressive_sample`` calls with the same ``torch.Generator`` objects
    (pinned by tests).  Equivalence with the production protocol -- global
    ``torch.manual_seed(idx*S+s)`` and ``generator=None`` -- additionally
    relies on the default-generator stream matching a fresh ``Generator``
    seeded identically; this is pinned on CPU by
    ``tests/test_gated_rollout.py::test_gate_none_matches_production_global_seed_protocol``
    and must be re-checked once on CUDA before any paired A/B on GPU.
3.  **Calibration before deployment.**  ``SpreadToAlpha`` maps spread to
    trust using quantiles measured by ``tools/calibrate_band_spread.py``.
    Running the gate with a hand-tuned mapping would turn it into a static
    band weight -- the exact configuration the novelty review said is already
    occupied (PW-FouCast / FADiff).  Production mappings are built with
    ``SpreadToAlpha.from_report`` which enforces a machine-readable view
    fingerprint; ``from_calibration``/``identity()`` are for tests and
    explicit control arms.

View discipline (adversarial review findings, 2026-08-10): calibrated
quantiles are only meaningful on the exact view they were measured on --
same value scale, same crop, same clamp.  A silent view mismatch does not
error out by itself; it drives every spread out of the calibrated range and
the gate degenerates to an identity (or to a static attenuator), producing a
false-negative A/B.  The defenses, in order: ``from_report`` carries the
fingerprint; ``BandGate`` computes its spread on a configurable *spread view*
(crop + clamp applied only for the trust computation, never for the content
that is re-encoded) and validates the fingerprint's height/width against it;
an order-of-magnitude scale check rejects grossly off-view spreads; and
``BandGate.telemetry()`` exposes the fraction of runtime spreads inside the
calibrated quantile range so an eval harness can refuse a run whose gate
never actually gated (0%) or always saturated (100%).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import torch

from common.metrics.band_spectral import (
    DEFAULT_BAND_EDGES,
    bandpass_decompose,
    power_band_spread,
    radial_band_masks,
    spatial_band_spread,
)
from .rf_stdit import sample_chunk_euler

__all__ = [
    "SpreadToAlpha",
    "BandGate",
    "gated_autoregressive_ensemble",
    "build_codec_fns",
]

# factor for the order-of-magnitude runtime scale check: natural event-to-
# event variation stays well inside this; a metric-vs-AE-native unit mismatch
# (x90) does not.
_SCALE_MISMATCH_FACTOR = 30.0


@dataclass(frozen=True)
class SpreadToAlpha:
    """Monotone map from per-band spread to per-band trust ``alpha``.

    Piecewise linear per band: ``alpha = 1`` for spread at or below ``q_lo``
    (calibration low quantile), decreasing linearly to ``alpha_min`` at
    ``q_hi`` (calibration high quantile), constant beyond.  Bands whose
    calibration was excluded (degenerate / no exportable mapping) are marked
    inactive and always map to ``alpha = 1``: the gate does not act where it
    could not be calibrated.

    ``view_height``/``view_width`` fingerprint the view the quantiles were
    measured on; ``BandGate`` refuses spread inputs of any other shape.
    """

    q_lo: torch.Tensor  # (J,)
    q_hi: torch.Tensor  # (J,)
    alpha_min: float = 0.3
    active: Optional[torch.Tensor] = None  # (J,) bool; None -> all active
    view_height: Optional[int] = None
    view_width: Optional[int] = None

    def __post_init__(self):
        if self.q_lo.shape != self.q_hi.shape:
            raise ValueError("q_lo and q_hi must have the same shape (J,)")
        if not bool(
            torch.isfinite(self.q_lo).all() and torch.isfinite(self.q_hi).all()
        ):
            raise ValueError(
                "q_lo/q_hi must be finite; NaN quantiles indicate a broken "
                "calibration report and would silently pass ordering checks"
            )
        active = self.active
        if active is None:
            active = torch.ones(self.q_lo.shape[0], dtype=torch.bool)
            object.__setattr__(self, "active", active)
        if active.shape != self.q_lo.shape:
            raise ValueError("active mask must have shape (J,)")
        if bool((self.q_hi[active] <= self.q_lo[active]).any()):
            raise ValueError(
                "q_hi must be strictly greater than q_lo in every active "
                "band; a degenerate band has no dynamic range and must be "
                "excluded at calibration time, not silently accepted here"
            )
        if not 0.0 <= self.alpha_min <= 1.0:
            raise ValueError(f"alpha_min must be in [0, 1], got {self.alpha_min}")

    @classmethod
    def from_calibration(
        cls,
        q_lo: Sequence[float],
        q_hi: Sequence[float],
        alpha_min: float = 0.3,
        view_height: Optional[int] = None,
        view_width: Optional[int] = None,
    ) -> "SpreadToAlpha":
        """Test/ablation constructor from raw quantiles (no fingerprint check).

        Production must use :meth:`from_report`.
        """
        return cls(
            q_lo=torch.as_tensor(list(q_lo), dtype=torch.float64),
            q_hi=torch.as_tensor(list(q_hi), dtype=torch.float64),
            alpha_min=alpha_min,
            view_height=view_height,
            view_width=view_width,
        )

    @classmethod
    def from_report(cls, report: Dict, alpha_min: float = 0.3) -> "SpreadToAlpha":
        """Build the production mapping from a calibration report dict.

        Refuses reports without a view fingerprint (``deployable: false``) --
        those are correlation-only runs.  Bands whose ``alpha_mapping`` is
        ``None`` (excluded at calibration) become inactive pass-through.
        """
        view = report.get("view")
        if not view or not report.get("deployable", False):
            raise ValueError(
                "calibration report carries no view fingerprint and is not "
                "deployable; re-run tools/calibrate_band_spread.py on the "
                "runtime view"
            )
        bands = sorted(report["bands"], key=lambda b: b["band"])
        q_lo, q_hi, active = [], [], []
        for band in bands:
            mapping = band.get("alpha_mapping")
            if mapping is None:
                q_lo.append(0.0)
                q_hi.append(1.0)  # placeholder; inactive bands never use it
                active.append(False)
            else:
                q_lo.append(float(mapping["q_lo"]))
                q_hi.append(float(mapping["q_hi"]))
                active.append(True)
        return cls(
            q_lo=torch.tensor(q_lo, dtype=torch.float64),
            q_hi=torch.tensor(q_hi, dtype=torch.float64),
            alpha_min=alpha_min,
            active=torch.tensor(active, dtype=torch.bool),
            view_height=int(view["height"]),
            view_width=int(view["width"]),
        )

    @classmethod
    def identity(cls, num_bands: int) -> "SpreadToAlpha":
        """alpha == 1 everywhere: gate plumbing active, trust decisions off.

        This is the roundtrip-control arm: it isolates the decode->encode
        feedback cost from the effect of the trust decisions themselves.
        """
        return cls(
            q_lo=torch.zeros(num_bands, dtype=torch.float64),
            q_hi=torch.ones(num_bands, dtype=torch.float64),
            alpha_min=1.0,
        )

    def __call__(self, spread: torch.Tensor) -> torch.Tensor:
        """Map spread ``(..., J)`` -> alpha ``(..., J)`` in ``[alpha_min, 1]``."""
        q_lo = self.q_lo.to(spread.device, spread.dtype)
        q_hi = self.q_hi.to(spread.device, spread.dtype)
        fraction = (spread - q_lo) / (q_hi - q_lo)
        fraction = fraction.clamp(0.0, 1.0)
        alpha = 1.0 - fraction * (1.0 - self.alpha_min)
        active = self.active.to(spread.device)
        return torch.where(active, alpha, torch.ones_like(alpha))


class BandGate:
    """Computes per-band trust from the ensemble and applies it per member.

    ``spread_view_crop``/``spread_view_clamp`` define the *spread view*: the
    trust computation is done on the cropped, clamped field so that it lives
    on the exact view the calibration measured (e.g. CIKM: crop
    ``13:-14`` and clamp ``[0, 90]`` on the metric scale).  The *content*
    that ``apply`` mixes and that gets re-encoded is always the full,
    unclamped field -- clamping the feedback would alter the generator's
    input distribution, which is not this module's call to make.
    """

    def __init__(
        self,
        band_edges: Sequence[float] = DEFAULT_BAND_EDGES,
        spread_to_alpha: Optional[SpreadToAlpha] = None,
        spread_definition: str = "spatial",
        protect_lowest_band: bool = True,
        spread_view_crop: Optional[Tuple[slice, slice]] = None,
        spread_view_clamp: Optional[Tuple[float, float]] = None,
    ):
        if spread_to_alpha is None:
            raise ValueError(
                "BandGate requires a calibrated SpreadToAlpha (or the explicit "
                "SpreadToAlpha.identity() control); refusing to invent a "
                "mapping -- see module docstring, rule 3"
            )
        if spread_definition not in ("spatial", "power"):
            raise ValueError(
                f"spread_definition must be 'spatial' or 'power', got "
                f"{spread_definition!r}"
            )
        num_bands = len(band_edges) - 1
        if spread_to_alpha.q_lo.shape[0] != num_bands:
            raise ValueError(
                f"SpreadToAlpha has {spread_to_alpha.q_lo.shape[0]} bands but "
                f"band_edges defines {num_bands}"
            )
        self.band_edges = tuple(band_edges)
        self.spread_to_alpha = spread_to_alpha
        self.spread_definition = spread_definition
        self.protect_lowest_band = protect_lowest_band
        self.spread_view_crop = spread_view_crop
        self.spread_view_clamp = spread_view_clamp
        self._mask_cache = {}
        # telemetry: decisions per band, and how many fell inside the
        # calibrated [q_lo, q_hi] range.  0% in-range over a whole eval run
        # means the gate never gated (view/scale mismatch, alpha stuck at 1);
        # 100% saturation is the opposite failure.  The eval harness should
        # log gate.telemetry() and treat either extreme as a broken run.
        self._decision_count = 0
        self._in_range_count = torch.zeros(num_bands, dtype=torch.long)
        self._below_count = torch.zeros(num_bands, dtype=torch.long)
        self._above_count = torch.zeros(num_bands, dtype=torch.long)

    def _masks(self, height: int, width: int, device: torch.device) -> torch.Tensor:
        key = (height, width, str(device))
        if key not in self._mask_cache:
            self._mask_cache[key] = radial_band_masks(
                height, width, self.band_edges, device=device
            )
        return self._mask_cache[key]

    def _spread_view(self, member_pixels: torch.Tensor) -> torch.Tensor:
        view = member_pixels
        if self.spread_view_crop is not None:
            row_slice, col_slice = self.spread_view_crop
            view = view[..., row_slice, col_slice]
        if self.spread_view_clamp is not None:
            low, high = self.spread_view_clamp
            view = view.clamp(low, high)
        return view

    def alpha_from_members(self, member_pixels: torch.Tensor) -> torch.Tensor:
        """Trust per band from the ensemble: ``(S, B, T, H, W)`` -> ``(B, J)``.

        Spread is computed on the spread view, per event, over the chunk's
        frames jointly (the gate decides once per chunk boundary), then mapped
        through the calibrated quantiles.  The result is invariant to member
        order (tested).  Fails loudly when the spread view does not match the
        calibration fingerprint or when the spread magnitude is orders of
        magnitude outside the calibrated range (unit/view mismatch).
        """
        if member_pixels.ndim != 5:
            raise ValueError(
                f"member_pixels must be (S, B, T, H, W), got "
                f"{tuple(member_pixels.shape)}"
            )
        view = self._spread_view(member_pixels)
        height, width = view.shape[-2:]
        mapping = self.spread_to_alpha
        if mapping.view_height is not None and (
            (height, width) != (mapping.view_height, mapping.view_width)
        ):
            raise ValueError(
                f"spread view is {height}x{width} but the calibration "
                f"fingerprint says {mapping.view_height}x{mapping.view_width}; "
                "quantiles do not transfer across views -- regenerate the "
                "calibration on the runtime view or fix spread_view_crop"
            )
        masks = self._masks(height, width, view.device)
        spread_fn = (
            spatial_band_spread
            if self.spread_definition == "spatial"
            else power_band_spread
        )
        rows = []
        for b in range(view.shape[1]):
            per_lead = spread_fn(view[:, b], masks)  # (T, J)
            rows.append(per_lead.mean(dim=0))  # (J,)
        spread = torch.stack(rows, dim=0)  # (B, J)

        self._scale_sanity_check(spread)
        self._record_telemetry(spread)

        alpha = mapping(spread)
        if self.protect_lowest_band:
            # The lowest band carries domain-total mass and large-scale
            # position; attenuating it starves the next chunk of the signal
            # even a pure advection forecast would keep.  The gate's job is
            # to demote unreliable *detail*, so band 0 is pinned to full
            # trust unless explicitly disabled for ablation.
            alpha = alpha.clone()
            alpha[:, 0] = 1.0
        return alpha

    def _scale_sanity_check(self, spread: torch.Tensor) -> None:
        mapping = self.spread_to_alpha
        active = mapping.active
        if not bool(active.any()):
            return
        positive_lo = mapping.q_lo[active & (mapping.q_lo > 0)]
        if positive_lo.numel() == 0:
            return
        active_spread = spread[:, active.to(spread.device)]
        med = active_spread.median()
        floor = positive_lo.min().item() / _SCALE_MISMATCH_FACTOR
        ceiling = mapping.q_hi[active].max().item() * _SCALE_MISMATCH_FACTOR
        if med < floor or med > ceiling:
            raise ValueError(
                f"runtime band spread (median {med:.4g}) is orders of "
                f"magnitude outside the calibrated quantile range "
                f"[{positive_lo.min().item():.4g}, "
                f"{mapping.q_hi[active].max().item():.4g}]: this is a "
                "view/unit mismatch (e.g. metric 0-90 quantiles against "
                "AE-native 0-1 pixels), not weather variability"
            )

    def _record_telemetry(self, spread: torch.Tensor) -> None:
        mapping = self.spread_to_alpha
        s = spread.detach().cpu().to(torch.float64)
        in_range = (s >= mapping.q_lo) & (s <= mapping.q_hi)
        self._in_range_count += in_range.sum(dim=0)
        self._below_count += (s < mapping.q_lo).sum(dim=0)
        self._above_count += (s > mapping.q_hi).sum(dim=0)
        self._decision_count += spread.shape[0]

    def telemetry(self) -> Dict:
        """Aggregated gate-decision statistics for the eval harness.

        Interpretation contract: over a full eval run, ``in_range_fraction``
        of 0.0 for every active band means the gate never made a real
        decision (alpha pinned at an extreme -- almost certainly a view
        mismatch that survived the shape check); 1.0 everywhere means the
        calibrated range is too wide to ever bind.  Either extreme should
        fail the run, not be reported as a gate result.
        """
        count = max(self._decision_count, 1)
        return {
            "decisions": self._decision_count,
            "in_range_fraction": (self._in_range_count / count).tolist(),
            "below_fraction": (self._below_count / count).tolist(),
            "above_fraction": (self._above_count / count).tolist(),
            "active": self.spread_to_alpha.active.tolist(),
        }

    def apply(
        self, member_pixels: torch.Tensor, alpha: torch.Tensor
    ) -> torch.Tensor:
        """Attenuate untrusted bands, per member: fall back to self low-pass.

        ``member_pixels (S, B, T, H, W)`` with ``alpha (B, J)`` ->
        same-shape tensor where member ``m``'s band ``j`` content is scaled by
        ``alpha[b, j]``.  With alpha == 1 this is an exact identity (the band
        decomposition is a partition), which the tests pin.

        Only the member's own content enters its output -- rule 1.  The full
        field is mixed (no crop, no clamp): the spread view exists for the
        trust *measurement*, not for the fed-back content.
        """
        if member_pixels.ndim != 5:
            raise ValueError(
                f"member_pixels must be (S, B, T, H, W), got "
                f"{tuple(member_pixels.shape)}"
            )
        height, width = member_pixels.shape[-2:]
        masks = self._masks(height, width, member_pixels.device)
        bands = bandpass_decompose(member_pixels, masks)  # (S, B, T, J, H, W)
        weights = alpha.to(bands.dtype)[None, :, None, :, None, None]
        return (bands * weights).sum(dim=-3).to(member_pixels.dtype)


def gated_autoregressive_ensemble(
    model,
    initial_cond: torch.Tensor,
    num_members: int,
    input_length: int,
    output_length: int,
    num_train_timesteps: int,
    euler_steps: int,
    member_generators: Optional[List[Optional[torch.Generator]]] = None,
    gate: Optional[BandGate] = None,
    decode_fn: Optional[Callable[[torch.Tensor], torch.Tensor]] = None,
    encode_fn: Optional[Callable[[torch.Tensor], torch.Tensor]] = None,
    sde_noise_scale: Optional[float] = None,
    sde_final_step_noise: bool = False,
    sde_drift_compensation: bool = True,
):
    """Chunk-synchronous ensemble rollout with optional band-trust gating.

    Mirrors ``rf_stdit.autoregressive_sample`` looped over members, with the
    loop order flipped (chunks outer, members inner) so the gate can see the
    whole ensemble at each chunk boundary.  With ``gate=None`` the feedback is
    ``cond = pred_chunk`` exactly as in production, and the outputs are
    bit-identical to per-member ``autoregressive_sample`` calls with the same
    generators (pinned by tests; see module docstring rule 2 for the exact
    scope of the equivalence claim vs the global-seed production protocol).

    With a gate: after every non-final chunk, each member's prediction is
    decoded to pixels (``decode_fn``), the ensemble band spread sets per-band
    trust, each member's *own* pixels are band-attenuated accordingly, and the
    result is re-encoded (``encode_fn``) as that member's next condition.  The
    returned predictions are always the raw chunk predictions -- gating only
    changes what later chunks are conditioned on, never the outputs
    themselves (pinned bitwise for every chunk by the sampler-spy test).

    Codec contract (see :func:`build_codec_fns` for the reference
    implementation matching the production conditioning chain):

    * ``decode_fn``: ``(B, T, h, w, c)`` *z-scored* latent (the working space
      of ``sample_chunk_euler``, i.e. after ``model.normalize``) ->
      ``(B, T, Hp, Wp)`` pixels on the calibration's value scale (CIKM:
      0-90 dBZ), full frame, no crop, no clamp;
    * ``encode_fn`` is its exact inverse back to the z-scored latent;
    * both must be **deterministic**.  In particular the VAE encode must use
      ``latent_dist.mode()`` -- ``.sample()`` would inject posterior noise
      drawn from the *global* RNG, breaking both member pairing and
      reproducibility, and the ``gate=None`` equivalence tests are blind to
      it because they never enter this branch.

    Returns ``(S, B, T_out, H, W, C)`` stacked latent predictions.
    """
    if output_length % input_length != 0:
        raise ValueError("output_length must be divisible by input_length.")
    if (gate is not None) and (decode_fn is None or encode_fn is None):
        raise ValueError("gate requires both decode_fn and encode_fn.")
    if member_generators is None:
        member_generators = [None] * num_members
    if len(member_generators) != num_members:
        raise ValueError(
            f"member_generators has {len(member_generators)} entries for "
            f"{num_members} members"
        )

    num_chunks = output_length // input_length
    conds = [initial_cond] * num_members
    predictions = [[] for _ in range(num_members)]

    for chunk_idx in range(1, num_chunks + 1):
        chunk_preds = []
        for m in range(num_members):
            pred = sample_chunk_euler(
                model=model,
                cond=conds[m],
                chunk_idx=chunk_idx,
                num_train_timesteps=num_train_timesteps,
                euler_steps=euler_steps,
                generator=member_generators[m],
                sde_noise_scale=sde_noise_scale,
                sde_final_step_noise=sde_final_step_noise,
                sde_drift_compensation=sde_drift_compensation,
            )
            predictions[m].append(pred)
            chunk_preds.append(pred)

        if chunk_idx == num_chunks:
            break

        if gate is None:
            conds = chunk_preds
            continue

        with torch.no_grad():
            pixel_members = torch.stack(
                [decode_fn(pred) for pred in chunk_preds], dim=0
            )  # (S, B, T, Hp, Wp)
            alpha = gate.alpha_from_members(pixel_members)  # (B, J)
            mixed = gate.apply(pixel_members, alpha)  # (S, B, T, Hp, Wp)
            conds = [encode_fn(mixed[m]) for m in range(num_members)]

    stacked = [
        torch.cat(member_chunks, dim=1) for member_chunks in predictions
    ]
    return torch.stack(stacked, dim=0)


def build_codec_fns(
    ae_model,
    flowcast_model,
    pixel_scale: float,
    normalized_autoencoder: bool,
):
    """Reference decode/encode pair matching the production conditioning chain.

    Mirrors ``test_flowcast.py`` step by step (encode: ``/255`` when the AE is
    trained on normalized inputs, ``latent_dist.mode()``, permute to
    ``(B, T, h, w, c)``, ``model.normalize``; decode: the exact inverse with
    ``decoded_to_eval_scale`` semantics), so the decoded pixels land on the
    metric value scale the calibration measured.  Deterministic by
    construction: encode uses ``latent_dist.mode()``, never ``.sample()``.

    ``ae_model`` is duck-typed: ``encode(x).latent_dist.mode()`` and
    ``decode(z).sample`` (the diffusers ``AutoencoderKL`` interface, already
    unwrapped from DataParallel).
    """

    def decode_fn(latent: torch.Tensor) -> torch.Tensor:
        batch, frames, height, width, channels = latent.shape
        z = flowcast_model.denormalize(latent)
        z = z.permute(0, 1, 4, 2, 3).reshape(batch * frames, channels, height, width)
        pixels = ae_model.decode(z).sample  # (B*T, 1, Hp, Wp)
        if normalized_autoencoder:
            pixels = pixels * pixel_scale
        else:
            pixels = pixels * (pixel_scale / 255.0)
        return pixels.reshape(batch, frames, *pixels.shape[-2:])

    def encode_fn(pixels: torch.Tensor) -> torch.Tensor:
        batch, frames, height_p, width_p = pixels.shape
        x = pixels.reshape(batch * frames, 1, height_p, width_p)
        if normalized_autoencoder:
            x = x / pixel_scale
        else:
            x = x * (255.0 / pixel_scale)
        z = ae_model.encode(x).latent_dist.mode()  # deterministic, no RNG
        z = z.reshape(batch, frames, *z.shape[-3:])
        z = z.permute(0, 1, 3, 4, 2).contiguous()
        return flowcast_model.normalize(z)

    return decode_fn, encode_fn
