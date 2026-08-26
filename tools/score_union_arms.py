"""Union-of-arms readout: does ensemble DIVERSITY still have headroom?

`max` over M=8 members is the most aggressive decision rule a single arm can
produce, and it still under-reports area (FBI@30 = 0.95-0.99).  So M=8 is
exhausted.  This asks the next question: is the binding constraint the member
COUNT, or the fact that 8 members of one arm are nearly identical (ssr 0.04-0.07)?

Pooling the reward-diverse students (same teacher, different reward weight)
adds members that differ by construction.  If that moves the number, diversity
was the constraint; if it does not, the model simply does not produce the area.

This is a DIAGNOSTIC, not a compute-matched result: k arms cost k x inference.
Report it as such.
"""
import argparse, json, os, sys
import h5py, numpy as np
sys.path.append(os.getcwd())
THRESHOLDS = (20.0, 30.0, 35.0, 40.0)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--op", default=">=", choices=[">", ">="])
    p.add_argument("--k", type=int, default=1, help="report if >=k members exceed (1 = union)")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    ge = a.op == ">="

    hs = [h5py.File(f, "r") for f in a.files]
    n = min(h["predictions"].shape[0] for h in hs)
    n_leads = hs[0]["predictions"].shape[2]
    tot_members = sum(h["predictions"].shape[1] for h in hs)

    tp = np.zeros((len(THRESHOLDS), n_leads)); fp = np.zeros_like(tp)
    fn = np.zeros_like(tp); tn = np.zeros_like(tp)

    for i in range(n):
        obs = np.asarray(hs[0]["truth"][i], dtype=np.float32)
        mem = np.concatenate([np.asarray(h["predictions"][i], dtype=np.float32) for h in hs], axis=0)
        for k, thr in enumerate(THRESHOLDS):
            o = (obs >= thr) if ge else (obs > thr)
            exc = (mem >= thr) if ge else (mem > thr)
            pr = exc.sum(axis=0) >= a.k
            tp[k] += (pr & o).sum(axis=(1, 2)); fp[k] += (pr & ~o).sum(axis=(1, 2))
            fn[k] += (~pr & o).sum(axis=(1, 2)); tn[k] += (~pr & ~o).sum(axis=(1, 2))
    for h in hs: h.close()

    csi = tp / np.maximum(tp + fp + fn, 1.0)
    fbi = (tp + fp) / np.maximum(tp + fn, 1.0)
    key = lambda x: {str(int(t)): float(v) for t, v in zip(THRESHOLDS, x.mean(axis=1))}
    r = {"files": [os.path.basename(f) for f in a.files], "n_arms": len(a.files),
         "total_members": int(tot_members), "k": a.k, "op": a.op, "n_events": int(n),
         "csi_per_threshold": key(csi), "fbi_per_threshold": key(fbi),
         "csi_m": float(csi.mean(axis=1).mean())}
    txt = json.dumps(r, indent=2); print(txt)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w").write(txt + "\n")

if __name__ == "__main__":
    main()
