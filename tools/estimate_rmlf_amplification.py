#!/usr/bin/env python3
"""Estimate the rollout-error interaction surface used by full RMLF (R3).

The tool is deliberately read-only: it loads a frozen FlowCast checkpoint and
latent *training/validation* events, compares clean and rollout-bridge
conditions under common target noise, and writes a joint sampling table
indexed by [transition, lead, corruption_bin, flow_time_bin].

What it measures, and why the obvious statistic is wrong
--------------------------------------------------------
The naive surface is ``[L_bridge - L_clean]_+ / d(bridge, clean)``.  It is
confounded: the velocity-regression loss grows with Flow time because
``x_tau`` approaches pure noise, and the denominator depends on the corruption
level ``a`` alone, so it cannot divide that growth out.  A surface built this
way is monotone in ``tau`` whether or not rollout conditioning interacts with
Flow time at all, and sampling from it is indistinguishable from ordinary
hard-timestep oversampling.

So this tool instead
  1. averages the per-sample log ratio ``log(L_bridge / L_clean)``, which is
     invariant to any per-``tau`` rescaling of the loss, and
  2. removes both main effects, leaving the two-way interaction residual
     ``I = R - Rbar(a,.) - Rbar(.,tau) + Rbar(.,.)``.

``I`` is what R3 samples from.  If the rollout penalty is additive in
(corruption, Flow time), ``I`` is zero and there is no lead--Flow coupling to
exploit -- which is a real answer, not a failure.  Every intermediate surface
is still written to the ``.npz`` (and drawn in the ``.png`` panel) so the
confound can be inspected rather than assumed.

Example (CIKM training subset):

    python tools/estimate_rmlf_amplification.py \
      --config experiments/cikm/runner/flowcast/flowcast_config_rmlf_r3.yaml \
      --checkpoint PARENT_CHECKPOINT_ABSOLUTE_PATH \
      --split training --max_events 600 \
      --out artifacts/cikm/rmlf/interaction_table.npz

Do NOT pass ``--max_batches`` for a real table: it truncates a
``shuffle=False`` loader, so on a chronologically sorted split it measures the
head of the manifest -- one season, not the distribution.  ``--max_events``
picks whole events by stable hash instead.

``--weights`` and ``--fp16`` both default to the config so the surface is
measured on exactly the weights and at exactly the precision the frozen
teacher will run; the controller verifies both.

The script refuses paths containing ``test`` so the training sampler cannot be
silently tuned on the test set.

Scope note: the event-level statistics below treat each dataset row as one
independent event.  That holds when ``raw_seq_len == input_length +
output_length`` (CIKM: 15 == 5 + 10), i.e. one window per event.  On a config
that slides several windows out of one storm, aggregate by ``file_row`` first
or the bootstrap will treat correlated windows as independent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper, make_chunk_index
from common.models.flowcast.rmlf import (
    build_joint_from_surface,
    interaction_residual,
    log_loss_ratio,
    relative_l2_per_sample,
    sample_rollout_bridge,
)
from experiments.sevir.dataset.sevirfulldataset import (
    DynamicEncodedSequentialSevirDataset,
    dynamic_encoded_sequential_collate,
)


def parse_float_list(value: str) -> list[float]:
    values = [float(item.strip()) for item in value.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected a non-empty comma-separated list")
    return values


def refuse_test_path(*paths: str) -> None:
    for path in paths:
        if "test" in str(path).lower():
            raise ValueError(
                "Refusing to build an RMLF training table from a path containing "
                f"'test': {path}"
            )


def state_dict_from_checkpoint(checkpoint: dict, preference: str = "auto") -> tuple[dict, str]:
    if preference not in {"auto", "ema", "raw"}:
        raise ValueError("preference must be one of: auto, ema, raw")
    if preference == "ema":
        keys = ("ema_model_state_dict",)
    elif preference == "raw":
        keys = ("model_state_dict", "model")
    else:
        # The RMLF bridge is trained with the EMA teacher, so an amplification
        # surface estimated from a crash-resume checkpoint should prefer the
        # saved EMA state when it is available.
        keys = ("ema_model_state_dict", "model_state_dict", "model")
    for key in keys:
        value = checkpoint.get(key)
        if isinstance(value, dict):
            state = {
                (name[7:] if name.startswith("module.") else name): tensor
                for name, tensor in value.items()
            }
            return state, key
    raise KeyError(
        f"checkpoint does not contain weights matching --weights={preference!r}"
    )


def scalar_from_checkpoint(checkpoint: dict, key: str) -> float:
    value = checkpoint.get(key)
    if value is None:
        raise KeyError(f"checkpoint is missing required normalizer value: {key}")
    if torch.is_tensor(value):
        value = value.detach().cpu().item()
    return float(value)


def make_dataset(config, data_file: str, meta_file: str):
    return DynamicEncodedSequentialSevirDataset(
        meta_csv=meta_file,
        data_file=data_file,
        data_type=str(OmegaConf.select(config, "data_params.data_key", default="vil")),
        raw_seq_len=int(OmegaConf.select(config, "data_params.raw_seq_len", default=49)),
        lag_time=int(OmegaConf.select(config, "data_params.input_length")),
        lead_time=int(OmegaConf.select(config, "data_params.output_length")),
        time_spacing=int(OmegaConf.select(config, "data_params.time_spacing", default=1)),
        stride=int(OmegaConf.select(config, "data_params.stride", default=1)),
        channel_last=True,
        debug_mode=False,
        transform=None,
    )


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "<unavailable>"


def stable_half(value) -> int:
    """Deterministic 0/1 split keyed on event identity.

    Splitting by batch parity only works if the loader order is unrelated to
    the signal.  It is not: `shuffle=False` over a chronologically sorted
    manifest makes even/odd halves neighbouring times, and sequences cut from
    ONE event land in both halves -- so agreement between halves would partly
    measure autocorrelation rather than reproducibility.  Hashing the event id
    keeps every sequence of an event on one side.
    """
    key = str(value).encode("utf-8")
    return hashlib.sha256(key).digest()[0] & 1


def resolve_split_key(metadata, requested):
    if requested:
        if requested not in metadata:
            raise KeyError(
                f"--split_key {requested!r} is not in the batch metadata; "
                f"available: {sorted(metadata)}"
            )
        return requested
    for candidate in ("file_row", "file_index", "id", "event_id"):
        if candidate in metadata:
            return candidate
    raise KeyError(
        "Could not auto-detect an event identifier for the split-half check; "
        f"pass --split_key explicitly.  Metadata keys: {sorted(metadata)}"
    )


def event_level_interaction(per_event_log_ratio: np.ndarray):
    """Paired interaction statistics computed WITHIN each event first.

    The earlier version averaged the log ratio over events, then propagated a
    per-cell variance through the interaction contrast assuming the cells were
    independent.  They are not: every (a, tau) cell of one event shares that
    event's target, target noise, bridge noise and model.  The contrast has
    coefficients of both signs, so the neglected covariance can inflate the
    variance as easily as shrink it -- "conservative" was an assumption, not a
    result.

    Forming the interaction inside each event and only then averaging over
    events keeps every covariance automatically, because the contrast is
    already collapsed to one number per cell per event.

    Returns ``(mean, sem, per_event)`` with shapes ``(..., A, Q)`` and
    ``(N, ..., A, Q)``.
    """
    per_event = np.asarray(per_event_log_ratio, dtype=np.float64)
    if per_event.ndim < 3:
        raise ValueError("expected at least (N, A, Q)")
    counts = np.ones_like(per_event[0])
    per_event_interaction = np.stack(
        [interaction_residual(sample, counts) for sample in per_event], axis=0
    )
    n = per_event_interaction.shape[0]
    mean = per_event_interaction.mean(axis=0)
    if n < 2:
        return mean, np.full_like(mean, np.inf), per_event_interaction
    sd = per_event_interaction.std(axis=0, ddof=1)
    return mean, sd / np.sqrt(n), per_event_interaction


def max_t_threshold(
    per_event_interaction: np.ndarray,
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
):
    """Family-wise threshold on the standardized interaction, by bootstrap.

    Resamples EVENTS (the independent unit), recomputes every cell's
    standardized interaction around the observed mean, and keeps the largest
    absolute value from each replicate.  The ``1 - alpha`` quantile of that
    max distribution is a single threshold valid for the whole table.

    This replaces a hand-picked ``gate_z`` and handles both problems a fixed z
    cannot: the cells are correlated (so Bonferroni is too harsh) and there are
    many of them (so a per-cell 95% bound is too lax).
    """
    per_event = np.asarray(per_event_interaction, dtype=np.float64)
    n = per_event.shape[0]
    if n < 8:
        return None, None
    rng = np.random.default_rng(seed)
    observed_mean = per_event.mean(axis=0)
    maxima = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        sample = per_event[idx]
        mean = sample.mean(axis=0)
        sd = sample.std(axis=0, ddof=1)
        sem = sd / np.sqrt(n)
        stat = np.abs(mean - observed_mean) / np.maximum(sem, 1e-12)
        maxima[b] = float(stat.max())
    return float(np.quantile(maxima, 1.0 - alpha)), maxima


def select_event_indices(dataset, split_key, max_events, seed_salt="rmlf"):
    """Reproducible, order-independent subsample of whole events.

    Taking the first N batches of a `shuffle=False` loader samples the head of
    the manifest, which on a chronologically sorted split is a particular
    season.  Ranking events by a stable hash instead covers the manifest
    uniformly, is reproducible without storing an index list, and never
    depends on file order.
    """
    metadata = dataset.metadata
    if split_key not in metadata.columns:
        raise KeyError(
            f"split key {split_key!r} not in manifest columns: "
            f"{list(metadata.columns)}"
        )
    ranked = sorted(
        range(len(metadata)),
        key=lambda row: hashlib.sha256(
            f"{seed_salt}:{metadata.iloc[row][split_key]}".encode("utf-8")
        ).hexdigest(),
    )
    if max_events is not None and max_events > 0:
        ranked = ranked[: int(max_events)]
    chosen = set(ranked)
    cum = np.asarray(dataset.cum_counts)
    indices = [
        idx
        for idx in range(len(dataset))
        if int(np.searchsorted(cum, idx, side="right")) in chosen
    ]
    return indices, sorted(chosen)


def copula_strength(joint: np.ndarray):
    """How far the IPF'd joint actually is from its own control.

    Passing the statistical gates does not mean R3 is a different treatment
    from R2G.  After ``exp(S / T)`` and IPF the joint can still be almost
    uniform, in which case the two arms sample nearly the same distribution and
    a null result says nothing about coupling -- it says the treatment was too
    weak to test.  These numbers must be read BEFORE training, and the
    temperature frozen on the basis of training/validation data only.
    """
    joint = np.asarray(joint, dtype=np.float64)
    joint = joint / joint.sum()
    uniform = np.full_like(joint, 1.0 / joint.size)
    ratio = joint / uniform
    with np.errstate(divide="ignore", invalid="ignore"):
        kl = float(np.sum(np.where(joint > 0, joint * np.log(ratio), 0.0)))
    stats = {
        "total_variation": float(0.5 * np.abs(joint - uniform).sum()),
        "kl_to_uniform": kl,
        "max_ratio": float(ratio.max()),
        "min_ratio": float(ratio.min()),
    }
    # Pairwise mutual information: which pair of axes the dependence lives on.
    names = ("lead", "a", "tau")
    for i in range(joint.ndim):
        for j in range(i + 1, joint.ndim):
            other = tuple(k for k in range(joint.ndim) if k not in (i, j))
            pair = joint.sum(axis=other)
            pi = pair.sum(axis=1, keepdims=True)
            pj = pair.sum(axis=0, keepdims=True)
            product = pi * pj
            with np.errstate(divide="ignore", invalid="ignore"):
                mi = float(
                    np.sum(
                        np.where(
                            pair > 0, pair * np.log(pair / np.maximum(product, 1e-300)), 0.0
                        )
                    )
                )
            stats[f"mutual_information_{names[i]}_{names[j]}"] = mi
    return stats


def write_per_lead_heatmaps(path: Path, *, a_levels, tau_levels, interaction, gated):
    """One (a, tau) panel per lead, raw on top and gated below.

    The claim is lead-STRATIFIED coupling, so the decision must not rest on a
    figure that averages the lead axis away: a positive interaction at lead 6
    and a negative one at lead 10 cancel there, and a strong single-lead signal
    disappears into a flat mean.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - plotting is optional
        print(f"Skipping per-lead heat maps ({exc}).")
        return None

    n_leads = interaction.shape[0]
    fig, axes = plt.subplots(
        2, n_leads, figsize=(3.4 * n_leads, 7.0), squeeze=False
    )
    for lead in range(n_leads):
        for row, (surface, label) in enumerate(
            ((interaction, "raw I"), (gated, "gated score"))
        ):
            ax = axes[row][lead]
            data = surface[lead]
            limit = float(np.abs(data).max()) or 1.0
            image = ax.imshow(
                data,
                origin="lower",
                aspect="auto",
                cmap="coolwarm",
                vmin=-limit,
                vmax=limit,
            )
            ax.set_title(f"lead {lead + 1} — {label}", fontsize=9)
            ax.set_xticks(range(len(tau_levels)))
            ax.set_xticklabels([f"{v:g}" for v in tau_levels], fontsize=7)
            ax.set_yticks(range(len(a_levels)))
            ax.set_yticklabels([f"{v:g}" for v in a_levels], fontsize=7)
            if lead == 0:
                ax.set_ylabel("corruption a")
            if row == 1:
                ax.set_xlabel("flow time tau")
            fig.colorbar(image, ax=ax, fraction=0.046)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def write_heatmaps(
    path: Path,
    *,
    a_levels,
    tau_levels,
    clean_loss,
    signed_delta,
    log_ratio,
    interaction,
    gated=None,
    sampled_joint=None,
):
    """Emit the panels the R3 go/no-go decision is read from.

    Panels 1-2 show the confound (clean loss and the raw difference both grow
    with Flow time); panel 3 shows the dimensionless penalty; panel 4 shows
    what is left once both main effects are removed.  Only panel 4 can justify
    calling the method a lead--Flow coupling.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - plotting is optional
        print(f"Skipping heat maps ({exc}); the .npz already has every surface.")
        return None

    panels = [
        ("clean_loss (confound)", clean_loss, "viridis"),
        ("signed_delta (confounded)", signed_delta, "viridis"),
        ("log_ratio (scale-free)", log_ratio, "viridis"),
        ("interaction residual (ungated)", interaction, "coolwarm"),
    ]
    if gated is not None:
        # What R3 SAMPLES is the gated signed score, not the raw residual.
        panels.append(("gated signed score (R3 input)", gated, "coolwarm"))
    if sampled_joint is not None:
        ratio = sampled_joint / (1.0 / sampled_joint.size)
        panels.append(
            ("sampled joint / R2G control", np.log(ratio).mean(axis=0), "coolwarm")
        )
    fig, axes = plt.subplots(1, len(panels), figsize=(4.8 * len(panels), 4.2))
    axes = np.atleast_1d(axes)
    for ax, (title, surface, cmap) in zip(axes, panels):
        kwargs = {}
        if cmap == "coolwarm":
            limit = float(np.abs(surface).max()) or 1.0
            kwargs = {"vmin": -limit, "vmax": limit}
        image = ax.imshow(
            surface, origin="lower", aspect="auto", cmap=cmap, **kwargs
        )
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("flow time tau")
        ax.set_ylabel("corruption a")
        ax.set_xticks(range(len(tau_levels)))
        ax.set_xticklabels([f"{v:g}" for v in tau_levels], fontsize=8)
        ax.set_yticks(range(len(a_levels)))
        ax.set_yticklabels([f"{v:g}" for v in a_levels], fontsize=8)
        fig.colorbar(image, ax=ax, fraction=0.046)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument(
        "--weights",
        choices=("ema", "raw"),
        default=None,
        help=(
            "Which weights to measure.  Defaults to the config's "
            "rmlf_params.teacher_checkpoint_type.  'auto' was removed: one "
            ".pt can hold BOTH model_state_dict and ema_model_state_dict, so "
            "an auto-preference could measure the EMA while the frozen "
            "teacher runs the raw weights -- with matching file hashes, the "
            "provenance check would still pass."
        ),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--split", choices=("training", "validation"), default="training")
    parser.add_argument("--data_file", default=None)
    parser.add_argument("--meta_file", default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument(
        "--max_events",
        type=int,
        default=600,
        help=(
            "Number of whole events, chosen by stable hash over the manifest "
            "so the subsample covers the split uniformly instead of taking "
            "its chronological head.  0 = use every event."
        ),
    )
    parser.add_argument(
        "--max_batches",
        type=int,
        default=0,
        help="0 = no cap (the event subsample already bounds the work).",
    )
    parser.add_argument("--n_boot", type=int, default=2000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--gate_mode",
        choices=("max_t", "fixed_z"),
        default="max_t",
        help=(
            "max_t = family-wise bootstrap threshold over events (preferred). "
            "fixed_z = --gate_z * event-level SE, a fallback when too few "
            "events are available to bootstrap."
        ),
    )
    parser.add_argument("--a_levels", type=parse_float_list, default=parse_float_list("0.10,0.25,0.40,0.55,0.70"))
    parser.add_argument("--tau_levels", type=parse_float_list, default=parse_float_list("0.10,0.25,0.50,0.75,0.95"))
    parser.add_argument(
        "--bridge_steps",
        type=int,
        default=None,
        help=(
            "Euler steps for the rollout bridge.  Defaults to "
            "sampling_params.euler_steps so the surface is measured with the "
            "deployment solver; overriding it measures a different operator."
        ),
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=1e-12,
        help="stabilizer inside the per-sample log loss ratio",
    )
    parser.add_argument(
        "--no_heatmaps",
        action="store_true",
        help="skip the PNG diagnostic panel",
    )
    parser.add_argument(
        "--gate_z",
        type=float,
        default=3.5,
        help=(
            "z multiplier used only when --gate_mode=fixed_z.  3.5 ~ a "
            "one-sided Bonferroni 5%% family-wise bound over ~125 cells.  "
            "Lower values (2.58) are for exploratory heat maps, never for a "
            "go/no-go decision."
        ),
    )
    parser.add_argument(
        "--split_key",
        default=None,
        help=(
            "metadata column identifying an EVENT.  Halves are split by a "
            "stable hash of it, so sequences from one storm never straddle "
            "the split.  Default: auto-detect file_row / file_index / id."
        ),
    )
    parser.add_argument("--relative_l2_floor", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument(
        "--fp16",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Run the bridge under autocast.  Defaults to the config's "
            "training_params.fp16, because the trained bridge runs inside the "
            "training autocast block -- measuring the surface in fp32 and then "
            "using it to steer an autocast operator is a mismatch this method "
            "is too fine-grained to absorb.  The controller checks it."
        ),
    )
    args = parser.parse_args()

    if args.max_batches < 0 or args.batch_size == 0:
        raise ValueError("max_batches must be non-negative and batch_size non-zero")
    if any(not 0.0 <= a <= 1.0 for a in args.a_levels):
        raise ValueError("all a_levels must lie in [0, 1]")
    if any(not 0.0 < tau <= 1.0 for tau in args.tau_levels):
        raise ValueError("all tau_levels must lie in (0, 1]")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    config = OmegaConf.load(args.config)
    deployment_euler_steps = int(
        OmegaConf.select(config, "sampling_params.euler_steps")
    )
    if args.weights is None:
        args.weights = str(
            OmegaConf.select(
                config, "rmlf_params.teacher_checkpoint_type", default="raw"
            )
        )
        print(
            f"--weights not given; using rmlf_params.teacher_checkpoint_type"
            f"={args.weights!r} so the surface is measured on exactly the "
            "weights the frozen teacher will run."
        )
    if args.bridge_steps is None:
        args.bridge_steps = deployment_euler_steps
    if args.bridge_steps < 1:
        raise ValueError("bridge_steps must be at least one")
    if args.bridge_steps != deployment_euler_steps:
        print(
            f"WARNING: bridge_steps={args.bridge_steps} != deployment "
            f"euler_steps={deployment_euler_steps}; the measured surface then "
            "includes solver error that the trained bridge will not have."
        )
    dataset_name = str(OmegaConf.select(config, "data_params.dataset_name", default="sevir"))
    latent_root = Path(f"datasets/{dataset_name}/data/{dataset_name}_latent_vae")
    prefix = "nowcast_training_full" if args.split == "training" else "nowcast_validation_full"
    data_file = args.data_file or str(latent_root / f"{prefix}.h5")
    meta_file = args.meta_file or str(latent_root / f"{prefix}_META.csv")
    refuse_test_path(data_file, meta_file, args.out)

    full_dataset = make_dataset(config, data_file, meta_file)
    manifest_split_key = resolve_split_key(
        {name: None for name in full_dataset.metadata.columns}, args.split_key
    )
    if args.max_events and args.max_events > 0:
        subset_indices, chosen_events = select_event_indices(
            full_dataset, manifest_split_key, args.max_events
        )
        dataset = torch.utils.data.Subset(full_dataset, subset_indices)
        print(
            f"Hash-sampled {len(chosen_events)} of "
            f"{len(full_dataset.metadata)} events "
            f"({len(subset_indices)} sequences) keyed on "
            f"{manifest_split_key!r}."
        )
    else:
        dataset = full_dataset
        chosen_events = list(range(len(full_dataset.metadata)))
    batch_size = args.batch_size or int(
        OmegaConf.select(config, "training_params.micro_batch_size", default=2)
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=dynamic_encoded_sequential_collate,
        drop_last=False,
        pin_memory=torch.cuda.is_available(),
    )

    first_inputs, first_outputs, _ = next(iter(loader))
    input_length = int(OmegaConf.select(config, "data_params.input_length"))
    output_length = int(OmegaConf.select(config, "data_params.output_length"))
    num_chunks = output_length // input_length
    if num_chunks < 2:
        raise ValueError("RMLF requires at least two output chunks")
    if first_inputs.shape[-1] != first_outputs.shape[-1]:
        raise ValueError("input/output latent channel counts differ")

    device = torch.device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    model = FlowCastSTDiTWrapper(
        latent_channels=int(first_inputs.shape[-1]),
        hidden_size=int(OmegaConf.select(config, "stdit.hidden_size")),
        depth=int(OmegaConf.select(config, "stdit.depth")),
        num_heads=int(OmegaConf.select(config, "stdit.num_heads")),
        patch_size=tuple(OmegaConf.select(config, "stdit.patch_size")),
        mlp_ratio=float(OmegaConf.select(config, "stdit.mlp_ratio", default=4.0)),
        drop_path=float(OmegaConf.select(config, "stdit.drop_path", default=0.0)),
        qk_norm=bool(OmegaConf.select(config, "stdit.qk_norm", default=True)),
        mean=scalar_from_checkpoint(checkpoint, "mean"),
        std=scalar_from_checkpoint(checkpoint, "std"),
    )
    selected_state, selected_key = state_dict_from_checkpoint(
        checkpoint, preference=args.weights
    )
    model.load_state_dict(selected_state, strict=True)
    model.to(device).eval().requires_grad_(False)

    num_train_timesteps = int(OmegaConf.select(config, "rflow_params.num_train_timesteps"))
    shape = (
        num_chunks - 1,
        input_length,
        len(args.a_levels),
        len(args.tau_levels),
    )
    amplification_sum = np.zeros(shape, dtype=np.float64)
    signed_delta_sum = np.zeros(shape, dtype=np.float64)
    clean_loss_sum = np.zeros(shape, dtype=np.float64)
    bridge_loss_sum = np.zeros(shape, dtype=np.float64)
    # The dimensionless penalty.  Averaged over SAMPLES first, then binned:
    # a ratio of bin means would hide the sample heterogeneity that decides
    # whether a bin's apparent structure is real or driven by a few events.
    log_ratio_sum = np.zeros(shape, dtype=np.float64)
    log_ratio_sq_sum = np.zeros(shape, dtype=np.float64)
    relative_delta_sum = np.zeros(shape, dtype=np.float64)
    # Two disjoint halves (even/odd batches) so the interaction surface can be
    # checked for sign agreement instead of being trusted from one estimate.
    half_log_ratio_sum = np.zeros((2,) + shape, dtype=np.float64)
    half_counts = np.zeros((2,) + shape, dtype=np.int64)
    counts = np.zeros(shape, dtype=np.int64)
    relative_l2_sum = np.zeros((num_chunks - 1, len(args.a_levels)), dtype=np.float64)
    relative_l2_count = np.zeros_like(relative_l2_sum, dtype=np.int64)

    if args.fp16 is None:
        args.fp16 = bool(
            OmegaConf.select(config, "training_params.fp16", default=False)
        )
        print(
            f"--fp16 not given; following training_params.fp16={args.fp16} so "
            "the surface is measured with the same operator training uses."
        )
    use_amp = bool(args.fp16 and device.type == "cuda")
    if args.fp16 and device.type != "cuda":
        print(
            "WARNING: --fp16 requested but the device is not CUDA, so the "
            "surface will be measured in fp32 and provenance will record "
            "'fp32'.  The controller will then refuse an fp16 training run."
        )
    batches_seen = 0
    split_key = None
    split_events: dict = {}
    # Per-EVENT log ratios, kept so the interaction contrast can be formed
    # inside each event before averaging.  (N, transitions, leads, A, Q) --
    # a few hundred thousand floats even for thousands of events.
    per_event_log_ratio: list = []
    per_event_half: list = []
    with torch.no_grad():
        for batch_idx, (inputs, outputs, batch_meta) in enumerate(
            tqdm(loader, desc="RMLF amplification")
        ):
            if args.max_batches and batch_idx >= args.max_batches:
                break
            if split_key is None:
                split_key = resolve_split_key(batch_meta[0], args.split_key)
            half_ids = np.array(
                [stable_half(meta[split_key]) for meta in batch_meta],
                dtype=np.int64,
            )
            for event_key in (str(meta[split_key]) for meta in batch_meta):
                split_events.setdefault(event_key, 0)
            batch_log_ratio = np.zeros(
                (inputs.shape[0],) + shape, dtype=np.float64
            )
            inputs = inputs.to(device, non_blocking=True)
            outputs = outputs.to(device, non_blocking=True)
            inputs = model.normalize(inputs)
            outputs = model.normalize(outputs)
            batches_seen += 1

            for transition in range(num_chunks - 1):
                previous_target = outputs[
                    :, transition * input_length : (transition + 1) * input_length
                ]
                current_target = outputs[
                    :, (transition + 1) * input_length : (transition + 2) * input_length
                ]
                teacher_condition = (
                    inputs
                    if transition == 0
                    else outputs[
                        :, (transition - 1) * input_length : transition * input_length
                    ]
                )
                target_noise = torch.randn_like(current_target)
                bridge_noise = torch.randn_like(previous_target)
                current_chunk_index = transition + 2
                generated_chunk_index = transition + 1

                for a_idx, a in enumerate(args.a_levels):
                    corruption = torch.full(
                        (inputs.shape[0],),
                        float(a),
                        device=device,
                        dtype=outputs.dtype,
                    )
                    with torch.amp.autocast(
                        device_type=device.type, enabled=use_amp
                    ):
                        bridge = sample_rollout_bridge(
                            model=model,
                            x_start=previous_target,
                            cond=teacher_condition,
                            chunk_idx=generated_chunk_index,
                            corruption=corruption,
                            num_train_timesteps=num_train_timesteps,
                            euler_steps=args.bridge_steps,
                            noise=bridge_noise,
                        )
                    rel = relative_l2_per_sample(
                        bridge,
                        previous_target,
                        floor=args.relative_l2_floor,
                    ).float()
                    relative_l2_sum[transition, a_idx] += float(rel.sum())
                    relative_l2_count[transition, a_idx] += int(rel.numel())

                    for tau_idx, tau in enumerate(args.tau_levels):
                        t_value = int(round(float(tau) * (num_train_timesteps - 1)))
                        t_value = max(1, min(num_train_timesteps - 1, t_value))
                        t = torch.full(
                            (inputs.shape[0],),
                            t_value,
                            device=device,
                            dtype=torch.long,
                        )
                        tau_q = t.to(dtype=outputs.dtype).view(
                            inputs.shape[0], 1, 1, 1, 1
                        ) / float(num_train_timesteps - 1)
                        x_t = tau_q * target_noise + (1.0 - tau_q) * current_target
                        target_velocity = current_target - target_noise
                        t_seq = make_chunk_index(
                            inputs.shape[0], current_chunk_index, device
                        )
                        with torch.amp.autocast(
                            device_type=device.type, enabled=use_amp
                        ):
                            v_clean = model(x_t, t, previous_target, t_seq)
                            v_bridge = model(x_t, t, bridge, t_seq)
                        reduce_dims = tuple(range(2, current_target.ndim))
                        clean_error = (
                            (v_clean.float() - target_velocity.float()) ** 2
                        ).mean(dim=reduce_dims)
                        bridge_error = (
                            (v_bridge.float() - target_velocity.float()) ** 2
                        ).mean(dim=reduce_dims)
                        signed = bridge_error - clean_error
                        # Legacy surface, kept only so the confound can be
                        # SHOWN rather than asserted: it inherits the Flow-time
                        # scale of the velocity loss, and rel depends on `a`
                        # alone so it cannot divide that scale out.
                        amplification = signed.clamp_min(0.0) / rel[:, None].clamp_min(1e-6)

                        clean_np = clean_error.double().cpu().numpy()
                        bridge_np = bridge_error.double().cpu().numpy()
                        per_sample_log_ratio = log_loss_ratio(
                            bridge_np, clean_np, eps=args.eps
                        )
                        per_sample_relative = (bridge_np - clean_np) / (
                            clean_np + args.eps
                        )

                        amplification_sum[transition, :, a_idx, tau_idx] += (
                            amplification.sum(dim=0).cpu().numpy()
                        )
                        signed_delta_sum[transition, :, a_idx, tau_idx] += (
                            signed.sum(dim=0).cpu().numpy()
                        )
                        clean_loss_sum[transition, :, a_idx, tau_idx] += clean_np.sum(
                            axis=0
                        )
                        bridge_loss_sum[transition, :, a_idx, tau_idx] += bridge_np.sum(
                            axis=0
                        )
                        batch_log_ratio[:, transition, :, a_idx, tau_idx] = (
                            per_sample_log_ratio
                        )
                        log_ratio_sum[transition, :, a_idx, tau_idx] += (
                            per_sample_log_ratio.sum(axis=0)
                        )
                        log_ratio_sq_sum[transition, :, a_idx, tau_idx] += (
                            (per_sample_log_ratio ** 2).sum(axis=0)
                        )
                        relative_delta_sum[transition, :, a_idx, tau_idx] += (
                            per_sample_relative.sum(axis=0)
                        )
                        for half in (0, 1):
                            member = half_ids == half
                            n_member = int(member.sum())
                            if n_member == 0:
                                continue
                            half_log_ratio_sum[
                                half, transition, :, a_idx, tau_idx
                            ] += per_sample_log_ratio[member].sum(axis=0)
                            half_counts[
                                half, transition, :, a_idx, tau_idx
                            ] += n_member
                        counts[transition, :, a_idx, tau_idx] += inputs.shape[0]

            per_event_log_ratio.append(batch_log_ratio)
            per_event_half.append(half_ids.copy())

    if batches_seen == 0:
        raise RuntimeError("no batches were processed")
    denominator = np.maximum(counts, 1)
    amplification = amplification_sum / denominator
    signed_delta = signed_delta_sum / denominator
    clean_loss = clean_loss_sum / denominator
    bridge_loss = bridge_loss_sum / denominator
    log_ratio = log_ratio_sum / denominator
    relative_delta = relative_delta_sum / denominator
    log_ratio_var = np.maximum(
        log_ratio_sq_sum / denominator - log_ratio ** 2, 0.0
    )
    log_ratio_sem = np.sqrt(log_ratio_var / denominator)
    relative_l2 = relative_l2_sum / np.maximum(relative_l2_count, 1)

    # THE surface R3 is allowed to sample from.  Both main effects are removed:
    # "corruption `a` makes prediction harder" and "high Flow time makes
    # prediction harder" are each fully explainable without any lead--Flow
    # coupling, and an additive surface therefore leaves a zero residual.
    # --- event-level paired interaction (keeps every within-event covariance)
    events = np.concatenate(per_event_log_ratio, axis=0)
    halves = np.concatenate(per_event_half, axis=0)
    interaction, interaction_sem, per_event_interaction = event_level_interaction(
        events
    )
    n_events = int(per_event_interaction.shape[0])

    # Event-DISJOINT halves, for a reproducibility check independent of the
    # confidence bound's distributional assumptions.
    half_interaction = np.stack(
        [
            per_event_interaction[halves == h].mean(axis=0)
            if int((halves == h).sum()) > 0
            else np.zeros_like(interaction)
            for h in (0, 1)
        ],
        axis=0,
    )
    both_seen = np.array(
        [int((halves == h).sum()) > 0 for h in (0, 1)]
    ).all() & np.ones_like(interaction, dtype=bool)
    same_sign = (
        np.sign(half_interaction[0]) == np.sign(half_interaction[1])
    ) & both_seen
    sign_agreement = float(same_sign.sum()) / float(max(int(both_seen.sum()), 1))

    # --- family-wise threshold -------------------------------------------
    boot_threshold, boot_maxima = max_t_threshold(
        per_event_interaction,
        n_boot=int(args.n_boot),
        alpha=float(args.alpha),
        seed=int(args.seed),
    )
    if args.gate_mode == "max_t" and boot_threshold is not None:
        gate_mode_used = "max_t"
        cell_threshold = boot_threshold * interaction_sem
    else:
        gate_mode_used = "fixed_z"
        if args.gate_mode == "max_t":
            print(
                f"WARNING: only {n_events} events -- too few to bootstrap; "
                f"falling back to fixed_z={args.gate_z}."
            )
        cell_threshold = float(args.gate_z) * interaction_sem

    # SIGNED score: IPF needs the sign, because a cell that is reliably
    # *easier* than additivity predicts is evidence about the copula too.
    magnitude = np.maximum(np.abs(interaction) - cell_threshold, 0.0)
    interaction_signed_score = np.where(same_sign, np.sign(interaction) * magnitude, 0.0)
    interaction_lcb = np.maximum(interaction - cell_threshold, 0.0)
    interaction_gated = np.where(same_sign, interaction_lcb, 0.0)
    # The MAIN R3 go/no-go: does the headline surface have anything at all?
    # Kept distinct from "does the SELECTED surface produce a real treatment",
    # because an ablation may run from a different surface entirely.
    main_surviving_cells = int((np.abs(interaction_signed_score) > 0).sum())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # What R3 will really sample, built with the same IPF the controller uses.
    from common.models.flowcast.rmlf import iterative_proportional_fitting

    # The temperature the SAMPLER will use.  Reporting the T=1 kernel while
    # training runs another temperature would describe a different treatment
    # than the one being applied -- and the whole point of this report is to
    # decide whether the treatment is strong enough to be worth running.
    sampler_temperature = float(
        OmegaConf.select(
            config, "rmlf_params.amplification_temperature", default=1.0
        )
    )
    # The surface and the marginal mode the SAMPLER will use.  Reporting the
    # default signed-score / matched joint while an ablation trains from
    # `interaction_gated` or `marginal_mode: raw` would describe a
    # distribution that is never sampled -- the provenance labels would still
    # agree, and only the numbers would be wrong.
    sampler_surface_key = str(
        OmegaConf.select(
            config,
            "rmlf_params.amplification_key",
            default="interaction_signed_score",
        )
    )
    sampler_marginal_mode = str(
        OmegaConf.select(config, "rmlf_params.marginal_mode", default="matched")
    )
    sampler_floor = float(
        OmegaConf.select(
            config, "rmlf_params.amplification_floor", default=1.0e-6
        )
    )
    reported_surfaces = {
        "interaction_signed_score": interaction_signed_score,
        "interaction_gated": interaction_gated,
        "interaction": interaction,
        "log_ratio": log_ratio,
        "amplification": amplification,
    }
    if sampler_surface_key not in reported_surfaces:
        raise ValueError(
            f"rmlf_params.amplification_key={sampler_surface_key!r} is not a "
            f"surface this tool produces: {sorted(reported_surfaces)}"
        )
    sampler_surface = reported_surfaces[sampler_surface_key]
    copula = {
        "amplification_temperature": sampler_temperature,
        "surface_key": sampler_surface_key,
        "marginal_mode": sampler_marginal_mode,
        "selected_surface_nonzero_cells": int(
            (np.abs(sampler_surface) > 0).sum()
        ),
    }
    # Build the joint for the SELECTED surface unconditionally.  Gating this on
    # the headline surface would mis-report both directions: an ablation
    # running from `log_ratio` would be called No-Go whenever the signed score
    # is empty (even though it has a perfectly good joint), and a
    # `interaction_gated` ablation whose positive part is empty would be called
    # a candidate (even though its joint is exactly the R2G control).
    sampled_joint = None
    try:
        per_transition = []
        ipf_errors = []
        ipf_iterations = []
        for transition in range(sampler_surface.shape[0]):
            fitted, diagnostics = build_joint_from_surface(
                sampler_surface[transition],
                marginal_mode=sampler_marginal_mode,
                temperature=sampler_temperature,
                floor=sampler_floor,
                return_diagnostics=True,
            )
            per_transition.append(fitted)
            ipf_errors.append(diagnostics["ipf_max_marginal_error"])
            ipf_iterations.append(diagnostics["ipf_iterations"])
        sampled_joint = np.mean(per_transition, axis=0)
        copula.update(copula_strength(sampled_joint))
        # If these are not tiny, R3's marginals are not the control's and the
        # arms differ by more than their copula.  IPF raises above the
        # fail tolerance, so a number here means it converged.
        copula["ipf_max_marginal_error"] = float(max(ipf_errors))
        copula["ipf_max_iterations"] = int(max(ipf_iterations))
    except ValueError as exc:
        # e.g. `raw` weighting on a surface with no positive mass.
        copula["joint_error"] = str(exc)
    # A joint that is uniform to numerical precision IS the R2G control: the
    # arm would be a duplicate of its own control, not a treatment.
    copula["treatment_equals_control"] = bool(
        sampled_joint is None
        or copula.get("total_variation", 0.0) < 1e-12
    )

    provenance = dict(
        # The three fields that DEFINE the treatment, not just the operator.
        # The copula report below is computed under exactly these, so binding
        # them to the table is what stops a table (and a reviewed TV/KL/MI
        # report) generated at one temperature from being used to train at
        # another -- IPF would still converge, the marginals would still match,
        # and nothing would flag that the reviewed treatment strength is not
        # the applied one.
        sampler_surface_key=sampler_surface_key,
        sampler_temperature=repr(sampler_temperature),
        sampler_marginal_mode=sampler_marginal_mode,
        source_checkpoint_sha256=sha256_file(args.checkpoint),
        source_checkpoint_path=os.path.abspath(args.checkpoint),
        source_weight_key=selected_key,
        config_sha256=sha256_file(args.config),
        git_commit=git_commit(),
        bridge_steps=str(args.bridge_steps),
        num_train_timesteps=str(num_train_timesteps),
        precision_mode="fp16_autocast" if use_amp else "fp32",
        dataset_split=args.split,
        dataset_manifest_sha256=sha256_file(meta_file),
        seed=str(args.seed),
    )
    np.savez_compressed(
        out,
        interaction_signed_score=interaction_signed_score.astype(np.float32),
        interaction_gated=interaction_gated.astype(np.float32),
        interaction_lcb=interaction_lcb.astype(np.float32),
        interaction_sem=interaction_sem.astype(np.float32),
        cell_threshold=cell_threshold.astype(np.float32),
        half_counts=half_counts,
        interaction=interaction.astype(np.float32),
        half_interaction=half_interaction.astype(np.float32),
        log_ratio=log_ratio.astype(np.float32),
        log_ratio_sem=log_ratio_sem.astype(np.float32),
        relative_delta=relative_delta.astype(np.float32),
        amplification=amplification.astype(np.float32),
        signed_delta=signed_delta.astype(np.float32),
        clean_loss=clean_loss.astype(np.float32),
        bridge_loss=bridge_loss.astype(np.float32),
        counts=counts,
        relative_l2=relative_l2.astype(np.float32),
        a_centers=np.asarray(args.a_levels, dtype=np.float32),
        tau_centers=np.asarray(args.tau_levels, dtype=np.float32),
        **{key: np.asarray([value]) for key, value in provenance.items()},
    )

    # Lead-averaged views, which are what the go/no-go decision is read from.
    lead_mean = lambda surface: surface.mean(axis=(0, 1))
    interaction_lead_mean = lead_mean(interaction)
    summary = {
        "config": os.path.abspath(args.config),
        "checkpoint": os.path.abspath(args.checkpoint),
        "checkpoint_weights": selected_key,
        "data_file": os.path.abspath(data_file),
        "meta_file": os.path.abspath(meta_file),
        "split": args.split,
        "batches_seen": batches_seen,
        "events_seen": int(counts[0, 0, 0, 0]),
        "shape": list(interaction.shape),
        "a_levels": args.a_levels,
        "tau_levels": args.tau_levels,
        "bridge_steps": args.bridge_steps,
        "deployment_euler_steps": deployment_euler_steps,
        "seed": args.seed,
        # --- go / no-go evidence -------------------------------------------
        # 1. Is the RAW surface simply monotone in tau?  If yes, and the
        #    interaction is ~0, R3 would be hard-timestep oversampling.
        "signed_delta_by_tau": lead_mean(signed_delta).mean(axis=0).tolist(),
        "clean_loss_by_tau": lead_mean(clean_loss).mean(axis=0).tolist(),
        # 2. The dimensionless penalty, still containing both main effects.
        "log_ratio_by_tau": lead_mean(log_ratio).mean(axis=0).tolist(),
        "log_ratio_by_a": lead_mean(log_ratio).mean(axis=1).tolist(),
        # 3. What actually survives.
        "interaction_abs_mean": float(np.abs(interaction).mean()),
        "interaction_max": float(interaction.max()),
        "interaction_to_logratio_ratio": float(
            np.abs(interaction).mean()
            / max(float(np.abs(log_ratio - log_ratio.mean()).mean()), 1e-12)
        ),
        "interaction_lead_mean": interaction_lead_mean.tolist(),
        # 4. Does it reproduce on an EVENT-disjoint half of the data?
        "split_key": split_key,
        "split_events_seen": len(split_events),
        "split_half_sign_agreement": sign_agreement,
        # 5. What actually survives both gates -- this is what R3 samples.
        "n_events": n_events,
        "gate_mode": gate_mode_used,
        "gate_z": args.gate_z,
        "maxT_threshold": boot_threshold,
        "maxT_n_boot": int(args.n_boot),
        "maxT_alpha": float(args.alpha),
        "max_events_requested": args.max_events,
        "events_in_manifest": len(chosen_events),
        # These describe the HEADLINE surface and decide the main R3 go/no-go,
        # independently of which surface an ablation config selects.
        "gated_cells_nonzero": main_surviving_cells,
        "gated_cells_total": int(interaction_signed_score.size),
        "gated_nonzero_fraction": float(
            main_surviving_cells / max(interaction_signed_score.size, 1)
        ),
        "gated_abs_mass": float(np.abs(interaction_signed_score).sum()),
        "main_r3_go": bool(main_surviving_cells > 0),
        "provenance": provenance,
        # 6. Is the treatment even different from its control?
        "copula_strength": copula,
        # Additive annihilation is exact only under a balanced design.
        "counts_balanced": bool(np.all(counts == counts.flat[0])),
        "max_amplification": float(amplification.max()),
        "mean_amplification": float(amplification.mean()),
    }
    out.with_suffix(out.suffix + ".json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))

    if not args.no_heatmaps:
        png = write_heatmaps(
            out.with_suffix(".png"),
            a_levels=args.a_levels,
            tau_levels=args.tau_levels,
            clean_loss=lead_mean(clean_loss),
            signed_delta=lead_mean(signed_delta),
            log_ratio=lead_mean(log_ratio),
            interaction=interaction_lead_mean,
            gated=lead_mean(interaction_signed_score),
            sampled_joint=sampled_joint,
        )
        if png is not None:
            print(f"Saved RMLF diagnostic heat maps to {png}")
        # The method is lead-STRATIFIED, so a lead-averaged panel can cancel a
        # positive interaction at lead 6 against a negative one at lead 10, or
        # hide a strong single-lead signal inside a flat mean.  Emit the
        # per-lead surfaces too -- both raw and the gated score R3 samples.
        per_lead = write_per_lead_heatmaps(
            out.with_suffix(".per_lead.png"),
            a_levels=args.a_levels,
            tau_levels=args.tau_levels,
            interaction=interaction.mean(axis=0),
            gated=interaction_signed_score.mean(axis=0),
        )
        if per_lead is not None:
            print(f"Saved per-lead interaction heat maps to {per_lead}")

    # Three distinct verdicts.  Collapsing them into one is how a log-ratio
    # ablation gets called No-Go because the headline surface is empty, and how
    # a positive-only ablation whose gated part is empty gets called a
    # candidate when its joint is exactly the control.
    main_selected = sampler_surface_key == "interaction_signed_score"
    if main_surviving_cells == 0:
        print(
            "\nMAIN R3 NO-GO: no cell of `interaction_signed_score` survives "
            "the family-wise threshold and the event-disjoint split-half "
            "check.  The rollout penalty is additive in (corruption, Flow "
            "time) as far as this data can tell -- the headline claim stops at "
            "R2, and lead-stratified coupling has no independent value here."
        )
    else:
        print(
            f"\nMAIN R3 candidate: {main_surviving_cells}/"
            f"{interaction_signed_score.size} cells of "
            "`interaction_signed_score` survive both gates "
            f"(gate={gate_mode_used}, event-disjoint halves keyed on "
            f"{split_key!r}, N={n_events} events, split-half sign agreement="
            f"{sign_agreement:.3f})."
        )

    label = (
        "the main arm"
        if main_selected and sampler_marginal_mode == "matched"
        else f"ablation {sampler_surface_key}/{sampler_marginal_mode}"
    )
    if "joint_error" in copula:
        print(
            f"  SELECTED TREATMENT ({label}) cannot be built: "
            f"{copula['joint_error']}  This arm will not start."
        )
    elif copula.get("treatment_equals_control", False):
        print(
            f"  SELECTED TREATMENT ({label}) is IDENTICAL to the R2G control: "
            "its joint is uniform to numerical precision, so the arm would "
            "duplicate its own control and could not differ from it for any "
            "reason.  Do not report it as a treatment."
        )
    else:
        print(
            f"  SELECTED TREATMENT ({label}) vs the R2G control: "
            f"TV={copula.get('total_variation', 0.0):.4f} "
            f"KL={copula.get('kl_to_uniform', 0.0):.4f} "
            f"ratio=[{copula.get('min_ratio', 1.0):.3f}, "
            f"{copula.get('max_ratio', 1.0):.3f}] "
            f"(T={sampler_temperature}, "
            f"IPF err={copula.get('ipf_max_marginal_error', 0.0):.2e} in "
            f"{copula.get('ipf_max_iterations', 0)} sweeps)"
        )
        if copula.get("total_variation", 0.0) < 0.02:
            print(
                "  WARNING: that joint is nearly uniform, so this arm and R2G "
                "would sample almost the same distribution.  A null result "
                "would then mean the treatment was too weak to test, not that "
                "coupling has no value.  Re-freeze "
                "amplification_temperature from training/validation evidence "
                "-- never from R3 test scores -- and re-run this tool so the "
                "report matches."
            )
    print(
        "  Read BOTH figures before launching: the six-panel summary and the "
        "per-lead panels.  If signed_delta rises with tau while the gated "
        "score is flat, this is hard-timestep oversampling, not coupling."
    )


if __name__ == "__main__":
    main()
