"""Offline tests for the checkpoint-selection rule.  No GPU, no dataset.

The point of the balanced selector is that it can disagree with the
wet-dominated micro average; ``test_balanced_can_disagree_with_micro`` locks
that behaviour down, because if it could not disagree the whole exercise
would be pointless.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.append(os.getcwd())

from tools.selection_rule import (
    THRESHOLDS_CIKM,
    SelectionRule,
    assign_strata,
    balanced_score,
    bootstrap_balanced,
    bootstrap_multiplicities,
    csi_grid,
    epsilon_from_bootstrap,
    official_csi_m,
    quantile_boundaries,
    severity_from_targets,
    stratified_dev_shadow_split,
)


# ---------------------------------------------------------------- severity
def test_severity_counts_thresholds_exceeded():
    # 1 frame, 2x2.  Values chosen to sit in distinct threshold bands.
    y = np.array([[[[0.0, 25.0], [33.0, 45.0]]]], dtype=np.float32)
    # exceedance counts: 0 -> 0, 25 -> 1 (>20), 33 -> 2 (>20,>30),
    # 45 -> 4 (>20,>30,>35,>40).  total 7 over 4 pixels.
    sev = severity_from_targets(y, THRESHOLDS_CIKM)
    assert sev.shape == (1,)
    assert sev[0] == pytest.approx(7.0 / 4.0)


def test_severity_is_strictly_greater_not_geq():
    # exactly 20.0 must NOT count: the evaluator uses ">"
    y = np.full((1, 1, 2, 2), 20.0, dtype=np.float32)
    assert severity_from_targets(y, THRESHOLDS_CIKM)[0] == 0.0


def test_severity_monotone_in_intensity():
    base = np.zeros((3, 2, 4, 4), dtype=np.float32)
    base[1] = 25.0
    base[2] = 45.0
    sev = severity_from_targets(base, THRESHOLDS_CIKM)
    assert sev[0] < sev[1] < sev[2]


# ------------------------------------------------------------------ strata
def test_quantile_boundaries_split_train_into_equal_counts():
    sev = np.linspace(0, 4, 1000)
    b = quantile_boundaries(sev, 4)
    assert len(b) == 3
    strata = assign_strata(sev, b)
    counts = np.bincount(strata, minlength=4)
    assert counts.min() >= 240 and counts.max() <= 260


def test_quantile_boundaries_collapse_on_ties_instead_of_faking_strata():
    # 80% of events are bone dry -> the low quantiles all land on 0.0
    sev = np.concatenate([np.zeros(800), np.linspace(0.1, 3.0, 200)])
    b = quantile_boundaries(sev, 4)
    assert len(np.unique(b)) == len(b)  # deduplicated
    assert len(b) < 3  # fewer strata than requested, recorded honestly


def test_assign_strata_uses_half_open_intervals():
    b = np.array([1.0, 2.0])
    got = assign_strata(np.array([0.5, 1.0, 1.5, 2.0, 2.5]), b)
    # stratum k = #{boundaries <= sev}, i.e. intervals [b_{k-1}, b_k):
    # a value sitting exactly on a boundary belongs to the UPPER stratum.
    assert got.tolist() == [0, 1, 1, 2, 2]


# ------------------------------------------------------------------- split
def test_stratified_split_is_deterministic_and_covers_every_stratum():
    strata = np.repeat([0, 1, 2, 3], 50)
    a = stratified_dev_shadow_split(strata, 0.5, seed=7)
    b = stratified_dev_shadow_split(strata, 0.5, seed=7)
    assert np.array_equal(a, b)
    c = stratified_dev_shadow_split(strata, 0.5, seed=8)
    assert not np.array_equal(a, c)
    for k in range(4):
        sel = strata == k
        assert a[sel].sum() == 25
        assert (1 - a[sel]).sum() == 25


def test_tiny_stratum_still_contributes_to_both_sides():
    strata = np.array([0] * 100 + [1] * 3)
    s = stratified_dev_shadow_split(strata, 0.5, seed=1)
    assert 1 <= s[strata == 1].sum() <= 2


# ------------------------------------------------------------------ scoring
def test_csi_grid_marks_empty_denominator_as_nan():
    tp = np.array([[1, 0]]); fn = np.array([[1, 0]]); fp = np.array([[0, 0]])
    g = csi_grid(tp, fn, fp)
    assert g[0, 0] == pytest.approx(0.5)
    assert np.isnan(g[0, 1])


def test_official_csi_m_is_accumulate_then_divide():
    # two events, 1 lead, 1 threshold.  Pooled CSI = 3/(3+1+1) = 0.6,
    # which is NOT the mean of the per-event CSIs (1.0 and 0.5).
    tp = np.array([[[2]], [[1]]]); fn = np.array([[[0]], [[1]]])
    fp = np.array([[[0]], [[1]]])
    mask = np.array([True, True])
    assert official_csi_m(tp, fn, fp, mask) == pytest.approx(3 / 5)


def test_balanced_score_equals_micro_when_strata_are_homogeneous():
    rng = np.random.default_rng(0)
    n, T, Q = 40, 2, 2
    tp = rng.integers(5, 10, (n, T, Q))
    fn = np.full((n, T, Q), 3)
    fp = np.full((n, T, Q), 2)
    strata = np.zeros(n, dtype=np.int64)  # a single stratum
    mask = np.ones(n, dtype=bool)
    s, per_k, _ = balanced_score(tp, fn, fp, strata, mask)
    assert s == pytest.approx(official_csi_m(tp, fn, fp, mask))
    assert list(per_k) == [0]


def test_balanced_can_disagree_with_micro():
    """The reason this selector exists.

    Checkpoint A is better on a small number of very wet events; B is better
    on the many dry ones.  Micro CSI-M is dominated by the wet events and
    prefers A; equal-weight-per-stratum prefers B.  On CIKM the test split is
    the dry regime, so the micro preference is exactly the trap.
    """
    T = Q = 1
    n_dry, n_wet = 90, 10
    strata = np.array([0] * n_dry + [1] * n_wet)
    mask = np.ones(n_dry + n_wet, dtype=bool)

    def build(dry_tp, wet_tp):
        tp = np.concatenate([np.full((n_dry, T, Q), dry_tp),
                             np.full((n_wet, T, Q), wet_tp)])
        # dry events carry 10 truth pixels each, wet events carry 1000
        fn = np.concatenate([np.full((n_dry, T, Q), 10 - dry_tp),
                             np.full((n_wet, T, Q), 1000 - wet_tp)])
        fp = np.zeros_like(tp)
        return tp, fn, fp

    A = build(4, 800)   # weak on dry, strong on wet
    B = build(7, 700)   # strong on dry, weaker on wet

    micro_A = official_csi_m(*A, mask)
    micro_B = official_csi_m(*B, mask)
    bal_A = balanced_score(*A, strata, mask)[0]
    bal_B = balanced_score(*B, strata, mask)[0]

    assert micro_A > micro_B, "wet events should dominate the micro average"
    assert bal_B > bal_A, "equal stratum weights should flip the preference"


def test_balanced_score_respects_custom_weights():
    T = Q = 1
    strata = np.array([0, 0, 1, 1])
    mask = np.ones(4, dtype=bool)
    tp = np.array([9, 9, 1, 1]).reshape(4, T, Q)
    fn = np.array([1, 1, 9, 9]).reshape(4, T, Q)
    fp = np.zeros((4, T, Q), dtype=np.int64)
    equal, per_k, _ = balanced_score(tp, fn, fp, strata, mask)
    assert per_k[0] == pytest.approx(0.9)
    assert per_k[1] == pytest.approx(0.1)
    assert equal == pytest.approx(0.5)
    skewed, _, _ = balanced_score(tp, fn, fp, strata, mask,
                                  weights={0: 3.0, 1: 1.0})
    assert skewed == pytest.approx(0.7)


def test_balanced_score_excludes_empty_cells_rather_than_scoring_them_zero():
    T, Q = 1, 2
    strata = np.zeros(2, dtype=np.int64)
    mask = np.ones(2, dtype=bool)
    tp = np.array([[[3, 0]], [[3, 0]]])
    fn = np.array([[[1, 0]], [[1, 0]]])
    fp = np.array([[[0, 0]], [[0, 0]]])
    s, _, n_empty = balanced_score(tp, fn, fp, strata, mask)
    assert n_empty == 1                       # threshold 1 never occurs
    assert s == pytest.approx(6 / 8)          # scored on threshold 0 only


# ---------------------------------------------------------------- bootstrap
def test_bootstrap_preserves_stratum_sizes():
    strata = np.repeat([0, 1], 20)
    mask = np.ones(40, dtype=bool)
    idx, W = bootstrap_multiplicities(strata, mask, B=50, seed=3)
    assert W.shape == (50, 40)
    for k in (0, 1):
        cols = np.flatnonzero(strata[idx] == k)
        assert np.allclose(W[:, cols].sum(axis=1), 20)


def test_bootstrap_is_reproducible_and_pairs_across_checkpoints():
    rng = np.random.default_rng(11)
    n, T, Q = 60, 2, 2
    strata = np.repeat([0, 1, 2], 20)
    mask = np.ones(n, dtype=bool)
    tp = rng.integers(1, 20, (n, T, Q)).astype(np.int64)
    fn = rng.integers(1, 20, (n, T, Q)).astype(np.int64)
    fp = rng.integers(1, 20, (n, T, Q)).astype(np.int64)

    idx, W = bootstrap_multiplicities(strata, mask, B=200, seed=5)
    idx2, W2 = bootstrap_multiplicities(strata, mask, B=200, seed=5)
    assert np.array_equal(W, W2)

    a = bootstrap_balanced(tp, fn, fp, strata, idx, W)
    # a checkpoint that is uniformly slightly better
    b = bootstrap_balanced(tp + 1, fn, fp, strata, idx, W)
    assert a.shape == (200,)
    paired = np.std(b - a)
    unpaired = np.sqrt(np.var(a) + np.var(b))
    assert paired < unpaired, "common random numbers must shrink the delta variance"
    assert (b > a).mean() == 1.0


def test_bootstrap_mean_tracks_the_point_estimate():
    rng = np.random.default_rng(2)
    n, T, Q = 120, 2, 2
    strata = np.repeat([0, 1], 60)
    mask = np.ones(n, dtype=bool)
    tp = rng.integers(5, 15, (n, T, Q)).astype(np.int64)
    fn = rng.integers(5, 15, (n, T, Q)).astype(np.int64)
    fp = rng.integers(5, 15, (n, T, Q)).astype(np.int64)
    point = balanced_score(tp, fn, fp, strata, mask)[0]
    idx, W = bootstrap_multiplicities(strata, mask, B=400, seed=9)
    boot = bootstrap_balanced(tp, fn, fp, strata, idx, W)
    assert abs(boot.mean() - point) < 3 * boot.std() / np.sqrt(400) + 1e-3
    assert epsilon_from_bootstrap(boot, 1.0) == pytest.approx(np.std(boot, ddof=1))


# --------------------------------------------------------------- rule I/O
def _demo_rule(**over):
    base = dict(
        schema_version=1, dataset_name="cikm", thresholds=list(THRESHOLDS_CIKM),
        pixel_scale=90.0, crop=[13, -14], n_strata_requested=4,
        boundaries=[0.1, 0.5, 1.2], n_strata_realised=4, stratum_weights="equal",
        empty_cell_policy="exclude", split_seed=1, frac_dev=0.5,
        selector_order=["balanced", "micro_csi_m", "fair_crps", "mse"],
        epsilon_rule="1 SE", bootstrap_B=100, bootstrap_seed=2,
        stage1_samples=1, stage2_samples=8, stage1_batch_size=8,
        stage2_batch_size=4, euler_steps=10, dtype="float32",
        seed_formula="base_seed + batch_index * S + sample_index",
        base_seed=42, train_h5_sha256="a" * 64, val_h5_sha256="b" * 64,
        created_utc="2026-08-01T00:00:00Z", notes="",
        val_event_id=[0, 1, 2, 3], val_file_row=[0, 1, 2, 3],
        val_severity=[0.0, 0.3, 0.8, 2.0], val_stratum=[0, 1, 2, 3],
        val_is_dev=[1, 0, 1, 0],
    )
    base.update(over)
    return SelectionRule(**base)


def test_rule_roundtrip(tmp_path):
    p = str(tmp_path / "rule.json")
    r = _demo_rule()
    digest = r.save(p)
    back = SelectionRule.load(p)
    assert back.payload_hash() == digest
    assert back.boundaries == r.boundaries
    assert back.event_mask("dev").tolist() == [True, False, True, False]
    assert back.event_mask("shadow").tolist() == [False, True, False, True]
    assert back.event_mask("all").all()


def test_hand_edited_rule_is_rejected(tmp_path):
    p = str(tmp_path / "rule.json")
    _demo_rule().save(p)
    with open(p) as f:
        d = json.load(f)
    d["frac_dev"] = 0.9  # sneak a change past the freeze
    with open(p, "w") as f:
        json.dump(d, f)
    with pytest.raises(ValueError, match="edited after freezing"):
        SelectionRule.load(p)


def test_unknown_split_name_is_an_error():
    with pytest.raises(ValueError):
        _demo_rule().event_mask("train")
