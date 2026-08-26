"""E1/E2 risk-predictability probe for the threshold-error refiner candidate.

Question (preregistered): are the frozen baseline's FN/FP errors at 35/40 dBZ
predictable from HISTORY beyond what (a) the prediction value itself and (b)
the ensemble's own exceedance/spread already tell you?  This is the gate the
whole risk-refiner line lives or dies on: the E0 bounded-oracle ceiling passed,
but the ledger says oracle room routinely fails to survive contact with a
realistic predictor, and the four risk maps are informationally a
reparametrisation of (exceedance probability, prediction) — so the only novel
predictability claim available is history/context signal, concentrated in DEEP
misses (cell present in history, absent in the prediction).

Arms (feature sets), fit with logistic regression + a small MLP:
  A0 trivial   : [zhat, zhat - theta]
  A1 ensemble  : A0 + [member exceedance freq, member spread, member max]
  A2 full      : A1 + history/context features + lead
  A2h history  : A0 + history/context features + lead   (attribution arm)

Primary endpoint: FN40, depth bins (5,10] and (10,20]: eval-split logistic
AUC(A2) - AUC(A1) >= 0.03 in both bins = PASS; in one = SOFT; neither = FAIL
(line closes).  Everything else is secondary.

Protocol notes:
* candidate sets follow strict '>' (positive prediction = zhat > theta),
  matching the published-metric operator;
* rows are sampled per (event, depth-bin): up to K positives and K negatives,
  so bins are populated and roughly balanced — AUC is rank-based and safe
  under this sampling, PR-type numbers would not be and are not reported;
* fit/eval split is by event parity (even/odd dump row) — pixel rows from one
  event never appear on both sides;
* the dataset row for each dump row comes from the dump's own `event_index`,
  and an alignment gate on the first events aborts if the dump truth does not
  match the decoded dataset frames.

Usage:
    python tools/e1_risk_probe.py \
        --dump audit_outputs/distill/test_s8/qw_t80.h5 \
        --data datasets/cikm/data/cikm_full/nowcast_testing_full.h5 \
        --output audit_outputs/e1_risk_probe_qw_t80.json \
        [--max-events N] [--per-bin 60]
"""

import argparse
import json

import h5py
import numpy as np
import torch
from scipy import ndimage

VALID_LO, VALID_HI = 13, 114
PIXEL_SCALE = 90.0
INPUT_LEN = 5
THRESHOLDS = (35.0, 40.0)
FN_BINS = ((0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 90.0))
FP_BINS = ((0.0, 2.0), (2.0, 5.0), (5.0, 90.0))
FEATURE_NAMES = [
    "zhat", "dist",                                   # A0
    "ens_exc", "ens_spread", "ens_max",               # +A1
    "hist_last", "hist_trend", "hist_max5",           # +A2
    "nbr11_hist_last", "nbr25_hist_max5", "nbr11_pred", "lead_frac",
]
ARMS = {
    "A0_trivial": [0, 1],
    "A1_ensemble": [0, 1, 2, 3, 4],
    "A2_full": list(range(12)),
    "A2h_history": [0, 1, 5, 6, 7, 8, 9, 10, 11],
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dump", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--per-bin", type=int, default=60,
                   help="max positives (and negatives) sampled per event per bin")
    p.add_argument("--align-tol", type=float, default=0.25,
                   help="max |dump truth - decoded dataset| tolerated (fp16 rounding)")
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args()


def decode_dbz(raw):
    return raw.astype(np.float32) * (PIXEL_SCALE / 255.0)


def load_dataset_event(vil, idx):
    """(15, 101, 101) dBZ metric view for one dataset row."""
    raw = np.transpose(vil[idx][VALID_LO:VALID_HI, VALID_LO:VALID_HI, :], (2, 0, 1))
    return decode_dbz(raw)


