"""Calibrated few-step distillation: teacher-endpoint matching + twCRPS.

Trains a K-step student against the frozen 10-step teacher on shared
initial noises, with a threshold-weighted ensemble CRPS on the decoded
ensemble spending the student's remaining freedom on calibration and tail
fidelity.  All loss primitives live in ``common/models/flowcast/distill.py``
and are unit-tested there; this file is deliberately a thin loop over them.

Two modes, mirroring ``train_grpo_pilot.py``:

``--stage0``   Self-check on real data, no optimizer step:
               * identity arm: student initialised with the teacher's
                 weights, run at the teacher's step count on the shared
                 noises, must give a distill loss of exactly 0.0 -- on the
                 real backbone and real conditions, not the unit-test toy;
               * the K-step distill loss is strictly positive and finite;
               * **the two loss terms are back-propagated separately** and
                 each must reach the student with a finite, non-zero
                 gradient norm.  A combined backward cannot distinguish
                 "the score term is wired" from "the distill term carries
                 everything", and the score path is the novel component;
               * the score term's share of the gradient is reported, because
                 an auxiliary loss must be calibrated by **gradient-norm
                 ratio, not loss ratio** -- the UOT arm in this repository
                 sat at 31.7% of the loss while carrying 213% of the
                 gradient, and that mismatch was the whole failure;
               * the teacher's parameters are bit-identical before and
                 after a full loss computation.

``--iters N``  Training.  Logs distill/score components, ensemble-mean
               CSI/MSE on the metric view, grad norm; writes weights-only
               student snapshots every ``--snapshot-every`` iterations
               (the v4 run kept exactly one overwritten checkpoint and the
               trajectory was unrecoverable -- that mistake is not being
               repeated).

Design notes that are decisions, not defaults:

* **The score is computed on the straight-through clamped decoded field.**
  The frozen evaluator clamps to [0, pixel_scale], and so did
  ``write_validation_ensemble`` when it produced the HDF5 the offline
  reward gate was measured on -- so a training loss on the *raw* decode is
  not the reward that was gated, and would spend gradient on sub-zero
  decoder ringing that no evaluator can see.  A plain clamp would instead
  kill the gradient where a member decodes below zero while the truth has
  echo (a real miss), so the default is straight-through: evaluator value,
  live gradient.  ``--score-view {ste,clamped,raw}`` exposes all three and
  every iteration logs the clamped score alongside the training one, so
  the choice is measurable rather than argued.
* **Lead-frame subsampling** (``--reward-frames``) bounds the memory of the
  grad-enabled decode: the reward sees a random subset of lead frames each
  iteration (unbiased over iterations), the distill term always sees all
  of them in latent space.
* **The teacher is a separate frozen module**, not a flag on the student:
  sharing one module and toggling requires_grad is how a "frozen" teacher
  quietly drifts through buffer updates.
"""

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from typing import Dict, List

import numpy as np
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Subset

sys.path.append(os.getcwd())

from common.models.flowcast.distill import (
    COMPOSITE_THRESHOLDS,
    autoregressive_sample_from_noises,
    clamp_straight_through,
    draw_chunk_noises,
    endpoint_distill_loss,
    qwcrps_window,
    twcrps_composite,
)
from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper
from experiments.sevir.dataset.sevirfulldataset import (
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
)

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)
# The dBZ thresholds above, and COMPOSITE_THRESHOLDS, are the CIKM protocol.
# Running a config whose pixel scale differs (SEVIR VIL, MeteoNet) would score
# "40" on a different unit system without any error -- this repository has
# already shipped that bug once (raw_to_eval_scale keyed on dataset name), so
# the scale is asserted at startup instead of assumed.
EXPECTED_PIXEL_SCALE = 90.0

# Files whose contents define the objective.  Their digests go into every
# evidence file so a snapshot can be attributed to a code version; the working
# tree is not a git repository, so nothing else identifies it.
FINGERPRINT_FILES = (
    "common/models/flowcast/distill.py",
    "common/metrics/crps.py",
    "tools/train_distill_reward.py",
)


