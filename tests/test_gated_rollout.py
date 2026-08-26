"""Tests for the band-trust gated ensemble rollout.

Load-bearing properties:

* ``gate=None`` reproduces the production sampler bit-for-bit -- the gated
  path must be a strict superset of ``autoregressive_sample``, otherwise any
  A/B against the baseline is confounded by the rollout plumbing itself;
* per-member content isolation -- member m's gated condition never contains
  another member's field (rule 1 of the module docstring); consensus feedback
  is the pre-identified way this design would silently damage CRPS;
* the gate refuses to run without a calibrated mapping (rule 3).
"""

import os
import sys

import pytest
import torch

sys.path.append(os.getcwd())

from common.metrics.band_spectral import radial_band_masks, bandpass_decompose
from common.models.flowcast.gated_rollout import (
    BandGate,
    SpreadToAlpha,
    gated_autoregressive_ensemble,
)
from common.models.flowcast.rf_stdit import autoregressive_sample

BAND_EDGES = (0.0, 0.25, 0.5, 1.0)
NUM_BANDS = len(BAND_EDGES) - 1


class LinearFakeModel(torch.nn.Module):
    """Deterministic stand-in with the FlowCast forward signature."""

    def forward(self, x_t, t, cond, t_seq):
        del t, t_seq
        return 0.05 * x_t + 0.1 * cond


def make_latents(batch=2, frames=2, height=8, width=8, channels=1, seed=3):
    generator = torch.Generator().manual_seed(seed)
    return torch.randn(batch, frames, height, width, channels, generator=generator)


def identity_mapping():
    return SpreadToAlpha.identity(NUM_BANDS)


def calibrated_mapping(alpha_min=0.2):
    return SpreadToAlpha.from_calibration(
        q_lo=[0.0] * NUM_BANDS, q_hi=[1.0] * NUM_BANDS, alpha_min=alpha_min
    )


def decode_fn(latent):
    # (B, T, H, W, C=1) -> (B, T, H, W)
    return latent.squeeze(-1)


def encode_fn(pixels):
    return pixels.unsqueeze(-1)


def rollout_kwargs():
    return dict(
        input_length=2,
        output_length=6,
        num_train_timesteps=10,
        euler_steps=4,
    )


def test_spread_to_alpha_monotone_and_clamped():
    mapping = calibrated_mapping(alpha_min=0.25)
    spread = torch.tensor([0.0, 0.5, 2.0])
    alpha = mapping(spread)
    assert alpha[0] == pytest.approx(1.0)
    assert alpha[1] == pytest.approx(1.0 - 0.5 * 0.75)
    assert alpha[2] == pytest.approx(0.25)
    # monotone non-increasing in spread
    dense = mapping(torch.linspace(-1, 3, 50).unsqueeze(-1).expand(50, 3))
    diffs = dense[1:] - dense[:-1]
    assert bool((diffs <= 1e-12).all())


def test_spread_to_alpha_rejects_degenerate_quantiles():
    with pytest.raises(ValueError):
        SpreadToAlpha.from_calibration(q_lo=[0.5, 0.5], q_hi=[0.5, 1.0])


def test_gate_requires_mapping():
    with pytest.raises(ValueError):
        BandGate(band_edges=BAND_EDGES, spread_to_alpha=None)


def test_gate_band_count_mismatch_raises():
    with pytest.raises(ValueError):
        BandGate(
            band_edges=BAND_EDGES,
            spread_to_alpha=SpreadToAlpha.identity(NUM_BANDS + 1),
        )


def test_alpha_invariant_to_member_order():
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=calibrated_mapping())
    members = torch.randn(4, 2, 3, 16, 16, generator=torch.Generator().manual_seed(5))
    alpha = gate.alpha_from_members(members)
    permuted = members[[2, 0, 3, 1]]
    alpha_permuted = gate.alpha_from_members(permuted)
    assert torch.allclose(alpha, alpha_permuted, atol=1e-12)


def test_lowest_band_is_protected():
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=calibrated_mapping(0.0))
    members = 10.0 * torch.randn(
        4, 1, 2, 16, 16, generator=torch.Generator().manual_seed(6)
    )
    alpha = gate.alpha_from_members(members)
    assert bool((alpha[:, 0] == 1.0).all())


