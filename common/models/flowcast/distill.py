"""Teacher-endpoint distillation with a tail-weighted ensemble score.

The training objective this module supports is

    L = ||student_K(eps, cond) - teacher_N(eps, cond)||^2
        + reward_weight * twCRPS_composite(obs, decode(student ensemble))

i.e. match the frozen teacher's deterministic Euler endpoint on a *shared*
initial noise, while a threshold-weighted ensemble score pulls the few-step
ensemble towards calibration and tail fidelity.  The division of labour is
deliberate and is the measured lesson of this repository, not taste:

* the score term alone moves the model off-manifold -- three independent
  dose-response probes showed a score improving while MSE/CSI degraded
  (k200c arm, band-gate arms, the Flow-GRPO lr sweep);
* the distillation term alone inherits the teacher's under-dispersion and
  tail deficit -- and few-step students are known to *lose* diversity on
  top of that (reverse-KL mode seeking; Data-Forcing / Distilling
  Diversity measured it in image/video domains);
* together, the endpoint term anchors the student to the teacher's
  manifold while the ensemble score spends the remaining freedom on
  spread and exceedances.  This is the RMMD / DMDR mechanism
  ("distillation loss as regularizer against reward hacking"), rebuilt
  here for a deterministic-ODE rectified-flow teacher.

Why endpoint matching and not distribution matching (DMD-style): the
teacher's sampler is a deterministic ODE per (eps, cond), so conditioned on
the shared noise the target is a *point*, no fake-score network is needed,
and the identity arm is exact -- a student with the teacher's weights and
the teacher's step grid reproduces the target bitwise, so the loss is
exactly zero.  Every arm of the training run therefore has a bit-level
no-op control, which is the house rule that caught the last three wiring
bugs in this repository.

Gradient truncation (``grad_last_k``) follows DRaFT-K: only the last ``k``
Euler steps of the student run under autograd; the prefix runs under
``no_grad`` and is detached.  Values are bitwise identical for every ``k``
(pinned by tests) -- ``k`` only chooses how much of the sampling chain the
gradient sees, trading memory for gradient completeness.

Score-term estimator: default ``almost_fair`` (Lang et al., AIFS-CRPS)
rather than exactly-fair.  The exactly-fair score is what the offline
reward gate measured (and the ``fair`` path here is parity-tested against
that gate's numpy reference), but as a *training* objective the exactly
fair score admits a degenerate optimum that afCRPS removes; alpha=0.05
follows the AIFS-CRPS precedent.  The composite runs over
``(-inf, 20, 30, 35, 40)`` dBZ because the offline gate measured a 3.8%
zero-gradient dead zone for a single t=40 score and 0.00% for this
composite -- a single high threshold is not a usable objective on this
model, however appealing "just optimise the tail" sounds.
"""

import contextlib
from typing import List, Optional, Sequence

import torch

from common.metrics.crps import crps_ensemble
from .schedule import build_sampling_timesteps, make_chunk_index

__all__ = [
    "COMPOSITE_THRESHOLDS",
    "autoregressive_sample_from_noises",
    "clamp_straight_through",
    "draw_chunk_noises",
    "endpoint_distill_loss",
    "qwcrps_window",
    "sample_chunk_euler_from_noise",
    "soft_chain",
    "twcrps_composite",
]

# -inf reproduces plain CRPS; the rest are the evaluator's reporting
# thresholds.  Keep in sync with tools/reward_dispersion_gate.TW_THRESHOLDS --
# the parity test imports both and fails if they drift apart.
COMPOSITE_THRESHOLDS = (float("-inf"), 20.0, 30.0, 35.0, 40.0)