def state_dict_digest(module: torch.nn.Module) -> str:
    h = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def code_fingerprint() -> Dict[str, str]:
    out = {}
    for rel in FINGERPRINT_FILES:
        try:
            with open(rel, "rb") as f:
                out[rel] = hashlib.sha256(f.read()).hexdigest()[:16]
        except OSError:
            out[rel] = "unavailable"
    return out


def ensemble_mean_metrics(pred_mean: torch.Tensor, truth: torch.Tensor) -> Dict[str, float]:
    """CSI-M / MSE of the ensemble mean, per lead frame then averaged.

    Trend diagnostics only -- the paper numbers come from the frozen
    evaluation pipeline, never from a training loop.  The per-frame-then-
    average reduction mirrors that pipeline (``MetricsAccumulator`` keeps one
    accumulator per lead, computes CSI per lead, then averages).  Pooling all
    frames instead weights leads by echo area, and few-step distillation
    degrades late leads first, so the two statistics can move in opposite
    directions -- the pooled-CSI-vs-FSS sign flip in the ForeDiff arm is the
    same class of mistake.
    """
    csi_per_thr = []
    for thr in THRESHOLDS:
        p, o = pred_mean >= thr, truth >= thr
        per_frame = []
        for f in range(pred_mean.shape[0]):
            tp = float((p[f] & o[f]).sum())
            fp = float((p[f] & ~o[f]).sum())
            fn = float((~p[f] & o[f]).sum())
            per_frame.append(tp / (tp + fp + fn + 1.0))
        csi_per_thr.append(float(np.mean(per_frame)))
    return {
        "csi_m": float(np.mean(csi_per_thr)),
        "mse": float(((pred_mean - truth) ** 2).mean()),
    }


