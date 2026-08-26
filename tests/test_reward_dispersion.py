"""Correctness gate for the candidate tail-weighted GRPO rewards.

A silently wrong reward is worse than no reward: it would train the policy
towards the wrong thing while every diagnostic still looks healthy.  The tests
that matter here are the two that tie the numpy per-member decomposition back to
something independent -- the repository's own torch (tw)CRPS, and the algebraic
identity that the group mean of the per-member rewards *is* the ensemble score.

The collapse tests are not decoration.  They are the reason ``twmae`` must not
be used as a reward even though it is the most obvious reading of "twCRPS per
member".
"""

import numpy as np
import pytest
import torch

from tools.reward_dispersion_gate import (
    csi_rewards,
    ensemble_terms,
    fair_crps_from_terms,
    fair_member_terms,
    loo_rewards,
    variance_split,
)
from common.metrics.crps import crps_ensemble, twcrps_ensemble

G, T, H, W = 8, 4, 9, 11


def _sample(seed: int = 0, spread: float = 6.0):
    rng = np.random.default_rng(seed)
    obs = rng.gamma(2.0, 8.0, size=(T, H, W)).astype(np.float32)
    members = (obs[None] + rng.normal(0.0, spread, size=(G, T, H, W))).astype(np.float32)
    return members, obs


# ---------------------------------------------------------------- identities
@pytest.mark.parametrize("threshold", [-np.inf, 20.0, 35.0])
def test_fair_group_mean_is_minus_ensemble_score(threshold):
    """The property the whole decomposition rests on."""
    members, obs = _sample()
    a, d = ensemble_terms(members, obs, threshold)
    acc, div = fair_member_terms(a, d)
    reward = -(acc - div)
    assert reward.shape == (G,)
    np.testing.assert_allclose(reward.mean(), -fair_crps_from_terms(a, d),
                               rtol=0, atol=1e-9)


@pytest.mark.parametrize("threshold", [20.0, 30.0, 40.0])
def test_matches_repo_torch_twcrps(threshold):
    """Independent implementation, different framework, different reduction order."""
    members, obs = _sample(seed=3)
    a, d = ensemble_terms(members, obs, threshold)
    mine = fair_crps_from_terms(a, d)

    ref = twcrps_ensemble(
        torch.from_numpy(obs).reshape(1, -1),
        torch.from_numpy(members).reshape(1, G, -1),
        threshold=threshold,
        estimator="fair",
    ).mean().item()
    assert mine == pytest.approx(ref, rel=1e-5, abs=1e-6)


def test_plain_threshold_reproduces_crps():
    """``-inf`` chaining must be exactly the unweighted score."""
    members, obs = _sample(seed=5)
    a, d = ensemble_terms(members, obs, -np.inf)
    mine = fair_crps_from_terms(a, d)
    ref = crps_ensemble(
        torch.from_numpy(obs).reshape(1, -1),
        torch.from_numpy(members).reshape(1, G, -1),
        estimator="fair",
    ).mean().item()
    assert mine == pytest.approx(ref, rel=1e-5, abs=1e-6)


def test_threshold_only_scores_exceedances():
    """Above a threshold no member reaches, every candidate must tie."""
    members, obs = _sample(seed=7)
    hi = float(max(members.max(), obs.max())) + 1.0
    a, d = ensemble_terms(members, obs, hi)
    np.testing.assert_allclose(a, np.zeros(G), atol=1e-6)
    np.testing.assert_allclose(d, np.zeros((G, G)), atol=1e-6)


# ------------------------------------------------------------ degenerate case
def test_identical_members_give_zero_spread_everywhere():
    """The 11.45%-of-groups pathology, at its limit: no reward may separate them."""
    _, obs = _sample(seed=11)
    one = obs + 2.0
    members = np.repeat(one[None], G, axis=0).astype(np.float32)

    for thr in (-np.inf, 20.0, 35.0):
        a, d = ensemble_terms(members, obs, thr)
        acc, div = fair_member_terms(a, d)
        for r in (-a, -(acc - div), loo_rewards(a, d)):
            assert float(r.max() - r.min()) < 1e-9

    csi = csi_rewards(members, obs)
    for key, val in csi.items():
        assert float(val.max() - val.min()) < 1e-12, key


# ------------------------------------------------------------- the twmae trap
def test_twmae_prefers_a_collapsed_ensemble():
    """Why the obvious per-member reading of twCRPS must not be the reward.

    A point mass at the truth-side median beats a well-spread ensemble under
    mean |x - y|, so optimising it drives the policy towards collapse -- the
    blurring failure the extreme-event work exists to fix.
    """
    members, obs = _sample(seed=13, spread=6.0)
    collapsed = np.repeat(members.mean(axis=0, keepdims=True), G, axis=0)

    a_spread, _ = ensemble_terms(members, obs, 20.0)
    a_coll, _ = ensemble_terms(collapsed, obs, 20.0)
    assert a_coll.mean() < a_spread.mean()          # collapse scores *better*


