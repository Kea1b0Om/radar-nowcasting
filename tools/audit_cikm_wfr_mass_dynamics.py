"""K0 -- CIKM mass-dynamics / support audit for the WFR kill-shot.

Answers, before a single line of WFR machinery is written:

  (a) how much non-conservation is actually there on CIKM's 60-minute lead,
      split into global endpoint change, cumulative path variation, and the
      part that optical-flow advection cannot explain (G_end / G_path / G_local);
  (b) how many wet atoms a dense OET would carry, i.e. whether full-resolution
      dense coupling is feasible at all;
  (c) how much mass sits in the boundary band and how many events are
      near-dry -- both of which would poison a mass ledger.

Mass definition (repository-calibrated reflectivity-derived PROXY mass, NOT
surface rainfall):

    dBZ = raw_uint8 * (90 / 255)          # matches test_flowcast.py raw_to_eval_scale
    Z   = 10 ** (dBZ / 10)
    R   = (Z / a) ** (1 / b)              # default Marshall-Palmer (a, b) = (200, 1.6)
    R[dBZ < dbz_floor] = 0                # raw==0 would otherwise carry R ~ 0.03 mm/h

Cell area and dt are identical for every valid cell, so they are absorbed into a
fixed M_scale and every statistic reported here is a ratio.

Only the central 101x101 valid domain is used: cikm_preprocessing.py center-pads
101 -> 128 with zeros (pad_top=13, pad_bottom=14), and test_flowcast.py crops
back to [13:114] before scoring.
"""

import argparse
import json
import os

import h5py
import numpy as np
import pandas as pd

VALID_LO, VALID_HI = 13, 114  # 101x101 valid window inside the 128x128 canvas
PIXEL_SCALE = 90.0  # config: evaluation_params.pixel_scale
FRAME_MINUTES = 6.0
LAST_INPUT_FRAME = 4  # 5 input frames (0..4), 10 lead frames (5..14)


def decode_dbz(raw):
    return raw.astype(np.float32) * (PIXEL_SCALE / 255.0)


def dbz_to_rain(dbz, zr_a, zr_b, dbz_floor):
    """dBZ -> rain rate proxy [mm/h], zeroed below the wet floor."""
    z = np.power(10.0, dbz / 10.0, dtype=np.float32)
    rain = np.power(z / zr_a, 1.0 / zr_b, dtype=np.float32)
    rain[dbz < dbz_floor] = 0.0
    return rain


def boundary_band_mask(size, band):
    mask = np.zeros((size, size), dtype=bool)
    mask[:band, :] = True
    mask[-band:, :] = True
    mask[:, :band] = True
    mask[:, -band:] = True
    return mask


def sample_stats(rain, band_mask, near_dry_atoms):
    """rain: (T, H, W) float32 on the valid domain."""
    eps = 1e-12
    mass = rain.sum(axis=(1, 2))  # (T,)
    wet = (rain > 0).sum(axis=(1, 2))  # (T,)

    m0_seq, mT_seq = mass[0], mass[-1]
    m0_lead, mT_lead = mass[LAST_INPUT_FRAME], mass[-1]

    diffs = np.abs(np.diff(mass))
    diffs_lead = np.abs(np.diff(mass[LAST_INPUT_FRAME:]))

    band_mass = (rain * band_mask[None]).sum(axis=(1, 2))

    out = {
        "n_frames": int(rain.shape[0]),
        "mass_max": float(mass.max()),
        "mass_mean": float(mass.mean()),
        # --- endpoint change (G_end), full sequence and the 60-min lead window
        "signed_endpoint_change_seq": float((mT_seq - m0_seq) / (m0_seq + eps)),
        "abs_endpoint_change_seq": float(abs(mT_seq - m0_seq) / (m0_seq + eps)),
        "signed_endpoint_change_lead": float((mT_lead - m0_lead) / (m0_lead + eps)),
        "G_end": float(abs(mT_lead - m0_lead) / (m0_lead + eps)),
        # --- cumulative path variation (G_path)
        "G_path_seq": float(diffs.sum() / (mass[:-1].sum() + eps)),
        "G_path": float(diffs_lead.sum() / (mass[LAST_INPUT_FRAME:-1].sum() + eps)),
        "cumulative_mass_variation_lead": float(diffs_lead.sum() / (m0_lead + eps)),
        "mean_step_mass_change_lead": float(
            (diffs_lead / (mass[LAST_INPUT_FRAME:-1] + eps)).mean()
        ),
        "max_min_mass_range_lead": float(
            (mass[LAST_INPUT_FRAME:].max() - mass[LAST_INPUT_FRAME:].min())
            / (mass[LAST_INPUT_FRAME:].mean() + eps)
        ),
        # --- support / dense-OET scale
        "wet_atoms_min": int(wet.min()),
        "wet_atoms_median": int(np.median(wet)),
        "wet_atoms_max": int(wet.max()),
        "wet_atoms_last_input": int(wet[LAST_INPUT_FRAME]),
        "wet_fraction_median": float(np.median(wet) / (rain.shape[1] * rain.shape[2])),
        # --- boundary contamination
        "boundary_band_mass_fraction_mean": float(
            (band_mass / (mass + eps)).mean()
        ),
        "boundary_band_mass_fraction_max": float((band_mass / (mass + eps)).max()),
        # --- degenerate events
        "full_dry": bool(mass.max() <= 0),
        "near_dry": bool(np.median(wet) < near_dry_atoms),
    }
    return out, mass, wet