def test_apply_with_full_trust_is_identity():
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=identity_mapping())
    members = torch.randn(3, 2, 2, 16, 16, generator=torch.Generator().manual_seed(7))
    alpha = torch.ones(2, NUM_BANDS, dtype=torch.float64)
    mixed = gate.apply(members, alpha)
    assert torch.allclose(mixed, members, atol=1e-5)


def test_apply_zero_alpha_removes_band_content():
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=identity_mapping())
    masks = radial_band_masks(16, 16, BAND_EDGES)
    raw = torch.randn(16, 16, dtype=torch.float64,
                      generator=torch.Generator().manual_seed(8))
    band1_only = bandpass_decompose(raw, masks)[1]
    members = band1_only.to(torch.float32)[None, None, None].expand(2, 1, 1, -1, -1)
    alpha = torch.ones(1, NUM_BANDS, dtype=torch.float64)
    alpha[:, 1] = 0.0
    mixed = gate.apply(members.contiguous(), alpha)
    assert mixed.abs().max() < 1e-5


def test_apply_is_per_member_given_fixed_alpha():
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=identity_mapping())
    generator = torch.Generator().manual_seed(9)
    members = torch.randn(3, 1, 2, 16, 16, generator=generator)
    alpha = torch.full((1, NUM_BANDS), 0.5, dtype=torch.float64)
    mixed = gate.apply(members, alpha)
    # replace the *other* members entirely; member 0's output must not move
    altered = members.clone()
    altered[1:] = 999.0
    mixed_altered = gate.apply(altered, alpha)
    assert torch.allclose(mixed[0], mixed_altered[0], atol=1e-12)


def test_ungated_ensemble_matches_production_sampler_bitwise():
    model = LinearFakeModel()
    cond = make_latents()
    seeds = [11, 12, 13]

    baseline = []
    for seed in seeds:
        generator = torch.Generator().manual_seed(seed)
        baseline.append(
            autoregressive_sample(
                model=model, initial_cond=cond, generator=generator,
                **rollout_kwargs(),
            )
        )
    baseline = torch.stack(baseline, dim=0)

    generators = [torch.Generator().manual_seed(seed) for seed in seeds]
    gated = gated_autoregressive_ensemble(
        model=model, initial_cond=cond, num_members=len(seeds),
        member_generators=generators, gate=None, **rollout_kwargs(),
    )
    assert torch.equal(gated, baseline)


def test_identity_gate_with_lossless_codec_matches_baseline_closely():
    model = LinearFakeModel()
    cond = make_latents()
    seeds = [21, 22]

    baseline = []
    for seed in seeds:
        generator = torch.Generator().manual_seed(seed)
        baseline.append(
            autoregressive_sample(
                model=model, initial_cond=cond, generator=generator,
                **rollout_kwargs(),
            )
        )
    baseline = torch.stack(baseline, dim=0)

    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=identity_mapping())
    generators = [torch.Generator().manual_seed(seed) for seed in seeds]
    gated = gated_autoregressive_ensemble(
        model=model, initial_cond=cond, num_members=len(seeds),
        member_generators=generators, gate=gate,
        decode_fn=decode_fn, encode_fn=encode_fn, **rollout_kwargs(),
    )
    # alpha == 1 everywhere: only the FFT decompose/sum roundtrip separates
    # the two paths, so they agree to float tolerance but not bitwise
    assert torch.allclose(gated, baseline, atol=1e-4)
    assert gated.shape == baseline.shape


def test_gate_only_changes_later_chunks():
    model = LinearFakeModel()
    cond = make_latents()
    seeds = [31, 32]
    kwargs = rollout_kwargs()
    chunk = kwargs["input_length"]

    generators = [torch.Generator().manual_seed(seed) for seed in seeds]
    ungated = gated_autoregressive_ensemble(
        model=model, initial_cond=cond, num_members=2,
        member_generators=generators, gate=None, **kwargs,
    )

    gate = BandGate(
        band_edges=BAND_EDGES, spread_to_alpha=calibrated_mapping(alpha_min=0.0)
    )
    generators = [torch.Generator().manual_seed(seed) for seed in seeds]
    gated = gated_autoregressive_ensemble(
        model=model, initial_cond=cond, num_members=2,
        member_generators=generators, gate=gate,
        decode_fn=decode_fn, encode_fn=encode_fn, **kwargs,
    )
    # chunk 1 is sampled before any gating can act: identical
    assert torch.equal(gated[:, :, :chunk], ungated[:, :, :chunk])
    # later chunks are conditioned differently
    assert not torch.allclose(gated[:, :, chunk:], ungated[:, :, chunk:])