class DistillTrainer:
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
        self.teacher_steps = OmegaConf.select(c, "sampling_params.euler_steps",
                                              default=c.test_params.euler_steps)
        self.pixel_scale = OmegaConf.select(c, "evaluation_params.pixel_scale",
                                            default=255.0)
        self.is_cikm = OmegaConf.select(c, "data_params.dataset_name",
                                        default="sevir") == "cikm"
        # Composite threshold weights.  The equal-weight default is NOT
        # neutral: stage0 measured the plain term at 0.35-0.98 and the t40
        # term at 0.0099-0.111, so under equal weights the tail contributes
        # one to two orders of magnitude less to the objective than the bulk
        # -- the composite was built to remove the dead zone, and nobody
        # checked what weight the tail retained afterwards.  ``--tail-weights``
        # takes explicit per-threshold weights (normalised internally).
        if args.tail_weights is not None:
            if len(args.tail_weights) != len(COMPOSITE_THRESHOLDS):
                raise ValueError(
                    f"--tail-weights needs {len(COMPOSITE_THRESHOLDS)} values "
                    f"for thresholds {COMPOSITE_THRESHOLDS}, got "
                    f"{len(args.tail_weights)}"
                )
            self.threshold_weights = list(args.tail_weights)
        else:
            self.threshold_weights = None

        # --qw-tau0 swaps the score term's weighting AXIS (outcome -> quantile
        # level).  It is mutually exclusive with the tw knobs: an arm that
        # changed both axes at once could not attribute its result to either,
        # which is the exact confound the 2x2 protocol exists to prevent.
        if args.qw_tau0 is not None:
            if not (0.0 <= args.qw_tau0 < 1.0):
                raise ValueError(f"--qw-tau0 must be in [0, 1), got {args.qw_tau0}")
            if args.tail_weights is not None or args.chaining_softness != 0.0:
                raise ValueError(
                    "--qw-tau0 is mutually exclusive with --tail-weights/"
                    "--chaining-softness: one arm, one axis"
                )

        if args.student_steps >= self.teacher_steps:
            raise ValueError(
                f"student_steps={args.student_steps} must be < teacher "
                f"steps={self.teacher_steps}; equality is the stage0 identity "
                f"arm, not a training configuration"
            )
        if args.group_size < 2:
            raise ValueError(
                f"group_size={args.group_size} < 2: the ensemble score "
                f"degenerates to per-member MAE, which rewards collapse "
                f"(the twmae trap measured by the offline reward gate)"
            )
        if abs(float(self.pixel_scale) - EXPECTED_PIXEL_SCALE) > 1e-9:
            raise ValueError(
                f"pixel_scale={self.pixel_scale} but the composite thresholds "
                f"{COMPOSITE_THRESHOLDS} and {THRESHOLDS} are CIKM dBZ; refusing "
                f"to score one unit system with another's thresholds"
            )
        self.code_fingerprint = code_fingerprint()
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
        ap_ch = ap.latent_channels

        def build_backbone():
            return FlowCastSTDiTWrapper(
                latent_channels=ap_ch, hidden_size=hp.hidden_size,
                depth=hp.depth, num_heads=hp.num_heads, patch_size=hp.patch_size,
            )

        def load_sd(path):
            ck = torch.load(path, map_location="cpu")
            sd = ck.get("model_state_dict", ck)
            return {(k[len("module."):] if k.startswith("module.") else k): v
                    for k, v in sd.items()}

        self.teacher = build_backbone()
        missing, unexpected = self.teacher.load_state_dict(
            load_sd(self.args.checkpoint), strict=False
        )
        if len(missing) > 2:  # mean/std buffers may legitimately be absent
            raise RuntimeError(f"checkpoint mismatch: {len(missing)} missing keys")
        self.teacher = self.teacher.to(self.device).eval().requires_grad_(False)

        self.teacher_digest = state_dict_digest(self.teacher)
        if self.args.expect_teacher_digest:
            if not self.teacher_digest.startswith(self.args.expect_teacher_digest):
                raise RuntimeError(
                    f"teacher digest {self.teacher_digest[:16]} does not match "
                    f"--expect-teacher-digest {self.args.expect_teacher_digest}"
                )

        self.student = build_backbone()
        if self.args.student_init:
            # Resuming or warm-starting the student must never move the
            # anchor: the teacher stays whatever --checkpoint says.  Loading a
            # trained student through --checkpoint would silently distil
            # towards the drifted student and still pass the identity arm.
            self.student.load_state_dict(load_sd(self.args.student_init),
                                         strict=False)
            print(f"student initialised from {self.args.student_init}", flush=True)
        else:
            self.student.load_state_dict(copy.deepcopy(self.teacher.state_dict()))
        self.student = self.student.to(self.device)
        n_par = sum(p.numel() for p in self.student.parameters())
        print(f"teacher frozen, student trainable: {n_par/1e6:.1f}M params, "
              f"teacher digest {self.teacher_digest[:12]}", flush=True)

        self.optimizer = torch.optim.AdamW(
            self.student.parameters(), lr=self.args.lr, weight_decay=0.0,
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
        # The frozen evaluation half must never be trained on.  Defaulting the
        # range to "everything" would put half the optimizer steps on it and
        # the contamination would only be discoverable in history.json after
        # the GPU time was spent -- and per SPLIT_FROZEN the half could not be
        # reused afterwards.  Training therefore refuses the overlap outright.
        if not self.args.stage0 and hi > self.args.frozen_half_start:
            if not self.args.allow_frozen_half:
                raise ValueError(
                    f"condition range [{lo}, {hi}) overlaps the frozen "
                    f"evaluation half [{self.args.frozen_half_start}, {total}); "
                    f"pass --condition-end {self.args.frozen_half_start} for "
                    f"training, or --allow-frozen-half to override deliberately"
                )
            print(f"WARNING: training on the frozen half, [{lo}, {hi})", flush=True)
        if (lo, hi) != (0, total):
            # Contiguous block, never a random subset: neighbouring events
            # share weather, so a random split would leak across the boundary.
            ds = Subset(ds, range(lo, hi))
        self.split_range = (lo, hi, total)
        self.loader = DataLoader(
            ds, batch_size=1, shuffle=True, collate_fn=dynamic_sequential_collate,
            num_workers=2, pin_memory=True, drop_last=True,
        )
        print(f"dataset: {len(ds)} conditions in [{lo}, {hi})", flush=True)

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
            return self.teacher.normalize(lat)

    def score_view(self, decoded: torch.Tensor) -> torch.Tensor:
        """Apply the configured clamping convention to a decoded field."""
        if self.args.score_view == "ste":
            return clamp_straight_through(decoded, 0.0, self.pixel_scale)
        if self.args.score_view == "clamped":
            return decoded.clamp(0.0, self.pixel_scale)
        if self.args.score_view == "raw":
            return decoded
        raise ValueError(f"unknown score_view {self.args.score_view!r}")

    def decode_frames(self, latent: torch.Tensor, frame_idx: torch.Tensor,
                      with_grad: bool) -> torch.Tensor:
        """Latent ``(N, T, h, w, c)`` -> dBZ ``(N, len(frame_idx), H, W)``.

        Crop applied, clamping left to ``score_view`` / the caller.  The
        frozen AE builds a graph when ``with_grad`` -- its parameters do not
        train but the score gradient must pass through its decoder.
        """
        lat = self.teacher.denormalize(latent[:, frame_idx].float())
        n, t = lat.shape[0], lat.shape[1]
        flat = lat.reshape(n * t, *lat.shape[2:]).permute(0, 3, 1, 2).contiguous()
        outs = []
        step = self.cfg.test_params.batch_size_autoencoder
        ctx = torch.enable_grad() if with_grad else torch.no_grad()
        with ctx:
            for i in range(0, flat.shape[0], step):
                outs.append(self.ae.decode(flat[i:i + step]).sample)
        px = torch.cat(outs, dim=0).reshape(n, t, *outs[0].shape[-2:])
        px = px * self.pixel_scale if self.ae_normalized else px
        if self.is_cikm:
            px = px[:, :, 13:-14, 13:-14]
        return px

    # ------------------------------------------------------------------ loss
    def compute_losses(self, cond0: torch.Tensor, truth: torch.Tensor,
                       rng: np.random.Generator,
                       student_steps: int) -> Dict[str, torch.Tensor]:
        """One condition: G shared-noise teacher/student pairs + scored ensemble."""
        g = self.args.group_size
        cond = cond0.expand(g, *cond0.shape[1:]).contiguous().to(self.dtype)
        noises = draw_chunk_noises(cond.shape, self.num_chunks, self.device,
                                   self.dtype)

        with torch.no_grad():
            with torch.autocast("cuda", dtype=self.dtype,
                                enabled=self.dtype != torch.float32):
                teacher_pred = autoregressive_sample_from_noises(
                    model=self.teacher, initial_cond=cond,
                    input_length=self.input_length,
                    output_length=self.output_length,
                    num_train_timesteps=self.T,
                    euler_steps=self.teacher_steps, noises=noises,
                )

        with torch.autocast("cuda", dtype=self.dtype,
                            enabled=self.dtype != torch.float32):
            student_pred = autoregressive_sample_from_noises(
                model=self.student, initial_cond=cond,
                input_length=self.input_length,
                output_length=self.output_length,
                num_train_timesteps=self.T,
                euler_steps=student_steps, noises=noises,
                grad_last_k=self.args.grad_last_k,
            )

        distill = endpoint_distill_loss(student_pred.float(), teacher_pred.float())

        n_frames = min(self.args.reward_frames, self.output_length)
        frame_idx = torch.as_tensor(
            np.sort(rng.choice(self.output_length, size=n_frames, replace=False)),
            device=self.device,
        )
        decoded = self.decode_frames(student_pred, frame_idx, with_grad=True)
        obs = truth[:, frame_idx]                                   # (G, F, H, W)
        # obs rows are identical copies (expand over G); the score wants one
        # event: obs (1, F, H, W) against the member axis ens (1, G, F, H, W).
        if self.args.qw_tau0 is not None:
            # Quantile-axis arm: pure window w(a) = 1{a >= tau0}, collapsed
            # optimum at tau* = (1 + tau0)/2.  Single component on purpose --
            # diluting it with the plain slot drags tau* back toward the
            # median (0.5 mix at tau0=0.8 lands at 0.57), and tau* is the
            # dose knob this arm exists to test.
            score = qwcrps_window(
                obs[:1], self.score_view(decoded).unsqueeze(0),
                tau0=self.args.qw_tau0,
            ).mean()
            components = {f"qw{int(round(self.args.qw_tau0 * 100)):02d}": score}
        else:
            score, components = twcrps_composite(
                obs[:1], self.score_view(decoded).unsqueeze(0),
                thresholds=COMPOSITE_THRESHOLDS,
                estimator=self.args.estimator, alpha=self.args.af_alpha,
                threshold_weights=self.threshold_weights,
                chaining_softness=self.args.chaining_softness,
                return_components=True,
            )

        total = distill + self.args.reward_weight * score
        with torch.no_grad():
            # Clamp members, then average -- decode_to_metric's order.  Doing
            # it the other way round biases the diagnostic low, and this
            # repository has made GO/NO-GO calls on exactly these trend numbers.
            clamped = decoded.clamp(0.0, self.pixel_scale)
            diag = ensemble_mean_metrics(clamped.mean(dim=0), obs[0])
            # Both the training score and the evaluator-consistent one, so the
            # score-view choice is decided on logged numbers, not on argument.
            # Hard chaining, equal weights: the arm-comparable diagnostic.
            # Deliberately NOT following --chaining-softness/--tail-weights --
            # if the yardstick moved with the objective, two arms could not be
            # compared and a softness sweep would be unreadable.
            diag["score_clamped"] = float(twcrps_composite(
                obs[:1], clamped.unsqueeze(0), thresholds=COMPOSITE_THRESHOLDS,
                estimator=self.args.estimator, alpha=self.args.af_alpha,
            ))
            # Ensemble spread on the metric view: the mechanism the reward is
            # supposed to restore and the one endpoint regression may compress.
            diag["member_spread"] = float(clamped.std(dim=0).mean())
        out = {
            "total": total, "distill": distill, "score": score,
            "frame_idx": frame_idx,
        }
        out.update({f"score_{k}": v for k, v in components.items()})
        out.update({k: torch.tensor(v) for k, v in diag.items()})
        return out

    def load_truth(self, x_true: torch.Tensor) -> torch.Tensor:
        truth = x_true.squeeze(1).to(self.device)
        if self.is_cikm:
            truth = truth[:, :, 13:-14, 13:-14]
        truth = truth.float() * (self.pixel_scale / 255.0)
        return truth.expand(self.args.group_size, *truth.shape[1:])

    # ---------------------------------------------------------------- stage 0
    def stage0(self):
        rng = np.random.default_rng(self.args.seed)
        torch.manual_seed(self.args.seed)
        records = []
        for step, batch in enumerate(self.loader):
            if step >= self.args.stage0_batches:
                break
            cond0 = self.encode_cond(batch[0])
            truth = self.load_truth(batch[1])

            # (a) identity arm on the real backbone: student == teacher
            # weights at the teacher's step count -> exactly zero.
            torch.manual_seed(1000 + step)
            with torch.no_grad():
                parts_id = self.compute_losses(cond0, truth, rng,
                                               student_steps=self.teacher_steps)
            identity = float(parts_id["distill"])

            # (b, c) the training configuration proper.  The two terms are
            # back-propagated *separately*: a combined backward passes on the
            # distill gradient alone, so a severed score path (a stray
            # detach, a no_grad around the decode) would print GO while every
            # lambda arm silently trained as lambda=0.
            torch.manual_seed(1000 + step)
            parts = self.compute_losses(cond0, truth, rng,
                                        student_steps=self.args.student_steps)

            self.student.zero_grad(set_to_none=True)
            parts["distill"].backward(retain_graph=True)
            gn_distill = float(torch.nn.utils.clip_grad_norm_(
                self.student.parameters(), 1e9))

            self.student.zero_grad(set_to_none=True)
            (self.args.reward_weight * parts["score"]).backward()
            gn_score = float(torch.nn.utils.clip_grad_norm_(
                self.student.parameters(), 1e9))
            self.student.zero_grad(set_to_none=True)

            share = gn_score / max(gn_distill + gn_score, 1e-30)
            rec = {
                "step": step,
                "identity_distill": identity,
                "identity_is_zero": identity == 0.0,
                "distill": float(parts["distill"]),
                "score": float(parts["score"]),
                "score_clamped": float(parts["score_clamped"]),
                "member_spread": float(parts["member_spread"]),
                "csi_m": float(parts["csi_m"]),
                "mse": float(parts["mse"]),
                "grad_norm_distill": gn_distill,
                "grad_norm_score": gn_score,
                "score_grad_share": share,
                "grad_finite": bool(np.isfinite(gn_distill) and np.isfinite(gn_score)),
                "grad_nonzero": gn_distill > 0.0 and gn_score > 0.0,
                **{k: float(v) for k, v in parts.items()
                   if k.startswith("score_t") or k == "score_plain"},
            }
            print(json.dumps(rec, indent=1), flush=True)
            records.append(rec)

        # (d) frozen means frozen
        teacher_ok = state_dict_digest(self.teacher) == self.teacher_digest
        id_ok = all(r["identity_is_zero"] for r in records)
        pos_ok = all(r["distill"] > 0.0 for r in records)
        grad_ok = all(r["grad_finite"] and r["grad_nonzero"] for r in records)
        shares = [r["score_grad_share"] for r in records]
        share_ok = float(np.mean(shares)) >= self.args.min_score_grad_share
        ok = id_ok and pos_ok and grad_ok and teacher_ok and share_ok

        print("\n=== STAGE 0 ===")
        print(f"  identity arm exactly zero      : {'PASS' if id_ok else 'FAIL'}"
              f"  (max {max(r['identity_distill'] for r in records):.3e})")
        print(f"  K-step distill loss positive   : {'PASS' if pos_ok else 'FAIL'}")
        print(f"  both terms reach the student   : {'PASS' if grad_ok else 'FAIL'}")
        print(f"  score grad share (mean)        : {np.mean(shares):.4f}"
              f"  [floor {self.args.min_score_grad_share}] "
              f"{'PASS' if share_ok else 'FAIL - reward is inert at this lambda'}")
        print(f"    ||grad distill|| median      : "
              f"{np.median([r['grad_norm_distill'] for r in records]):.4e}")
        print(f"    ||grad lambda*score|| median : "
              f"{np.median([r['grad_norm_score'] for r in records]):.4e}")
        print(f"  teacher untouched (digest)     : {'PASS' if teacher_ok else 'FAIL'}")
        print(f"\nVERDICT: {'GO' if ok else 'STOP - wiring or dosage is wrong'}")
        if not share_ok:
            print("  (calibrate --reward-weight by gradient-norm ratio, not by "
                  "loss ratio: the UOT arm sat at 31.7% of the loss while "
                  "carrying 213% of the gradient)")
        self._write_history(records, "stage0.json")
        return ok

    # ----------------------------------------------------------------- train
    def train(self):
        rng = np.random.default_rng(self.args.seed)
        torch.manual_seed(self.args.seed)
        snap_dir = os.path.join(self.args.output_dir, "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        if os.listdir(snap_dir) and not self.args.allow_dirty_output:
            # Two optimizer trajectories under one run's provenance is not a
            # resumable experiment, it is an unattributable one.
            raise RuntimeError(
                f"{snap_dir} is not empty; a fresh run would mix trajectories. "
                f"Use a new --output-dir (or --allow-dirty-output)."
            )
        # Records land on disk as they are produced: the v4 run's trajectory was
        # lost because it existed only in one overwritten file, and an ssh drop
        # at iteration 950 would otherwise take the whole dose-response with it.
        jsonl_path = os.path.join(self.args.output_dir, "history.jsonl")
        os.makedirs(self.args.output_dir, exist_ok=True)
        jsonl = open(jsonl_path, "a", buffering=1)

        def save_snapshot(path, iteration):
            torch.save({
                "model_state_dict": self.student.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "torch_rng_state": torch.get_rng_state(),
                "cuda_rng_state_all": torch.cuda.get_rng_state_all(),
                "numpy_rng_state": rng.bit_generator.state,
                "iter": iteration,
                "args": vars(self.args),
                "teacher_digest": self.teacher_digest,
                "code_fingerprint": self.code_fingerprint,
            }, path)

        history: List[Dict] = []
        t0 = time.time()
        it = 0
        while it < self.args.iters:
            for batch in self.loader:
                if it >= self.args.iters:
                    break
                cond0 = self.encode_cond(batch[0])
                truth = self.load_truth(batch[1])
                self.optimizer.zero_grad(set_to_none=True)
                parts = self.compute_losses(cond0, truth, rng,
                                            student_steps=self.args.student_steps)
                parts["total"].backward()
                gn = torch.nn.utils.clip_grad_norm_(self.student.parameters(),
                                                    self.args.max_grad_norm)
                self.optimizer.step()

                rec = {
                    "iter": it,
                    "distill": float(parts["distill"]),
                    "score": float(parts["score"]),
                    "score_clamped": float(parts["score_clamped"]),
                    "member_spread": float(parts["member_spread"]),
                    "total": float(parts["total"].detach()),
                    "csi_m": float(parts["csi_m"]),
                    "mse": float(parts["mse"]),
                    "grad_norm": float(gn),
                    "truth_frac_ge20": float((truth[0] >= 20).float().mean()),
                    "elapsed_s": time.time() - t0,
                    **{k: float(v) for k, v in parts.items()
                       if k.startswith("score_t") or k == "score_plain"},
                }
                history.append(rec)
                jsonl.write(json.dumps(rec) + "\n")
                if it % self.args.log_every == 0:
                    print(json.dumps(rec), flush=True)
                if self.args.snapshot_every and (it + 1) % self.args.snapshot_every == 0:
                    path = os.path.join(snap_dir, f"student_iter{it + 1:06d}.pt")
                    save_snapshot(path, it + 1)
                    print(f"snapshot -> {path}", flush=True)
                it += 1

        save_snapshot(os.path.join(snap_dir, "student_final.pt"), it)
        jsonl.close()
        # "Frozen" is a claim about the whole run, not about startup: a shared
        # module or a mis-scoped optimizer would corrupt every target from the
        # iteration it appeared, while all logged quantities stayed plausible.
        teacher_ok = state_dict_digest(self.teacher) == self.teacher_digest
        print(f"teacher digest unchanged: {'PASS' if teacher_ok else 'FAIL'}",
              flush=True)
        self._write_history(history, "history.json",
                            extra={"teacher_digest_end_ok": teacher_ok})
        if history:
            n = min(20, max(1, len(history) // 2))
            print(f"\n=== trend (subsampled-frame training diagnostics, "
                  f"NOT evaluation numbers) ===")
            keys = ["distill", "score", "score_clamped", "member_spread",
                    "csi_m", "mse", "score_plain", "score_t35", "score_t40"]
            for key in keys:
                if key not in history[0]:
                    continue
                first = np.mean([h[key] for h in history[:n]])
                last = np.mean([h[key] for h in history[-n:]])
                print(f"  {key:<14} first{n}={first:.5f}  last{n}={last:.5f}  "
                      f"delta={last - first:+.5f}")

    def _write_history(self, records, name, extra=None):
        os.makedirs(self.args.output_dir, exist_ok=True)
        out = os.path.join(self.args.output_dir, name)
        payload = {"config": vars(self.args), "split_range": self.split_range,
                   "teacher_digest": self.teacher_digest,
                   "code_fingerprint": self.code_fingerprint,
                   "composite_thresholds": list(COMPOSITE_THRESHOLDS),
                       "threshold_weights": self.threshold_weights,
                       "chaining_softness": self.args.chaining_softness,
                       "qw_tau0": self.args.qw_tau0,
                   "history": records}
        if extra:
            payload.update(extra)
        with open(out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nwrote {out}", flush=True)

    def run(self):
        if self.args.stage0:
            self.stage0()
        else:
            self.train()


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", required=True,
                   help="Teacher checkpoint. The student initialises from it "
                        "unless --student-init is given; never point this at a "
                        "trained student, that silently moves the anchor.")
    p.add_argument("--student-init", default=None,
                   help="Optional separate student initialisation (warm start "
                        "or continuation). The teacher always comes from "
                        "--checkpoint.")
    p.add_argument("--expect-teacher-digest", default=None,
                   help="Fail fast unless the teacher state-dict digest starts "
                        "with this prefix.")
    p.add_argument("--train-file", required=True)
    p.add_argument("--train-meta", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--stage0", action="store_true")
    p.add_argument("--stage0-batches", type=int, default=3)
    p.add_argument("--student-steps", type=int, default=4)
    p.add_argument("--group-size", type=int, default=8,
                   help="Ensemble members per condition (shared-noise pairs).")
    p.add_argument("--grad-last-k", type=int, default=1,
                   help="Student Euler steps under autograd (DRaFT-K).")
    p.add_argument("--reward-weight", type=float, default=0.05)
    p.add_argument("--reward-frames", type=int, default=4,
                   help="Random lead frames decoded with grad for the score.")
    p.add_argument("--estimator", default="almost_fair",
                   choices=["fair", "almost_fair", "biased"])
    p.add_argument("--af-alpha", type=float, default=0.05)
    p.add_argument(
        "--chaining-softness", type=float, default=0.0,
        help="Width in dBZ of the smooth chaining transform v(z). 0 = the "
        "hard max(z,t) used by every arm so far (bitwise unchanged). The "
        "hard form has exactly zero gradient below the threshold, so it "
        "cannot ask an under-predicting model for more extreme echo; "
        "softness s gives gradient sigmoid(-d/s) at distance d below, i.e. "
        "it buys a finite correction window, not a global cure. Recorded in "
        "the run manifest.",
    )
    p.add_argument(
        "--tail-weights", type=float, nargs="+", default=None,
        help="Per-threshold weights for the composite, in the order "
        "(-inf, 20, 30, 35, 40). Default None = equal weights, which is what "
        "the first sweep used and which leaves the tail terms 1-2 orders of "
        "magnitude below the bulk. Normalised internally; recorded in the "
        "run manifest.",
    )
    p.add_argument(
        "--qw-tau0", type=float, default=None,
        help="Quantile-axis score arm: replace the tw composite with the "
        "quantile-weighted CRPS window w(a)=1{a>=tau0} (Gneiting & Ranjan "
        "2011, the un-refuted half). Collapsed-ensemble optimum moves from "
        "the conditional median to the conditional quantile (1+tau0)/2. "
        "Mutually exclusive with --tail-weights/--chaining-softness; the "
        "score_clamped diagnostic stays on the pinned tw yardstick either "
        "way. Recorded in the run manifest.",
    )
    p.add_argument("--score-view", default="ste", choices=["ste", "clamped", "raw"],
                   help="Clamping convention for the training score. 'ste' "
                        "(default) takes the evaluator's clamped value with a "
                        "straight-through gradient; 'clamped' matches the "
                        "evaluator exactly but drops gradient outside range; "
                        "'raw' scores the unclamped decode.")
    p.add_argument("--min-score-grad-share", type=float, default=0.01,
                   help="Stage0 floor on ||grad(lambda*score)|| / (||grad "
                        "distill|| + ||grad score||). Below it the reward has "
                        "no gradient authority and any lambda conclusion is "
                        "about a term that never moved anything.")
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--max-grad-norm", type=float, default=1.0)
    # fp16 is deliberately absent: this loop has no GradScaler, so fp16
    # backward would underflow small distill gradients to zero (flat curves
    # that look like "no effect") or overflow to NaN after an optimizer step.
    p.add_argument("--precision", default="bf16", choices=["bf16", "fp32"])
    p.add_argument("--iters", type=int, default=1000)
    p.add_argument("--snapshot-every", type=int, default=200)
    p.add_argument("--condition-start", type=int, default=0)
    p.add_argument("--condition-end", type=int, default=None)
    p.add_argument("--frozen-half-start", type=int, default=1000,
                   help="First condition index of the frozen evaluation half; "
                        "training refuses to touch it (see SPLIT_FROZEN.md).")
    p.add_argument("--allow-frozen-half", action="store_true",
                   help="Deliberately train on the frozen half. This burns it.")
    p.add_argument("--allow-dirty-output", action="store_true",
                   help="Permit a non-empty snapshot dir (mixes trajectories).")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


if __name__ == "__main__":
    DistillTrainer(parse_args()).run()