def advection_residual(rain, dbz, attenuation=1e-3):
    """G_local: L1 residual after warping each frame onto the next by dense flow.

    Flow is estimated on the dBZ field (bounded, roughly Gaussian-ish) rather
    than on the heavy-tailed rain rate. Warping is bilinear, hence NOT mass
    conserving -- this is a diagnostic residual, not a solver.

    Returns (G_local, G_persist): the same L1 residual with and without flow.
    """
    from skimage.registration import optical_flow_tvl1
    from skimage.transform import warp

    eps = 1e-12
    num_flow = 0.0
    num_persist = 0.0
    den = 0.0

    h, w = rain.shape[1], rain.shape[2]
    rows, cols = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")

    for t in range(rain.shape[0] - 1):
        src, dst = rain[t], rain[t + 1]
        if src.sum() <= 0 and dst.sum() <= 0:
            continue
        v, u = optical_flow_tvl1(
            dbz[t + 1], dbz[t], attachment=5.0, tightness=0.3, num_warp=3
        )
        warped = warp(
            src,
            np.array([rows + v, cols + u]),
            order=1,
            mode="constant",
            cval=0.0,
            preserve_range=True,
        )
        num_flow += np.abs(dst - warped).sum()
        num_persist += np.abs(dst - src).sum()
        den += np.abs(src).sum()

    if den <= 0:
        return float("nan"), float("nan")
    return float(num_flow / (den + eps)), float(num_persist / (den + eps))


def run_split(h5_path, meta_path, args, zr_a, zr_b):
    meta = pd.read_csv(meta_path)
    band_mask = boundary_band_mask(VALID_HI - VALID_LO, args.boundary_band)

    with h5py.File(h5_path, "r") as hf:
        data = hf["vil"]
        n_total = data.shape[0]
        idx = np.arange(n_total)
        if args.max_samples and args.max_samples < n_total:
            rng = np.random.default_rng(args.seed)
            idx = np.sort(rng.choice(n_total, size=args.max_samples, replace=False))

        flow_idx = set()
        if args.flow_samples > 0:
            rng = np.random.default_rng(args.seed + 1)
            k = min(args.flow_samples, len(idx))
            flow_idx = set(rng.choice(idx, size=k, replace=False).tolist())

        rows = []
        mass_curves = []
        for n, i in enumerate(idx):
            raw = data[i][VALID_LO:VALID_HI, VALID_LO:VALID_HI, :]  # (H, W, T)
            raw = np.transpose(raw, (2, 0, 1))  # (T, H, W)
            dbz = decode_dbz(raw)
            rain = dbz_to_rain(dbz, zr_a, zr_b, args.dbz_floor)

            stats, mass, wet = sample_stats(rain, band_mask, args.near_dry_atoms)
            stats["file_row"] = int(i)
            stats["sample_id"] = (
                str(meta.iloc[i]["sample_id"]) if i < len(meta) else f"row_{i}"
            )

            if i in flow_idx and not stats["full_dry"]:
                g_local, g_persist = advection_residual(
                    rain[LAST_INPUT_FRAME:], dbz[LAST_INPUT_FRAME:]
                )
                stats["G_local"] = g_local
                stats["G_persist"] = g_persist
            else:
                stats["G_local"] = float("nan")
                stats["G_persist"] = float("nan")

            rows.append(stats)
            if len(mass_curves) < args.keep_curves:
                mass_curves.append(
                    {"file_row": int(i), "mass": [float(x) for x in mass],
                     "wet": [int(x) for x in wet]}
                )
            if args.progress and (n + 1) % args.progress == 0:
                print(f"  ... {n + 1}/{len(idx)}", flush=True)

    return pd.DataFrame(rows), mass_curves