def test_gate_without_codec_raises():
    model = LinearFakeModel()
    cond = make_latents()
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=identity_mapping())
    with pytest.raises(ValueError):
        gated_autoregressive_ensemble(
            model=model, initial_cond=cond, num_members=2,
            gate=gate, **rollout_kwargs(),
        )


# ---- fixes from the adversarial review (2026-08-10) ----


def test_spread_to_alpha_rejects_nan_quantiles():
    with pytest.raises(ValueError):
        SpreadToAlpha.from_calibration(
            q_lo=[0.0, float("nan")], q_hi=[1.0, 2.0]
        )


def make_report(view=True, exclude_band=None):
    bands = []
    for j in range(NUM_BANDS):
        mapping = None if j == exclude_band else {"q_lo": 0.1 + j, "q_hi": 1.0 + j}
        bands.append({"band": j, "alpha_mapping": mapping})
    report = {"bands": bands, "deployable": bool(view)}
    report["view"] = {"height": 16, "width": 16} if view else None
    return report


def test_from_report_requires_view_fingerprint():
    with pytest.raises(ValueError):
        SpreadToAlpha.from_report(make_report(view=False))


def test_from_report_excluded_band_is_passthrough():
    mapping = SpreadToAlpha.from_report(make_report(exclude_band=2))
    assert not bool(mapping.active[2])
    spread = torch.full((1, NUM_BANDS), 1e6, dtype=torch.float64)
    alpha = mapping(spread)
    assert alpha[0, 2] == pytest.approx(1.0)  # inactive: never attenuated
    assert alpha[0, 1] == pytest.approx(mapping.alpha_min)


def test_gate_rejects_view_shape_mismatch():
    mapping = SpreadToAlpha.from_report(make_report())  # fingerprint 16x16
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=mapping)
    members = torch.rand(3, 1, 2, 32, 32)
    with pytest.raises(ValueError, match="do not transfer across views"):
        gate.alpha_from_members(members)


def test_gate_rejects_order_of_magnitude_scale_mismatch():
    # quantiles measured on a 0-90 view, runtime pixels on a 0-1 view:
    # spread is ~90x below the calibrated range and must fail loudly
    mapping = SpreadToAlpha.from_calibration(
        q_lo=[10.0] * NUM_BANDS, q_hi=[20.0] * NUM_BANDS,
        view_height=16, view_width=16,
    )
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=mapping)
    members = 0.01 * torch.randn(
        4, 1, 2, 16, 16, generator=torch.Generator().manual_seed(41)
    )
    with pytest.raises(ValueError, match="view/unit mismatch"):
        gate.alpha_from_members(members)


def test_gate_spread_view_crop_and_clamp_only_affect_trust():
    mapping = calibrated_mapping()
    gate_full = BandGate(band_edges=BAND_EDGES, spread_to_alpha=mapping)
    gate_view = BandGate(
        band_edges=BAND_EDGES,
        spread_to_alpha=calibrated_mapping(),
        spread_view_crop=(slice(2, -2), slice(2, -2)),
        spread_view_clamp=(0.0, 1.0),
    )
    members = torch.randn(4, 1, 2, 16, 16, generator=torch.Generator().manual_seed(42))
    alpha_full = gate_full.alpha_from_members(members)
    alpha_view = gate_view.alpha_from_members(members)
    assert not torch.allclose(alpha_full, alpha_view)  # trust view differs
    # ...but apply() always mixes the full field: same alpha -> same output
    fixed_alpha = torch.full((1, NUM_BANDS), 0.7, dtype=torch.float64)
    assert torch.allclose(
        gate_full.apply(members, fixed_alpha), gate_view.apply(members, fixed_alpha)
    )


def test_gate_telemetry_counts_decisions():
    mapping = calibrated_mapping()
    gate = BandGate(band_edges=BAND_EDGES, spread_to_alpha=mapping)
    members = torch.randn(4, 3, 2, 16, 16, generator=torch.Generator().manual_seed(43))
    gate.alpha_from_members(members)
    gate.alpha_from_members(members)
    telemetry = gate.telemetry()
    assert telemetry["decisions"] == 6  # 2 calls x batch 3
    for key in ("in_range_fraction", "below_fraction", "above_fraction"):
        assert len(telemetry[key]) == NUM_BANDS


