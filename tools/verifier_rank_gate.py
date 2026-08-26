"""Offline gate for inference-time selection (lane 4) and RL reward signal (lane 1).

Runs on a frozen `EnsembleWriter` HDF5 - no GPU, no model load, no training code
touched.  Settles two questions that must both hold before either lane earns a
GPU-hour.

**Stage A - headroom and advantage signal (uses truth; no verifier involved).**
How much deterministic skill is reachable by *choosing among members we already
draw*?  Pooled in the repository convention (sum TP/FP/FN over events, form the
ratio last):

  * ``ens_mean``               - the current production deterministic product
  * ``member_mean_over_index`` - mean over fixed member index j = "pick at random"
  * ``oracle`` / ``antioracle``- per event the best / worst member, bracketing the range

``oracle - random`` is the whole budget any verifier, best-of-N or SMC scheme can
compete for.  Small budget relative to run-to-run noise (~0.5% relative on
CSI-M in this project) means lane 4 dies here, for free.

The same per-member rewards answer a different question for lane 1: GRPO forms
advantages *within* a group of samples from one condition, so its learning signal
is the **within-event** spread of reward, not the between-event spread.  Reported
as ``within_event_std``, its ratio to ``between_event_std``, and the fraction of
groups that are degenerate (all members identical, i.e. exactly zero gradient).

**Stage B - can anything rank members without the truth?**
Per-(event, member) features a deployed system could actually compute, scored by
within-event Spearman against per-member true skill and - the number that
decides it - the pooled CSI actually realised by selecting on each feature, as a
recovery fraction ``(selected - random) / (oracle - random)``.

Two features need a climatology (per-lead exceedance profile, radial power
spectrum).  Those are estimated from truth in the *other* half of a two-fold
event split, never from the event being scored, so no per-event truth reaches a
verifier score.  Recorded in the report under ``uses_climatology``.

A combined ridge critic (within-event rank features, grouped CV over contiguous
event blocks) answers the weaker but sufficient question: is there *any* usable
signal in the feature set, even if no single feature carries it.  Written in
numpy - the box has no sklearn.

Usage:

    python tools/verifier_rank_gate.py \
        --input audit_outputs/band_spread_calibration/v4_validation_members.h5 \
        --output-dir audit_outputs/verifier_gate/v4_validation \
        --input-length 5
"""

import argparse
import json
import os
import sys
import warnings
from typing import Dict, List, Optional, Tuple

import h5py
import numpy as np

sys.path.append(os.getcwd())

THRESHOLDS: Tuple[float, ...] = (20.0, 30.0, 35.0, 40.0)
RADIAL_BINS = 16
AREA_THRESHOLD = 35.0

# Every feature is oriented "higher = the verifier believes this member is better",
# so a negative Spearman is informative (the feature is anti-predictive), not a
# sign-convention accident.
FEATURE_NAMES: Tuple[str, ...] = (
    "consensus_l2",       # -mean (member - ensemble mean)^2      typicality
    "consensus_l1_med",   # -mean |member - ensemble median|      robust typicality
    "lead0_agreement",    # -mean (member[0] - mean[0])^2         early divergence
    "temporal_smooth",    # -mean (x[t+1]-x[t])^2                 rollout roughness
    "boundary_smooth",    # -mean (x[L]-x[L-1])^2 at the AR seam  chunk-seam artifact
    "area_profile_clim",  # -||area>=thr profile - climatology||  needs climatology
    "spectrum_clim",      # -||radial log power - climatology||   needs climatology
    "area35_level",       # raw exceedance area, no reference     anti-feature control
    "p99_level",          # raw intensity tail level             anti-feature control
)
CLIMATOLOGY_FEATURES = ("area_profile_clim", "spectrum_clim")
PER_MEMBER_FEATURE_KEYS = (
    "consensus_l2", "consensus_l1_med", "lead0_agreement",
    "temporal_smooth", "boundary_smooth", "area35_level", "p99_level",
)


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
class RadialBinner:
    """Precomputed radial-frequency binning for a fixed field shape.

    The frequency grid comes from `fftfreq` on both axes rather than from a row
    index: an index-based construction silently mislabels the negative-frequency
    half, which is the bug found in the DRIFT-Net audit.  Binning is done with
    `bincount`, not a per-bin boolean mask, because the masked version costs
    RADIAL_BINS passes over every field and turns this script into hours.
    """

    def __init__(self, height: int, width: int, n_bins: int = RADIAL_BINS):
        fy = np.fft.fftfreq(height)[:, None]
        fx = np.fft.fftfreq(width)[None, :]
        radius = np.hypot(fy, fx).ravel()
        edges = np.linspace(0.0, radius.max() + 1e-9, n_bins + 1)
        self.n_bins = n_bins
        self.index = np.clip(np.digitize(radius, edges) - 1, 0, n_bins - 1).astype(np.intp)
        self.counts = np.maximum(np.bincount(self.index, minlength=n_bins), 1).astype(np.float64)

    def log_power(self, field: np.ndarray) -> np.ndarray:
        """Radially binned log10 power of `(T, H, W)`, averaged over T."""
        spec = (np.abs(np.fft.fft2(field, axes=(-2, -1))) ** 2).mean(axis=0).ravel()
        binned = np.bincount(self.index, weights=spec, minlength=self.n_bins) / self.counts
        return np.log10(binned + 1e-12)