def summarize(df):
    """Quantile summary over non-degenerate events."""
    live = df[~df["full_dry"]]
    keep = live[~live["near_dry"]]
    qs = [0.05, 0.25, 0.5, 0.75, 0.95]

    def q(col, frame=keep):
        s = frame[col].dropna()
        if len(s) == 0:
            return {}
        return {f"p{int(p * 100)}": float(s.quantile(p)) for p in qs} | {
            "mean": float(s.mean()),
            "n": int(len(s)),
        }

    summary = {
        "n_samples": int(len(df)),
        "n_full_dry": int(df["full_dry"].sum()),
        "n_near_dry": int(df["near_dry"].sum()),
        "n_used": int(len(keep)),
        "G_end": q("G_end"),
        "G_path": q("G_path"),
        "G_local": q("G_local"),
        "G_persist": q("G_persist"),
        "signed_endpoint_change_lead": q("signed_endpoint_change_lead"),
        "cumulative_mass_variation_lead": q("cumulative_mass_variation_lead"),
        "max_min_mass_range_lead": q("max_min_mass_range_lead"),
        "wet_atoms_median": q("wet_atoms_median"),
        "wet_atoms_max": q("wet_atoms_max"),
        "boundary_band_mass_fraction_mean": q("boundary_band_mass_fraction_mean"),
    }
    if len(keep):
        summary["frac_G_end_gt_0.20"] = float((keep["G_end"] > 0.20).mean())
        summary["frac_G_end_gt_0.50"] = float((keep["G_end"] > 0.50).mean())
        summary["frac_signed_growth"] = float(
            (keep["signed_endpoint_change_lead"] > 0).mean()
        )
        summary["frac_boundary_gt_0.20"] = float(
            (keep["boundary_band_mass_fraction_mean"] > 0.20).mean()
        )
        wa = keep["wet_atoms_max"]
        summary["dense_oet_MiB_p95"] = float(
            (wa.quantile(0.95) ** 2) * 4 / 1024 ** 2
        )
        summary["dense_oet_MiB_max"] = float((wa.max() ** 2) * 4 / 1024 ** 2)
        gl = keep["G_local"].dropna()
        gp = keep["G_persist"].dropna()
        if len(gl) and len(gp):
            summary["flow_explains_median"] = float(
                1.0 - gl.median() / (gp.median() + 1e-12)
            )
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default="datasets/cikm/data/cikm_full")
    p.add_argument("--splits", nargs="+", default=["training", "validation"])
    p.add_argument("--out-dir", default="artifacts/cikm/wfr_audit")
    p.add_argument("--dbz-floor", type=float, default=15.0,
                   help="dBZ below this carries no mass (raw==0 -> 0 dBZ -> R~0.03).")
    p.add_argument("--zr", nargs=2, type=float, default=[200.0, 1.6],
                   metavar=("A", "B"), help="Primary Z=aR^b coefficients.")
    p.add_argument("--zr-alt", nargs=2, type=float, default=[300.0, 1.4],
                   metavar=("A", "B"), help="Sensitivity Z-R coefficients.")
    p.add_argument("--boundary-band", type=int, default=5)
    p.add_argument("--near-dry-atoms", type=int, default=50)
    p.add_argument("--max-samples", type=int, default=0, help="0 = all")
    p.add_argument("--flow-samples", type=int, default=200,
                   help="Samples that additionally get the optical-flow residual.")
    p.add_argument("--keep-curves", type=int, default=50)
    p.add_argument("--progress", type=int, default=500)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    report = {
        "config": {
            "valid_window": [VALID_LO, VALID_HI],
            "pixel_scale": PIXEL_SCALE,
            "frame_minutes": FRAME_MINUTES,
            "dbz_floor": args.dbz_floor,
            "zr_primary": args.zr,
            "zr_alt": args.zr_alt,
            "boundary_band": args.boundary_band,
            "near_dry_atoms": args.near_dry_atoms,
            "mass_caption": "repository-calibrated reflectivity-derived proxy mass",
        },
        "splits": {},
    }

    for split in args.splits:
        h5_path = os.path.join(args.data_dir, f"nowcast_{split}_full.h5")
        meta_path = os.path.join(args.data_dir, f"nowcast_{split}_full_META.csv")
        print(f"[{split}] {h5_path}", flush=True)

        df, curves = run_split(h5_path, meta_path, args, *args.zr)
        df.to_csv(os.path.join(args.out_dir, f"k0_{split}_primary.csv"), index=False)
        report["splits"][split] = {"primary": summarize(df)}

        # Z-R sensitivity: same samples, alternative coefficients, no flow pass.
        alt_args = argparse.Namespace(**vars(args))
        alt_args.flow_samples = 0
        df_alt, _ = run_split(h5_path, meta_path, alt_args, *args.zr_alt)
        df_alt.to_csv(os.path.join(args.out_dir, f"k0_{split}_zralt.csv"), index=False)
        report["splits"][split]["zr_alt"] = summarize(df_alt)

        with open(os.path.join(args.out_dir, f"k0_{split}_curves.json"), "w") as fh:
            json.dump(curves, fh)

    out_json = os.path.join(args.out_dir, "k0_summary.json")
    with open(out_json, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))
    print(f"\nwrote {out_json}")


if __name__ == "__main__":
    main()
