"""Rollout-Matched Lead--Flow Coupling utilities.

The module implements the training-only pieces described by RMLF:

1. an *anchored rollout bridge* obtained by noising a ground-truth previous
   chunk and denoising it with a frozen teacher.  The hypothesis is that it
   preserves the observed weather basin; that is what the R1/R2 pair plus the
   offline same-basin diagnostics are for, so it is not asserted here;
2. a configurable joint sampler over previous-chunk corruption, current Flow
   time, and within-chunk lead; and
3. clean/rollout condition mixing with an optional conservative latent gate.

Nothing in this module changes FlowCast inference.  With RMLF disabled, the
original teacher-forced objective and sampler are untouched.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch

from .schedule import build_sampling_timesteps


_VALID_CONDITION_MODES = {"bridge", "self_forcing"}
_VALID_COUPLING_MODES = {
    "independent",
    "diagonal",
    "grid_independent",
    "amplification_table",
}
_VALID_DIAGONAL_DIRECTIONS = {"same", "opposite"}
_VALID_MIX_GRANULARITIES = {"batch", "sample"}
_VALID_TEACHER_MODES = {"frozen", "ema"}
# Surfaces the R3 sampler is allowed to read from an estimator ``.npz``.
# ``interaction_signed_score`` is the default: it is the only one that is both
# de-confounded (neither main effect survives, so it cannot be reproduced by
# hard-timestep oversampling) and noise-gated.  The rest are ablations, listed
# from strongest to weakest control.
_VALID_TABLE_KEYS = {
    "interaction_signed_score",
    "interaction_gated",
    "interaction",
    "log_ratio",
    "amplification",
}
_VALID_MARGINAL_MODES = {"matched", "raw"}
# Provenance keys carried by an estimator .npz.  Keep in sync with the
# `provenance` dict in tools/estimate_rmlf_amplification.py -- T24 asserts the
# two agree, because a mismatch either drops a field silently or makes a
# correctly generated table unloadable.
_TABLE_PROVENANCE_FIELDS = (
    "sampler_surface_key",
    "sampler_temperature",
    "sampler_marginal_mode",
    "source_checkpoint_sha256",
    "source_checkpoint_path",
    "source_weight_key",
    "config_sha256",
    "git_commit",
    "bridge_steps",
    "num_train_timesteps",
    "precision_mode",
    "dataset_split",
    "dataset_manifest_sha256",
    "seed",
)
# Operator fields that must be present AND equal; absence is not tolerated,
# because "no record" cannot establish that the table describes this run's
# operator.
_TABLE_OPERATOR_FIELDS = ("bridge_steps", "num_train_timesteps")
_RNG_STREAM_OFFSETS = {
    "mask": 0,
    "plan": 1,
    "bridge": 2,
    "clean_t": 3,
}


@dataclass(frozen=True)
class RMLFConfig:
    """Configuration for rollout-matched training.

    ``condition_mode='bridge'`` starts the teacher from a noised version of
    the observed previous chunk, so at moderate corruption it is *expected* to
    stay in the observed future basin rather than pairing an arbitrary free
    rollout with an incompatible observed next chunk.  Whether it actually
    does is an empirical question -- R2 also differs from R1 in corruption
    magnitude, so `R2 > R1` alone does not establish the mechanism.

    ``condition_mode='self_forcing'`` is the deliberately stronger baseline:
    it starts from pure noise and therefore reproduces ordinary free-running
    self forcing, including its possible mode-mismatch failure.

    ``coupling_mode='amplification_table'`` is the full RMLF variant.  It
    expects an ``.npz`` file produced by ``tools/estimate_rmlf_amplification.py``
    containing ``a_centers``, ``tau_centers`` and the surface named by
    ``amplification_key`` (default ``interaction_signed_score``).
    """

    enabled: bool = False
    condition_mode: str = "bridge"
    rollout_probability: float = 0.5
    warmup_steps: int = 0
    # Anchor for the warmup ramp.  In a continuation the trainer restores the
    # parent's `global_step` (hundreds of thousands), so a ramp measured from
    # zero is already saturated on the first batch and the configured warmup
    # silently does nothing.  Set this to the parent checkpoint's global_step
    # to ramp over the first `warmup_steps` steps OF THE CONTINUATION; leave
    # both at 0 to deliberately start at full rollout probability.
    warmup_start_global_step: int = 0
    corruption_min: float = 0.05
    corruption_max: float = 0.65
    # Must equal sampling_params.euler_steps unless the reduced-fidelity
    # efficiency ablation is explicitly requested; the trainer enforces this.
    bridge_euler_steps: int = 10
    allow_reduced_bridge_fidelity: bool = False
    mix_granularity: str = "batch"
    max_relative_l2: Optional[float] = None
    relative_l2_floor: float = 0.10

    coupling_mode: str = "independent"
    coupling_strength: float = 0.75
    diagonal_direction: str = "same"
    lead_power: float = 0.0
    focus_lead_mass: float = 0.75
    amplification_table: Optional[str] = None
    # Which surface inside the estimator ``.npz`` drives the R3 sampler.
    # ``interaction_gated`` = the two-way residual (both main effects removed)
    # after a lower-confidence bound and an event-disjoint split-half sign
    # check.  The ungated ``interaction`` is unsafe as a sampler: with a truly
    # zero interaction, noise still makes ~half the cells positive and
    # clipping at zero converts that noise into a training signal.
    # ``log_ratio`` and ``amplification`` are ablations -- both keep a
    # monotone Flow-time component and can be explained as ordinary
    # hard-timestep oversampling.
    amplification_key: str = "interaction_signed_score"
    # ``matched`` = IPF the score kernel to fixed uniform (lead, a, tau)
    # marginals, so R3 differs from the grid_independent control ONLY in the
    # dependence structure.  ``raw`` reproduces the earlier positive-part
    # weighting and is an ablation: it changes all three marginals at once and
    # therefore cannot separate coupling from hard-region curriculum.
    marginal_mode: str = "matched"
    amplification_temperature: float = 1.0
    amplification_floor: float = 1.0e-6
    random_seed: int = 314159

    # ``frozen`` pins the rollout teacher to one immutable parent checkpoint
    # for the whole run, so the condition-error distribution the student is
    # trained against does not drift and is identical across R1/R2/R3.
    # ``ema`` restores the co-evolving student EMA and is kept only as an
    # ablation -- it answers a different question.
    teacher_mode: str = "frozen"
    teacher_checkpoint: Optional[str] = None
    teacher_checkpoint_type: str = "raw"
    # Escape hatch for a deliberate cross-model ablation only.  With it false
    # (the default) the trainer refuses to start unless the frozen teacher and
    # run_params.preload_model are the same file, and unless an R3 table was
    # measured on that same checkpoint.
    allow_teacher_parent_mismatch: bool = False

    def __post_init__(self) -> None:
        if self.condition_mode not in _VALID_CONDITION_MODES:
            raise ValueError(
                f"condition_mode must be one of {_VALID_CONDITION_MODES}; "
                f"got {self.condition_mode!r}."
            )
        if self.coupling_mode not in _VALID_COUPLING_MODES:
            raise ValueError(
                f"coupling_mode must be one of {_VALID_COUPLING_MODES}; "
                f"got {self.coupling_mode!r}."
            )
        if self.diagonal_direction not in _VALID_DIAGONAL_DIRECTIONS:
            raise ValueError(
                "diagonal_direction must be 'same' or 'opposite'; "
                f"got {self.diagonal_direction!r}."
            )
        if self.mix_granularity not in _VALID_MIX_GRANULARITIES:
            raise ValueError(
                f"mix_granularity must be one of {_VALID_MIX_GRANULARITIES}; "
                f"got {self.mix_granularity!r}."
            )
        if not 0.0 <= self.rollout_probability <= 1.0:
            raise ValueError("rollout_probability must lie in [0, 1].")
        if not 0.0 <= self.corruption_min <= self.corruption_max <= 1.0:
            raise ValueError(
                "corruption_min/corruption_max must satisfy "
                "0 <= min <= max <= 1."
            )
        if self.bridge_euler_steps < 1:
            raise ValueError("bridge_euler_steps must be at least 1.")
        if not 0.0 <= self.coupling_strength <= 1.0:
            raise ValueError("coupling_strength must lie in [0, 1].")
        if self.lead_power < 0.0:
            raise ValueError("lead_power must be non-negative.")
        if not 0.0 <= self.focus_lead_mass <= 1.0:
            raise ValueError("focus_lead_mass must lie in [0, 1].")
        if self.amplification_temperature <= 0.0:
            raise ValueError("amplification_temperature must be positive.")
        if self.amplification_floor < 0.0:
            raise ValueError("amplification_floor must be non-negative.")
        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative.")
        if self.warmup_steps < 0:
            raise ValueError("warmup_steps must be non-negative.")
        if self.warmup_start_global_step < 0:
            raise ValueError("warmup_start_global_step must be non-negative.")
        if self.max_relative_l2 is not None and self.max_relative_l2 <= 0.0:
            raise ValueError("max_relative_l2 must be positive or None.")
        if self.relative_l2_floor <= 0.0:
            raise ValueError("relative_l2_floor must be positive.")
        if (
            self.coupling_mode in {"amplification_table", "grid_independent"}
            and not self.amplification_table
        ):
            raise ValueError(
                f"coupling_mode={self.coupling_mode!r} requires "
                "amplification_table: the control arm must sample the SAME "
                "discrete grid as the coupled arm."
            )
        if self.marginal_mode not in _VALID_MARGINAL_MODES:
            raise ValueError(
                f"marginal_mode must be one of {sorted(_VALID_MARGINAL_MODES)}; "
                f"got {self.marginal_mode!r}."
            )
        if self.amplification_key not in _VALID_TABLE_KEYS:
            raise ValueError(
                f"amplification_key must be one of {sorted(_VALID_TABLE_KEYS)}; "
                f"got {self.amplification_key!r}."
            )
        if self.teacher_mode not in _VALID_TEACHER_MODES:
            raise ValueError(
                f"teacher_mode must be one of {sorted(_VALID_TEACHER_MODES)}; "
                f"got {self.teacher_mode!r}."
            )
        if self.teacher_checkpoint_type not in {"raw", "ema"}:
            raise ValueError(
                "teacher_checkpoint_type must be 'raw' or 'ema'; "
                f"got {self.teacher_checkpoint_type!r}."
            )

    def validate_for_training(self) -> None:
        """Checks that only make sense when a real run is being launched.

        Kept out of ``__post_init__`` so unit tests can build a controller and
        hand it a teacher module directly, without inventing a checkpoint path.
        The trainer calls this before the first step.
        """
        if not self.enabled:
            return
        if self.teacher_mode == "frozen" and not self.teacher_checkpoint:
            raise ValueError(
                "teacher_mode='frozen' requires teacher_checkpoint: an absolute "
                "path to the immutable parent checkpoint shared by every arm."
            )
        if (
            self.condition_mode == "self_forcing"
            and self.coupling_mode != "independent"
        ):
            raise ValueError(
                "self_forcing is an R1 baseline and must use "
                "coupling_mode='independent'; diagonal/table coupling is only "
                "defined for the bridge corruption variable."
            )


@dataclass
class RMLFPlan:
    """Per-batch training plan for a later autoregressive chunk."""

    corruption: torch.Tensor  # (B,), normalized Flow time in [0, 1]
    target_t: torch.Tensor  # (B,), integer Flow timestep in [1, N-1]
    lead_weights: torch.Tensor  # (B, T), each row has mean one
    focus_lead: torch.Tensor  # (B,), -1 when no discrete lead is selected


@dataclass
class RMLFCondition:
    """Mixed condition and diagnostics returned by ``build_condition``."""

    condition: torch.Tensor
    rollout_mask: torch.Tensor  # (B,) bool, after the latent gate
    bridge_accepted: torch.Tensor  # (B,) bool
    relative_l2: torch.Tensor  # (B,)


class RMLFController:
    """Samples RMLF plans and builds rollout-matched previous-chunk states."""

    def __init__(self, config: RMLFConfig):
        self.config = config
        self._amplification: Optional[torch.Tensor] = None
        self._a_centers: Optional[torch.Tensor] = None
        self._tau_centers: Optional[torch.Tensor] = None
        self._generators: Dict[tuple[str, str], torch.Generator] = {}
        self._pending_stream_states: Dict[str, torch.Tensor] = {}
        self._table_floor_share: Optional[float] = None
        self._table_source_sha256: Optional[str] = None
        self._ipf_diagnostics: Dict[tuple, Dict[str, float]] = {}
        self._table_provenance: Dict[str, Any] = {}
        self._joint_cache: Dict[tuple, torch.Tensor] = {}
        if config.coupling_mode in {"amplification_table", "grid_independent"}:
            self._load_amplification_table(Path(str(config.amplification_table)))

    def generator(
        self, device: torch.device, stream: str = "plan"
    ) -> torch.Generator:
        """Return a checkpointable RMLF RNG stream.

        Mask, joint-plan, bridge-noise and clean-anchor timestep draws use
        separate streams.  Consequently, changing the coupling sampler does
        not silently change the rollout masks or bridge noise in an ablation.
        None of these streams perturb the original RF objective's global RNG.
        """
        if stream not in _RNG_STREAM_OFFSETS:
            raise ValueError(
                f"Unknown RMLF RNG stream {stream!r}; expected one of "
                f"{sorted(_RNG_STREAM_OFFSETS)}."
            )
        key = (str(device), stream)
        if key not in self._generators:
            gen = torch.Generator(device=device)
            # Every DDP rank deliberately uses the same RMLF RNG stream.  The
            # distributed sampler already gives each rank different events;
            # matched corruption plans reduce an unnecessary source of run
            # variance and let the compact rank-0 checkpoint restore all ranks.
            gen.manual_seed(
                int(self.config.random_seed)
                + int(_RNG_STREAM_OFFSETS[stream]) * 1_000_003
            )
            if stream in self._pending_stream_states:
                gen.set_state(self._pending_stream_states.pop(stream))
            self._generators[key] = gen
        return self._generators[key]

    def state_dict(self) -> Dict[str, Any]:
        stream_states = {
            stream: generator.get_state().cpu()
            for (_, stream), generator in self._generators.items()
        }
        stream_states.update(
            {key: value.cpu() for key, value in self._pending_stream_states.items()}
        )
        return {
            "random_seed": int(self.config.random_seed),
            "warmup_steps": int(self.config.warmup_steps),
            "warmup_start_global_step": int(
                self.config.warmup_start_global_step
            ),
            # Stream-only keys are intentional: a rank-0 checkpoint is
            # broadcast to every DDP rank, whose local device names differ.
            "stream_states": stream_states,
        }

    def load_state_dict(self, state: Optional[Dict[str, Any]]) -> None:
        if not state:
            return
        saved_seed = int(state.get("random_seed", self.config.random_seed))
        if saved_seed != int(self.config.random_seed):
            raise ValueError(
                "RMLF random_seed differs from checkpoint: "
                f"config={self.config.random_seed}, checkpoint={saved_seed}."
            )
        # A restart that moves the warmup schedule would give this arm a
        # different rollout-probability trajectory from its siblings.
        for field in ("warmup_steps", "warmup_start_global_step"):
            if field not in state:
                continue
            saved = int(state[field])
            current = int(getattr(self.config, field))
            if saved != current:
                raise ValueError(
                    f"RMLF {field} differs from checkpoint: "
                    f"config={current}, checkpoint={saved}."
                )
        raw_states = state.get("stream_states", {})
        # Backward-compatible handling for the early single-stream draft.
        if not raw_states and state.get("generator_states"):
            legacy = state["generator_states"]
            first = next(iter(legacy.values()), None)
            if first is not None:
                raw_states = {"plan": first}
        self._pending_stream_states = {
            str(key): value.detach().cpu() for key, value in raw_states.items()
        }
        for (_, stream), generator in self._generators.items():
            if stream in self._pending_stream_states:
                generator.set_state(self._pending_stream_states.pop(stream))

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled)

    def _load_amplification_table(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"RMLF amplification table not found: {path}")
        # The control arm needs the GRID, not the surface: it samples the same
        # discrete (lead, a, tau) bins with the same uniform marginals, and
        # differs from the coupled arm only in the dependence structure.
        grid_only = self.config.coupling_mode == "grid_independent"
        key = str(self.config.amplification_key)
        with np.load(path, allow_pickle=False) as data:
            required = {"a_centers", "tau_centers"} | (set() if grid_only else {key})
            missing = required.difference(data.files)
            if missing:
                raise ValueError(
                    f"RMLF table {path} is missing keys: {sorted(missing)}. "
                    "Regenerate it with tools/estimate_rmlf_amplification.py; "
                    "tables produced before the interaction rewrite only carry "
                    "the raw 'amplification' surface, which is confounded with "
                    "the Flow-time main effect."
                )
            amplification = (
                np.zeros(
                    (len(data["a_centers"]), len(data["tau_centers"])),
                    dtype=np.float64,
                )
                if grid_only
                else np.asarray(data[key], dtype=np.float64)
            )
            a_centers = np.asarray(data["a_centers"], dtype=np.float64)
            tau_centers = np.asarray(data["tau_centers"], dtype=np.float64)
            self._table_provenance = {
                name: str(np.asarray(data[name]).reshape(-1)[0])
                # Must stay in sync with the provenance dict written by
                # tools/estimate_rmlf_amplification.py.  A field the estimator
                # writes but this list omits is silently dropped here and then
                # reported as "missing" by verify_table_provenance below.
                for name in _TABLE_PROVENANCE_FIELDS
                if name in data.files
            }
            self._table_source_sha256 = self._table_provenance.get(
                "source_checkpoint_sha256"
            )

        if amplification.ndim not in (2, 3, 4):
            raise ValueError(
                f"{key} must have shape (A,Q), (T,A,Q), or "
                f"(C,T,A,Q); got {amplification.shape}."
            )
        if a_centers.ndim != 1 or tau_centers.ndim != 1:
            raise ValueError("a_centers and tau_centers must be one-dimensional.")
        if amplification.shape[-2:] != (len(a_centers), len(tau_centers)):
            raise ValueError(
                "Amplification table bins do not match centers: "
                f"{amplification.shape[-2:]} vs "
                f"({len(a_centers)}, {len(tau_centers)})."
            )
        if not np.all(np.isfinite(amplification)):
            raise ValueError(f"{key} contains NaN or infinite values.")
        if not np.all((0.0 <= a_centers) & (a_centers <= 1.0)):
            raise ValueError("a_centers must lie in [0, 1].")
        if not np.all((0.0 < tau_centers) & (tau_centers <= 1.0)):
            raise ValueError("tau_centers must lie in (0, 1].")
        if len(a_centers) > 1 and not np.all(np.diff(a_centers) > 0):
            raise ValueError("a_centers must be strictly increasing.")
        if len(tau_centers) > 1 and not np.all(np.diff(tau_centers) > 0):
            raise ValueError("tau_centers must be strictly increasing.")

        # A surface whose positive part is dominated by the numerical floor
        # carries no coupling signal: sampling from it is uniform sampling with
        # extra machinery, and any R3-vs-R2 difference would come from the
        # bin grid rather than from lead--Flow structure.  Refuse it loudly
        # instead of running an experiment that cannot answer its own question.
        positive = np.clip(amplification, 0.0, None)
        floor = float(self.config.amplification_floor)
        signal_mass = float(positive.sum())
        floor_mass = floor * positive.size
        if grid_only:
            # Uniform by construction; there is no surface to interrogate.
            self._table_floor_share = 1.0
        elif self.config.marginal_mode == "matched":
            # A zero score kernel IPFs to exactly the uniform joint, i.e. R3
            # collapses onto the grid_independent control.  That is the
            # correct behaviour, but it is not an experiment -- say so.
            if float(np.abs(amplification).sum()) <= 0.0:
                raise ValueError(
                    f"RMLF table {path} key {key!r} is identically zero: no "
                    "cell survived the interaction gates, so the IPF joint is "
                    "exactly the grid_independent control and R3 cannot differ "
                    "from it.  This is the documented R3 No-Go: stop at R2."
                )
        elif signal_mass <= 0.0:
            raise ValueError(
                f"RMLF table {path} key {key!r} has no positive mass: the "
                "interaction residual is everywhere <= 0, i.e. the rollout "
                "penalty is additive in (corruption, Flow time) and there is "
                "no lead--Flow coupling to exploit.  This is the documented "
                "R3 No-Go: stop at R2."
            )
        elif signal_mass < floor_mass:
            raise ValueError(
                f"RMLF table {path} key {key!r} is floor-dominated "
                f"(positive mass {signal_mass:.3e} < floor mass "
                f"{floor_mass:.3e}); R3 would degenerate to uniform sampling. "
                "Inspect the interaction heat map before running R3."
            )
        if not grid_only and self.config.marginal_mode == "raw":
            self._table_floor_share = floor_mass / (signal_mass + floor_mass)

        self._amplification = torch.from_numpy(amplification)
        self._a_centers = torch.from_numpy(a_centers)
        self._tau_centers = torch.from_numpy(tau_centers)

    def verify_table_provenance(
        self,
        teacher_sha256: Optional[str],
        *,
        num_train_timesteps: Optional[int] = None,
        precision_mode: Optional[str] = None,
    ) -> None:
        """Refuse an R3 table that was not measured on the frozen teacher.

        The surface describes ONE model's rollout errors.  Sampling training
        difficulty from a surface measured on some other checkpoint silently
        breaks the link between what was measured and what is being trained.
        """
        if self.config.coupling_mode not in {
            "amplification_table",
            "grid_independent",
        }:
            return
        # NOTE: `allow_teacher_parent_mismatch` is deliberately NOT honoured
        # here.  It exists to permit `student parent != frozen teacher` for a
        # cross-model ablation.  Even then the table must still have been
        # measured ON THIS TEACHER with THIS operator -- otherwise the surface
        # describes a model that appears nowhere in the run.  The trainer skips
        # only the teacher-vs-parent path comparison.
        if not self._table_source_sha256:
            raise ValueError(
                f"RMLF table {self.config.amplification_table} carries no "
                "source_checkpoint_sha256.  Regenerate it with the current "
                "tools/estimate_rmlf_amplification.py, which stamps the "
                "provenance of the checkpoint it measured."
            )
        if not teacher_sha256:
            raise ValueError(
                "Cannot verify RMLF table provenance: no teacher checkpoint "
                "digest was supplied."
            )
        if self._table_source_sha256 != teacher_sha256:
            raise ValueError(
                "RMLF table was measured on a DIFFERENT checkpoint than the "
                "frozen teacher.\n"
                f"  table  source sha256: {self._table_source_sha256}\n"
                f"  teacher       sha256: {teacher_sha256}\n"
                f"  table path          : {self.config.amplification_table}\n"
                f"  table source path   : "
                f"{self._table_provenance.get('source_checkpoint_path', '<unrecorded>')}"
            )

        # A file hash is not enough.  One .pt routinely holds BOTH
        # `model_state_dict` and `ema_model_state_dict`, so a table measured on
        # the EMA and a teacher running the raw weights have identical file
        # digests and would sail through the check above -- while describing a
        # different model's rollout errors.
        expected = (
            {"ema_model_state_dict"}
            if self.config.teacher_checkpoint_type == "ema"
            else {"model_state_dict", "model"}
        )
        weight_key = self._table_provenance.get("source_weight_key")
        if not weight_key:
            raise ValueError(
                f"RMLF table {self.config.amplification_table} carries no "
                "source_weight_key; regenerate it so the raw/EMA choice is "
                "recorded."
            )
        if weight_key not in expected:
            raise ValueError(
                "RMLF table measured the wrong weights inside the parent "
                "checkpoint.\n"
                f"  table source_weight_key   : {weight_key}\n"
                f"  teacher_checkpoint_type   : "
                f"{self.config.teacher_checkpoint_type} (expects one of "
                f"{sorted(expected)})"
            )

        # Treatment definition.  The operator checks below establish that the
        # table describes this run's bridge; these establish that it describes
        # this run's SAMPLER.  Without them a table -- and the copula report
        # that was reviewed alongside it -- could be generated at one
        # temperature and then used to train at another: IPF still converges,
        # the marginals still match the control, and nothing indicates that the
        # treatment strength that was approved is not the one being applied.
        if self.config.coupling_mode == "amplification_table":
            for field, current in (
                ("sampler_surface_key", self.config.amplification_key),
                ("sampler_marginal_mode", self.config.marginal_mode),
            ):
                recorded = self._table_provenance.get(field)
                if recorded is None:
                    raise ValueError(
                        f"RMLF table {self.config.amplification_table} carries "
                        f"no {field}; regenerate it with the current "
                        "tools/estimate_rmlf_amplification.py."
                    )
                if recorded != str(current):
                    raise ValueError(
                        f"RMLF table was built for {field}={recorded!r} but "
                        f"this run uses {str(current)!r}.  Re-run the estimator "
                        "with the config you intend to train, so the copula "
                        "report describes the treatment being applied."
                    )
            recorded_temperature = self._table_provenance.get(
                "sampler_temperature"
            )
            if recorded_temperature is None:
                raise ValueError(
                    f"RMLF table {self.config.amplification_table} carries no "
                    "sampler_temperature; regenerate it."
                )
            if not math.isclose(
                float(recorded_temperature),
                float(self.config.amplification_temperature),
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    "RMLF table was built at amplification_temperature="
                    f"{recorded_temperature} but this run uses "
                    f"{self.config.amplification_temperature}.  The joint would "
                    "be re-fitted at the new temperature, so the reviewed "
                    "copula strength (TV / KL / density ratio / MI) would not "
                    "describe the treatment actually applied.  Re-run the "
                    "estimator and re-read the report before changing it."
                )
        elif self.config.coupling_mode == "grid_independent":
            # The control reads only the grid, so it does not have to match the
            # coupled arm's sampler settings -- but the table must still be one
            # a coupled arm could use, or the two arms are not sharing a grid.
            for field in (
                "sampler_surface_key",
                "sampler_temperature",
                "sampler_marginal_mode",
            ):
                if self._table_provenance.get(field) is None:
                    raise ValueError(
                        f"RMLF table {self.config.amplification_table} carries "
                        f"no {field}; regenerate it so the control and the "
                        "coupled arm are provably reading the same table."
                    )

        # The surface is specific to the operator that produced it.  A table
        # measured on a different Flow-time discretization maps (a, tau) onto
        # different integer timesteps; one measured in fp32 while training runs
        # the bridge under autocast describes a slightly different operator --
        # and this method exists precisely to estimate a fine-grained surface.
        if precision_mode is not None:
            recorded_precision = self._table_provenance.get("precision_mode")
            if recorded_precision is None:
                raise ValueError(
                    f"RMLF table {self.config.amplification_table} carries no "
                    "precision_mode; regenerate it so the fp32/autocast choice "
                    "is recorded."
                )
            if recorded_precision != precision_mode:
                raise ValueError(
                    "RMLF table was measured at a different precision than "
                    "training uses.\n"
                    f"  table precision   : {recorded_precision}\n"
                    f"  training precision: {precision_mode}\n"
                    "Re-run the estimator with a matching --fp16 setting."
                )
        for field, current in (
            ("bridge_steps", self.config.bridge_euler_steps),
            ("num_train_timesteps", num_train_timesteps),
        ):
            if current is None:
                continue
            recorded = self._table_provenance.get(field)
            if recorded is None:
                raise ValueError(
                    f"RMLF table {self.config.amplification_table} carries no "
                    f"{field}; regenerate it with the current "
                    "tools/estimate_rmlf_amplification.py.  An unrecorded "
                    "operator cannot be shown to match this run's."
                )
            if int(recorded) != int(current):
                raise ValueError(
                    f"RMLF table {field}={recorded} but the run uses "
                    f"{current}; the surface describes a different operator "
                    "than the one being trained."
                )

    @property
    def table_provenance(self) -> Dict[str, Any]:
        return dict(self._table_provenance)

    @property
    def ipf_diagnostics(self) -> Dict[tuple, Dict[str, float]]:
        """Per-transition IPF convergence, populated lazily by sampling."""
        return dict(self._ipf_diagnostics)

    def effective_rollout_probability(self, global_step: int) -> float:
        """Rollout probability ramped over the CONTINUATION, not all of time.

        ``global_step`` is restored from the parent checkpoint, so measuring
        the ramp from zero would leave it saturated from the very first batch.
        The ramp therefore runs over ``global_step - warmup_start_global_step``.
        """
        p = float(self.config.rollout_probability)
        warmup = int(self.config.warmup_steps)
        if warmup <= 0:
            return p
        local_step = max(
            0, int(global_step) - int(self.config.warmup_start_global_step)
        )
        return p * min(1.0, float(local_step) / float(warmup))

    @staticmethod
    def _rand(
        shape: tuple[int, ...],
        *,
        device: torch.device,
        dtype: torch.dtype,
        generator: Optional[torch.Generator],
    ) -> torch.Tensor:
        return torch.rand(shape, device=device, dtype=dtype, generator=generator)

    def _base_lead_weights(
        self,
        batch_size: int,
        chunk_length: int,
        *,
        device: torch.device,
        dtype: torch.dtype,
    ) -> torch.Tensor:
        if self.config.lead_power == 0.0:
            return torch.ones(batch_size, chunk_length, device=device, dtype=dtype)
        lead = torch.arange(
            1, chunk_length + 1, device=device, dtype=dtype
        ) / float(chunk_length)
        weights = lead.pow(float(self.config.lead_power))
        weights = weights / weights.mean().clamp_min(torch.finfo(dtype).eps)
        return weights.unsqueeze(0).expand(batch_size, -1).clone()

    def sample_plan(
        self,
        *,
        batch_size: int,
        chunk_index: int,
        chunk_length: int,
        num_train_timesteps: int,
        device: torch.device,
        dtype: torch.dtype,
        generator: Optional[torch.Generator] = None,
    ) -> RMLFPlan:
        """Sample corruption, target Flow time and lead weighting.

        ``chunk_index`` is one-based and denotes the *current* target chunk.
        The first chunk is not rollout-conditioned; callers should invoke this
        method only for ``chunk_index >= 2``.
        """
        if batch_size < 1 or chunk_length < 1:
            raise ValueError("batch_size and chunk_length must be positive.")
        if num_train_timesteps < 2:
            raise ValueError("num_train_timesteps must be at least 2.")
        if chunk_index < 2:
            raise ValueError("RMLF plans are only defined for chunk_index >= 2.")

        if generator is None:
            generator = self.generator(device, "plan")
        mode = self.config.coupling_mode
        focus = torch.full(
            (batch_size,), -1, device=device, dtype=torch.long
        )

        if mode in {"amplification_table", "grid_independent"}:
            assert self._a_centers is not None
            assert self._tau_centers is not None
            joint = self._joint_distribution(chunk_index, chunk_length)
            flat = joint.reshape(-1).to(device=device, dtype=torch.float64)
            if not torch.isfinite(flat).all() or float(flat.sum()) <= 0.0:
                raise ValueError("RMLF joint sampling table has no positive mass.")
            table = joint
            indices = torch.multinomial(
                flat / flat.sum(),
                batch_size,
                replacement=True,
                generator=generator,
            )
            n_a = table.shape[-2]
            n_tau = table.shape[-1]
            focus = torch.div(indices, n_a * n_tau, rounding_mode="floor")
            remainder = indices % (n_a * n_tau)
            a_idx = torch.div(remainder, n_tau, rounding_mode="floor")
            tau_idx = remainder % n_tau
            corruption = self._a_centers.to(device=device, dtype=dtype)[a_idx]
            tau = self._tau_centers.to(device=device, dtype=dtype)[tau_idx]
            lead_weights = (
                (1.0 - float(self.config.focus_lead_mass))
                * torch.ones(batch_size, chunk_length, device=device, dtype=dtype)
            )
            one_hot = torch.nn.functional.one_hot(
                focus.clamp(0, chunk_length - 1), num_classes=chunk_length
            ).to(dtype=dtype)
            lead_weights = lead_weights + (
                float(self.config.focus_lead_mass) * float(chunk_length) * one_hot
            )
        else:
            u_a = self._rand(
                (batch_size,), device=device, dtype=dtype, generator=generator
            )
            corruption = float(self.config.corruption_min) + u_a * (
                float(self.config.corruption_max) - float(self.config.corruption_min)
            )
            u_tau = self._rand(
                (batch_size,), device=device, dtype=dtype, generator=generator
            )
            if mode == "diagonal":
                anchor = (
                    corruption
                    if self.config.diagonal_direction == "same"
                    else 1.0 - corruption
                )
                strength = float(self.config.coupling_strength)
                tau = strength * anchor + (1.0 - strength) * u_tau
            else:
                tau = u_tau
            lead_weights = self._base_lead_weights(
                batch_size, chunk_length, device=device, dtype=dtype
            )

        target_t = torch.round(tau * float(num_train_timesteps - 1)).long()
        target_t = target_t.clamp(1, num_train_timesteps - 1)
        return RMLFPlan(
            corruption=corruption.clamp(0.0, 1.0),
            target_t=target_t,
            lead_weights=lead_weights,
            focus_lead=focus,
        )

    def _joint_distribution(
        self, chunk_index: int, chunk_length: int
    ) -> torch.Tensor:
        """(lead, a, tau) sampling distribution, cached per transition.

        ``grid_independent`` -> exactly uniform on the grid.  This is the
        control R3 must beat: same bins, same marginals, no dependence.

        ``amplification_table`` + ``marginal_mode='matched'`` -> the score
        kernel ``exp(S / T)`` IPF'd onto the SAME uniform marginals.  R3 then
        differs from the control only in the copula, so a win cannot be
        explained by "trained more on hard leads / hard timesteps / hard
        corruption".  A score with no interaction IPFs back to the uniform
        joint, i.e. R3 degenerates onto the control exactly as it should.

        ``marginal_mode='raw'`` -> the earlier positive-part weighting, kept as
        an ablation that deliberately moves all three marginals.
        """
        cache_key = (chunk_index, chunk_length, self.config.marginal_mode)
        cached = self._joint_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.config.coupling_mode == "grid_independent":
            n_a = int(self._a_centers.numel())
            n_tau = int(self._tau_centers.numel())
            joint = torch.full(
                (chunk_length, n_a, n_tau),
                1.0 / float(chunk_length * n_a * n_tau),
                dtype=torch.float64,
            )
            self._joint_cache[cache_key] = joint
            return joint

        table = self._select_table_slice(chunk_index, chunk_length).to(
            dtype=torch.float64
        )
        fitted, diagnostics = build_joint_from_surface(
            table.numpy(),
            marginal_mode=self.config.marginal_mode,
            temperature=self.config.amplification_temperature,
            floor=self.config.amplification_floor,
            return_diagnostics=True,
        )
        self._ipf_diagnostics[cache_key] = diagnostics
        joint = torch.from_numpy(fitted)
        self._joint_cache[cache_key] = joint
        return joint

    def _select_table_slice(
        self, chunk_index: int, chunk_length: int
    ) -> torch.Tensor:
        assert self._amplification is not None
        table = self._amplification
        if table.ndim == 2:
            table = table.unsqueeze(0).expand(chunk_length, -1, -1)
        elif table.ndim == 3:
            if table.shape[0] != chunk_length:
                raise ValueError(
                    f"Table lead dimension {table.shape[0]} does not match "
                    f"chunk_length={chunk_length}."
                )
        else:
            transition_index = chunk_index - 2
            if transition_index >= table.shape[0]:
                raise ValueError(
                    f"Table has {table.shape[0]} chunk transitions but "
                    f"chunk_index={chunk_index} requests transition "
                    f"{transition_index}."
                )
            table = table[transition_index]
            if table.shape[0] != chunk_length:
                raise ValueError(
                    f"Table lead dimension {table.shape[0]} does not match "
                    f"chunk_length={chunk_length}."
                )
        return table

    def sample_rollout_mask(
        self,
        batch_size: int,
        *,
        global_step: int,
        device: torch.device,
        generator: Optional[torch.Generator] = None,
    ) -> torch.Tensor:
        if generator is None:
            generator = self.generator(device, "mask")
        p = self.effective_rollout_probability(global_step)
        if p <= 0.0:
            return torch.zeros(batch_size, device=device, dtype=torch.bool)
        if p >= 1.0:
            return torch.ones(batch_size, device=device, dtype=torch.bool)
        if self.config.mix_granularity == "batch":
            draw = torch.rand((), device=device, generator=generator) < p
            return torch.full(
                (batch_size,), bool(draw.item()), device=device, dtype=torch.bool
            )
        return torch.rand(batch_size, device=device, generator=generator) < p

    @torch.no_grad()
    def build_condition(
        self,
        *,
        teacher_model: torch.nn.Module,
        clean_previous_chunk: torch.Tensor,
        teacher_condition: torch.Tensor,
        generated_chunk_index: int,
        corruption: torch.Tensor,
        rollout_mask: torch.Tensor,
        num_train_timesteps: int,
        noise: Optional[torch.Tensor] = None,
    ) -> RMLFCondition:
        """Create a clean/rollout mixture for a later target chunk.

        ``generated_chunk_index`` is the one-based index of the previous chunk
        being generated (1 when constructing the condition for target chunk 2).
        The returned tensor is detached by construction.
        """
        batch_size = clean_previous_chunk.shape[0]
        if corruption.shape != (batch_size,):
            raise ValueError(
                f"corruption must have shape ({batch_size},); "
                f"got {tuple(corruption.shape)}."
            )
        if rollout_mask.shape != (batch_size,):
            raise ValueError(
                f"rollout_mask must have shape ({batch_size},); "
                f"got {tuple(rollout_mask.shape)}."
            )
        if not torch.any(rollout_mask):
            zeros = torch.zeros(
                batch_size,
                device=clean_previous_chunk.device,
                dtype=clean_previous_chunk.dtype,
            )
            return RMLFCondition(
                condition=clean_previous_chunk.detach(),
                rollout_mask=rollout_mask,
                bridge_accepted=torch.ones_like(rollout_mask),
                relative_l2=zeros,
            )

        effective_corruption = corruption
        if self.config.condition_mode == "self_forcing":
            effective_corruption = torch.ones_like(corruption)

        if noise is None:
            noise = torch.randn(
                clean_previous_chunk.shape,
                device=clean_previous_chunk.device,
                dtype=clean_previous_chunk.dtype,
                generator=self.generator(clean_previous_chunk.device, "bridge"),
            )
        rollout = sample_rollout_bridge(
            model=teacher_model,
            x_start=clean_previous_chunk,
            cond=teacher_condition,
            chunk_idx=generated_chunk_index,
            corruption=effective_corruption,
            num_train_timesteps=num_train_timesteps,
            euler_steps=int(self.config.bridge_euler_steps),
            noise=noise,
        )
        relative_l2 = relative_l2_per_sample(
            rollout,
            clean_previous_chunk,
            floor=float(self.config.relative_l2_floor),
        )
        accepted = torch.ones_like(rollout_mask)
        if self.config.max_relative_l2 is not None:
            accepted = relative_l2 <= float(self.config.max_relative_l2)
        final_mask = rollout_mask & accepted
        view_shape = (batch_size,) + (1,) * (clean_previous_chunk.ndim - 1)
        condition = torch.where(
            final_mask.view(view_shape), rollout, clean_previous_chunk
        ).detach()
        return RMLFCondition(
            condition=condition,
            rollout_mask=final_mask,
            bridge_accepted=accepted,
            relative_l2=relative_l2,
        )


def relative_l2_per_sample(
    candidate: torch.Tensor,
    reference: torch.Tensor,
    *,
    floor: float = 0.10,
) -> torch.Tensor:
    """Scale-stabilized relative RMS error for the conservative bridge gate."""
    if candidate.shape != reference.shape:
        raise ValueError(
            f"candidate/reference shapes differ: {candidate.shape} vs {reference.shape}"
        )
    reduce_dims = tuple(range(1, candidate.ndim))
    numerator = (candidate - reference).float().pow(2).mean(dim=reduce_dims).sqrt()
    denominator = reference.float().pow(2).mean(dim=reduce_dims).sqrt()
    denominator = denominator.clamp_min(float(floor))
    return (numerator / denominator).to(dtype=reference.dtype)


@torch.no_grad()
def sample_rollout_bridge(
    *,
    model: torch.nn.Module,
    x_start: torch.Tensor,
    cond: torch.Tensor,
    chunk_idx: int,
    corruption: torch.Tensor,
    num_train_timesteps: int,
    euler_steps: int,
    noise: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    """Denoise a noised observed chunk from an arbitrary per-sample Flow time.

    For corruption ``a``, the initial state follows the exact FlowCast training
    interpolation ``z_a = a * eps + (1-a) * x_start``.  The teacher then
    integrates from ``a`` to zero.  ``a=0`` is exactly teacher forcing, whereas
    ``a=1`` is ordinary free-running self forcing.

    The integration grid is the *deployment* grid: the same
    ``build_sampling_timesteps(num_train_timesteps, euler_steps)`` boundaries
    used by ``sample_chunk_euler``, clamped per sample to ``[0, start_t]``.
    Two consequences matter for the ablation:

    * with ``euler_steps`` equal to the inference setting, ``a=1`` reproduces
      ``sample_chunk_euler`` *exactly* (given the same noise), so R1 really is
      the deployment condition rather than a coarser proxy;
    * a partially corrupted bridge is then literally the deployment sampler
      resumed midway, and grid points above ``start_t`` collapse to zero-length
      steps instead of silently rescaling to a different solver fidelity.
    """
    if num_train_timesteps < 2:
        raise ValueError("num_train_timesteps must be at least 2.")
    if euler_steps < 1:
        raise ValueError("euler_steps must be at least 1.")
    batch_size = x_start.shape[0]
    if corruption.shape != (batch_size,):
        raise ValueError(
            f"corruption must have shape ({batch_size},); got {corruption.shape}."
        )
    if noise is None:
        noise = torch.randn_like(x_start)
    elif noise.shape != x_start.shape:
        raise ValueError(f"noise shape {noise.shape} != x_start shape {x_start.shape}")

    start_t = torch.round(
        corruption.to(device=x_start.device, dtype=torch.float32)
        * float(num_train_timesteps - 1)
    ).long().clamp(0, num_train_timesteps - 1)
    a_quantized = start_t.to(dtype=x_start.dtype) / float(num_train_timesteps - 1)
    a_view = a_quantized.view(batch_size, *([1] * (x_start.ndim - 1)))
    z = a_view * noise + (1.0 - a_view) * x_start

    grid = build_sampling_timesteps(
        num_train_timesteps, euler_steps, x_start.device
    )
    chunk_index = torch.full(
        (batch_size,), chunk_idx, dtype=torch.long, device=x_start.device
    )
    for step in range(euler_steps):
        current_t = torch.minimum(grid[step], start_t)
        next_t = torch.minimum(grid[step + 1], start_t)
        delta = (current_t - next_t).to(dtype=x_start.dtype)
        delta = delta / float(num_train_timesteps - 1)
        if not torch.any(delta > 0):
            continue
        # t=0 is never used as a model-evaluation point in FlowCast's Euler
        # solver.  Inactive samples receive t=1 and a zero integration step.
        model_t = torch.where(
            delta > 0, current_t.clamp_min(1), torch.ones_like(current_t)
        )
        velocity = model(z, model_t, cond, chunk_index)
        delta_view = delta.view(batch_size, *([1] * (x_start.ndim - 1)))
        z = z + velocity * delta_view
    return z.detach()


def iterative_proportional_fitting(
    kernel: np.ndarray,
    marginals,
    *,
    max_iters: int = 5000,
    tol: float = 1.0e-10,
    fail_tol: float = 1.0e-8,
    return_diagnostics: bool = False,
):
    """Rescale ``kernel`` to a joint distribution with the given 1-D marginals.

    This is what makes R3 an experiment about *dependence*.  A sampler built
    straight from a score surface changes the marginal of every variable it
    touches at once -- it trains more on hard leads, more on hard Flow times,
    more on hard corruption levels, and on a discrete grid instead of a
    continuous one.  Any of those alone can move the metric, so a win would not
    identify coupling; it would identify hard-region curriculum.

    IPF keeps the score's *dependence structure* while forcing
    ``sum_{a,tau} Q(l,a,tau) = Q_l`` and the two analogous constraints.  Pair
    it with a control that samples the same grid with the same marginals but
    independently, and the only remaining difference between the two arms is
    the copula.

    Convergence is CHECKED, not assumed.  Hitting the iteration cap and
    returning whatever the last sweep produced would hand R3 a joint whose
    marginals differ from the control's -- reintroducing exactly the confound
    this function exists to remove, silently.  A low
    ``amplification_temperature`` makes the kernel's dynamic range large and is
    where the cap actually bites: on a 5x5x5 surface at ``T = 0.25``, 500
    sweeps leave a marginal error of ~5e-5 while 5000 reach ~1e-10.  So the
    final marginals are re-measured after the loop and anything worse than
    ``fail_tol`` raises.
    """
    kernel = np.asarray(kernel, dtype=np.float64)
    if kernel.ndim != len(marginals):
        raise ValueError(
            f"kernel has {kernel.ndim} axes but {len(marginals)} marginals were given."
        )
    targets = []
    for axis, marginal in enumerate(marginals):
        target = np.asarray(marginal, dtype=np.float64)
        if target.shape != (kernel.shape[axis],):
            raise ValueError(
                f"marginal {axis} has shape {target.shape}, expected "
                f"({kernel.shape[axis]},)."
            )
        if np.any(target < 0):
            raise ValueError("marginals must be non-negative.")
        total = target.sum()
        if total <= 0:
            raise ValueError(f"marginal {axis} sums to zero.")
        targets.append(target / total)

    if np.any(kernel < 0):
        raise ValueError("kernel must be non-negative.")
    joint = kernel / kernel.sum()
    if not np.isfinite(joint).all():
        raise ValueError("kernel is not finite after normalization.")

    def marginal_error(candidate):
        worst = 0.0
        for axis, target in enumerate(targets):
            other = tuple(i for i in range(candidate.ndim) if i != axis)
            worst = max(
                worst,
                float(np.abs(candidate.sum(axis=other) - target).max()),
            )
        return worst

    iterations = 0
    for iterations in range(1, int(max_iters) + 1):
        for axis, target in enumerate(targets):
            other = tuple(i for i in range(joint.ndim) if i != axis)
            current = joint.sum(axis=other)
            scale = np.divide(
                target, current, out=np.ones_like(target), where=current > 0
            )
            shape = [1] * joint.ndim
            shape[axis] = joint.shape[axis]
            joint = joint * scale.reshape(shape)
        joint = joint / joint.sum()
        if marginal_error(joint) <= tol:
            break

    final_error = marginal_error(joint)
    if final_error > fail_tol:
        raise RuntimeError(
            "IPF did not converge: "
            f"max_marginal_error={final_error:.3e} > fail_tol={fail_tol:.3e} "
            f"after {iterations} sweeps.  The joint's marginals differ from "
            "the control's, so an R3-vs-R2G difference could come from a "
            "marginal shift rather than from the copula.  Raise max_iters, or "
            "raise amplification_temperature to shrink the kernel's dynamic "
            "range."
        )
    if return_diagnostics:
        return joint, {
            "ipf_iterations": int(iterations),
            "ipf_max_marginal_error": float(final_error),
        }
    return joint


def build_joint_from_surface(
    surface,
    *,
    marginal_mode: str,
    temperature: float,
    floor: float = 1.0e-6,
    return_diagnostics: bool = False,
):
    """The single definition of R3's sampling distribution.

    Both the controller (which trains from it) and the estimator (which
    reports its TV / KL / density ratio / mutual information) call this.  They
    used to build the joint independently, so any run that changed
    ``amplification_key`` or ``marginal_mode`` produced a report describing a
    distribution that was never sampled -- the provenance fields would agree,
    the labels would agree, and only the numbers would be wrong.  A report that
    can silently describe the wrong treatment is worse than no report, because
    the whole point of it is to decide whether the treatment is worth running.

    ``matched`` exponentially tilts by the score and then fits the result onto
    uniform marginals, so it differs from the ``grid_independent`` control only
    in the copula.  ``raw`` is the ablation: it weights by the positive part
    directly, which moves all three marginals and is therefore reproducible by
    ordinary hard-region curriculum.
    """
    if marginal_mode not in _VALID_MARGINAL_MODES:
        raise ValueError(
            f"marginal_mode must be one of {sorted(_VALID_MARGINAL_MODES)}; "
            f"got {marginal_mode!r}."
        )
    if temperature <= 0.0:
        raise ValueError("temperature must be positive.")
    surface = np.asarray(surface, dtype=np.float64)

    if marginal_mode == "raw":
        weights = np.clip(surface, 0.0, None) + float(floor)
        weights = np.power(weights, 1.0 / float(temperature))
        total = weights.sum()
        if not np.isfinite(total) or total <= 0.0:
            raise ValueError("surface has no positive mass under 'raw' weighting.")
        joint = weights / total
        diagnostics = {"ipf_iterations": 0, "ipf_max_marginal_error": 0.0}
    else:
        kernel = np.exp(np.clip(surface / float(temperature), -50.0, 50.0))
        uniform = [np.ones(size) / float(size) for size in kernel.shape]
        joint, diagnostics = iterative_proportional_fitting(
            kernel, uniform, return_diagnostics=True
        )
    if return_diagnostics:
        return joint, diagnostics
    return joint


def log_loss_ratio(
    bridge_loss: np.ndarray,
    clean_loss: np.ndarray,
    *,
    eps: float = 1.0e-12,
) -> np.ndarray:
    """Dimensionless per-sample rollout penalty ``log((L_b+e)/(L_c+e))``.

    The raw difference ``L_bridge - L_clean`` inherits the overall scale of the
    velocity-regression loss, which grows with Flow time because ``x_tau``
    approaches pure noise.  Dividing by a corruption-only distance such as
    ``relative_l2(a)`` cannot remove that Flow-time main effect, so a surface
    built from the raw difference is monotone in ``tau`` for reasons that have
    nothing to do with rollout conditioning.  The log-ratio is invariant to any
    per-``tau`` rescaling ``L -> s(tau) L`` and is therefore the right quantity
    to average over samples *before* binning.
    """
    bridge = np.asarray(bridge_loss, dtype=np.float64)
    clean = np.asarray(clean_loss, dtype=np.float64)
    if bridge.shape != clean.shape:
        raise ValueError(
            f"bridge/clean shapes differ: {bridge.shape} vs {clean.shape}"
        )
    return np.log(bridge + eps) - np.log(clean + eps)


def interaction_residual(
    values: np.ndarray,
    counts: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Two-way interaction residual of a ``(..., A, Q)`` surface.

    Returns ``R[a,q] - Rbar[a,.] - Rbar[.,q] + Rbar[.,.]`` with count-weighted
    marginals, computed independently for every leading index (transition and
    lead).  What survives is exactly the part of the surface that a purely
    additive ``f(a) + g(tau)`` explanation cannot produce.

    This is the statistic R3 must sample from.  If the rollout penalty is
    additive -- corruption makes things harder, high Flow time makes things
    harder, and the two do not interact -- the residual is zero and there is no
    lead--Flow coupling to exploit, no matter how strong the raw surface looks.

    Annihilation of an additive surface is *exact* when the design is balanced
    (every cell seen by the same number of events), which is what the estimator
    produces: it evaluates every ``(a, tau)`` cell for every event.  Under a
    ragged design it is only approximate, so the estimator reports whether its
    counts were balanced.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.ndim < 2:
        raise ValueError("values must have at least two dimensions (A, Q).")
    if counts is None:
        weights = np.ones_like(values)
    else:
        weights = np.asarray(counts, dtype=np.float64)
        if weights.shape != values.shape:
            raise ValueError(
                f"counts shape {weights.shape} != values shape {values.shape}"
            )
        weights = np.maximum(weights, 0.0)

    def _wmean(axis):
        total = weights.sum(axis=axis, keepdims=True)
        num = (values * weights).sum(axis=axis, keepdims=True)
        return np.divide(
            num, total, out=np.zeros_like(num), where=total > 0
        )

    mean_over_tau = _wmean(-1)  # (..., A, 1): corruption main effect
    mean_over_a = _wmean(-2)  # (..., 1, Q): Flow-time main effect
    grand = _wmean((-2, -1))  # (..., 1, 1)
    residual = values - mean_over_tau - mean_over_a + grand
    # Empty bins carry no evidence; leave them at exactly zero so they cannot
    # win sampling mass through the amplification floor alone.
    if counts is not None:
        residual = np.where(weights > 0, residual, 0.0)
    return residual


def freeze_module(module: torch.nn.Module) -> torch.nn.Module:
    """Put a rollout teacher permanently into inference state."""
    module.eval()
    module.requires_grad_(False)
    return module


def parameter_fingerprint(module: torch.nn.Module) -> str:
    """Order-stable hash of a module's parameters and buffers.

    Used by the frozen-teacher regression test: a teacher that is genuinely
    immutable must produce the same fingerprint before and after arbitrarily
    many student optimizer steps and eval-EMA updates.
    """
    import hashlib

    digest = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(
            tensor.detach().to(device="cpu", dtype=torch.float64).numpy().tobytes()
        )
    return digest.hexdigest()


def rmlf_config_from_mapping(mapping: Optional[Dict[str, Any]]) -> RMLFConfig:
    """Create ``RMLFConfig`` from a plain mapping, ignoring no fields.

    Keeping this strict catches misspelled YAML keys rather than silently
    running a different experiment.
    """
    if mapping is None:
        return RMLFConfig(enabled=False)
    unknown = set(mapping).difference(RMLFConfig.__dataclass_fields__)
    if unknown:
        raise ValueError(f"Unknown rmlf_params keys: {sorted(unknown)}")
    return RMLFConfig(**mapping)
