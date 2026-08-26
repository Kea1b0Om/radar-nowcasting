"""Flow-GRPO pilot on FlowCast: rollout -> reward -> group advantage -> update.

Runs against a frozen checkpoint and never touches the supervised training code.

Two modes:

``--stage0``  Self-check only, no optimizer step.  Verifies the invariants that
              make the rest meaningful and that a training curve cannot reveal:

              * the importance ratio is **exactly** 1 when the policy has not
                moved (if it is not, the stored ``log_prob_old`` and the update
                pass disagree, and every later ratio is measuring the bug rather
                than the policy);
              * ``zero_std_ratio`` matches the value measured offline for this
                reward (0.45% for csi_M, 11.45% for csi40) -- a mismatch means
                the reward wired here is not the reward that was gated;
              * advantages are finite, zero-mean per group, and exactly zero on
                degenerate groups;
              * gradients are finite and reach the backbone.

``--steps N`` Pilot training.  Logs reward, its components, ratio/clip
              diagnostics, grad norm and ``zero_std_ratio`` every step.

Design points that came out of measurement rather than taste:

* the policy is the **uncompensated** SDE at ``kappa=1`` -- the marginal-
  preserving form provably cannot widen the group, and the uncompensated one was
  measured to widen the within-group reward range 2.35x at no cost in CSI/MSE;
* the reward is composite and continuous, because a single-threshold CSI leaves
  11.45% of groups with identical members and therefore exactly zero gradient;
* the baseline for any later comparison must use **this same sampler** -- the
  sampler change alone is worth -10.2% CRPS, and attributing that to RL would be
  a measurement error, not a result.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Subset

sys.path.append(os.getcwd())

from common.models.flowcast.grpo import (
    clipped_policy_loss,
    group_advantages,
    sde_step_with_logprob,
)
from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper, make_chunk_index
from common.models.flowcast.schedule import build_sampling_timesteps
from experiments.sevir.dataset.sevirfulldataset import (
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
)

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)


@dataclass
class Transition:
    """One stored SDE step, everything the update pass needs to rescore it."""

    z: torch.Tensor
    z_next: torch.Tensor
    cond: torch.Tensor
    chunk_idx: int
    t_int: int
    s_cur: float
    s_next: float
    log_prob_old: torch.Tensor


def per_event_reward(
    pred: torch.Tensor,
    truth: torch.Tensor,
    w_csi: float,
    w_cont: float,
    mse_ref: float,
) -> Dict[str, torch.Tensor]:
    """Composite continuous reward on the metric view, shape ``(N,)``.

    ``pred``/``truth`` are ``(N, T, H, W)`` in dBZ after crop and clamp -- the
    same view every other number in this project is reported on.
    """
    csi_terms = []
    for thr in THRESHOLDS:
        p, o = pred >= thr, truth >= thr
        tp = (p & o).flatten(1).sum(dim=1).float()
        fp = (p & ~o).flatten(1).sum(dim=1).float()
        fn = (~p & o).flatten(1).sum(dim=1).float()
        csi_terms.append(tp / (tp + fp + fn + 1.0))
    csi_m = torch.stack(csi_terms, dim=0).mean(dim=0)
    mse = ((pred - truth) ** 2).flatten(1).mean(dim=1)
    cont = 1.0 - (mse / mse_ref).clamp(0.0, 2.0) / 2.0
    return {
        "reward": w_csi * csi_m + w_cont * cont,
        "csi_m": csi_m,
        "mse": mse,
        "continuous": cont,
    }


class Pilot:
    def __init__(self, args):
        self.args = args
        self.cfg = OmegaConf.load(args.config)
        self.device = torch.device("cuda")
        self.dtype = {"bf16": torch.bfloat16, "fp16": torch.float16,
                      "fp32": torch.float32}[args.precision]

        c = self.cfg
        self.input_length = OmegaConf.select(c, "data_params.input_length",
                                             default=c.data_params.lag_time)
        self.output_length = OmegaConf.select(c, "data_params.output_length",
                                              default=c.data_params.lead_time)
        self.num_chunks = self.output_length // self.input_length
        self.T = c.rflow_params.num_train_timesteps
        self.euler_steps = OmegaConf.select(c, "sampling_params.euler_steps",
                                            default=c.test_params.euler_steps)
        self.pixel_scale = OmegaConf.select(c, "evaluation_params.pixel_scale",
                                            default=255.0)
        self.is_cikm = OmegaConf.select(c, "data_params.dataset_name",
                                        default="sevir") == "cikm"
        self.grid = build_sampling_timesteps(self.T, self.euler_steps, self.device)
        self.scale = float(self.T - 1)

        self._build_models()
        self._build_data()

    # ------------------------------------------------------------------ setup
    def _build_models(self):
        from diffusers.models.autoencoders import AutoencoderKL

        ap = self.cfg.autoencoder_params
        self.ae = AutoencoderKL(
            in_channels=1, out_channels=1, down_block_types=ap.down_block_types,
            up_block_types=ap.up_block_types, block_out_channels=ap.block_out_channels,
            act_fn=ap.act_fn, latent_channels=ap.latent_channels,
            norm_num_groups=ap.norm_num_groups, layers_per_block=ap.layers_per_block,
        )
        ck = torch.load(ap.autoencoder_checkpoint, map_location="cpu")
        state = {(k[len("module."):] if k.startswith("module.") else k): v
                 for k, v in ck["model_state_dict"].items()}
        self.ae.load_state_dict(state)
        self.ae = self.ae.to(self.device).eval().requires_grad_(False)
        self.ae_normalized = ap.normalized_autoencoder

        hp = self.cfg.stdit
        self.model = FlowCastSTDiTWrapper(
            latent_channels=ap.latent_channels, hidden_size=hp.hidden_size,
            depth=hp.depth, num_heads=hp.num_heads, patch_size=hp.patch_size,
        )
        ck = torch.load(self.args.checkpoint, map_location="cpu")
        sd = ck.get("model_state_dict", ck)
        sd = {(k[len("module."):] if k.startswith("module.") else k): v
              for k, v in sd.items()}
        missing, unexpected = self.model.load_state_dict(sd, strict=False)
        if len(missing) > 2:  # mean/std buffers may legitimately be absent
            raise RuntimeError(f"checkpoint mismatch: {len(missing)} missing keys")
        self.model = self.model.to(self.device)
        print(f"loaded policy: {sum(p.numel() for p in self.model.parameters())/1e6:.1f}M "
              f"params, missing={len(missing)} unexpected={len(unexpected)}", flush=True)

        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.args.lr, weight_decay=0.0,
            betas=(0.9, 0.999),
        )

    def _build_data(self):
        c = self.cfg
        ds = DynamicSequentialSevirDataset(
            meta_csv=self.args.train_meta, data_file=self.args.train_file,
            data_type=OmegaConf.select(c, "data_params.data_key", default="vil"),
            raw_seq_len=OmegaConf.select(c, "data_params.raw_seq_len", default=49),
            lag_time=self.input_length, lead_time=self.output_length,
            time_spacing=c.data_params.time_spacing,
            stride=OmegaConf.select(c, "data_params.stride", default=12),
            channel_last=False, debug_mode=False,
        )
        total = len(ds)
        lo = self.args.condition_start
        hi = total if self.args.condition_end is None else min(self.args.condition_end, total)
        if not 0 <= lo < hi:
            raise ValueError(f"bad condition range [{lo}, {hi}) for {total} conditions")
        if (lo, hi) != (0, total):
            # Contiguous block, never a random subset: neighbouring validation
            # events share weather, so a random split would put the same storm
            # on both sides of the RL/eval boundary.
            ds = Subset(ds, range(lo, hi))
        self.split_range = (lo, hi, total)
        if self.args.max_conditions:
            ds = Subset(ds, range(min(self.args.max_conditions, len(ds))))
        self.loader = DataLoader(
            ds, batch_size=1, shuffle=True, collate_fn=dynamic_sequential_collate,
            num_workers=2, pin_memory=True, drop_last=True,
        )
        print(f"dataset: {len(ds)} conditions", flush=True)

    # ------------------------------------------------------------- primitives
    def encode_cond(self, x_cond: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            x = x_cond.to(self.device)
            if self.ae_normalized:
                x = x / 255.0
            b, t = x.shape[0], x.shape[2]
            flat = x.permute(0, 2, 1, 3, 4).reshape(b * t, 1, *x.shape[-2:])
            lat = self.ae.encode(flat).latent_dist.mode()
            lat = lat.reshape(b, t, *lat.shape[1:]).permute(0, 1, 3, 4, 2)
            return self.model.normalize(lat)

    def decode_to_metric(self, latent: torch.Tensor) -> torch.Tensor:
        """Latent ``(N, T, h, w, c)`` -> dBZ ``(N, T, 101, 101)``, the metric view."""
        with torch.no_grad():
            # the rollout runs in bf16/fp16; the frozen AE is fp32
            lat = self.model.denormalize(latent.float())
            n, t = lat.shape[0], lat.shape[1]
            flat = lat.reshape(n * t, *lat.shape[2:]).permute(0, 3, 1, 2).contiguous()
            out = []
            step = self.cfg.test_params.batch_size_autoencoder
            for i in range(0, flat.shape[0], step):
                out.append(self.ae.decode(flat[i:i + step]).sample)
            px = torch.cat(out, dim=0).reshape(n, t, *out[0].shape[-2:])
            px = px * self.pixel_scale if self.ae_normalized else px
            if self.is_cikm:
                px = px[:, :, 13:-14, 13:-14]
            return px.clamp(0.0, self.pixel_scale)

    # ---------------------------------------------------------------- rollout
    @torch.no_grad()
    def rollout(self, cond0: torch.Tensor) -> (List[Transition], torch.Tensor):
        """G members from one condition, storing every stochastic transition."""
        g = self.args.group_size
        cond = cond0.expand(g, *cond0.shape[1:]).contiguous().to(self.dtype)
        transitions: List[Transition] = []
        preds = []
        for chunk in range(1, self.num_chunks + 1):
            chunk_index = make_chunk_index(g, chunk, self.device)
            z = torch.randn(cond.shape, device=self.device, dtype=self.dtype)
            for cur, nxt in zip(self.grid[:-1], self.grid[1:]):
                t_int = int(cur.item())
                s_cur, s_next = t_int / self.scale, int(nxt.item()) / self.scale
                t = torch.full((g,), t_int, device=self.device, dtype=torch.long)
                with torch.autocast("cuda", dtype=self.dtype, enabled=self.dtype != torch.float32):
                    v = self.model(z, t, cond, chunk_index)
                if s_next <= 0.0:
                    z = (z.float() + v.float() * (s_cur - s_next)).to(self.dtype)
                    continue
                z_next, logp, _, _ = sde_step_with_logprob(
                    z, v, s_cur, s_next, kappa=self.args.kappa,
                    compensate=not self.args.uncompensated, reduction="mean",
                )
                transitions.append(Transition(
                    z=z.detach().clone(), z_next=z_next.detach().clone(),
                    cond=cond.detach().clone(), chunk_idx=chunk, t_int=t_int,
                    s_cur=s_cur, s_next=s_next, log_prob_old=logp.detach().clone(),
                ))
                z = z_next.to(self.dtype)
            preds.append(z)
            cond = z
        return transitions, torch.cat(preds, dim=1)

    def score(self, latent_pred: torch.Tensor, truth: torch.Tensor) -> Dict:
        px = self.decode_to_metric(latent_pred)
        return per_event_reward(px, truth, self.args.w_csi, self.args.w_cont,
                                self.args.mse_ref)

    # ----------------------------------------------------------------- update
    def policy_logprobs(self, batch: List[Transition]) -> torch.Tensor:
        """Rescore stored transitions under the current policy.

        One forward **per transition**, at the same batch shape the rollout used.
        Stacking transitions into one wider batch is cheaper on paper but changes
        the bf16 kernel choice and reduction order, which showed up as a
        ratio-vs-1 noise floor of 3.9e-4 on an untouched policy -- only 2.6x
        below the 1e-3 clip range, i.e. the clip would have been guarding mostly
        numerical noise.  At G=16 two separate forwards cost the same as one
        double-width forward anyway (measured: 2 x 0.050 s vs 0.104 s).
        """
        logps = []
        for tr in batch:
            chunk_index = make_chunk_index(tr.z.shape[0], tr.chunk_idx, self.device)
            t = torch.full((tr.z.shape[0],), tr.t_int, device=self.device,
                           dtype=torch.long)
            with torch.autocast("cuda", dtype=self.dtype,
                                enabled=self.dtype != torch.float32):
                v = self.model(tr.z, t, tr.cond, chunk_index)
            _, lp, _, _ = sde_step_with_logprob(
                tr.z, v, tr.s_cur, tr.s_next, kappa=self.args.kappa,
                compensate=not self.args.uncompensated,
                prev_sample=tr.z_next, reduction="mean",
            )
            logps.append(lp)
        return torch.cat(logps, dim=0)

    # -------------------------------------------------------------- iteration
    def train_iteration(self, conditions, rng) -> Dict:
        """Collect ``K`` groups, then take several optimizer steps over them.

        This is the shape the reference uses and the reason run1 was uninformative:
        with one condition per optimizer step and the update taken immediately
        after the rollout, ``log_prob_new`` is computed under the very weights
        that produced ``log_prob_old``, so the ratio is identically 1, the clip
        can never bind, and the objective silently degenerates to plain REINFORCE.
        Here the weights move between minibatches inside the update phase, so the
        ratio genuinely departs from 1 and ``clip_fraction`` becomes a real
        diagnostic rather than a constant zero.
        """
        stored, rewards, parts_acc, truth_wet = [], [], [], []
        for x_cond, x_true in conditions:
            cond0 = self.encode_cond(x_cond)
            truth = x_true.squeeze(1).to(self.device)
            if self.is_cikm:
                truth = truth[:, :, 13:-14, 13:-14]
            truth = truth.float() * (self.pixel_scale / 255.0)
            truth = truth.expand(self.args.group_size, *truth.shape[1:])
            transitions, latent_pred = self.rollout(cond0)
            parts = self.score(latent_pred, truth)
            picks = rng.choice(len(transitions),
                               size=min(self.args.transitions_per_update, len(transitions)),
                               replace=False)
            stored.append([transitions[i] for i in picks])
            rewards.append(parts["reward"])
            parts_acc.append(parts)
            truth_wet.append(float((truth[0] >= 20).float().mean()))

        reward_mat = torch.stack(rewards, dim=0)                    # (K, G)
        adv = group_advantages(reward_mat, mode=self.args.adv_mode)  # (K, G)

        flat = [(k, tr) for k, trs in enumerate(stored) for tr in trs]
        order = rng.permutation(len(flat))
        chunks = np.array_split(order, self.args.num_minibatches)

        step_stats = []
        for _ in range(self.args.num_inner_epochs):
            for mb in chunks:
                if len(mb) == 0:
                    continue
                sel = [flat[i] for i in mb]
                # Gradient accumulation *inside* the minibatch: one autograd graph
                # alive at a time.  Scoring the whole minibatch first and calling
                # backward once keeps every graph resident -- measured at 9.13 GiB
                # per forward+backward at G=16, so eight of them OOM a 47 GiB card.
                # Accumulating gives the same effective batch at 1/len(mb) the peak.
                self.optimizer.zero_grad(set_to_none=True)
                mb_stats, mb_loss = [], 0.0
                for k, tr in sel:
                    logp_new = self.policy_logprobs([tr])
                    loss, st = clipped_policy_loss(
                        logp_new, tr.log_prob_old, adv[k], self.args.clip_range
                    )
                    (loss / len(sel)).backward()
                    mb_stats.append(st)
                    mb_loss += float(loss) / len(sel)
                gn = torch.nn.utils.clip_grad_norm_(self.model.parameters(),
                                                    self.args.max_grad_norm)
                self.optimizer.step()
                step_stats.append({
                    "loss": mb_loss,
                    "grad_norm": float(gn),
                    "ratio_mean": float(np.mean([s["ratio_mean"] for s in mb_stats])),
                    "ratio_max_abs_dev": float(max(s["ratio_max_abs_dev"] for s in mb_stats)),
                    "clip_fraction": float(np.mean([s["clip_fraction"] for s in mb_stats])),
                })

        span = reward_mat.amax(dim=1) - reward_mat.amin(dim=1)
        return {
            "reward_mean": float(reward_mat.mean()),
            "csi_m_mean": float(torch.stack([p["csi_m"] for p in parts_acc]).mean()),
            "mse_mean": float(torch.stack([p["mse"] for p in parts_acc]).mean()),
            "reward_within_range": float(span.mean()),
            "zero_std_ratio": float((span <= 1e-12).float().mean()),
            "adv_abs_mean": float(adv.abs().mean()),
            "truth_frac_ge20": float(np.mean(truth_wet)),
            "n_optim_steps": len(step_stats),
            "loss": float(np.mean([s["loss"] for s in step_stats])),
            "grad_norm": float(np.mean([s["grad_norm"] for s in step_stats])),
            "ratio_max_abs_dev": float(max(s["ratio_max_abs_dev"] for s in step_stats)),
            "ratio_mean": float(np.mean([s["ratio_mean"] for s in step_stats])),
            "clip_fraction": float(np.mean([s["clip_fraction"] for s in step_stats])),
        }

    def run_batched(self):
        rng = np.random.default_rng(self.args.seed)
        torch.manual_seed(self.args.seed)
        history, buf = [], []
        t0 = time.time()
        it = 0
        while it < self.args.iters:
            for batch in self.loader:
                buf.append((batch[0], batch[1]))
                if len(buf) < self.args.conditions_per_iter:
                    continue
                rec = self.train_iteration(buf, rng)
                buf = []
                rec["iter"] = it
                rec["elapsed_s"] = time.time() - t0
                history.append(rec)
                if it % self.args.log_every == 0:
                    print(json.dumps(rec), flush=True)
                it += 1
                if it >= self.args.iters:
                    break

        os.makedirs(self.args.output_dir, exist_ok=True)
        out = os.path.join(self.args.output_dir, "history.json")
        with open(out, "w") as f:
            json.dump({"config": vars(self.args), "split_range": self.split_range,
                       "history": history}, f, indent=2)
        print(f"\nwrote {out}", flush=True)
        self.verdict(history)

    def verdict(self, history: List[Dict]):
        """Pre-registered readout - fixed before the run, not chosen after it."""
        if len(history) < 20:
            print("too few iterations for the pre-registered readout")
            return
        r = np.array([h["reward_mean"] for h in history])
        w = np.array([h["truth_frac_ge20"] for h in history])
        n = len(r)
        A = np.column_stack([np.ones(n), np.arange(n) / n, w])
        beta, *_ = np.linalg.lstsq(A, r, rcond=None)
        resid = r - A @ beta
        se = np.sqrt((resid ** 2).sum() / (n - 3) * np.linalg.inv(A.T @ A)[1, 1])
        t_stat = beta[1] / se
        mse = np.array([h["mse_mean"] for h in history])
        clip = np.array([h["clip_fraction"] for h in history])
        dev = np.array([h["ratio_max_abs_dev"] for h in history])

        print("\n=== PRE-REGISTERED READOUT (RL-train half only) ===")
        print(f"  iterations                     : {n}")
        print(f"  reward first10 / last10        : {r[:10].mean():.5f} / {r[-10:].mean():.5f}")
        print(f"  wetness-controlled trend       : slope {beta[1]:+.5f}  SE {se:.5f}  "
              f"t = {t_stat:+.2f}")
        print(f"  MSE first10 / last10           : {mse[:10].mean():.3f} / {mse[-10:].mean():.3f}")
        print(f"  clip_fraction mean / max       : {clip.mean():.5f} / {clip.max():.5f}")
        print(f"  ratio max|dev| median / max    : {np.median(dev):.3e} / {dev.max():.3e}")
        live = dev.max() > 1e-9
        print(f"\n  objective is genuinely PPO     : {'YES' if live else 'NO - still REINFORCE'}")
        if not live:
            print("  VERDICT: INVALID - ratio never left 1, the fix did not take effect")
        elif t_stat > 2.0 and mse[-10:].mean() <= mse[:10].mean():
            print("  VERDICT: GO - reward rises and MSE does not degrade; "
                  "proceed to the frozen half [1000, 2000)")
        elif t_stat > 2.0:
            print("  VERDICT: NO-GO - reward rises but MSE degrades "
                  "(off-manifold, the k200c signature)")
        else:
            print("  VERDICT: NO-GO - no learning signal on the data being "
                  "directly optimised, at the reference batch scale")

    # ------------------------------------------------------------------- main
    def run(self):
        if not self.args.stage0 and self.args.conditions_per_iter > 1:
            return self.run_batched()
        rng = np.random.default_rng(self.args.seed)
        torch.manual_seed(self.args.seed)
        history = []
        step = 0
        t_start = time.time()

        for batch in self.loader:
            if step >= self.args.steps and not self.args.stage0:
                break
            x_cond, x_true = batch[0], batch[1]
            cond0 = self.encode_cond(x_cond)
            truth = x_true.squeeze(1).to(self.device)
            if self.is_cikm:
                truth = truth[:, :, 13:-14, 13:-14]
            truth = truth.float() * (self.pixel_scale / 255.0)
            truth = truth.expand(self.args.group_size, *truth.shape[1:])

            transitions, latent_pred = self.rollout(cond0)
            parts = self.score(latent_pred, truth)
            rewards = parts["reward"].view(1, -1)

            spread = float(rewards.max() - rewards.min())
            zero_std = float((rewards.std(dim=1) <= 1e-12).float().mean())
            adv = group_advantages(rewards, mode=self.args.adv_mode).flatten()

            picks = rng.choice(len(transitions),
                               size=min(self.args.transitions_per_update, len(transitions)),
                               replace=False)
            sel = [transitions[i] for i in picks]
            logp_old = torch.cat([t.log_prob_old for t in sel], dim=0)
            logp_new = self.policy_logprobs(sel)
            adv_rep = adv.repeat(len(sel))

            loss, stats = clipped_policy_loss(
                logp_new, logp_old, adv_rep, self.args.clip_range
            )

            rec = {
                "step": step,
                "truth_mean_dbz": float(truth[0].mean()),
                "truth_frac_ge20": float((truth[0] >= 20).float().mean()),
                "truth_frac_ge35": float((truth[0] >= 35).float().mean()),
                "reward_mean": float(parts["reward"].mean()),
                "csi_m_mean": float(parts["csi_m"].mean()),
                "mse_mean": float(parts["mse"].mean()),
                "reward_within_range": spread,
                "zero_std_ratio": zero_std,
                "adv_abs_mean": float(adv.abs().mean()),
                "loss": float(loss),
                "n_transitions": len(transitions),
                **stats,
            }

            if self.args.stage0:
                ratio_dev = stats["ratio_max_abs_dev"]
                rec["stage0_ratio_is_one"] = ratio_dev < self.args.ratio_tol
                loss.backward()
                gn = torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1e9)
                rec["grad_norm"] = float(gn)
                rec["grad_finite"] = bool(torch.isfinite(gn))
                self.optimizer.zero_grad(set_to_none=True)
                print(json.dumps(rec, indent=1), flush=True)
                history.append(rec)
                if step + 1 >= self.args.stage0_batches:
                    break
            else:
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                gn = torch.nn.utils.clip_grad_norm_(self.model.parameters(),
                                                    self.args.max_grad_norm)
                rec["grad_norm"] = float(gn)
                self.optimizer.step()
                history.append(rec)
                if step % self.args.log_every == 0:
                    rec["elapsed_s"] = time.time() - t_start
                    print(json.dumps(rec), flush=True)
            step += 1

        os.makedirs(self.args.output_dir, exist_ok=True)
        out = os.path.join(self.args.output_dir,
                           "stage0.json" if self.args.stage0 else "history.json")
        with open(out, "w") as f:
            json.dump({"config": vars(self.args), "split_range": self.split_range,
                       "history": history}, f, indent=2)
        print(f"\nwrote {out}", flush=True)
        self.summarize(history)

    def summarize(self, history: List[Dict]):
        if not history:
            print("no steps recorded")
            return
        if self.args.stage0:
            ok_ratio = all(h["stage0_ratio_is_one"] for h in history)
            ok_grad = all(h["grad_finite"] for h in history)
            zs = float(np.mean([h["zero_std_ratio"] for h in history]))
            rng_ = float(np.mean([h["reward_within_range"] for h in history]))
            print("\n=== STAGE 0 ===")
            print(f"  ratio == 1 on untouched policy : {'PASS' if ok_ratio else 'FAIL'}"
                  f"  (max dev {max(h['ratio_max_abs_dev'] for h in history):.3e})")
            print(f"  gradients finite               : {'PASS' if ok_grad else 'FAIL'}")
            print(f"  mean within-group reward range : {rng_:.5f}")
            print(f"  zero_std_ratio                 : {100*zs:.2f}%")
            print(f"  grad norm (median)             : "
                  f"{np.median([h['grad_norm'] for h in history]):.4e}")
            print("\nVERDICT:", "GO" if (ok_ratio and ok_grad) else "STOP - loop is wrong")
        else:
            first = np.mean([h["reward_mean"] for h in history[:10]])
            last = np.mean([h["reward_mean"] for h in history[-10:]])
            print(f"\nreward first10={first:.5f} last10={last:.5f} delta={last-first:+.5f}")
            print(f"mean clip_fraction={np.mean([h['clip_fraction'] for h in history]):.4f}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--train-file", required=True)
    p.add_argument("--train-meta", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--stage0", action="store_true", help="self-check only, no update")
    p.add_argument("--stage0-batches", type=int, default=5)
    p.add_argument("--ratio-tol", type=float, default=1e-4)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--group-size", type=int, default=16)
    p.add_argument("--kappa", type=float, default=1.0)
    p.add_argument("--uncompensated", action="store_true", default=True)
    p.add_argument("--compensated", dest="uncompensated", action="store_false")
    p.add_argument("--transitions-per-update", type=int, default=2)
    p.add_argument("--clip-range", type=float, default=1e-3)
    p.add_argument("--adv-mode", default="global_std", choices=["global_std", "group_std"])
    p.add_argument("--lr", type=float, default=1e-6)
    p.add_argument("--max-grad-norm", type=float, default=1.0)
    p.add_argument("--w-csi", type=float, default=1.0)
    p.add_argument("--w-cont", type=float, default=0.1)
    p.add_argument("--mse-ref", type=float, default=75.0)
    p.add_argument("--precision", default="bf16", choices=["bf16", "fp16", "fp32"])
    p.add_argument("--max-conditions", type=int, default=None)
    p.add_argument("--conditions-per-iter", type=int, default=1,
                   help="Groups collected before any optimizer step. >1 enables "
                        "the batched loop where the ratio can actually leave 1.")
    p.add_argument("--num-minibatches", type=int, default=4,
                   help="Optimizer steps per collection phase.")
    p.add_argument("--num-inner-epochs", type=int, default=1)
    p.add_argument("--iters", type=int, default=200,
                   help="Collection phases (batched loop only).")
    p.add_argument("--condition-start", type=int, default=0,
                   help="First condition index (inclusive). Use with --condition-end "
                        "to keep the frozen evaluation half untouched.")
    p.add_argument("--condition-end", type=int, default=None,
                   help="Last condition index (exclusive).")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    Pilot(parse_args()).run()