def contingency(pred: np.ndarray, obs: np.ndarray, thr: float) -> Tuple[float, float, float]:
    """TP/FP/FN with the evaluator's '>=' convention."""
    p, o = pred >= thr, obs >= thr
    both = np.count_nonzero(p & o)
    return float(both), float(np.count_nonzero(p) - both), float(np.count_nonzero(o) - both)


def area_profile(field: np.ndarray, thr: float) -> np.ndarray:
    """Per-lead fraction of pixels >= thr, shape `(T,)`."""
    return (field >= thr).reshape(field.shape[0], -1).mean(axis=1).astype(np.float64)


# --------------------------------------------------------------------------
# pass 1 - one streaming scan over events
# --------------------------------------------------------------------------
def scan(
    path: str,
    input_length: int,
    window: str,
    max_events: Optional[int],
    progress_every: int,
) -> Dict[str, np.ndarray]:
    with h5py.File(path, "r") as handle:
        preds, truth = handle["predictions"], handle["truth"]
        n_all, n_members, total_leads = preds.shape[0], preds.shape[1], preds.shape[2]
        height, width = preds.shape[-2], preds.shape[-1]
        n = n_all if max_events is None else min(max_events, n_all)

        if window == "chunk2":
            lead_idx = list(range(input_length, total_leads))
        elif window == "chunk1":
            lead_idx = list(range(0, min(input_length, total_leads)))
        else:
            lead_idx = list(range(total_leads))
        if not lead_idx:
            raise ValueError(f"empty lead window for window={window!r}, input_length={input_length}")
        sel = np.asarray(lead_idx)
        # The autoregressive seam sits between lead L-1 and L in the *full* array;
        # it is read from the full event, not the scoring window, so window=chunk2
        # can still measure it.
        seam = input_length if 0 < input_length < total_leads else None

        binner = RadialBinner(height, width)
        n_thr, n_leads = len(THRESHOLDS), len(lead_idx)
        acc: Dict[str, np.ndarray] = {
            "tp": np.zeros((n, n_members, n_thr)),
            "fp": np.zeros((n, n_members, n_thr)),
            "fn": np.zeros((n, n_members, n_thr)),
            "tp_mean": np.zeros((n, n_thr)),
            "fp_mean": np.zeros((n, n_thr)),
            "fn_mean": np.zeros((n, n_thr)),
            "mse": np.zeros((n, n_members)),
            "truth_area": np.zeros((n, n_thr)),
            "member_area_prof": np.zeros((n, n_members, n_leads)),
            "member_spectrum": np.zeros((n, n_members, RADIAL_BINS)),
            "truth_area_prof": np.zeros((n, n_leads)),
            "truth_spectrum": np.zeros((n, RADIAL_BINS)),
        }
        for key in PER_MEMBER_FEATURE_KEYS:
            acc[key] = np.zeros((n, n_members))

        for i in range(n):
            members_full = np.asarray(preds[i], dtype=np.float32)
            obs = np.asarray(truth[i], dtype=np.float32)[sel]
            members = members_full[:, sel]
            ens_mean = members.mean(axis=0)
            ens_med = np.median(members, axis=0)

            for k, thr in enumerate(THRESHOLDS):
                tp, fp, fn = contingency(ens_mean, obs, thr)
                acc["tp_mean"][i, k] = tp
                acc["fp_mean"][i, k] = fp
                acc["fn_mean"][i, k] = fn
                acc["truth_area"][i, k] = float(np.mean(obs >= thr))

            acc["truth_area_prof"][i] = area_profile(obs, AREA_THRESHOLD)
            acc["truth_spectrum"][i] = binner.log_power(obs)

            for m in range(n_members):
                mem = members[m]
                for k, thr in enumerate(THRESHOLDS):
                    tp, fp, fn = contingency(mem, obs, thr)
                    acc["tp"][i, m, k] = tp
                    acc["fp"][i, m, k] = fp
                    acc["fn"][i, m, k] = fn
                acc["mse"][i, m] = float(np.mean((mem - obs) ** 2))

                acc["consensus_l2"][i, m] = -float(np.mean((mem - ens_mean) ** 2))
                acc["consensus_l1_med"][i, m] = -float(np.mean(np.abs(mem - ens_med)))
                acc["lead0_agreement"][i, m] = -float(np.mean((mem[0] - ens_mean[0]) ** 2))
                diff = np.diff(mem, axis=0)
                acc["temporal_smooth"][i, m] = -float(np.mean(diff**2)) if diff.size else 0.0
                if seam is not None:
                    step = members_full[m, seam] - members_full[m, seam - 1]
                    acc["boundary_smooth"][i, m] = -float(np.mean(step**2))
                acc["area35_level"][i, m] = float(np.mean(mem >= AREA_THRESHOLD))
                acc["p99_level"][i, m] = float(np.percentile(mem, 99.0))
                acc["member_area_prof"][i, m] = area_profile(mem, AREA_THRESHOLD)
                acc["member_spectrum"][i, m] = binner.log_power(mem)

            if progress_every and (i + 1) % progress_every == 0:
                print(f"  scanned {i + 1}/{n} events", flush=True)

    acc["n_events"] = n
    acc["n_members"] = n_members
    acc["lead_idx"] = np.asarray(lead_idx)
    acc["seam_lead"] = np.asarray([-1 if seam is None else seam])
    return acc


