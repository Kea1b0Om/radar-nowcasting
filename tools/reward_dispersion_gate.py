"""Within-group dispersion of candidate GRPO rewards, including tail-weighted
ensemble scores.  Offline: reads a frozen ``EnsembleWriter`` HDF5, no GPU, no
model load, no training code touched.

Why this exists
---------------
``verifier_rank_gate.py`` measured the GRPO learning signal for *deterministic
pixel* rewards and found single-threshold CSI unusable: at csi40, 11.45% of
groups have all members scoring identically, so the advantage is exactly zero
and roughly a ninth of the gradient contribution is noise (or, before the
float32 fix, large random-sign garbage).  Composite csi_M dropped that to 0.45%.

The open question this tool settles is the next one: **does a threshold-weighted
ensemble score survive the same test?**  That matters because twCRPS is the
score the probabilistic-axis story wants to optimise, and because no existing
work uses a tail-weighted *ensemble* score as an RL reward.

The definition problem (do not skip this)
-----------------------------------------
CRPS and twCRPS score an **ensemble**, not a member.  GRPO needs a per-member
scalar.  There is more than one way to descend from one to the other and they do
not agree, so all three are measured here:

``twmae_t``      -mean |max(x_i,t) - max(y,t)|.  This is literally "twCRPS of a
                 one-member ensemble" (the fair correction is undefined at M=1
                 and CRPS degenerates to MAE).  **It is a trap.**  E_p|x-y| is
                 minimised by a point mass at the median, so optimising it
                 rewards ensemble collapse -- the exact blurring failure the
                 extreme-event work is trying to undo.  Measured so the trap is
                 documented with a number rather than argued about.

``twcrps_fair_t`` the per-member decomposition of the *fair* ensemble score:

                     fairCRPS = (1/G) sum_i [ a_i - 1/(2(G-1)) sum_{j!=i} d_ij ]

                 with ``a_i = mean|x_i - y|_t`` and ``d_ij = mean|x_i - x_j|_t``
                 (all after the chaining transform ``v(z) = max(z,t)``).  The
                 reward is minus the bracket, so the group mean of the rewards is
                 exactly ``-fairCRPS`` of that ensemble -- checked numerically,
                 not asserted.  It carries a diversity bonus: a member is paid
                 for being far from the others, which is what makes the fair
                 score minimised by the true predictive distribution rather than
                 by a point mass.  This is the principled choice.

``twcrps_loo_t``  leave-one-out marginal value,
                 ``fairCRPS(ens without i) - fairCRPS(ens)``.  Positive when
                 dropping the member would make the ensemble worse.  Ties the
                 reward to the deployed product directly; needs G >= 3.

Reported per reward, matching ``advantage_diagnostics`` in the verifier gate so
the numbers land in the same table as the CSI ones:

  * ``within_event_std`` and its ratio to ``between_event_std`` -- GRPO forms
    advantages inside a group, so only the within-event part is signal;
  * ``frac_degenerate_groups`` -- the fraction with exactly zero gradient;
  * for the two ensemble rewards, the split of within-group variance into the
    accuracy term and the diversity term, because a reward whose spread is
    almost all diversity is paying for being an outlier, not for being right.

Usage:

    python tools/reward_dispersion_gate.py \
        --input audit_outputs/band_spread_calibration/v4_validation_members.h5 \
        --output-dir audit_outputs/reward_dispersion/v4_validation \
        --input-length 5 --window all
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

import h5py
import numpy as np

sys.path.append(os.getcwd())

CSI_THRESHOLDS = (20.0, 30.0, 35.0, 40.0)
# -inf reproduces plain CRPS; the rest are the evaluator's reporting thresholds.
TW_THRESHOLDS = (-np.inf, 20.0, 30.0, 35.0, 40.0)
DEGENERATE_ATOL = 1e-9


def _tag(t: float) -> str:
    return "plain" if not np.isfinite(t) else f"t{int(t)}"


# --------------------------------------------------------------------------
# per-event reward construction
# --------------------------------------------------------------------------
def csi_rewards(members: np.ndarray, obs: np.ndarray) -> Dict[str, np.ndarray]:
    """Single-threshold and mean CSI per member, shape ``(G,)`` each.

    Uses the pilot's ``>=`` convention and its ``+1.0`` denominator guard so the
    numbers are the ones the RL loop would actually see, not a cleaner variant.
    """
    out, per_thr = {}, []
    o_masks = [obs >= thr for thr in CSI_THRESHOLDS]
    for k, thr in enumerate(CSI_THRESHOLDS):
        o = o_masks[k]
        p = members >= thr
        tp = np.count_nonzero(p & o, axis=(1, 2, 3)).astype(np.float64)
        fp = np.count_nonzero(p & ~o, axis=(1, 2, 3)).astype(np.float64)
        fn = np.count_nonzero(~p & o, axis=(1, 2, 3)).astype(np.float64)
        csi = tp / (tp + fp + fn + 1.0)
        out[f"csi{int(thr)}"] = csi
        per_thr.append(csi)
    out["csi_m"] = np.mean(per_thr, axis=0)
    return out


def ensemble_terms(members: np.ndarray, obs: np.ndarray, threshold: float):
    """``a_i`` and ``d_ij`` for one event at one chaining threshold.

    Every term of the (tw)CRPS is a mean over pixels, so the pixel reduction can
    be done first and the ensemble algebra afterwards on ``G`` and ``G*G``
    scalars -- exact, not an approximation, and it keeps the whole scan in a few
    hundred MB.
    """
    if np.isfinite(threshold):
        m = np.maximum(members, threshold)
        o = np.maximum(obs, threshold)
    else:
        m, o = members, obs
    axes = tuple(range(1, m.ndim))
    a = np.abs(m - o[None]).mean(axis=axes)                       # (G,)
    d = np.abs(m[:, None] - m[None, :]).mean(axis=tuple(range(2, m.ndim + 1)))
    return a.astype(np.float64), d.astype(np.float64)             # (G,), (G,G)


def fair_crps_from_terms(a: np.ndarray, d: np.ndarray) -> float:
    """fairCRPS = mean_i a_i - (1/(2G(G-1))) sum_{i!=j} d_ij."""
    g = a.shape[0]
    if g < 2:
        return float(a.mean())
    return float(a.mean() - d.sum() / (2.0 * g * (g - 1)))


def fair_member_terms(a: np.ndarray, d: np.ndarray):
    """Accuracy and diversity halves of the per-member fair decomposition.

    reward_i = -(accuracy_i - diversity_i); the group mean of the reward is
    exactly ``-fairCRPS``.
    """
    g = a.shape[0]
    if g < 2:
        return a.copy(), np.zeros_like(a)
    diversity = d.sum(axis=1) / (2.0 * (g - 1))
    return a.copy(), diversity


def loo_rewards(a: np.ndarray, d: np.ndarray) -> np.ndarray:
    """``fairCRPS(ens without i) - fairCRPS(ens)``; needs ``G >= 3``."""
    g = a.shape[0]
    if g < 3:
        return np.zeros_like(a)
    full = fair_crps_from_terms(a, d)
    total_d = d.sum()
    row_d = d.sum(axis=1)  # d_ii = 0, so this is sum_{j != i} d_ij
    sum_a = a.sum()
    out = np.empty_like(a)
    for i in range(g):
        a_wo = (sum_a - a[i]) / (g - 1)
        # dropping i removes its row and column
        d_wo = total_d - 2.0 * row_d[i]
        out[i] = (a_wo - d_wo / (2.0 * (g - 1) * (g - 2))) - full
    return out


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------
def scan(
    path: str,
    input_length: int,
    window: str,
    max_events: Optional[int],
    w_csi: float,
    w_cont: float,
    mse_ref: float,
    tw_thresholds: Sequence[float],
    progress_every: int,
) -> Dict[str, object]:
    with h5py.File(path, "r") as handle:
        preds, truth = handle["predictions"], handle["truth"]
        n_all, n_members, total_leads = preds.shape[0], preds.shape[1], preds.shape[2]
        n = n_all if max_events is None else min(max_events, n_all)

        if window == "chunk2":
            lead_idx = list(range(input_length, total_leads))
        elif window == "chunk1":
            lead_idx = list(range(0, min(input_length, total_leads)))
        elif window == "all":
            lead_idx = list(range(total_leads))
        else:
            raise ValueError(f"unknown window {window!r}")
        if not lead_idx:
            raise ValueError(f"empty lead window for window={window!r}")
        sel = np.asarray(lead_idx)

        names: List[str] = [f"csi{int(t)}" for t in CSI_THRESHOLDS]
        names += ["csi_m", "neg_mse", "composite"]
        for t in tw_thresholds:
            names += [f"twmae_{_tag(t)}", f"twcrps_fair_{_tag(t)}", f"twcrps_loo_{_tag(t)}"]
        rewards = {k: np.zeros((n, n_members)) for k in names}
        # diagnostic halves of the fair decomposition
        halves = {
            f"{part}_{_tag(t)}": np.zeros((n, n_members))
            for t in tw_thresholds for part in ("acc", "div")
        }
        ens_fair = {f"ens_fair_{_tag(t)}": np.zeros(n) for t in tw_thresholds}
        identity_gap = 0.0

        for i in range(n):
            members = np.asarray(preds[i], dtype=np.float32)[:, sel]
            obs = np.asarray(truth[i], dtype=np.float32)[sel]

            for key, val in csi_rewards(members, obs).items():
                rewards[key][i] = val
            mse = ((members - obs[None]) ** 2).reshape(n_members, -1).mean(axis=1)
            rewards["neg_mse"][i] = -mse
            cont = 1.0 - np.clip(mse / mse_ref, 0.0, 2.0) / 2.0
            rewards["composite"][i] = w_csi * rewards["csi_m"][i] + w_cont * cont

            for t in tw_thresholds:
                tag = _tag(t)
                a, d = ensemble_terms(members, obs, t)
                acc, div = fair_member_terms(a, d)
                rewards[f"twmae_{tag}"][i] = -a
                rewards[f"twcrps_fair_{tag}"][i] = -(acc - div)
                rewards[f"twcrps_loo_{tag}"][i] = loo_rewards(a, d)
                halves[f"acc_{tag}"][i] = acc
                halves[f"div_{tag}"][i] = div
                fair = fair_crps_from_terms(a, d)
                ens_fair[f"ens_fair_{tag}"][i] = fair
                # identity that makes the decomposition legitimate
                identity_gap = max(
                    identity_gap,
                    abs(float(rewards[f"twcrps_fair_{tag}"][i].mean()) + fair),
                )

            if progress_every and (i + 1) % progress_every == 0:
                print(f"  scanned {i + 1}/{n} events", flush=True)

    return {
        "rewards": rewards,
        "halves": halves,
        "ens_fair": ens_fair,
        "n_events": n,
        "n_members": n_members,
        "lead_idx": np.asarray(lead_idx),
        "identity_max_abs_gap": identity_gap,
    }


# --------------------------------------------------------------------------
# read-out
# --------------------------------------------------------------------------
def advantage_diagnostics(reward: np.ndarray, label: str) -> Dict[str, object]:
    """Same statistic set as ``verifier_rank_gate.advantage_diagnostics``."""
    r = reward[np.isfinite(reward).all(axis=1)]
    if r.size == 0:
        return {"label": label, "n_events_usable": 0}
    within = r.std(axis=1, ddof=1)
    per_event_mean = r.mean(axis=1)
    span = r.max(axis=1) - r.min(axis=1)
    between = float(per_event_mean.std(ddof=1))
    scale = float(np.mean(np.abs(per_event_mean)))

    # Exact variance decomposition (population moments, equal group sizes):
    #   total = within + between.
    # Done separately from the ddof=1 statistics above, which are kept because
    # the published verifier-gate table reports those.  Mixing the two is what
    # lets a "share" exceed 1: mean-of-ddof=1-within over a perfectly centred
    # reward is G/(G-1) times the population value.
    pop_within = float(r.var(axis=1).mean())
    pop_between = float(per_event_mean.var())
    pop_total = pop_within + pop_between
    return {
        "label": label,
        "n_events_usable": int(r.shape[0]),
        "within_event_std_mean": float(within.mean()),
        "within_event_std_median": float(np.median(within)),
        "between_event_std": between,
        "within_over_between": float(within.mean() / max(between, 1e-12)),
        # Exactly in [0, 1] and defined for every reward, including ones centred
        # per event by construction (leave-one-out), where ``within_over_between``
        # diverges because ``between`` is ~0.  Reads as "the share of total
        # reward variance GRPO's group-relative advantage can actually use".
        "within_var_share": float(pop_within / pop_total) if pop_total > 0 else float("nan"),
        "pop_within_var": pop_within,
        "pop_between_var": pop_between,
        "within_event_range_mean": float(span.mean()),
        "relative_within_std": float(within.mean() / max(scale, 1e-12)),
        "frac_degenerate_groups": float(np.mean(span <= DEGENERATE_ATOL)),
        "frac_groups_range_below_1pct_of_scale": float(
            np.mean(span < 0.01 * max(scale, 1e-12))
        ),
    }


def _fmt(x: float, width: int) -> str:
    """Fixed-point when it fits, scientific when it does not - a reward that is
    centred per event makes ``within/between`` enormous, and a column that spills
    into its neighbour is how a table gets misread."""
    if not np.isfinite(x):
        return f"{'n/a':>{width}}"
    return f"{x:>{width}.4f}" if abs(x) < 1e4 else f"{x:>{width}.2e}"


def variance_split(acc: np.ndarray, div: np.ndarray, label: str) -> Dict[str, object]:
    """How much of the within-group reward spread is accuracy vs diversity.

    reward_i = -(acc_i - div_i), so Var_within(reward) = Var(acc) + Var(div)
    - 2 Cov(acc, div).  A reward whose spread is carried by ``div`` is paying
    for being an outlier rather than for being right.
    """
    a = acc - acc.mean(axis=1, keepdims=True)
    d = div - div.mean(axis=1, keepdims=True)
    va = float((a ** 2).mean())
    vd = float((d ** 2).mean())
    cov = float((a * d).mean())
    total = va + vd - 2.0 * cov
    return {
        "label": label,
        "within_var_accuracy": va,
        "within_var_diversity": vd,
        "within_cov": cov,
        "within_var_total": total,
        "diversity_share": float(vd / total) if total > 0 else float("nan"),
        "corr_acc_div": float(cov / np.sqrt(va * vd)) if va > 0 and vd > 0 else float("nan"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--input-length", type=int, default=5)
    p.add_argument("--window", default="all", choices=["all", "chunk1", "chunk2"])
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--w-csi", type=float, default=1.0)
    p.add_argument("--w-cont", type=float, default=0.1)
    p.add_argument("--mse-ref", type=float, default=75.0)
    p.add_argument("--progress-every", type=int, default=200)
    args = p.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"scanning {args.input} (window={args.window})", flush=True)
    res = scan(
        args.input, args.input_length, args.window, args.max_events,
        args.w_csi, args.w_cont, args.mse_ref, TW_THRESHOLDS, args.progress_every,
    )
    rewards, halves = res["rewards"], res["halves"]

    print(f"\nevents={res['n_events']}  members={res['n_members']}  "
          f"leads={list(res['lead_idx'])}")
    gap = res["identity_max_abs_gap"]
    print(f"fair decomposition identity  max |mean_i r_i + fairCRPS| = {gap:.3e} "
          f"({'OK' if gap < 1e-6 else 'FAILED - decomposition is wrong'})")
    if gap >= 1e-6:
        raise SystemExit("fair per-member decomposition does not reproduce the "
                         "ensemble score; refusing to report dispersion numbers")

    diags = [advantage_diagnostics(rewards[k], k) for k in rewards]
    print("\n=== within-group reward dispersion (GRPO learning signal) ===")
    head = (f"{'reward':<22}{'within_std':>12}{'w_var_share':>13}{'w/between':>12}"
            f"{'degen%':>9}")
    print(head)
    print("-" * len(head))
    for d in diags:
        if not d.get("n_events_usable"):
            continue
        print(f"{d['label']:<22}{d['within_event_std_mean']:>12.5f}"
              f"{_fmt(d['within_var_share'], 13)}{_fmt(d['within_over_between'], 12)}"
              f"{100 * d['frac_degenerate_groups']:>9.2f}")

    splits = []
    for t in TW_THRESHOLDS:
        tag = _tag(t)
        splits.append(variance_split(halves[f"acc_{tag}"], halves[f"div_{tag}"],
                                     f"twcrps_fair_{tag}"))
    print("\n=== fair reward: accuracy vs diversity share of within-group spread ===")
    head2 = f"{'reward':<22}{'var_acc':>12}{'var_div':>12}{'div_share':>11}{'corr':>8}"
    print(head2)
    print("-" * len(head2))
    for s in splits:
        print(f"{s['label']:<22}{s['within_var_accuracy']:>12.3e}"
              f"{s['within_var_diversity']:>12.3e}{s['diversity_share']:>11.3f}"
              f"{s['corr_acc_div']:>8.3f}")

    ens = {k: float(v.mean()) for k, v in res["ens_fair"].items()}
    print("\n=== ensemble fair (tw)CRPS, mean over events ===")
    for k, v in ens.items():
        print(f"  {k:<22}{v:>12.4f}")

    report = {
        "input": os.path.abspath(args.input),
        "window": args.window,
        "n_events": res["n_events"],
        "n_members": res["n_members"],
        "lead_idx": [int(x) for x in res["lead_idx"]],
        "identity_max_abs_gap": gap,
        "dispersion": diags,
        "variance_split": splits,
        "ensemble_fair_crps": ens,
        "reward_params": {"w_csi": args.w_csi, "w_cont": args.w_cont,
                          "mse_ref": args.mse_ref},
    }
    out = os.path.join(args.output_dir, "reward_dispersion.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    np.savez_compressed(
        os.path.join(args.output_dir, "per_member_rewards.npz"),
        **{k: v for k, v in rewards.items()},
        **{k: v for k, v in halves.items()},
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
