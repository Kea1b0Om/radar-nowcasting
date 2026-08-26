"""CSI-optimal per-threshold decision rules on a saved ensemble (T0-2 + T1-1).

Why this exists
---------------
``score_test_published.py`` collapses the ensemble to ONE field and then
thresholds it at all four levels.  That forces a single operating point on
four different decision problems.  For a pooled-IoU metric the Bayes-optimal
rule is a threshold on the exceedance probability, and the optimal threshold
is metric-dependent:

    theta*_t = CSI*_t / (1 + CSI*_t)          (Nowozin CVPR2014 Prop.4 +
                                               Dinkelbach; Koyejo NeurIPS2014;
                                               Natarajan arXiv:1505.01802)

    decide 1  iff  p_i(t) > theta*_t,   p_i(t) = (1/M) #{s : x_i^s >= t}

which for M members is  count >= floor(M*theta*_t) + 1.

CIKM's evaluator accumulates ONE contingency table over the whole test set
(SDIR/helpers/evaluation.py:55-62,88), i.e. the score is a pooled IoU whose
numerator and denominator do not decompose over pixels.  That is Nowozin's
original setting, so the theorem applies literally rather than by analogy.

Protocol is bit-identical to score_test_published.py: per-(threshold, lead)
accumulators -> per-lead CSI -> lead-equal-weight mean -> threshold mean.

Comparison operator
-------------------
``--op`` selects ``>`` or ``>=``.  The published evaluators
(SDIR/helpers/evaluation.py:16-17, common/metrics/crft_evaluation.py:17-18)
both use ``>=``; score_test_published.py uses ``>``.  On CIKM this is a no-op:
30 dBZ maps to byte 85 exactly, but the CIKM byte grid has stride 3 starting
at 8 (8,11,...,83,86,...), so 85 never occurs -- measured 0 hits in 102.0M
test output pixels.  On SEVIR (value_scale=255, integer thresholds) and on
other datasets it is NOT a no-op and must be re-measured before use.
Default is ``>=`` to match the evaluators.

Arms
----
  member0 / mean / max / qNN   collapse-then-threshold (reproduces the old tool)
  count:k1,k2,k3,k4            per-threshold "at least k of M members exceed t"
  theta-star:c20,c30,c35,c40   derive k_t from a REFERENCE CSI vector

``theta-star`` must be given CSI values measured on a *different* split than
the one being scored (validation), otherwise the rule is tuned on test.  The
tool records the reference vector in the output so this is auditable.
"""

import argparse
import json
import math
import os
import sys

import h5py
import numpy as np

sys.path.append(os.getcwd())

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)


def k_from_reference_csi(ref_csi, n_members):
    """theta* = CSI/(1+CSI);  p > theta*  <=>  count >= floor(M*theta*)+1."""
    ks, thetas = [], []
    for c in ref_csi:
        th = c / (1.0 + c)
        thetas.append(th)
        ks.append(min(n_members, math.floor(n_members * th) + 1))
    return ks, thetas