def add_climatology_features(acc: Dict[str, np.ndarray], seed: int) -> None:
    """Fill the two climatology-referenced features from the opposite fold's truth."""
    n, m = acc["n_events"], acc["n_members"]
    fold = np.random.default_rng(seed).integers(0, 2, size=n)
    acc["area_profile_clim"] = np.zeros((n, m))
    acc["spectrum_clim"] = np.zeros((n, m))
    for f in (0, 1):
        target, source = fold == f, fold != f
        if not np.any(source) or not np.any(target):
            continue
        clim_prof = acc["truth_area_prof"][source].mean(axis=0)
        clim_spec = acc["truth_spectrum"][source].mean(axis=0)
        acc["area_profile_clim"][target] = -np.sqrt(
            ((acc["member_area_prof"][target] - clim_prof[None, None, :]) ** 2).sum(axis=2)
        )
        acc["spectrum_clim"][target] = -np.sqrt(
            ((acc["member_spectrum"][target] - clim_spec[None, None, :]) ** 2).sum(axis=2)
        )
    acc["fold"] = fold


# --------------------------------------------------------------------------
# targets and pooled arms
# --------------------------------------------------------------------------
def per_event_csi(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray) -> np.ndarray:
    """Per-event CSI; NaN where the event has neither observed nor predicted pixels."""
    denom = tp + fp + fn
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(denom > 0, tp / np.maximum(denom, 1e-12), np.nan)


def pooled_csi(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray) -> float:
    s_tp, s_fp, s_fn = float(tp.sum()), float(fp.sum()), float(fn.sum())
    return s_tp / max(s_tp + s_fp + s_fn, 1.0)


def _pooled_row(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray,
                mse: Optional[np.ndarray] = None) -> Dict[str, float]:
    row = {}
    for k, thr in enumerate(THRESHOLDS):
        row[f"csi{int(thr)}"] = pooled_csi(tp[..., k], fp[..., k], fn[..., k])
    row["csi_M"] = float(np.mean([row[f"csi{int(t)}"] for t in THRESHOLDS]))
    if mse is not None:
        row["mse"] = float(np.mean(mse))
    return row