def event_features(members, frames):
    """members (S,T,H,W) fp32, frames (15,H,W) -> feature planes (F,T,H,W)."""
    n_leads = members.shape[1]
    zhat = members[0]
    inputs = frames[:INPUT_LEN]
    hist_last = inputs[-1]
    hist_trend = inputs[-1] - inputs[-3]
    hist_max5 = inputs.max(axis=0)
    nbr11_hist_last = ndimage.maximum_filter(hist_last, size=11)
    nbr25_hist_max5 = ndimage.maximum_filter(hist_max5, size=25)
    spread = members.std(axis=0)
    emax = members.max(axis=0)
    nbr11_pred = np.stack(
        [ndimage.maximum_filter(zhat[t], size=11) for t in range(n_leads)]
    )
    lead = np.arange(n_leads, dtype=np.float32) / max(n_leads - 1, 1)

    def tile(plane):
        return np.broadcast_to(plane, (n_leads,) + plane.shape)

    planes = [
        zhat,
        None,  # dist filled per threshold
        None,  # ens_exc filled per threshold
        spread,
        emax,
        tile(hist_last),
        tile(hist_trend),
        tile(hist_max5),
        tile(nbr11_hist_last),
        tile(nbr25_hist_max5),
        nbr11_pred,
        lead[:, None, None] * np.ones_like(zhat),
    ]
    return planes


def auc_rank(scores, labels):
    """Mann-Whitney AUC; nan if one class is missing."""
    pos = labels > 0.5
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1)
    # midranks for ties
    sorted_scores = scores[order]
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = 0.5 * (i + 1 + j + 1)
        i = j + 1
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def fit_logistic(x_fit, y_fit, epochs=300, lr=0.05):
    x = torch.from_numpy(x_fit)
    y = torch.from_numpy(y_fit)
    w = torch.zeros(x.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=lr)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    for _ in range(epochs):
        opt.zero_grad()
        loss = loss_fn(x @ w + b, y)
        loss.backward()
        opt.step()
    return lambda xe: (torch.from_numpy(xe) @ w.detach() + b.detach()).numpy()


