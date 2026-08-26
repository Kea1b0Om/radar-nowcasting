"""K1 v1.1 -- CIKM hidden-intermediate-frame oracle (fairness-closed).

Both endpoints are visible to every method; the intermediate frames are hidden
truth. Oracle interpolation, NOT nowcasting.

Spans (CIKM is 6 min per frame, valid domain 101x101 at 1 km):
    12 min : X4 -> X6,  hidden X5            (t = 0.5)   <- primary gate
    24 min : X4 -> X8,  hidden X5, X6, X7                <- secondary

Changes vs v1.0 (all four are fairness defects found in review of the v1.0 pack):
  1. `coarse2km` is skipped by default; when coarsening IS used, `cell_km`
     becomes 2.0 everywhere (atoms, splat, kernel, FSS window, HF cutoff) and R
     is block-*averaged* (density) rather than block-summed, so the dBZ used for
     FSS is not inflated by 10*b*log10(4) ~ +9.6 dBZ.
  2. Optical flow now has a *same-proxy* variant estimated on log1p(R) of the
     same floored field the OT methods see; the full-dBZ variant is retained
     only as a privileged upper bound.
  3. BOT+FR accepts an absolute epsilon so its entropic bandwidth can be matched
     to WFR's on the training pilot; both methods report coupling diagnostics
     (retained edges, mass-weighted RMS transport distance, plan entropy).
  4. Initiation is diagnosed by the share of target mass sitting in cells that
     were dry at the source frame -- the v1.0 dead/born fractions only detected
     atoms fully decoupled beyond pi*delta and said nothing about initiation.

Statistics are event-level: hidden frames within a file_row are averaged before
any bootstrap, and each baseline is compared as a *fixed* method (no per-sample
oracle selection). See tools/summarize_k1_gate.py.
"""

import argparse
import json
import os

import h5py
import numpy as np
import pandas as pd
import torch

from common.wfr_oracle import core

VERSION = "1.1"
VALID_LO, VALID_HI = 13, 114
PIXEL_SCALE = 90.0
BASE_CELL_KM = 1.0
LAST_INPUT_FRAME = 4
SPANS = {12: (4, 6, [5]), 24: (4, 8, [5, 6, 7])}


# ------------------------------------------------------------------ data ---

def decode_dbz(raw):
    return raw.astype(np.float32) * (PIXEL_SCALE / 255.0)


def dbz_to_rain(dbz, zr_a, zr_b, dbz_floor):
    rain = np.power(np.power(10.0, dbz / 10.0) / zr_a, 1.0 / zr_b).astype(np.float32)
    rain[dbz < dbz_floor] = 0.0
    return rain


def rain_to_dbz(rain, zr_a, zr_b):
    out = np.full(rain.shape, -100.0, dtype=np.float32)
    pos = rain > 0
    out[pos] = 10.0 * np.log10(zr_a * np.power(rain[pos], zr_b))
    return out


def block_reduce_mean(field, factor):
    """Density-preserving coarsening (rain rate and dBZ are both intensities)."""
    h, w = field.shape
    h2, w2 = h // factor, w // factor
    return field[: h2 * factor, : w2 * factor].reshape(h2, factor, w2, factor).mean((1, 3))


# --------------------------------------------------------------- methods ---

def method_linear(r0, r1, t, **_):
    return core.linear_field_interpolate(r0, r1, t), {}


def _tvl1_pair(field0, field1):
    from skimage.registration import optical_flow_tvl1
    v_f, u_f = optical_flow_tvl1(field1, field0, attachment=5.0, tightness=0.3,
                                 num_warp=3)
    v_b, u_b = optical_flow_tvl1(field0, field1, attachment=5.0, tightness=0.3,
                                 num_warp=3)
    return (v_f, u_f), (v_b, u_b)


def _flow_blend(r0, r1, t, fwd, bwd):
    from skimage.transform import warp
    h, w = r0.shape
    rows, cols = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    (v_f, u_f), (v_b, u_b) = fwd, bwd
    a = warp(r0, np.array([rows + t * v_f, cols + t * u_f]), order=1,
             mode="constant", cval=0.0, preserve_range=True)
    b = warp(r1, np.array([rows + (1 - t) * v_b, cols + (1 - t) * u_b]), order=1,
             mode="constant", cval=0.0, preserve_range=True)
    return ((1 - t) * a + t * b).astype(np.float32)


def method_flow_full(r0, r1, t, dbz0=None, dbz1=None, cache=None, **_):
    """Privileged upper bound: flow estimated on the unthresholded dBZ field."""
    if cache is not None and "full" in cache:
        fwd, bwd = cache["full"]
    else:
        fwd, bwd = _tvl1_pair(dbz0, dbz1)
        if cache is not None:
            cache["full"] = (fwd, bwd)
    return _flow_blend(r0, r1, t, fwd, bwd), {}