def test_gate_none_matches_production_global_seed_protocol():
    """The production protocol is torch.manual_seed(idx*S+s) + generator=None.

    The gated path uses fresh torch.Generator objects.  This pins, on CPU,
    that the two seeding styles produce identical streams across >= 2
    batches (two batches catch a wrongly *held* generator carried across
    batches).  CUDA equivalence must be re-checked once before GPU A/Bs.
    """
    model = LinearFakeModel()
    num_members = 3
    kwargs = rollout_kwargs()

    for batch_idx in range(2):
        cond = make_latents(seed=100 + batch_idx)

        production = []
        for member in range(num_members):
            torch.manual_seed(batch_idx * num_members + member)
            production.append(
                autoregressive_sample(
                    model=model, initial_cond=cond, generator=None, **kwargs
                )
            )
        production = torch.stack(production, dim=0)

        generators = [
            torch.Generator().manual_seed(batch_idx * num_members + member)
            for member in range(num_members)
        ]
        gated = gated_autoregressive_ensemble(
            model=model, initial_cond=cond, num_members=num_members,
            member_generators=generators, gate=None, **kwargs,
        )
        assert torch.equal(gated, production)


def test_gated_outputs_are_raw_predictions_for_all_chunks(monkeypatch):
    """Outputs must be the raw sampler returns for EVERY chunk.

    A mutant that overwrites later chunks' outputs with the gated (trust-
    weighted) content passes the earlier only-changes-later-chunks test; this
    spy pins the frozen semantics bitwise: gating touches conditions only.
    """
    import common.models.flowcast.gated_rollout as module

    recorded = []
    original = module.sample_chunk_euler

    def spy(**call_kwargs):
        pred = original(**call_kwargs)
        recorded.append(pred.clone())
        return pred

    monkeypatch.setattr(module, "sample_chunk_euler", spy)

    model = LinearFakeModel()
    cond = make_latents()
    kwargs = rollout_kwargs()
    chunk = kwargs["input_length"]
    num_chunks = kwargs["output_length"] // chunk
    num_members = 2
    gate = BandGate(
        band_edges=BAND_EDGES, spread_to_alpha=calibrated_mapping(alpha_min=0.0)
    )
    generators = [torch.Generator().manual_seed(50 + m) for m in range(num_members)]
    out = module.gated_autoregressive_ensemble(
        model=model, initial_cond=cond, num_members=num_members,
        member_generators=generators, gate=gate,
        decode_fn=decode_fn, encode_fn=encode_fn, **kwargs,
    )
    assert len(recorded) == num_chunks * num_members
    for k in range(num_chunks):
        for m in range(num_members):
            assert torch.equal(
                out[m, :, k * chunk : (k + 1) * chunk],
                recorded[k * num_members + m],
            )


class FakeLatentDist:
    def __init__(self, value):
        self.value = value

    def mode(self):
        return self.value

    def sample(self):
        raise AssertionError(
            "codec must be deterministic: latent_dist.sample() draws from the "
            "global RNG and breaks member pairing"
        )


class FakeEncoded:
    def __init__(self, value):
        self.latent_dist = FakeLatentDist(value)


class FakeDecoded:
    def __init__(self, value):
        self.sample = value


class FakeAE:
    """Identity AE with the diffusers AutoencoderKL duck-type."""

    def encode(self, x):
        return FakeEncoded(x)

    def decode(self, z):
        return FakeDecoded(z)


class FakeFlowCast:
    def normalize(self, x):
        return (x - 0.5) / 2.0

    def denormalize(self, x):
        return x * 2.0 + 0.5


def test_build_codec_fns_roundtrip_and_determinism():
    from common.models.flowcast.gated_rollout import build_codec_fns

    decode, encode = build_codec_fns(
        FakeAE(), FakeFlowCast(), pixel_scale=90.0, normalized_autoencoder=True
    )
    latent = torch.rand(2, 3, 8, 8, 1)
    pixels = decode(latent)
    assert pixels.shape == (2, 3, 8, 8)
    # identity AE: decode is denormalize -> x90; encode inverts exactly, and
    # FakeLatentDist.sample() raising proves the mode() path is used
    back = encode(pixels)
    assert torch.allclose(back, latent, atol=1e-6)