def sample_chunk_euler_from_noise(
    model,
    cond: torch.Tensor,
    chunk_idx: int,
    num_train_timesteps: int,
    euler_steps: int,
    noise: torch.Tensor,
    grad_last_k: Optional[int] = None,
) -> torch.Tensor:
    """Deterministic Euler for one chunk, starting from a *provided* noise.

    Bitwise identical to ``sample_chunk_euler(..., sde_noise_scale=None)``
    fed the same initial draw (pinned by tests).  Taking the noise as an
    argument instead of a generator is what makes teacher/student pairing
    possible: both integrate from the *same* eps, so the endpoint loss
    compares two solvers of the same ODE instance rather than two samples.

    ``grad_last_k``: number of final Euler steps that run under autograd.
    ``None`` means all of them.  ``0`` produces a fully detached sample.
    The no-grad prefix is detached step by step so at most ``k`` autograd
    graphs of the backbone are alive at once.
    """
    if noise.shape != cond.shape:
        raise ValueError(
            f"noise shape {tuple(noise.shape)} != cond shape {tuple(cond.shape)}"
        )
    batch_size = cond.shape[0]
    device = cond.device
    dtype = cond.dtype
    timesteps = build_sampling_timesteps(num_train_timesteps, euler_steps, device)
    chunk_index = make_chunk_index(batch_size, chunk_idx, device)

    n_steps = timesteps.numel() - 1
    k = n_steps if grad_last_k is None else int(grad_last_k)
    if k < 0:
        raise ValueError(f"grad_last_k must be non-negative, got {k}")
    k = min(k, n_steps)

    z = noise
    for i, (current_t, next_t) in enumerate(zip(timesteps[:-1], timesteps[1:])):
        with_grad = i >= n_steps - k
        ctx = contextlib.nullcontext() if with_grad else torch.no_grad()
        with ctx:
            t = torch.full(
                (batch_size,),
                int(current_t.item()),
                device=device,
                dtype=torch.long,
            )
            velocity = model(z, t, cond, chunk_index)
            # Same expression, same order as sample_chunk_euler: bit parity
            # is a test invariant, so do not "simplify" this line.
            delta_t = (current_t - next_t).to(dtype=dtype) / float(
                num_train_timesteps - 1
            )
            z_new = z + velocity * delta_t
        z = z_new if with_grad else z_new.detach()
    return z


def draw_chunk_noises(
    shape: Sequence[int],
    num_chunks: int,
    device,
    dtype,
    generator: Optional[torch.Generator] = None,
) -> List[torch.Tensor]:
    """Pre-draw the per-chunk initial noises in the deployed sampler's order.

    ``autoregressive_sample`` draws one ``randn`` per chunk, sequentially,
    as its only generator use (kappa=0).  Drawing the same tensors here from
    a generator in the same state therefore reproduces the deployed RNG
    stream exactly, which is what lets a stored baseline be re-created and
    compared bitwise (pinned by tests).
    """
    return [
        torch.randn(tuple(shape), device=device, dtype=dtype, generator=generator)
        for _ in range(num_chunks)
    ]


def autoregressive_sample_from_noises(
    model,
    initial_cond: torch.Tensor,
    input_length: int,
    output_length: int,
    num_train_timesteps: int,
    euler_steps: int,
    noises: Sequence[torch.Tensor],
    grad_last_k: Optional[int] = None,
) -> torch.Tensor:
    """Chunked autoregressive rollout from explicit per-chunk noises.

    Chunk ``c+1`` is conditioned on this model's own chunk ``c`` output --
    the deployment wiring.  For the student that matters: the distillation
    target for chunk 2 is the teacher's chunk 2 *given the teacher's chunk
    1*, while the student's chunk 2 is given its own chunk 1, so the loss
    sees the autoregressive drift instead of hiding it behind teacher
    forcing (the ForeDiff arm died on exactly that mismatch).
    """
    if output_length % input_length != 0:
        raise ValueError("output_length must be divisible by input_length.")
    num_chunks = output_length // input_length
    if len(noises) != num_chunks:
        raise ValueError(f"expected {num_chunks} noises, got {len(noises)}")

    cond = initial_cond
    predictions = []
    for chunk_idx in range(1, num_chunks + 1):
        pred_chunk = sample_chunk_euler_from_noise(
            model=model,
            cond=cond,
            chunk_idx=chunk_idx,
            num_train_timesteps=num_train_timesteps,
            euler_steps=euler_steps,
            noise=noises[chunk_idx - 1],
            grad_last_k=grad_last_k,
        )
        predictions.append(pred_chunk)
        cond = pred_chunk
    return torch.cat(predictions, dim=1)