def method_flow_proxy(r0, r1, t, cache=None, **_):
    """Fair primary baseline: flow estimated on log1p(R) of the same floored field
    the OT methods see, so both sides use identical information."""
    if cache is not None and "proxy" in cache:
        fwd, bwd = cache["proxy"]
    else:
        fwd, bwd = _tvl1_pair(np.log1p(r0), np.log1p(r1))
        if cache is not None:
            cache["proxy"] = (fwd, bwd)
    return _flow_blend(r0, r1, t, fwd, bwd), {}


def _coupling_diagnostics(x0, x1, plan, prefix):
    """Retained edges, mass-weighted RMS transport distance, normalised entropy."""
    tot = plan.sum().clamp(min=1e-30)
    ei, ej = torch.nonzero(plan > 0, as_tuple=True)
    if ei.numel() == 0:
        return {f"{prefix}_edges": 0, f"{prefix}_rms_km": float("nan"),
                f"{prefix}_entropy": float("nan")}
    w = plan[ei, ej] / tot
    d = torch.linalg.norm(x1[ej] - x0[ei], dim=-1)
    rms = torch.sqrt((w * d ** 2).sum()).item()
    ent = -(w * torch.log(w.clamp(min=1e-30))).sum().item()
    return {f"{prefix}_edges": int(ei.numel()), f"{prefix}_rms_km": float(rms),
            f"{prefix}_entropy": float(ent)}


def method_bot_fr(r0, r1, t, device="cpu", cell_km=1.0, eps_rel=0.01,
                  eps_abs=None, **_):
    x0, a = core.field_to_atoms(r0, cell_km, device)
    x1, b = core.field_to_atoms(r1, cell_km, device)
    if a.numel() == 0 or b.numel() == 0:
        return method_linear(r0, r1, t)

    m0_tot, m1_tot = a.sum(), b.sum()
    p, q = a / m0_tot, b / m1_tot
    cost = core.pairwise_sq_dist(x0, x1)
    eps = eps_abs if eps_abs is not None else eps_rel * float(cost.mean())
    pi = core.sinkhorn_balanced(p, q, cost, eps)

    keep = pi > (1e-6 * pi.max().clamp(min=1e-30))
    ei, ej = torch.nonzero(keep, as_tuple=True)
    w = pi[ei, ej]
    mass_total = ((1 - t) * torch.sqrt(m0_tot) + t * torch.sqrt(m1_tot)) ** 2
    pos = (1 - t) * x0[ei] + t * x1[ej]
    mass = mass_total * w / w.sum().clamp(min=1e-30)

    field, lost = core.splat_bilinear(pos, mass, r0.shape, cell_km=cell_km)
    diag = {"eps_used": float(eps)}
    diag.update(_coupling_diagnostics(x0, x1, pi, "bot"))
    diag["splat_lost_frac"] = float(lost / mass.sum().clamp(min=1e-12))
    return field.cpu().numpy(), diag


def method_wfr(r0, r1, t, device="cpu", cell_km=1.0, delta=12.0, eps_rel=0.005,
               n_iter=800, **_):
    x0, a = core.field_to_atoms(r0, cell_km, device)
    x1, b = core.field_to_atoms(r1, cell_km, device)
    if a.numel() == 0 or b.numel() == 0:
        return method_linear(r0, r1, t)

    cost, valid = core.wfr_cost(x0, x1, delta)
    lam = 2.0 * delta ** 2
    eps = eps_rel * lam
    gamma = core.sinkhorn_unbalanced(a, b, cost, valid, lam, eps, n_iter=n_iter)
    m0, m1, dead, born = core.semi_coupling_lift(gamma, a, b)

    keep = gamma > (1e-6 * gamma.max().clamp(min=1e-30))
    ei, ej = torch.nonzero(keep, as_tuple=True)
    pos_e, mass_e = core.cone_interpolate(x0[ei], x1[ej], m0[ei, ej], m1[ei, ej],
                                          delta, t)
    pos = torch.cat([pos_e, x0[dead > 0], x1[born > 0]], dim=0)
    mass = torch.cat([mass_e, (1 - t) ** 2 * dead[dead > 0],
                      t ** 2 * born[born > 0]], dim=0)

    field, lost = core.splat_bilinear(pos, mass, r0.shape, cell_km=cell_km)
    growth = torch.clamp(m1[ei, ej] - m0[ei, ej], min=0).sum()
    diag = {
        "eps_used": float(eps),
        "decoupled_death_frac": float(dead.sum() / a.sum().clamp(min=1e-30)),
        "decoupled_birth_frac": float(born.sum() / b.sum().clamp(min=1e-30)),
        "edge_growth_share": float(growth / b.sum().clamp(min=1e-30)),
        "splat_lost_frac": float(lost / mass.sum().clamp(min=1e-12)),
    }
    diag.update(_coupling_diagnostics(x0, x1, gamma, "wfr"))
    return field.cpu().numpy(), diag