def fit_mlp(x_fit, y_fit, epochs=4, batch=65536, lr=1e-3, seed=0):
    torch.manual_seed(seed)
    net = torch.nn.Sequential(
        torch.nn.Linear(x_fit.shape[1], 32), torch.nn.ReLU(),
        torch.nn.Linear(32, 16), torch.nn.ReLU(),
        torch.nn.Linear(16, 1),
    )
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    x = torch.from_numpy(x_fit)
    y = torch.from_numpy(y_fit)
    n = x.shape[0]
    for ep in range(epochs):
        perm = torch.randperm(n)
        for s in range(0, n, batch):
            idx = perm[s:s + batch]
            opt.zero_grad()
            loss = loss_fn(net(x[idx]).squeeze(-1), y[idx])
            loss.backward()
            opt.step()
    net.eval()
    def predict(xe):
        with torch.no_grad():
            out = []
            xt = torch.from_numpy(xe)
            for s in range(0, xt.shape[0], 262144):
                out.append(net(xt[s:s + 262144]).squeeze(-1).numpy())
        return np.concatenate(out)
    return predict


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    # rows[key] : list of (features(12,), label, bin_id, parity)
    rows = {f"{kind}{int(t)}": [] for t in THRESHOLDS for kind in ("fn", "fp")}

    with h5py.File(args.dump, "r") as dump, h5py.File(args.data, "r") as data:
        preds, truth_ds = dump["predictions"], dump["truth"]
        event_index = np.asarray(dump["event_index"]) if "event_index" in dump else None
        vil = data["vil"]
        n_all = preds.shape[0]
        n = n_all if args.max_events is None else min(args.max_events, n_all)

        for i in range(n):
            ds_idx = int(event_index[i]) if event_index is not None else i
            members = np.asarray(preds[i], dtype=np.float32)
            truth = np.asarray(truth_ds[i], dtype=np.float32)
            frames = load_dataset_event(vil, ds_idx)

            if i < 3:  # alignment gate
                gap = float(np.abs(frames[INPUT_LEN:] - truth).max())
                if gap > args.align_tol:
                    raise SystemExit(
                        f"ALIGNMENT FAILED at dump row {i} (dataset row {ds_idx}): "
                        f"max|truth - decoded frames| = {gap:.3f} > {args.align_tol}. "
                        "Refusing to fabricate history features."
                    )

            planes = event_features(members, frames)
            parity = i % 2
            for thr in THRESHOLDS:
                dist = planes[0] - thr
                exc = (members > thr).mean(axis=0)
                feats = np.stack(
                    [planes[0], dist, exc] + planes[3:], axis=-1
                )  # (T,H,W,12)
                pred_pos = planes[0] > thr
                true_pos = truth > thr

                for kind, cand, label_map, bins, depth in (
                    ("fn", ~pred_pos, true_pos, FN_BINS, thr - planes[0]),
                    ("fp", pred_pos, ~true_pos, FP_BINS, planes[0] - thr),
                ):
                    key = f"{kind}{int(thr)}"
                    for b_id, (lo, hi) in enumerate(bins):
                        in_bin = cand & (depth > lo) & (depth <= hi)
                        for want_pos in (True, False):
                            sel = in_bin & (label_map == want_pos)
                            idx = np.flatnonzero(sel.ravel())
                            if idx.size == 0:
                                continue
                            if idx.size > args.per_bin:
                                idx = rng.choice(idx, args.per_bin, replace=False)
                            f = feats.reshape(-1, len(FEATURE_NAMES))[idx]
                            lab = np.full(len(idx), float(want_pos), dtype=np.float32)
                            rows[key].append(
                                (f.astype(np.float32), lab, b_id, parity)
                            )
            if (i + 1) % 500 == 0:
                print(f"event {i + 1}/{n}", flush=True)

    out = {"dump": args.dump, "n_events": int(n), "per_bin": args.per_bin,
           "feature_names": FEATURE_NAMES, "arms": {}, "results": {}}
    for key, chunks in rows.items():
        if not chunks:
            continue
        x = np.concatenate([c[0] for c in chunks])
        y = np.concatenate([c[1] for c in chunks])
        b_id = np.concatenate([np.full(len(c[1]), c[2]) for c in chunks])
        par = np.concatenate([np.full(len(c[1]), c[3]) for c in chunks])
        fit_m, ev_m = par == 0, par == 1
        mu = x[fit_m].mean(axis=0)
        sd = x[fit_m].std(axis=0) + 1e-6
        xs = (x - mu) / sd

        res = {"n_fit": int(fit_m.sum()), "n_eval": int(ev_m.sum()), "bins": {}}
        bins = FN_BINS if key.startswith("fn") else FP_BINS
        preds_cache = {}
        for arm, cols in ARMS.items():
            xa_fit, xa_ev = xs[fit_m][:, cols], xs[ev_m][:, cols]
            models = {
                "logit": fit_logistic(xa_fit, y[fit_m]),
                "mlp": fit_mlp(xa_fit, y[fit_m], seed=args.seed),
            }
            preds_cache[arm] = {
                name: model(xa_ev) for name, model in models.items()
            }
        y_ev, b_ev = y[ev_m], b_id[ev_m]
        for arm in ARMS:
            res[arm] = {
                name: auc_rank(scores, y_ev)
                for name, scores in preds_cache[arm].items()
            }
        for bi, (lo, hi) in enumerate(bins):
            m = b_ev == bi
            entry = {"range_dbz": [lo, hi],
                     "n_pos": int(y_ev[m].sum()), "n_neg": int((1 - y_ev[m]).sum())}
            for arm in ARMS:
                entry[arm] = {
                    name: auc_rank(preds_cache[arm][name][m], y_ev[m])
                    for name in ("logit", "mlp")
                }
            res["bins"][f"bin{bi}"] = entry
        out["results"][key] = res

    # preregistered endpoint: FN40 deep bins, logit AUC(A2)-AUC(A1)
    try:
        fn40 = out["results"]["fn40"]["bins"]
        deltas = {
            b: fn40[b]["A2_full"]["logit"] - fn40[b]["A1_ensemble"]["logit"]
            for b in ("bin1", "bin2")
        }
        n_hit = sum(1 for v in deltas.values() if v >= 0.03)
        out["endpoint"] = {
            "deltas_A2_minus_A1_logit": deltas,
            "verdict": {2: "PASS", 1: "SOFT", 0: "FAIL"}[n_hit],
        }
    except KeyError:
        out["endpoint"] = {"verdict": "INCOMPLETE"}

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out.get("endpoint", {}), indent=2))
    print(f"written: {args.output}")


if __name__ == "__main__":
    main()