def endpoint_distill_loss(
    student_pred: torch.Tensor, teacher_pred: torch.Tensor
) -> torch.Tensor:
    """Mean squared endpoint mismatch on the shared-noise ODE pair.

    The teacher endpoint is a constant of the optimisation; detach rather
    than trust the caller to have run it under ``no_grad``.
    """
    if student_pred.shape != teacher_pred.shape:
        raise ValueError(
            f"shape mismatch: student {tuple(student_pred.shape)} vs "
            f"teacher {tuple(teacher_pred.shape)}"
        )
    return ((student_pred - teacher_pred.detach()) ** 2).mean()


def clamp_straight_through(x: torch.Tensor, lo: float, hi: float) -> torch.Tensor:
    """``clamp(x, lo, hi)`` in value, identity in gradient.

    The evaluation pipeline (and ``write_validation_ensemble``, which produced
    the HDF5 the offline reward gate was measured on) clamps decoded fields to
    ``[0, pixel_scale]`` *before* scoring.  A training loss must therefore see
    the clamped value or it is not optimising the score that was gated:
    sub-zero decoder ringing in dry areas would otherwise contribute a large,
    near-constant-sign penalty that no evaluator can see, and pull against the
    distillation anchor (the teacher decodes to the same background).

    A plain ``clamp`` fixes the value but kills the gradient exactly where a
    member decodes below zero while the truth has echo -- a genuine miss with
    no learning signal.  The straight-through form keeps the evaluator's value
    and still lets that miss push the member back into range.  Both properties
    are asserted in the tests.
    """
    return x + (x.clamp(lo, hi) - x).detach()


def soft_chain(z: torch.Tensor, threshold: float, softness: float) -> torch.Tensor:
    """Smooth chaining transform ``v(z)``, replacing ``max(z, t)``.

    ``v_s(z) = t + s * softplus((z - t) / s)`` for softness ``s > 0``, and
    exactly ``max(z, t)`` at ``s = 0``.  As ``s -> 0`` the smooth form
    converges to the hard one uniformly (the gap is bounded by
    ``s * log 2``), so the hard score is recovered in the limit rather than
    approximated by something else.

    Why this exists -- the measured failure, not a smoothness preference.
    The hard transform has **exactly zero gradient at every pixel below the
    threshold**: ``max(35, 40)`` and ``max(20, 40)`` are both 40, so a member
    that under-predicts heavy echo receives no signal telling it to increase.
    Measured on this model, the deployed teacher produces only 45% of the
    observed >=40 dBZ area on CIKM test, i.e. the region where correction is
    most needed is precisely the region the score cannot see.  Re-weighting
    the tail terms was tried first and made every metric slightly worse
    (tiltA/tiltB arms) -- moving gradient onto a term that has none is not a
    dose problem, it is a geometry problem.

    Propriety, stated precisely (Allen, Ginsbourger & Ziegel, SIAM/ASA JUQ
    11(3):906-940, 2023, Prop. 3): CRPS composed with *any* measurable
    chaining function is proper; **injectivity is necessary and sufficient
    for strict propriety**.  Monotonicity is therefore not what buys
    propriety -- propriety was never at risk -- it buys injectivity, hence
    strictness.  This matters here because the hard transform is *not*
    injective below the threshold, and the resulting score is proper but not
    strictly proper: it is, in Wessel et al.'s words (arXiv:2506.13687),
    "insensitive to how the forecast distributions behave below the
    threshold".  That paper's remedy is to add plain CRPS to the composite --
    which this objective already does, and which is measured here **not** to
    fix the extreme deficit.  Strict propriety and gradient reach are
    different properties: a strictly proper score can still be numerically
    flat where correction is needed.

    Prior art, explicitly: the smooth relaxation is NOT new.  Hakvoort,
    Francois, Whan & Dirksen (arXiv:2503.07374) already train CNNs for
    extreme wind with a shifted Gaussian-CDF weight ``w(z) = c + Phi(z)``,
    whose chaining function converges to ``max(z, mu)`` as ``sigma -> 0``.
    ``v_s`` here is the logistic sibling of that construction (its derivative
    is ``sigmoid((z - t) / s)``, so ``s`` plays the role of ``sigma``), and it
    is used here as a known tool aimed at a newly measured problem, not as a
    contribution in itself.  Their stated motivation is flexible bulk/tail
    weighting, not gradient geometry.  ``s`` is in dBZ.

    ``threshold = -inf`` is the identity for any softness (plain CRPS).
    """
    if softness < 0.0:
        raise ValueError(f"softness must be non-negative, got {softness}")
    if threshold == float("-inf"):
        return z
    if softness == 0.0:
        return z.clamp_min(threshold)
    # softplus in fp32: the (z - t) / s ratio overflows fast in fp16 for the
    # small softness values that make this transform useful.
    scaled = (z.float() - threshold) / softness
    return (threshold + softness * torch.nn.functional.softplus(scaled)).to(z.dtype)


