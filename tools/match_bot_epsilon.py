"""Match BOT+FR's entropic bandwidth to WFR's on the training pilot.

WFR uses eps = eps_rel * 2 delta^2 (units km^2); BOT's default eps_rel * mean(cost)
is a different scale, which left BOT ~5x denser than WFR in the v1.0 pack and
confounded the "WFR beats BOT+FR" observation.

This scans absolute epsilons for BOT and reports, against WFR's values, the
mass-weighted RMS transport distance, retained edge count and plan entropy, so a
single matched epsilon can be frozen before the gate.
"""

import argparse

import h5py
import numpy as np
import torch

from common.wfr_oracle import core
from tools.run_cikm_hidden_frame_oracle import (
    VALID_LO, VALID_HI, LAST_INPUT_FRAME, decode_dbz, dbz_to_rain,
    _coupling_diagnostics)


def diagnostics_for_pair(r0, r1, delta, wfr_eps_rel, bot_eps_list, device):
    x0, a = core.field_to_atoms(r0, 1.0, device)
    x1, b = core.field_to_atoms(r1, 1.0, device)
    if a.numel() == 0 or b.numel() == 0:
        return None

    cost_w, valid = core.wfr_cost(x0, x1, delta)
    lam = 2.0 * delta ** 2
    gamma = core.sinkhorn_unbalanced(a, b, cost_w, valid, lam,
                                     wfr_eps_rel * lam, n_iter=800)
    out = {"wfr": _coupling_diagnostics(x0, x1, gamma, "wfr")}

    p, q = a / a.sum(), b / b.sum()
    cost_b = core.pairwise_sq_dist(x0, x1)
    for eps in bot_eps_list:
        pi = core.sinkhorn_balanced(p, q, cost_b, eps)
        out[f"bot_eps{eps:g}"] = _coupling_diagnostics(x0, x1, pi, "bot")
    out["bot_default"] = _coupling_diagnostics(
        x0, x1, core.sinkhorn_balanced(p, q, cost_b, 0.01 * float(cost_b.mean())),
        "bot")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default="datasets/cikm/data/cikm_full")
    p.add_argument("--split", default="training")
    p.add_argument("--n-samples", type=int, default=20)
    p.add_argument("--delta", type=float, default=12.0)
    p.add_argument("--wfr-eps-rel", type=float, default=0.005)
    p.add_argument("--bot-eps", nargs="+", type=float,
                   default=[0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
    p.add_argument("--dbz-floor", type=float, default=20.0)
    p.add_argument("--zr", nargs=2, type=float, default=[200.0, 1.6])
    p.add_argument("--max-atoms", type=int, default=7000)
    p.add_argument("--min-atoms", type=int, default=50)
    p.add_argument("--device", default="cuda:1")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    acc = {}
    with h5py.File(f"{args.data_dir}/nowcast_{args.split}_full.h5", "r") as hf:
        data = hf["vil"]
        rng = np.random.default_rng(args.seed)
        kept = 0
        for i in rng.permutation(data.shape[0]):
            if kept >= args.n_samples:
                break
            raw = np.transpose(data[i][VALID_LO:VALID_HI, VALID_LO:VALID_HI, :],
                               (2, 0, 1))
            rain = dbz_to_rain(decode_dbz(raw), *args.zr, args.dbz_floor)
            n_atoms = int((rain[LAST_INPUT_FRAME] > 0).sum())
            if not (args.min_atoms <= n_atoms <= args.max_atoms):
                continue
            kept += 1
            res = diagnostics_for_pair(rain[4], rain[6], args.delta,
                                       args.wfr_eps_rel, args.bot_eps, args.device)
            if res is None:
                continue
            for key, d in res.items():
                acc.setdefault(key, []).append(d)

    print(f"{kept} events, delta={args.delta} km, WFR eps_rel={args.wfr_eps_rel}\n")
    print(f"{'config':>16} {'edges':>10} {'rms_km':>9} {'entropy':>9}")
    ref = None
    for key, lst in acc.items():
        pre = "wfr" if key == "wfr" else "bot"
        e = np.median([d[f"{pre}_edges"] for d in lst])
        r = np.median([d[f"{pre}_rms_km"] for d in lst])
        h = np.median([d[f"{pre}_entropy"] for d in lst])
        if key == "wfr":
            ref = (e, r, h)
        print(f"{key:>16} {e:>10.0f} {r:>9.3f} {h:>9.3f}")
    if ref:
        print(f"\nmatch target (WFR): edges={ref[0]:.0f} rms={ref[1]:.3f} "
              f"entropy={ref[2]:.3f}")


if __name__ == "__main__":
    main()
