"""Frozen, test-blind checkpoint-selection rule + offline scoring.

Why this file exists
--------------------
CIKM's validation split is much wetter than its test split (measured
2026-07-26: pixels >=30 dBZ are 24.96% of validation targets but only 7.75%
of test targets; >=40 dBZ is 4.32% vs 0.89%).  Selecting checkpoints by
``partial_csi_m`` -- a micro-averaged CSI over that wet validation subset --
therefore ranks checkpoints by how well they do on wet events, which is not
the regime the test set is in.  The SimVP calibration run showed this
failure directly: validation CSI-M went +6.8% between epoch 48 and 68 while
test CSI-M went -1.4%.

The fix here is a *selector*, not a new reported metric.  Final numbers are
still the official micro CSI-M produced by ``test_flowcast.py``.  What
changes is which checkpoint gets carried to the test set.

Design constraints (frozen before any checkpoint is ranked):

1. Intensity strata are defined by the official evaluation thresholds
   (20/30/35/40 dBZ) only -- no new tuning constants.
2. Stratum boundaries are quantiles of the **training** split.  The test
   split's wetness (7.75% / 0.89%) is never used as a resampling target;
   doing so would be test-informed model selection.
3. Strata are weighted equally by default: absent a known deployment
   climatology, every intensity regime gets an equal say.  This is what
   pulls the selector away from the wet-dominated micro average.
4. Validation is split into ``dev`` (drives selection) and ``shadow``
   (touched once, to check the selector did not just overfit ``dev``).
5. Every choice above is serialised to a JSON rule file with a content
   hash.  Scoring code refuses to run against a rule whose hash does not
   match its contents.

Severity statistic
------------------
For a target sequence ``y`` on the dBZ evaluation scale::

    sev(e) = mean over (lead time, pixel) of  #{theta in THETA : y > theta}

which is the mean per-pixel exceedance count, in [0, |THETA|].  It is
monotone in both intensity and area, uses exactly the official thresholds
and the official strict-``>`` comparison, and introduces no free constants.
(The same "count of thresholds exceeded" construction was used as the
joint-histogram key ``L`` in the SDIR G1b calibration audit.)
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Official CIKM evaluation thresholds (dBZ).  Kept here so the selector can
# never silently drift from experiments/cikm/.../*.yaml evaluation_params.
THRESHOLDS_CIKM: Tuple[float, ...] = (20.0, 30.0, 35.0, 40.0)

RULE_SCHEMA_VERSION = 1


# --------------------------------------------------------------------------
# severity
# --------------------------------------------------------------------------
def severity_from_targets(
    targets: np.ndarray, thresholds: Sequence[float]
) -> np.ndarray:
    """Mean per-pixel exceedance count for a batch of target sequences.

    Args:
        targets: (B, T, H, W) on the evaluation scale (dBZ for CIKM), already
            cropped exactly as the evaluator crops.
        thresholds: the official evaluation thresholds.

    Returns:
        (B,) float64 severity in [0, len(thresholds)].
    """
    if targets.ndim != 4:
        raise ValueError(f"expected (B, T, H, W), got {targets.shape}")
    y = targets.astype(np.float32, copy=False)
    counts = np.zeros(y.shape[0], dtype=np.float64)
    for th in thresholds:
        # strict ">" matches MetricsAccumulator / CRFT's evaluator on this data
        counts += (y > np.float32(th)).sum(axis=(1, 2, 3))
    npix = float(y.shape[1] * y.shape[2] * y.shape[3])
    return counts / npix


def compute_split_severity(
    h5_path: str,
    meta_csv: str,
    *,
    data_key: str = "vil",
    raw_seq_len: int = 15,
    lag_time: int = 5,
    lead_time: int = 10,
    time_spacing: int = 1,
    stride: int = 1,
    crop: Optional[Tuple[int, int]] = (13, -14),
    pixel_scale: float = 90.0,
    chunk: int = 128,
    progress: bool = True,
) -> Dict[str, np.ndarray]:
    """Severity of every event in a split, using the evaluator's own view.

    Reads only the target frames, applies the same crop and the same
    ``raw * pixel_scale / 255`` rescaling that ``test_flowcast.py`` applies
    to ground truth, then computes :func:`severity_from_targets`.

    No model is loaded; this is a pure data pass.
    """
    import h5py
    import pandas as pd

    meta = pd.read_csv(meta_csv)
    n_events = len(meta)
    if n_events == 0:
        raise ValueError(f"empty metadata: {meta_csv}")
    col = "file_row" if "file_row" in meta.columns else "file_index"
    file_rows = meta[col].to_numpy(dtype=np.int64)

    seq_len = (lag_time + lead_time) * time_spacing
    if raw_seq_len < seq_len:
        raise ValueError("raw_seq_len smaller than (lag+lead)*time_spacing")
    # One stratum label per *event* only makes sense when the sliding window
    # yields exactly one sequence per event, which is the CIKM case
    # (raw_seq_len 15 == seq_len 15).  Otherwise event_id would no longer
    # equal the dataset index and the strata would silently misalign.
    n_seq_per_event = 1 + (raw_seq_len - seq_len) // max(stride, 1)
    if n_seq_per_event != 1:
        raise ValueError(
            f"this rule assumes one sequence per event, but the sliding "
            f"window yields {n_seq_per_event} (raw_seq_len={raw_seq_len}, "
            f"seq_len={seq_len}, stride={stride})"
        )
    # Mirror DynamicSequentialSevirDataset.__getitem__ target indexing.
    y_end = seq_len - 1
    y_idx = sorted(y_end - i * time_spacing for i in range(lead_time))

    sev = np.zeros(n_events, dtype=np.float64)
    scale = np.float32(pixel_scale / 255.0)

    with h5py.File(h5_path, "r") as f:
        dset = f[data_key]
        for start in range(0, n_events, chunk):
            stop = min(start + chunk, n_events)
            rows = file_rows[start:stop]
            # h5py fancy indexing needs sorted, unique indices
            order = np.argsort(rows, kind="stable")
            block = dset[np.asarray(rows)[order]]  # (b, H, W, raw_seq_len)
            inv = np.empty_like(order)
            inv[order] = np.arange(len(order))
            block = block[inv]

            y = block[..., y_idx]  # (b, H, W, T)
            y = np.transpose(y, (0, 3, 1, 2))  # (b, T, H, W)
            if crop is not None:
                lo, hi = crop
                y = y[:, :, lo:hi, lo:hi]
            y = y.astype(np.float32) * scale
            sev[start:stop] = severity_from_targets(y, THRESHOLDS_CIKM)
            if progress:
                print(f"  severity {stop}/{n_events}", flush=True)

    return {
        "event_id": np.arange(n_events, dtype=np.int64),
        "file_row": file_rows,
        "severity": sev,
    }


# --------------------------------------------------------------------------
# strata + split
# --------------------------------------------------------------------------
def quantile_boundaries(sev_train: np.ndarray, n_strata: int) -> np.ndarray:
    """Equal-count stratum cut points from the TRAIN split severity.

    Duplicated cut points (which happen when a large fraction of training
    events share the same severity, e.g. many all-dry events) are collapsed,
    so the realised number of strata can be smaller than ``n_strata``.  That
    collapse is recorded in the rule file rather than silently fixed.
    """
    if n_strata < 2:
        raise ValueError("n_strata must be >= 2")
    qs = np.linspace(0.0, 1.0, n_strata + 1)[1:-1]
    cuts = np.quantile(sev_train, qs)
    cuts = np.unique(np.round(cuts, 12))
    return cuts.astype(np.float64)


def assign_strata(sev: np.ndarray, boundaries: np.ndarray) -> np.ndarray:
    """Map severity to stratum index 0..len(boundaries)."""
    return np.searchsorted(boundaries, sev, side="right").astype(np.int64)


def stratified_dev_shadow_split(
    strata: np.ndarray, frac_dev: float, seed: int
) -> np.ndarray:
    """Deterministic stratified split of validation events.

    Returns an int array: 1 = dev (drives selection), 0 = shadow (held out).
    Within each stratum, ``round(n_k * frac_dev)`` events go to dev.
    """
    if not (0.0 < frac_dev < 1.0):
        raise ValueError("frac_dev must be in (0, 1)")
    rng = np.random.default_rng(seed)
    is_dev = np.zeros(len(strata), dtype=np.int64)
    for k in np.unique(strata):
        idx = np.flatnonzero(strata == k)
        perm = rng.permutation(idx)
        n_dev = int(round(len(idx) * frac_dev))
        n_dev = min(max(n_dev, 1), len(idx) - 1) if len(idx) >= 2 else len(idx)
        is_dev[perm[:n_dev]] = 1
    return is_dev


# --------------------------------------------------------------------------
# the frozen rule
# --------------------------------------------------------------------------
@dataclass
class SelectionRule:
    """Everything that must be fixed before any checkpoint is scored."""

    schema_version: int
    dataset_name: str
    thresholds: List[float]
    pixel_scale: float
    crop: Optional[List[int]]

    # strata
    n_strata_requested: int
    boundaries: List[float]            # from TRAIN severity quantiles
    n_strata_realised: int
    stratum_weights: str               # "equal" | "train_frequency"
    empty_cell_policy: str             # "exclude"

    # dev / shadow
    split_seed: int
    frac_dev: float

    # selector
    selector_order: List[str]          # lexicographic keys
    epsilon_rule: str                  # how the "close enough" band is derived
    bootstrap_B: int
    bootstrap_seed: int

    # protocol that dumps must match to be comparable
    stage1_samples: int
    stage2_samples: int
    stage1_batch_size: int
    stage2_batch_size: int
    euler_steps: int
    dtype: str
    seed_formula: str
    base_seed: int

    # provenance
    train_h5_sha256: str
    val_h5_sha256: str
    created_utc: str
    notes: str = ""

    # per-validation-event assignment (parallel arrays)
    val_event_id: List[int] = field(default_factory=list)
    val_file_row: List[int] = field(default_factory=list)
    val_severity: List[float] = field(default_factory=list)
    val_stratum: List[int] = field(default_factory=list)
    val_is_dev: List[int] = field(default_factory=list)

    # ---------------------------------------------------------------
    def payload_hash(self) -> str:
        d = asdict(self)
        d.pop("rule_sha256", None)
        blob = json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def save(self, path: str) -> str:
        d = asdict(self)
        d["rule_sha256"] = self.payload_hash()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            json.dump(d, f, indent=2, sort_keys=True)
        return d["rule_sha256"]

    @staticmethod
    def load(path: str) -> "SelectionRule":
        with open(path) as f:
            d = json.load(f)
        stored = d.pop("rule_sha256", None)
        rule = SelectionRule(**d)
        if stored is not None and rule.payload_hash() != stored:
            raise ValueError(
                f"selection rule {path} has been edited after freezing "
                f"(stored sha256 {stored[:12]}..., recomputed "
                f"{rule.payload_hash()[:12]}...).  Re-freeze it explicitly "
                f"instead of hand-editing, or the selection is no longer "
                f"blind."
            )
        return rule

    # ---------------------------------------------------------------
    @property
    def strata(self) -> np.ndarray:
        return np.asarray(self.val_stratum, dtype=np.int64)

    @property
    def is_dev(self) -> np.ndarray:
        return np.asarray(self.val_is_dev, dtype=np.int64)

    def event_mask(self, split: str) -> np.ndarray:
        """Boolean mask over validation events for 'dev' | 'shadow' | 'all'."""
        if split == "dev":
            return self.is_dev == 1
        if split == "shadow":
            return self.is_dev == 0
        if split == "all":
            return np.ones(len(self.val_event_id), dtype=bool)
        raise ValueError(f"unknown split: {split}")


def sha256_file(path: str, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------
# scoring primitives (operate on per-event contingency dumps)
# --------------------------------------------------------------------------
def csi_grid(tp: np.ndarray, fn: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Pooled CSI on a (T, Q) grid; NaN where the denominator is empty."""
    denom = tp + fn + fp
    out = np.full(denom.shape, np.nan, dtype=np.float64)
    nz = denom > 0
    out[nz] = tp[nz] / denom[nz]
    return out