def twcrps_composite(
    obs: torch.Tensor,
    ens: torch.Tensor,
    thresholds: Sequence[float] = COMPOSITE_THRESHOLDS,
    estimator: str = "almost_fair",
    alpha: float = 0.05,
    threshold_weights: Optional[Sequence[float]] = None,
    chaining_softness: float = 0.0,
    return_components: bool = False,
):
    """Composite threshold-weighted ensemble CRPS, scalar, to be minimised.

    ``obs``: ``(B, *spatial)``; ``ens``: ``(B, M, *spatial)``.  Returns the
    mean over thresholds of the per-pixel (tw)CRPS mean.  ``estimator``
    passes through to ``crps_ensemble``; the ``fair`` path with uniform
    weights is algebraically the offline gate's reward (its group mean is
    ``-fairCRPS``), which the parity test checks against the numpy
    reference rather than asserting.

    The chaining transform is ``soft_chain``: ``max(z, t)`` at the default
    ``chaining_softness=0`` (bitwise the previous behaviour, so every stored
    number stays reproducible), and a smooth strictly-increasing relaxation
    of width ``chaining_softness`` dBZ otherwise.  The hard form has exactly
    zero gradient below the threshold, which is why re-weighting the tail
    terms could not improve extremes; see ``soft_chain``.

    ``return_components`` additionally returns the weighted per-threshold
    pieces.  Under uniform weights the t=35/40 terms are one to two orders
    of magnitude smaller than the plain term, so a falling total says
    nothing about tail behaviour on its own -- the paper's tail claim is
    unfalsifiable from the aggregate and the components must be logged.
    """
    if len(thresholds) == 0:
        raise ValueError("thresholds must be non-empty")
    if ens.dim() < 2 or ens.shape[1] < 2:
        # M == 1 makes crps_ensemble degenerate to per-member MAE, which is
        # minimised by a point mass at the median -- the twmae collapse trap
        # the offline gate measured and rejected.  Refuse rather than
        # silently optimise the inverse of the intended objective.
        raise ValueError(
            "twcrps_composite needs at least 2 ensemble members; M=1 "
            "degenerates to MAE, which rewards ensemble collapse (twmae trap)"
        )
    if threshold_weights is None:
        w = [1.0 / len(thresholds)] * len(thresholds)
    else:
        if len(threshold_weights) != len(thresholds):
            raise ValueError(
                f"{len(threshold_weights)} weights for {len(thresholds)} thresholds"
            )
        total = float(sum(threshold_weights))
        if total <= 0:
            raise ValueError("threshold_weights must have positive sum")
        w = [float(x) / total for x in threshold_weights]

    pieces = []
    labels = []
    for weight, thr in zip(w, thresholds):
        thr = float(thr)
        score = crps_ensemble(
            soft_chain(obs, thr, chaining_softness),
            soft_chain(ens, thr, chaining_softness),
            estimator=estimator,
            alpha=alpha,
        )
        pieces.append(weight * score.mean())
        labels.append("plain" if thr == float("-inf") else f"t{int(thr)}")
    total = torch.stack(pieces).sum()
    if return_components:
        return total, dict(zip(labels, pieces))
    return total