METHODS = {
    "linear": method_linear,
    "flow_proxy": method_flow_proxy,
    "flow_full": method_flow_full,
    "bot_fr": method_bot_fr,
    "wfr": method_wfr,
}


# --------------------------------------------------------------- metrics ---

def nl1(pred, truth):
    return float(np.abs(pred - truth).sum() / (np.abs(truth).sum() + 1e-12))


def fss(pred_dbz, truth_dbz, thr, window_cells):
    pf = (pred_dbz >= thr).astype(np.float32)
    po = (truth_dbz >= thr).astype(np.float32)
    if po.sum() == 0 and pf.sum() == 0:
        return float("nan")
    if window_cells > 1:
        k = torch.ones((1, 1, window_cells, window_cells)) / window_cells ** 2
        pf = torch.nn.functional.conv2d(torch.as_tensor(pf)[None, None], k,
                                        padding=window_cells // 2)[0, 0].numpy()
        po = torch.nn.functional.conv2d(torch.as_tensor(po)[None, None], k,
                                        padding=window_cells // 2)[0, 0].numpy()
    num = float(((pf - po) ** 2).sum())
    den = float((pf ** 2).sum() + (po ** 2).sum())
    return float(1.0 - num / (den + 1e-12)) if den > 0 else float("nan")


def hf_energy_ratio(pred, truth, cell_km, cutoff_km=10.0):
    def hf(x):
        f = np.fft.rfft2(x)
        ky = np.fft.fftfreq(x.shape[0], d=cell_km)[:, None]
        kx = np.fft.rfftfreq(x.shape[1], d=cell_km)[None, :]
        kr = np.sqrt(ky ** 2 + kx ** 2)
        return float((np.abs(f) ** 2)[kr > 1.0 / cutoff_km].sum())
    e_t = hf(truth)
    return float(hf(pred) / (e_t + 1e-12)) if e_t > 0 else float("nan")


def score_pair(pred, truth, cell_km, sigma_km, fss_window_km, zr_a, zr_b,
               thresholds=(35.0, 40.0)):
    out = {}
    sigma_cells = sigma_km / cell_km
    win = max(1, int(round(fss_window_km / cell_km)) | 1)  # force odd
    pa = core.gaussian_blur(torch.as_tensor(pred), sigma_cells).numpy()
    ta = core.gaussian_blur(torch.as_tensor(truth), sigma_cells).numpy()
    out["A_nl1"] = nl1(pa, ta)
    out["B_nl1_raw"] = nl1(pred, truth)

    pdbz = rain_to_dbz(pred, zr_a, zr_b)
    tdbz = rain_to_dbz(truth, zr_a, zr_b)
    for thr in thresholds:
        out[f"B_fss{int(thr)}_w1"] = fss(pdbz, tdbz, thr, 1)
        out[f"B_fss{int(thr)}_wN"] = fss(pdbz, tdbz, thr, win)
    out["B_peak_retention"] = float(pred.max() / (truth.max() + 1e-12))
    out["B_q99_retention"] = float(
        np.quantile(pred, 0.99) / (np.quantile(truth, 0.99) + 1e-12))
    out["B_hf_energy_ratio"] = hf_energy_ratio(pred, truth, cell_km)
    out["B_mass_ratio"] = float(pred.sum() / (truth.sum() + 1e-12))
    out["fss_window_cells"] = win
    return out


# ------------------------------------------------------------------- run ---

def run(args):
    os.makedirs(args.out_dir, exist_ok=True)
    zr_a, zr_b = args.zr
    h5_path = os.path.join(args.data_dir, f"nowcast_{args.split}_full.h5")
    rows = []

    with h5py.File(h5_path, "r") as hf:
        data = hf["vil"]
        rng = np.random.default_rng(args.seed)
        pool = rng.permutation(data.shape[0])  # draw until n native events found
        n_kept = 0

        for i in pool:
            if n_kept >= args.n_samples:
                break
            raw = np.transpose(data[i][VALID_LO:VALID_HI, VALID_LO:VALID_HI, :],
                               (2, 0, 1))
            dbz_all = decode_dbz(raw)
            rain_all = dbz_to_rain(dbz_all, zr_a, zr_b, args.dbz_floor)
            n_atoms = int((rain_all[LAST_INPUT_FRAME] > 0).sum())
            if n_atoms < args.min_atoms:
                continue

            factor, stratum, cell_km = 1, "native", BASE_CELL_KM
            if n_atoms > args.max_atoms:
                if args.overflow == "skip":
                    continue
                factor, stratum, cell_km = 2, "coarse2km", 2 * BASE_CELL_KM
            n_kept += 1

            for span, (i0, i1, hidden) in SPANS.items():
                if span not in args.spans:
                    continue
                r0, r1 = rain_all[i0], rain_all[i1]
                d0, d1 = dbz_all[i0], dbz_all[i1]
                if factor > 1:
                    r0, r1 = (block_reduce_mean(r0, factor),
                              block_reduce_mean(r1, factor))
                    d0, d1 = (block_reduce_mean(d0, factor),
                              block_reduce_mean(d1, factor))
                flow_cache = {}

                # initiation proxy: target mass sitting where the source was dry
                dry0 = r0 <= 0

                for hf_idx in hidden:
                    t = (hf_idx - i0) / (i1 - i0)
                    truth = rain_all[hf_idx]
                    if factor > 1:
                        truth = block_reduce_mean(truth, factor)
                    if truth.sum() <= 0:
                        continue

                    for name in args.methods:
                        pred, diag = METHODS[name](
                            r0, r1, t, dbz0=d0, dbz1=d1, cache=flow_cache,
                            device=args.device, cell_km=cell_km,
                            delta=args.delta, eps_rel=(args.wfr_eps_rel
                                                       if name == "wfr"
                                                       else args.bot_eps_rel),
                            eps_abs=args.bot_eps_abs if name == "bot_fr" else None,
                            n_iter=args.n_iter)
                        rec = {"file_row": int(i), "span_min": span, "t": t,
                               "hidden_frame": hf_idx, "method": name,
                               "stratum": stratum, "cell_km": cell_km,
                               "n_atoms": n_atoms, "delta_km": args.delta,
                               "zr_a": zr_a, "zr_b": zr_b,
                               "dbz_floor": args.dbz_floor,
                               "target_mass_in_source_dry_frac": float(
                                   (r1 * dry0).sum() / max(r1.sum(), 1e-12)),
                               "truth_mass_in_source_dry_frac": float(
                                   (truth * dry0).sum() / max(truth.sum(), 1e-12))}
                        rec.update(score_pair(pred, truth, cell_km, args.sigma_km,
                                              args.fss_window_km, zr_a, zr_b))
                        rec.update({f"diag_{k}": v for k, v in diag.items()})
                        rows.append(rec)

            if args.progress and n_kept % args.progress == 0:
                print(f"  ... {n_kept}/{args.n_samples} native events", flush=True)

    df = pd.DataFrame(rows)
    tag = (f"v{VERSION}_{args.split}_delta{args.delta:g}"
           f"_zr{zr_a:g}-{zr_b:g}_floor{args.dbz_floor:g}")
    if args.tag:
        tag += f"_{args.tag}"
    path = os.path.join(args.out_dir, f"k1_{tag}.csv")
    df.to_csv(path, index=False)
    print(f"wrote {path}  ({df.file_row.nunique()} events, {len(df)} rows)")
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="datasets/cikm/data/cikm_full")
    p.add_argument("--split", default="training")
    p.add_argument("--out-dir", default="artifacts/cikm/wfr_oracle_v11")
    p.add_argument("--tag", default="")
    p.add_argument("--n-samples", type=int, default=200)
    p.add_argument("--spans", nargs="+", type=int, default=[12])
    p.add_argument("--methods", nargs="+",
                   default=["linear", "flow_proxy", "flow_full", "bot_fr", "wfr"])
    p.add_argument("--delta", type=float, default=12.0)
    p.add_argument("--wfr-eps-rel", type=float, default=0.005)
    p.add_argument("--bot-eps-rel", type=float, default=0.01)
    p.add_argument("--bot-eps-abs", type=float, default=None,
                   help="Absolute entropic epsilon for BOT (bandwidth matching).")
    p.add_argument("--n-iter", type=int, default=800)
    p.add_argument("--sigma-km", type=float, default=2.0)
    p.add_argument("--fss-window-km", type=float, default=5.0)
    p.add_argument("--dbz-floor", type=float, default=20.0)
    p.add_argument("--zr", nargs=2, type=float, default=[200.0, 1.6])
    p.add_argument("--min-atoms", type=int, default=50)
    p.add_argument("--max-atoms", type=int, default=7000)
    p.add_argument("--overflow", choices=["coarsen", "skip"], default="skip")
    p.add_argument("--device", default="cuda:1")
    p.add_argument("--progress", type=int, default=25)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    run(args)


if __name__ == "__main__":
    main()