def selection_arms(
    acc: Dict[str, np.ndarray], target: np.ndarray, curve_draws: int = 20, seed: int = 42
) -> Dict[str, Dict[str, float]]:
    """Pooled arms, including the baseline that a *random selector* actually gets.

    ``random_pick`` (per event choose one member, then pool) and
    ``member_mean_over_index`` (use member j everywhere, average the scores over
    j) are different statistics - pooling is nonlinear, so they differ by a
    Jensen-type offset.  The recovery denominator has to be the first one,
    because that is what a verifier is competing against; the second is reported
    only to show how little the fixed member index matters.
    """
    n, m = acc["n_events"], acc["n_members"]
    tp, fp, fn = acc["tp"], acc["fp"], acc["fn"]
    arms: Dict[str, Dict[str, float]] = {
        "ens_mean": _pooled_row(acc["tp_mean"], acc["fp_mean"], acc["fn_mean"])
    }
    per_member = [_pooled_row(tp[:, j], fp[:, j], fn[:, j], acc["mse"][:, j]) for j in range(m)]
    arms["member_mean_over_index"] = {k: float(np.mean([r[k] for r in per_member])) for k in per_member[0]}
    arms["member_std_over_index"] = {k: float(np.std([r[k] for r in per_member])) for k in per_member[0]}
    single = best_of_n_curve(acc, target, (1,), curve_draws, seed)["1"]
    arms["random_pick"] = {k: v for k, v in single.items()
                           if not k.endswith("_std_over_draws") and k != "draws"}

    valid = np.isfinite(target)
    rows = np.arange(n)
    best = np.argmax(np.where(valid, target, -np.inf), axis=1)
    worst = np.argmin(np.where(valid, target, np.inf), axis=1)
    arms["oracle"] = _pooled_row(tp[rows, best], fp[rows, best], fn[rows, best], acc["mse"][rows, best])
    arms["antioracle"] = _pooled_row(tp[rows, worst], fp[rows, worst], fn[rows, worst], acc["mse"][rows, worst])
    return arms


def best_of_n_curve(
    acc: Dict[str, np.ndarray], target: np.ndarray, sizes: Tuple[int, ...], draws: int, seed: int
) -> Dict[str, Dict[str, float]]:
    """Oracle-selection skill as a function of ensemble size N.

    Answers the question a fixed-S file cannot answer directly: is the selection
    budget still growing at S, or has it saturated?  Subsets of size N are drawn
    without replacement per event and the *oracle* member within each subset is
    kept, so the curve is the ceiling for best-of-N at that N.  A curve that has
    flattened by S means no affordable increase in S rescues selection, which
    turns "no headroom at S=8" into "no headroom at any N".
    """
    n, m = acc["n_events"], acc["n_members"]
    rows = np.arange(n)
    out: Dict[str, Dict[str, float]] = {}
    for size in sizes:
        if size > m:
            continue
        rng = np.random.default_rng(seed + size)
        per_draw: List[Dict[str, float]] = []
        for _ in range(draws):
            sub = np.argsort(rng.random((n, m)), axis=1)[:, :size]
            sub_target = np.take_along_axis(target, sub, axis=1)
            local = np.argmax(np.where(np.isfinite(sub_target), sub_target, -np.inf), axis=1)
            pick = sub[rows, local]
            per_draw.append(
                _pooled_row(acc["tp"][rows, pick], acc["fp"][rows, pick],
                            acc["fn"][rows, pick], acc["mse"][rows, pick])
            )
        out[str(size)] = {
            **{k: float(np.mean([r[k] for r in per_draw])) for k in per_draw[0]},
            **{f"{k}_std_over_draws": float(np.std([r[k] for r in per_draw])) for k in per_draw[0]},
            "draws": draws,
        }
    return out


def advantage_diagnostics(reward: np.ndarray, label: str) -> Dict[str, object]:
    """GRPO's learning signal: within-group reward spread and degenerate groups."""
    r = reward[np.isfinite(reward).all(axis=1)]
    if r.size == 0:
        return {"label": label, "n_events_usable": 0}
    within = r.std(axis=1, ddof=1)
    per_event_mean = r.mean(axis=1)
    span = r.max(axis=1) - r.min(axis=1)
    between = float(per_event_mean.std(ddof=1))
    return {
        "label": label,
        "n_events_usable": int(r.shape[0]),
        "within_event_std_mean": float(within.mean()),
        "within_event_std_median": float(np.median(within)),
        "between_event_std": between,
        "within_over_between": float(within.mean() / max(between, 1e-12)),
        "within_event_range_mean": float(span.mean()),
        "relative_within_std_mean": float(np.mean(within / np.maximum(np.abs(per_event_mean), 1e-12))),
        "frac_degenerate_groups": float(np.mean(span <= 1e-9)),
        "frac_groups_range_below_0p01": float(np.mean(span < 0.01)),
    }