def qwcrps_window(
    obs: torch.Tensor,
    ens: torch.Tensor,
    tau0: float = 0.0,
    batch_chunk: int = 8,
) -> torch.Tensor:
    """Quantile-weighted CRPS with window weight ``w(a) = 1{a >= tau0}``.

    Per-pixel map, same shapes as ``crps_ensemble``: ``obs (B, *spatial)``,
    ``ens (B, M, *spatial)``.  Exact score of the empirical M-member measure:

        qwCRPS = 2 * sum_i (x_(i) - y) * (1{y <= x_(i)} * W_i - V_i)

    with ``W_i = |I_i ^ [tau0, 1]|`` and ``V_i = int_{I_i ^ [tau0,1]} a da``
    over the rank interval ``I_i = ((i-1)/M, i/M]`` of the sorted members.
    ``tau0 = 0`` recovers the plain empirical CRPS (== ``crps_ensemble`` with
    ``estimator="biased"``; pinned by test).

    Why this exists -- the other half of Gneiting & Ranjan (2011).  Every
    refuted arm in this repository weighted the *outcome* axis (twCRPS
    chaining), and for a collapsed ensemble any such weighting keeps the
    optimum at the conditional median: the first-order condition is
    w(a)(2F(a)-1) = 0 for every w.  Weighting the *quantile-level* axis
    changes the two slopes of the collapsed loss instead of where it is
    measured: a point forecast x pays ``2*V*(y-x)+`` for under-prediction and
    ``2*(W-V)*(x-y)+`` for over-prediction, so the collapsed optimum is the
    conditional quantile ``tau* = V/W = (1 + tau0)/2`` -- q90 at tau0 = 0.8
    -- rather than the median.  The score stays proper (a mixture of proper
    quantile scores), so the tilt binds only while the ensemble is
    degenerate and releases as real spread appears.

    Estimator caveat, stated rather than hidden: this is the exact score of
    the empirical measure (the "biased"/NRG flavour).  A fair
    (finite-M-debiased) analogue of the *windowed* score needs an
    order-statistics derivation that does not reduce to the pairwise-spread
    correction of ``crps_ensemble``; it is deliberately out of scope for the
    dose arms, whose members are near-collapsed (the fair-vs-biased gap is
    O(within-window spread), measured orders of magnitude below the tilt
    signal there).  Do not compare absolute values across estimator families.

    Ranks come from ``torch.sort``, so the gradient of member ``j`` is
    ``2 * (1{y <= x_j} * W_r(j) - V_r(j))`` with ``r(j)`` its rank --
    asymmetric by construction: at tau0 = 0.8 an under-predicting collapsed
    ensemble is pushed up 9x harder than an over-predicting one is pushed
    down (``V/(W-V) = 9``; pinned by test).

    ``M == 1`` is refused for the same reason as ``twcrps_composite``: a
    single member turns any ensemble score into a per-member point loss and
    silently rewards collapse (the twmae trap).
    """
    if ens.dim() != obs.dim() + 1:
        raise ValueError(
            f"ens must have one extra member dim: obs {obs.shape}, ens {ens.shape}"
        )
    if not (0.0 <= tau0 < 1.0):
        raise ValueError(f"tau0 must be in [0, 1), got {tau0}")
    if ens.shape[1] < 2:
        raise ValueError(
            "qwcrps_window needs at least 2 ensemble members; M=1 degenerates "
            "to a per-member point loss, which rewards ensemble collapse "
            "(twmae trap)"
        )
    batch, members = ens.shape[0], ens.shape[1]
    # bf16/fp16 lose the tail signal in the (vals - obs) * coef products; the
    # coefficients themselves are exact rationals of M and tau0.
    work_dtype = ens.dtype
    if work_dtype in (torch.float16, torch.bfloat16):
        work_dtype = torch.float32

    idx = torch.arange(1, members + 1, dtype=torch.float64)
    lo = (idx - 1.0) / members
    hi = idx / members
    a = lo.clamp_min(tau0)
    alive = hi > a
    w_i = torch.where(alive, hi - a, torch.zeros_like(hi))
    v_i = torch.where(alive, (hi * hi - a * a) / 2.0, torch.zeros_like(hi))
    spatial_ones = [1] * (ens.dim() - 2)
    w_i = w_i.to(device=ens.device, dtype=work_dtype).reshape(1, members, *spatial_ones)
    v_i = v_i.to(device=ens.device, dtype=work_dtype).reshape(1, members, *spatial_ones)

    out = torch.empty(obs.shape, device=obs.device, dtype=work_dtype)
    for start in range(0, batch, max(batch_chunk, 1)):
        sl = slice(start, min(start + max(batch_chunk, 1), batch))
        vals, _ = torch.sort(ens[sl].to(work_dtype), dim=1)
        o = obs[sl].to(work_dtype).unsqueeze(1)
        c = (o <= vals).to(work_dtype)
        out[sl] = 2.0 * ((vals - o) * (c * w_i - v_i)).sum(dim=1)
    return out