def score(path, rule, op=">=", max_events=None, ref_csi=None):
    ge = (op == ">=")

    with h5py.File(path, "r") as handle:
        preds, truth = handle["predictions"], handle["truth"]
        n_all, n_members, n_leads = preds.shape[0], preds.shape[1], preds.shape[2]
        n = n_all if max_events is None else min(max_events, n_all)

        ks = thetas = None
        if rule.startswith("count:"):
            ks = [int(v) for v in rule.split(":", 1)[1].split(",")]
            if len(ks) != len(THRESHOLDS):
                raise ValueError(f"count rule needs {len(THRESHOLDS)} values, got {ks}")
        elif rule.startswith("theta-star"):
            if ref_csi is None:
                if ":" not in rule:
                    raise ValueError("theta-star needs reference CSI: theta-star:c20,c30,c35,c40")
                ref_csi = [float(v) for v in rule.split(":", 1)[1].split(",")]
            ks, thetas = k_from_reference_csi(ref_csi, n_members)

        tp = np.zeros((len(THRESHOLDS), n_leads), dtype=np.float64)
        fp = np.zeros_like(tp)
        fn = np.zeros_like(tp)
        tn = np.zeros_like(tp)
        sse = np.zeros(n_leads, dtype=np.float64)
        sae = np.zeros(n_leads, dtype=np.float64)
        npix = np.zeros(n_leads, dtype=np.float64)
        tie = np.zeros(len(THRESHOLDS), dtype=np.float64)   # truth pixels exactly == t

        for i in range(n):
            members = np.asarray(preds[i], dtype=np.float32)   # (S, T, H, W)
            obs = np.asarray(truth[i], dtype=np.float32)       # (T, H, W)

            pred = None
            if rule == "member0":
                pred = members[0]
            elif rule == "mean":
                pred = members.mean(axis=0)
            elif rule == "max":
                pred = members.max(axis=0)
            elif rule.startswith("q"):
                q = float(rule[1:]) / 100.0
                if not 0.0 < q < 1.0:
                    raise ValueError(f"quantile out of range in {rule!r}")
                pred = np.quantile(members, q, axis=0)
            elif ks is None:
                raise ValueError(f"unknown rule {rule!r}")

            if pred is not None:
                diff = pred - obs
                sse += (diff ** 2).sum(axis=(1, 2))
                sae += np.abs(diff).sum(axis=(1, 2))
            npix += float(obs.shape[1] * obs.shape[2])

            for k, thr in enumerate(THRESHOLDS):
                o = (obs >= thr) if ge else (obs > thr)
                tie[k] += float((obs == np.float32(thr)).sum())
                if pred is not None:
                    p = (pred >= thr) if ge else (pred > thr)
                else:
                    exc = (members >= thr) if ge else (members > thr)
                    p = exc.sum(axis=0) >= ks[k]
                tp[k] += (p & o).sum(axis=(1, 2))
                fp[k] += (p & ~o).sum(axis=(1, 2))
                fn[k] += (~p & o).sum(axis=(1, 2))
                tn[k] += (~p & ~o).sum(axis=(1, 2))

    csi = tp / np.maximum(tp + fp + fn, 1.0)
    denom = (tp + fn) * (fn + tn) + (tp + fp) * (fp + tn)
    hss = 2.0 * (tp * tn - fn * fp) / np.maximum(denom, 1e-12)
    pod = tp / np.maximum(tp + fn, 1.0)
    far = fp / np.maximum(tp + fp, 1.0)
    fbi = (tp + fp) / np.maximum(tp + fn, 1.0)          # frequency bias

    key = lambda arr: {str(int(t)): float(v) for t, v in zip(THRESHOLDS, arr.mean(axis=1))}
    out = {
        "file": os.path.abspath(path),
        "rule": rule,
        "op": op,
        "n_events": int(n),
        "n_members_in_file": int(n_members),
        "n_leads": int(n_leads),
        "csi_per_threshold": key(csi),
        "hss_per_threshold": key(hss),
        "pod_per_threshold": key(pod),
        "far_per_threshold": key(far),
        "fbi_per_threshold": key(fbi),
        "csi_m": float(csi.mean(axis=1).mean()),
        "hss_m": float(hss.mean(axis=1).mean()),
        "csi_per_lead_m": [float(v) for v in csi.mean(axis=0)],
        "truth_tie_pixels": {str(int(t)): float(v) for t, v in zip(THRESHOLDS, tie)},
    }
    if pred is not None:
        out["mse"] = float((sse / npix).mean())
        out["mae"] = float((sae / npix).mean())
    else:
        out["mse"] = None       # count rules produce a mask, not a field
        out["mae"] = None
    if ks is not None:
        out["k_per_threshold"] = {str(int(t)): int(k) for t, k in zip(THRESHOLDS, ks)}
        if thetas is not None:
            out["theta_star"] = {str(int(t)): float(v) for t, v in zip(THRESHOLDS, thetas)}
            out["reference_csi"] = {str(int(t)): float(v) for t, v in zip(THRESHOLDS, ref_csi)}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--rule", default="member0",
                   help="member0 | mean | max | qNN | count:k1,k2,k3,k4 | theta-star:c20,c30,c35,c40")
    p.add_argument("--op", default=">=", choices=[">", ">="],
                   help="comparison operator; evaluators use '>=' (default)")
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--out", default=None)
    a = p.parse_args()

    r = score(a.path, a.rule, op=a.op, max_events=a.max_events)
    txt = json.dumps(r, indent=2)
    print(txt)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            fh.write(txt + "\n")


if __name__ == "__main__":
    main()