def official_csi_m(
    tp: np.ndarray, fn: np.ndarray, fp: np.ndarray, mask: np.ndarray
) -> float:
    """Micro CSI-M in the published convention.

    Pool hits/misses/false-alarms over all selected events (accumulate then
    divide), per lead time and threshold; average over thresholds, then over
    lead times.  Same family as ``MetricsAccumulator`` + ``calculate_metrics``
    and as CRFT/SDIR's ``helpers/evaluation.py``.
    """
    grid = csi_grid(tp[mask].sum(0), fn[mask].sum(0), fp[mask].sum(0))
    return float(np.nanmean(grid))


def balanced_score(
    tp: np.ndarray,
    fn: np.ndarray,
    fp: np.ndarray,
    strata: np.ndarray,
    mask: np.ndarray,
    weights: Optional[Dict[int, float]] = None,
) -> Tuple[float, Dict[int, float], int]:
    """S_balanced: intensity-stratum-averaged CSI.

        S = sum_k w_k * mean_{t, theta} CSI_k(t, theta)

    with ``w_k`` equal by default.  Within a stratum the pooling is micro
    (accumulate then divide), i.e. the same estimator family as the official
    metric -- only the aggregation across events changes.

    Returns (S, per-stratum score, number of excluded empty cells).
    """
    ks = np.unique(strata[mask])
    per_k: Dict[int, float] = {}
    n_empty = 0
    for k in ks:
        sel = mask & (strata == k)
        grid = csi_grid(tp[sel].sum(0), fn[sel].sum(0), fp[sel].sum(0))
        n_empty += int(np.isnan(grid).sum())
        per_k[int(k)] = float(np.nanmean(grid))
    if weights is None:
        s = float(np.mean([per_k[int(k)] for k in ks]))
    else:
        w = np.array([weights.get(int(k), 0.0) for k in ks], dtype=np.float64)
        if w.sum() <= 0:
            raise ValueError("stratum weights sum to zero")
        w = w / w.sum()
        s = float(np.sum(w * np.array([per_k[int(k)] for k in ks])))
    return s, per_k, n_empty