def test_fair_score_does_not_prefer_collapse():
    """The diversity term is what removes that incentive."""
    members, obs = _sample(seed=13, spread=6.0)
    collapsed = np.repeat(members.mean(axis=0, keepdims=True), G, axis=0)

    fair_spread = fair_crps_from_terms(*ensemble_terms(members, obs, 20.0))
    fair_coll = fair_crps_from_terms(*ensemble_terms(collapsed, obs, 20.0))
    assert fair_coll > fair_spread                  # collapse scores worse
    # and the sign flip really comes from the diversity half
    _, d = ensemble_terms(members, obs, 20.0)
    assert d.sum() > 0.0


# --------------------------------------------------------------- leave-one-out
def test_loo_rewards_are_ordered_by_member_quality():
    """A member equal to the truth must be worth more than a badly biased one."""
    members, obs = _sample(seed=17)
    members[0] = obs                                  # perfect
    members[1] = obs + 40.0                           # badly biased
    a, d = ensemble_terms(members, obs, 20.0)
    r = loo_rewards(a, d)
    assert r[0] > r[1]
    assert r[0] == max(r)


def test_loo_sum_relates_to_ensemble_score():
    """Sanity bound: LOO values are finite and centred near zero for a
    homogeneous ensemble (no member is special)."""
    members, obs = _sample(seed=19)
    a, d = ensemble_terms(members, obs, 20.0)
    r = loo_rewards(a, d)
    assert np.all(np.isfinite(r))
    assert abs(float(r.mean())) < float(np.abs(r).max()) + 1e-12


def test_loo_needs_three_members():
    members, obs = _sample(seed=23)
    a, d = ensemble_terms(members[:2], obs, 20.0)
    np.testing.assert_allclose(loo_rewards(a, d), np.zeros(2))


# ------------------------------------------------------------ variance split
def test_variance_split_adds_up():
    rng = np.random.default_rng(29)
    acc = rng.normal(size=(50, G))
    div = rng.normal(size=(50, G))
    s = variance_split(acc, div, "x")
    direct = ((acc - acc.mean(axis=1, keepdims=True))
              - (div - div.mean(axis=1, keepdims=True))) ** 2
    assert s["within_var_total"] == pytest.approx(float(direct.mean()), rel=1e-9)


def test_variance_split_pure_accuracy():
    rng = np.random.default_rng(31)
    acc = rng.normal(size=(50, G))
    s = variance_split(acc, np.zeros_like(acc), "x")
    assert s["diversity_share"] == pytest.approx(0.0, abs=1e-12)


# ------------------------------------------------------------------- CSI path
def test_csi_matches_the_pilot_formula():
    """The RL loop's guarded CSI, reproduced exactly (including the +1)."""
    members, obs = _sample(seed=37)
    got = csi_rewards(members, obs)
    thr = 30.0
    p, o = members[2] >= thr, obs >= thr
    tp = np.count_nonzero(p & o)
    fp = np.count_nonzero(p & ~o)
    fn = np.count_nonzero(~p & o)
    assert got["csi30"][2] == pytest.approx(tp / (tp + fp + fn + 1.0))
    np.testing.assert_allclose(
        got["csi_m"],
        np.mean([got["csi20"], got["csi30"], got["csi35"], got["csi40"]], axis=0),
    )


# ------------------------------------------------------- read-out robustness
def test_within_var_share_is_defined_for_centred_rewards():
    """Leave-one-out rewards are ~zero-mean per event, so ``within/between``
    diverges.  The variance share must stay finite and hit 1 exactly."""
    from tools.reward_dispersion_gate import advantage_diagnostics

    rng = np.random.default_rng(41)
    r = rng.normal(size=(200, G))
    r = r - r.mean(axis=1, keepdims=True)          # centred per event
    d = advantage_diagnostics(r, "centred")
    assert d["within_var_share"] == pytest.approx(1.0, abs=1e-9)
    assert d["within_over_between"] > 1e3          # the metric that breaks


def test_variance_decomposition_is_exact():
    """total = within + between must hold to floating point, or the share is
    not a share."""
    from tools.reward_dispersion_gate import advantage_diagnostics

    rng = np.random.default_rng(43)
    r = rng.normal(size=(150, G)) + rng.normal(size=(150, 1)) * 3.0
    d = advantage_diagnostics(r, "mixed")
    total = float(r.var())
    assert d["pop_within_var"] + d["pop_between_var"] == pytest.approx(total, rel=1e-9)
    assert 0.0 < d["within_var_share"] < 1.0


def test_within_var_share_zero_when_members_agree():
    """No within-group spread at all -> nothing for GRPO to learn from."""
    from tools.reward_dispersion_gate import advantage_diagnostics

    rng = np.random.default_rng(47)
    r = np.repeat(rng.normal(size=(100, 1)), G, axis=1)
    d = advantage_diagnostics(r, "flat")
    assert d["within_var_share"] == pytest.approx(0.0, abs=1e-12)
    assert d["frac_degenerate_groups"] == pytest.approx(1.0)


def test_fmt_switches_to_scientific():
    from tools.reward_dispersion_gate import _fmt

    assert _fmt(0.1234, 8).strip() == "0.1234"
    assert "e" in _fmt(1.5e9, 10)
    assert _fmt(float("nan"), 6).strip() == "n/a"