# --------------------------------------------------------------------------
# Stage B - ranking quality
# --------------------------------------------------------------------------
def avg_rank(x: np.ndarray) -> np.ndarray:
    """Average ranks along axis 1 (ties shared), vectorised over events."""
    from scipy.stats import rankdata

    return rankdata(x, axis=1).astype(np.float64)


def within_event_spearman(feature: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Spearman rho per event across members, vectorised (Pearson on average ranks)."""
    ok = np.isfinite(feature).all(axis=1) & np.isfinite(target).all(axis=1)
    out = np.full(feature.shape[0], np.nan)
    if not np.any(ok):
        return out
    rf, rt = avg_rank(feature[ok]), avg_rank(target[ok])
    rf = rf - rf.mean(axis=1, keepdims=True)
    rt = rt - rt.mean(axis=1, keepdims=True)
    num = (rf * rt).sum(axis=1)
    den = np.sqrt((rf**2).sum(axis=1) * (rt**2).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
    out[ok] = rho
    return out


def event_bootstrap_mean(values: np.ndarray, iterations: int, seed: int) -> Dict[str, float]:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n": 0}
    rng = np.random.default_rng(seed)
    draws = v[rng.integers(0, v.size, size=(iterations, v.size))].mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"mean": float(v.mean()), "ci_low": float(lo), "ci_high": float(hi), "n": int(v.size)}


def realised_selection(
    acc: Dict[str, np.ndarray], score: np.ndarray, arms: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """Pooled metrics from argmax(score) per event, and recovery of the oracle budget."""
    n = acc["n_events"]
    rows = np.arange(n)
    usable = np.isfinite(score).any(axis=1)
    pick = np.argmax(np.where(np.isfinite(score), score, -np.inf), axis=1)
    pick[~usable] = 0  # documented fallback; counted below
    out = _pooled_row(acc["tp"][rows, pick], acc["fp"][rows, pick], acc["fn"][rows, pick],
                      acc["mse"][rows, pick])
    out["n_fallback_to_member0"] = int(np.count_nonzero(~usable))
    rnd, orc = arms["random_pick"], arms["oracle"]
    for key in ("csi30", "csi35", "csi40", "csi_M"):
        budget = orc[key] - rnd[key]
        out[f"recovery_{key}"] = float((out[key] - rnd[key]) / budget) if abs(budget) > 1e-12 else float("nan")
    return out


def rank_center(x: np.ndarray) -> np.ndarray:
    """Average ranks along members, centred and scaled to roughly [-1, 1]."""
    r = avg_rank(x)
    m = x.shape[1]
    return (r - (m + 1) / 2.0) / max((m - 1) / 2.0, 1e-12)


def ridge_critic_cv(
    features: np.ndarray, target: np.ndarray, n_folds: int, alpha: float
) -> Tuple[np.ndarray, Dict[str, object]]:
    """Grouped-CV ridge on within-event ranks. numpy only - the box has no sklearn.

    Folds are contiguous event blocks, not random events: neighbouring events in
    a validation split can share weather, and random folds would let the critic
    see the same storm on both sides of the split.
    """
    n, m, p = features.shape
    keep = np.isfinite(target).all(axis=1) & np.isfinite(features).all(axis=(1, 2))
    idx = np.nonzero(keep)[0]
    pred = np.full((n, m), np.nan)
    if idx.size < max(n_folds * 4, 20):
        return pred, {"note": "too few usable events for CV", "n_usable": int(idx.size)}

    xr = np.stack([rank_center(features[idx, :, j]) for j in range(p)], axis=-1)  # (K, m, p)
    yr = rank_center(target[idx])
    blocks = np.array_split(np.arange(idx.size), n_folds)
    coefs: List[np.ndarray] = []
    for f in range(n_folds):
        test = blocks[f]
        train = np.concatenate([blocks[g] for g in range(n_folds) if g != f])
        xt, yt = xr[train].reshape(-1, p), yr[train].reshape(-1)
        w = np.linalg.solve(xt.T @ xt + alpha * np.eye(p), xt.T @ yt)
        coefs.append(w)
        pred[idx[test]] = xr[test] @ w
    return pred, {
        "n_usable": int(idx.size),
        "n_folds": n_folds,
        "alpha": alpha,
        "coef_mean": [float(v) for v in np.mean(coefs, axis=0)],
        "coef_std": [float(v) for v in np.std(coefs, axis=0)],
    }


# --------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--input-length", type=int, default=5,
                        help="chunk length; leads >= this form the autoregressive chunk")
    parser.add_argument("--window", choices=("chunk2", "all", "chunk1"), default="chunk2")
    parser.add_argument("--selection-target", default="csi35",
                        choices=("csi35", "csi40", "csi_M", "neg_mse"))
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--ridge-alpha", type=float, default=10.0)
    parser.add_argument("--curve-draws", type=int, default=20,
                        help="random subsets per N for the best-of-N ceiling curve")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--progress-every", type=int, default=200)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    with h5py.File(args.input, "r") as handle:
        manifest = json.loads(handle.attrs.get("manifest_json", "{}"))

    acc = scan(args.input, args.input_length, args.window, args.max_events, args.progress_every)
    add_climatology_features(acc, args.seed)
    n, m = acc["n_events"], acc["n_members"]
    print(f"scanned {n} events x {m} members; window leads {acc['lead_idx'].tolist()}, "
          f"seam lead {int(acc['seam_lead'][0])}", flush=True)

    csi_thr = {
        int(thr): per_event_csi(acc["tp"][..., k], acc["fp"][..., k], acc["fn"][..., k])
        for k, thr in enumerate(THRESHOLDS)
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        csi_m = np.nanmean(np.stack([csi_thr[int(t)] for t in THRESHOLDS], axis=-1), axis=-1)
    targets = {"csi35": csi_thr[35], "csi40": csi_thr[40], "csi_M": csi_m, "neg_mse": -acc["mse"]}
    sel_target = targets[args.selection_target]
    arms = selection_arms(acc, sel_target, args.curve_draws, args.seed)

    report: Dict[str, object] = {
        "input": os.path.abspath(args.input),
        "input_manifest": manifest,
        "config": vars(args),
        "window_leads": acc["lead_idx"].tolist(),
        "seam_lead": int(acc["seam_lead"][0]),
        "n_events": int(n),
        "n_members": int(m),
        "stage_a_arms": arms,
        "stage_a_best_of_n_curve": best_of_n_curve(
            acc, sel_target, (1, 2, 3, 4, 6, 8), args.curve_draws, args.seed
        ),
        "stage_a_headroom": {},
        "stage_a_advantage": {k: advantage_diagnostics(v, k) for k, v in targets.items()},
        "target_coverage": {
            f"csi{int(t)}_events_all_members_defined":
                int(np.isfinite(csi_thr[int(t)]).all(axis=1).sum()) for t in THRESHOLDS
        },
        "truth_area_mean": {
            f"thr{int(t)}": float(acc["truth_area"][:, k].mean()) for k, t in enumerate(THRESHOLDS)
        },
    }
    rnd, orc, ensm = arms["random_pick"], arms["oracle"], arms["ens_mean"]
    for key in ("csi30", "csi35", "csi40", "csi_M"):
        report["stage_a_headroom"][key] = {
            "random_pick": rnd[key],
            "member_mean_over_index": arms["member_mean_over_index"][key],
            "ens_mean": ensm[key],
            "oracle": orc[key],
            "antioracle": arms["antioracle"][key],
            "oracle_minus_random_abs": orc[key] - rnd[key],
            "oracle_minus_random_rel_pct": 100.0 * (orc[key] - rnd[key]) / max(rnd[key], 1e-12),
            "oracle_minus_ensmean_rel_pct": 100.0 * (orc[key] - ensm[key]) / max(ensm[key], 1e-12),
        }

    feats = np.stack([acc[name] for name in FEATURE_NAMES], axis=-1)
    stage_b: Dict[str, object] = {"features": {}, "uses_climatology": list(CLIMATOLOGY_FEATURES)}
    for fi, name in enumerate(FEATURE_NAMES):
        entry: Dict[str, object] = {}
        for tname, tvals in targets.items():
            rho = within_event_spearman(feats[..., fi], tvals)
            entry[f"spearman_vs_{tname}"] = event_bootstrap_mean(rho, args.bootstrap, args.seed + fi)
        entry["realised_selection"] = realised_selection(acc, feats[..., fi], arms)
        stage_b["features"][name] = entry

    critic_pred, critic_meta = ridge_critic_cv(feats, sel_target, args.folds, args.ridge_alpha)
    critic_meta["feature_names"] = list(FEATURE_NAMES)
    rho = within_event_spearman(critic_pred, sel_target)
    stage_b["ridge_critic"] = {
        "meta": critic_meta,
        f"spearman_vs_{args.selection_target}": event_bootstrap_mean(rho, args.bootstrap, args.seed),
        "realised_selection": realised_selection(acc, critic_pred, arms),
    }
    report["stage_b"] = stage_b

    out_json = os.path.join(args.output_dir, "verifier_gate_report.json")
    with open(out_json, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    np.savez_compressed(
        os.path.join(args.output_dir, "per_member_features.npz"),
        features=feats.astype(np.float32),
        feature_names=np.array(FEATURE_NAMES),
        fold=acc["fold"],
        **{f"target_{k}": v.astype(np.float32) for k, v in targets.items()},
    )

    print("\n=== Stage A: selection headroom (pooled, window=%s) ===" % args.window)
    print("%-26s %8s %8s %8s %8s" % ("arm", "csi30", "csi35", "csi40", "csi_M"))
    for name in ("ens_mean", "random_pick", "member_mean_over_index", "oracle", "antioracle"):
        a = arms[name]
        print("%-26s %8.4f %8.4f %8.4f %8.4f" % (name, a["csi30"], a["csi35"], a["csi40"], a["csi_M"]))
    print("  member-index std: csi35=%.4f csi40=%.4f"
          % (arms["member_std_over_index"]["csi35"], arms["member_std_over_index"]["csi40"]))
    for key in ("csi30", "csi35", "csi40", "csi_M"):
        h = report["stage_a_headroom"][key]
        print("  budget %-6s oracle-random_pick = %+.4f (%+.2f%% rel) | oracle-ensmean = %+.2f%% rel"
              % (key, h["oracle_minus_random_abs"], h["oracle_minus_random_rel_pct"],
                 h["oracle_minus_ensmean_rel_pct"]))

    print("\n=== Stage A: best-of-N oracle ceiling (target=%s) ===" % args.selection_target)
    curve = report["stage_a_best_of_n_curve"]
    base = curve.get("1", {}).get("csi35")
    print("%-4s %8s %8s %8s %8s %14s" % ("N", "csi30", "csi35", "csi40", "csi_M", "d(csi35) vs N=1"))
    for size in sorted(curve, key=int):
        c = curve[size]
        gain = "" if base in (None, 0) else "%+13.2f%%" % (100.0 * (c["csi35"] - base) / base)
        print("%-4s %8.4f %8.4f %8.4f %8.4f %14s"
              % (size, c["csi30"], c["csi35"], c["csi40"], c["csi_M"], gain))

    print("\n=== Stage A: GRPO advantage signal (within-group reward spread) ===")
    for k, d in report["stage_a_advantage"].items():
        if d.get("n_events_usable"):
            print("  %-8s within_std=%.5f between_std=%.5f ratio=%.3f range=%.5f "
                  "rel_within=%.3f degenerate=%.2f%%"
                  % (k, d["within_event_std_mean"], d["between_event_std"], d["within_over_between"],
                     d["within_event_range_mean"], d["relative_within_std_mean"],
                     100 * d["frac_degenerate_groups"]))

    print("\n=== Stage B: verifier ranking (target=%s) ===" % args.selection_target)
    print("%-20s %22s %12s %12s" % ("feature", "rho [95% CI]", "recov_csi35", "recov_csi40"))
    for name in list(FEATURE_NAMES) + ["RIDGE_CRITIC(cv)"]:
        e = stage_b["features"][name] if name in stage_b["features"] else stage_b["ridge_critic"]
        key = f"spearman_vs_{args.selection_target}"
        s, r = e[key], e["realised_selection"]
        print("%-20s %+.3f [%+.3f,%+.3f] %+12.3f %+12.3f"
              % (name, s["mean"], s["ci_low"], s["ci_high"], r["recovery_csi35"], r["recovery_csi40"]))
    print("\nreport: %s" % out_json)


if __name__ == "__main__":
    main()