# --------------------------------------------------------------------------
# stratified event-level bootstrap
# --------------------------------------------------------------------------
def bootstrap_multiplicities(
    strata: np.ndarray, mask: np.ndarray, B: int, seed: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Stratified event-level bootstrap resampling weights.

    Returns ``(event_index, W)`` where ``event_index`` lists the selected
    events and ``W`` is (B, n_selected) giving how many times each event was
    drawn in each replicate.  Resampling happens *within* stratum with the
    stratum's own size preserved, which is the pairing that matches the
    stratified estimator.

    The same ``W`` must be reused across checkpoints so differences are
    paired.
    """
    rng = np.random.default_rng(seed)
    idx = np.flatnonzero(mask)
    pos = {int(e): i for i, e in enumerate(idx)}
    W = np.zeros((B, len(idx)), dtype=np.float64)
    for k in np.unique(strata[mask]):
        members = np.flatnonzero(mask & (strata == k))
        cols = np.array([pos[int(m)] for m in members])
        n = len(members)
        draws = rng.integers(0, n, size=(B, n))
        for b in range(B):
            counts = np.bincount(draws[b], minlength=n)
            W[b, cols] += counts
    return idx, W


def bootstrap_balanced(
    tp: np.ndarray,
    fn: np.ndarray,
    fp: np.ndarray,
    strata: np.ndarray,
    idx: np.ndarray,
    W: np.ndarray,
) -> np.ndarray:
    """S_balanced for every bootstrap replicate.  Returns (B,)."""
    B = W.shape[0]
    T, Q = tp.shape[1], tp.shape[2]
    flat = T * Q
    ks = np.unique(strata[idx])
    per_k = np.empty((len(ks), B), dtype=np.float64)
    for i, k in enumerate(ks):
        cols = np.flatnonzero(strata[idx] == k)
        Wk = W[:, cols]
        a = (Wk @ tp[idx][cols].reshape(len(cols), flat)).reshape(B, T, Q)
        b = (Wk @ fn[idx][cols].reshape(len(cols), flat)).reshape(B, T, Q)
        c = (Wk @ fp[idx][cols].reshape(len(cols), flat)).reshape(B, T, Q)
        denom = a + b + c
        with np.errstate(invalid="ignore", divide="ignore"):
            grid = np.where(denom > 0, a / denom, np.nan)
        per_k[i] = np.nanmean(grid.reshape(B, flat), axis=1)
    return per_k.mean(axis=0)


def epsilon_from_bootstrap(samples: np.ndarray, n_se: float = 1.0) -> float:
    """The frozen 'close enough' band: ``n_se`` bootstrap standard errors."""
    return float(n_se * np.std(samples, ddof=1))
