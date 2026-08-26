"""Field-wise unbalanced optimal transport on regular 2D grids.

Implements the entropic unbalanced OT problem with KL marginal relaxation
(Sejourne et al., "Sinkhorn divergences for unbalanced optimal transport"):

    UOT(a, b) = min_pi <C, pi> + eps * KL(pi | a x b)
                + rho * KL(pi_1 | a) + rho * KL(pi_2 | b)

between two non-negative mass fields ``a`` and ``b`` living on the same
H x W grid with squared Euclidean ground cost. The marginal relaxation is
what allows precipitation mass to be created (convective growth) or
destroyed (dissipation) at a price controlled by ``reach`` instead of
being teleported across the domain, which is why the *unbalanced* problem
is the physically correct one for radar fields.

Key properties used by the rest of the code base:

- the Gibbs kernel of a squared Euclidean cost on a regular grid is a
  separable Gaussian, so one Sinkhorn iteration costs O(N * sqrt(N))
  via two axis-wise log-matmuls instead of O(N^2);
- Sinkhorn iterations run under ``torch.no_grad()`` and the final value
  is evaluated from the (detached) converged dual potentials, so
  gradients w.r.t. the mass fields follow the envelope theorem exactly
  as in geomloss;
- the debiased divergence  S = UOT(a,b) - UOT(a,a)/2 - UOT(b,b)/2
  + eps/2 * (m(a) - m(b))^2  is >= 0 and == 0 iff a == b, which makes it
  usable as a training loss.

A dense O(N^2) reference implementation (``dense_uot_reference``) is kept
in this module so unit tests can validate the separable fast path.
"""

import math
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from common.losses.motion_cost import (
    MotionCostConfig,
    flow_to_metric,
    metric_cost_matrix,
)

_LOG_TINY = -1e30


def sum_pool2d(x: torch.Tensor, factor: int) -> torch.Tensor:
    """Mass-conserving downsampling of (..., H, W) fields."""
    if factor <= 1:
        return x
    lead = x.shape[:-2]
    h, w = x.shape[-2:]
    if h % factor != 0 or w % factor != 0:
        raise ValueError(f"Grid ({h},{w}) not divisible by pool factor {factor}.")
    flat = x.reshape(-1, 1, h, w)
    pooled = F.avg_pool2d(flat, kernel_size=factor, stride=factor)
    pooled = pooled * float(factor * factor)
    return pooled.reshape(*lead, h // factor, w // factor)


def dbz_to_rainrate(dbz: torch.Tensor, zr_a: float = 200.0, zr_b: float = 1.6) -> torch.Tensor:
    """Marshall-Palmer Z-R conversion. dBZ is logarithmic and has no additive
    mass meaning; rain rate (mm/h) does."""
    z_lin = torch.pow(10.0, dbz / 10.0)
    return torch.pow(z_lin.clamp_min(0.0) / zr_a, 1.0 / zr_b)


def mass_from_field(
    field: torch.Tensor,
    transform: str = "vil",
    low_threshold: float = 0.0,
    gamma: float = 1.0,
    mass_scale: float = 1.0,
    zr_a: float = 200.0,
    zr_b: float = 1.6,
    threshold_mode: str = "hard",
    threshold_softness: float = 4.0,
    zero_point: Optional[float] = None,
) -> torch.Tensor:
    """Map a physical field (eval units) to a non-negative transport mass.

    transform:
      - "vil" / "identity": the field is already an additive quantity
        (e.g. SEVIR VIL); low-echo noise below ``low_threshold`` is removed.
      - "zr_dbz": the field is radar reflectivity in dBZ; converted to
        linear rain rate through Marshall-Palmer before thresholding.
    threshold_mode:
      - "hard": relu(m - thr). Exact threshold-excess mass, but the
        gradient is exactly zero wherever the prediction sits below the
        threshold - a missed extreme core receives NO transport gradient.
        Use for *metrics*.
      - "soft": softplus((m - thr)/beta) * beta with beta =
        ``threshold_softness``. Slightly non-zero below the threshold and
        differentiable everywhere, so the loss can pull missed cores up
        through the threshold. Use for *training*.
    gamma: convex intensity weighting m = m ** gamma (gamma > 1 makes
      misplaced *intense* cores dominate the loss).
    mass_scale: fixed global scale divisor for numerical conditioning.
      Must be a constant across the dataset - never normalize per sample,
      that would erase exactly the mass difference UOT is meant to price.
    zero_point: the RAW FIELD value that means "no echo" (e.g. 0.0 dBZ).
      With the plain soft threshold every no-echo pixel still carries a
      small positive mass (softplus never reaches zero); over a padded
      128x128 CIKM frame that adds ~800 units of fake background mass -
      several times a real storm's mass - which both drowns the transport
      geometry and inflates any mass normalization. When zero_point is
      given, the soft mass is anchored so that field == zero_point maps to
      EXACTLY zero mass (the softplus value at the zero point is
      subtracted and the result clamped at 0), while sub-threshold pixels
      above the zero point keep a smooth gradient.

    NOTE on semantics: with low_threshold > 0 the transported quantity is
    *threshold-excess* mass, not total physical rain mass; growth/decay
    read off the marginal relaxation are therefore "risk-weighted excess
    mass changes", not literal rain budgets.
    """
    if transform in ("vil", "identity"):
        mass = field
    elif transform == "zr_dbz":
        mass = dbz_to_rainrate(field, zr_a=zr_a, zr_b=zr_b)
    else:
        raise ValueError(f"Unknown mass transform: {transform}")
    if threshold_mode == "hard":
        mass = torch.relu(mass - low_threshold)
    elif threshold_mode == "soft":
        beta = max(threshold_softness, 1e-6)
        mass = F.softplus((mass - low_threshold) / beta) * beta
        if zero_point is not None:
            if transform == "zr_dbz":
                zp_intensity = float(
                    (10.0 ** (float(zero_point) / 10.0) / zr_a) ** (1.0 / zr_b)
                )
            else:
                zp_intensity = float(zero_point)
            floor = math.log1p(math.exp((zp_intensity - low_threshold) / beta)) * beta
            mass = (mass - floor).clamp_min(0.0)
    else:
        raise ValueError(f"Unknown threshold_mode: {threshold_mode}")
    if gamma != 1.0:
        mass = torch.pow(mass, gamma)
    if mass_scale != 1.0:
        mass = mass / mass_scale
    return mass


@dataclass
class GridUOTConfig:
    """Configuration for the grid UOT divergence.

    blur:  entropic length scale in *original pixel* units; eps = blur ** 2.
    reach: marginal-relaxation length scale in pixel units; rho = reach ** 2.
           Mass whose cheapest matching displacement is much larger than
           ``reach`` is created/destroyed instead of transported.
    downsample: mass-conserving sum-pool factor applied before Sinkhorn;
           grid spacing is scaled accordingly so blur/reach keep their
           physical meaning in original-pixel units.
    """

    blur: float = 3.0
    reach: float = 16.0
    downsample: int = 4
    n_iters: int = 100
    debiased: bool = True
    self_iters: int = 50
    # early stopping: iterations halt once max potential update falls
    # below tol * eps (checked every check_every iterations)
    tol: float = 1e-4
    check_every: int = 10
    # memory bound (elements) for the chunked exact logsumexp
    lse_chunk_elements: int = 16_000_000
    # flow-aligned ground cost; None or alpha=0 keeps the separable Euclidean
    # path untouched (the identity arm is the old code, not a dense re-derivation)
    motion: Optional["MotionCostConfig"] = None


class GridUnbalancedSinkhorn(nn.Module):
    """Batched debiased unbalanced Sinkhorn divergence between (B, H, W)
    non-negative mass fields, log-domain, separable kernel."""

    def __init__(self, config: GridUOTConfig):
        super().__init__()
        self.config = config
        self._kernel_cache = {}

    # ------------------------------------------------------------------ #
    # kernel machinery
    # ------------------------------------------------------------------ #
    def _axis_log_kernels(self, h, w, spacing, device):
        key = (h, w, float(spacing), device)
        cached = self._kernel_cache.get(key)
        if cached is not None:
            return cached
        eps = self.config.blur ** 2
        coords_h = torch.arange(h, device=device, dtype=torch.float32) * spacing
        coords_w = torch.arange(w, device=device, dtype=torch.float32) * spacing
        log_kh = -((coords_h[:, None] - coords_h[None, :]) ** 2) / eps
        log_kw = -((coords_w[:, None] - coords_w[None, :]) ** 2) / eps
        self._kernel_cache[key] = (log_kh, log_kw)
        return log_kh, log_kw

    def _motion_log_kernel(self, flow, h, w, spacing, device):
        """``(B, N, N)`` log Gibbs kernel ``-C/eps`` for the flow-aligned cost.

        Not cached: the metric depends on the sample's own motion field.

        The flow arrives on the *original* grid while Sinkhorn runs on the
        sum-pooled one, so it is average-pooled to match.  Averaging, not
        summing: this is a velocity, and the coordinate grid is already scaled
        by ``spacing`` to keep everything in original-pixel units, so the
        vectors must not be rescaled with the pooling factor.
        """
        flow = flow.to(device)
        if flow.dim() == 4 and flow.shape[-2:] != (h, w):
            flow = F.adaptive_avg_pool2d(flow, (h, w))
        metric = flow_to_metric(flow, self.config.blur, self.config.motion)
        cost = metric_cost_matrix(metric, h, w, spacing, dtype=torch.float32)
        return -cost / (self.config.blur ** 2)

    def _lse_mm(self, log_f: torch.Tensor, log_k: torch.Tensor) -> torch.Tensor:
        """EXACT logsumexp along the last axis, chunked over the output axis.

        log_f: (..., N) log-domain values; log_k: (M, N) with entries <= 0.
        Returns (..., M):  out[..., m] = LSE_n( log_f[..., n] + log_k[m, n] ).

        Deliberately NOT the exp-then-matmul trick: exponentiating log_k in
        float32 underflows to exactly zero beyond ~13 blur lengths, which
        silently converts far-displaced sparse mass into creation/destruction
        (measured 40-56% underestimation on delta pairs at 32 px shift).
        torch.logsumexp performs the max-shift jointly over (log_f + log_k),
        so no distance can underflow. Memory is bounded by chunking over M.
        """
        m_total, n_total = log_k.shape
        lead_elems = int(log_f.numel() // max(n_total, 1))
        chunk = max(1, min(m_total, self.config.lse_chunk_elements // max(lead_elems * n_total, 1)))
        outs = []
        for start in range(0, m_total, chunk):
            block = log_k[start : start + chunk]  # (m, N)
            outs.append(torch.logsumexp(log_f.unsqueeze(-2) + block, dim=-1))
        return torch.cat(outs, dim=-1)

    def _kernel_lse2d(self, log_field, log_kh, log_kw):
        """out[b,i1,i2] = LSE_{j1,j2}( log_field[b,j1,j2]
        + log_kh[i1,j1] + log_kw[i2,j2] )."""
        out = self._lse_mm(log_field, log_kw)          # over W: (B, H, W')
        out = out.transpose(-1, -2)                    # (B, W', H)
        out = self._lse_mm(out, log_kh)                # over H: (B, W', H')
        return out.transpose(-1, -2)                   # (B, H', W')

    # ------------------------------------------------------------------ #
    # solver
    # ------------------------------------------------------------------ #
    def _kernel_lse_dense(self, log_field, log_k):
        """Dense counterpart of ``_kernel_lse2d`` for a non-separable cost.

        log_field: ``(B, H, W)``; log_k: ``(B, N, N)`` with ``N = H*W``, entries
        ``-C_ij / eps``.  Returns ``(B, H, W)``.

        Used only when a flow-aligned ground cost is active.  The Euclidean cost
        keeps the separable path untouched, so the ``alpha = 0`` arm is the old
        code rather than a dense path that merely agrees with it.
        """
        b, h, w = log_field.shape
        flat = log_field.reshape(b, 1, h * w)                    # (B,1,N) over j
        out = torch.logsumexp(flat + log_k, dim=-1)              # (B,N) over i
        return out.reshape(b, h, w)

    def _solve_potentials(self, log_a, log_b, lse, n_iters):
        """Unbalanced Sinkhorn fixed point in log domain.

        f <- -lam * eps * LSE_j( log b_j + (g_j - C_ij)/eps ),
        lam = rho / (rho + eps); symmetric for g.
        Potentials returned *divided by eps* would lose precision, so we
        keep f, g themselves (same units as the cost).

        ``lse`` applies the Gibbs kernel; it is the only thing that differs
        between the separable and the dense ground cost.
        """
        eps = self.config.blur ** 2
        rho = self.config.reach ** 2
        lam = rho / (rho + eps)
        tol = self.config.tol * eps
        f = torch.zeros_like(log_a)
        g = torch.zeros_like(log_b)
        for it in range(n_iters):
            f_new = -lam * eps * lse(log_b + g / eps)
            g = -lam * eps * lse(log_a + f_new / eps)
            if (it + 1) % self.config.check_every == 0:
                delta = (f_new - f).abs().max()
                f = f_new
                if delta < tol:
                    break
            else:
                f = f_new
        return f, g

    def _solve_symmetric(self, log_a, lse, n_iters):
        """Symmetric potential for the debiasing terms UOT(a, a): averaged
        fixed-point iteration for stability."""
        eps = self.config.blur ** 2
        rho = self.config.reach ** 2
        lam = rho / (rho + eps)
        tol = self.config.tol * eps
        p = torch.zeros_like(log_a)
        for it in range(n_iters):
            p_new = -lam * eps * lse(log_a + p / eps)
            delta_p = 0.5 * (p_new - p)
            p = p + delta_p
            if (it + 1) % self.config.check_every == 0 and delta_p.abs().max() < tol:
                break
        return p

    def _dual_value(self, a, b, f, g, log_a, log_b, lse64):
        """Dual objective at (f, g); exact envelope gradients w.r.t. a, b
        when the potentials are converged and detached.

        OT = <a, rho(1 - e^{-f/rho})> + <b, rho(1 - e^{-g/rho})>
             - eps * ( <a x b, e^{(f + g - C)/eps}> - m(a) m(b) )

        Evaluated in float64: the debiased divergence subtracts three
        near-equal extensive quantities, and float32 cancellation there
        can produce spurious zero/negative divergences between large,
        nearly identical fields. The float64 cast is autograd-transparent,
        so gradients w.r.t. the float32 masses remain exact.
        """
        eps = self.config.blur ** 2
        rho = self.config.reach ** 2
        a64, b64 = a.double(), b.double()
        f64, g64 = f.double(), g.double()
        log_a64, log_b64 = log_a.double(), log_b.double()
        term_a = (a64 * rho * (1.0 - torch.exp(-f64 / rho))).sum(dim=(-1, -2))
        term_b = (b64 * rho * (1.0 - torch.exp(-g64 / rho))).sum(dim=(-1, -2))
        # total plan mass: sum_ij a_i b_j e^{(f_i + g_j - C_ij)/eps}
        inner = lse64(log_b64 + g64 / eps)
        log_plan = log_a64 + f64 / eps + inner
        plan_mass = torch.exp(
            torch.logsumexp(log_plan.reshape(log_plan.shape[0], -1), dim=-1)
        )
        mass_a = a64.sum(dim=(-1, -2))
        mass_b = b64.sum(dim=(-1, -2))
        return term_a + term_b - eps * (plan_mass - mass_a * mass_b)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def forward(
        self,
        a: torch.Tensor,
        b: torch.Tensor,
        flow: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Debiased unbalanced Sinkhorn divergence, one value per batch item.

        a, b: (B, H, W) non-negative mass fields on the same grid.
        flow:  optional (B, 2, H, W) or (B, 2) motion field in original-pixel
               units per lead step.  Ignored unless ``motion.alpha > 0``.
        Runs in float32 regardless of autocast: Sinkhorn exponentials are
        not fp16-safe.
        """
        if a.shape != b.shape:
            raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")
        if a.dim() != 3:
            raise ValueError("Expected (B, H, W) mass fields.")
        cfg = self.config
        use_motion = cfg.motion is not None and cfg.motion.enabled
        if use_motion and flow is None:
            raise ValueError("motion cost is enabled but no flow field was given")

        with torch.amp.autocast(device_type=a.device.type, enabled=False):
            a = a.float()
            b = b.float()
            spacing = float(cfg.downsample)
            if cfg.downsample > 1:
                a = sum_pool2d(a, cfg.downsample)
                b = sum_pool2d(b, cfg.downsample)
            h, w = a.shape[-2:]

            if use_motion:
                log_k = self._motion_log_kernel(flow, h, w, spacing, a.device)
                lse = lambda lf: self._kernel_lse_dense(lf, log_k)          # noqa: E731
                lse64 = lambda lf: self._kernel_lse_dense(lf, log_k.double())  # noqa: E731
            else:
                log_kh, log_kw = self._axis_log_kernels(h, w, spacing, a.device)
                lse = lambda lf: self._kernel_lse2d(lf, log_kh, log_kw)     # noqa: E731
                lse64 = lambda lf: self._kernel_lse2d(                      # noqa: E731
                    lf, log_kh.double(), log_kw.double())

            log_a = torch.log(a.clamp_min(1e-30))
            log_b = torch.log(b.clamp_min(1e-30))

            with torch.no_grad():
                f, g = self._solve_potentials(log_a, log_b, lse, cfg.n_iters)
            value = self._dual_value(
                a, b, f.detach(), g.detach(), log_a, log_b, lse64
            )
            if not cfg.debiased:
                return value.to(torch.float32)

            with torch.no_grad():
                p_a = self._solve_symmetric(log_a, lse, cfg.self_iters)
                p_b = self._solve_symmetric(log_b, lse, cfg.self_iters)
            value_aa = self._dual_value(
                a, a, p_a.detach(), p_a.detach(), log_a, log_a, lse64
            )
            value_bb = self._dual_value(
                b, b, p_b.detach(), p_b.detach(), log_b, log_b, lse64
            )
            eps = cfg.blur ** 2
            mass_gap = a.double().sum(dim=(-1, -2)) - b.double().sum(dim=(-1, -2))
            result = value - 0.5 * value_aa - 0.5 * value_bb + 0.5 * eps * mass_gap ** 2
            return result.to(torch.float32)

    def sequence(
        self,
        a_seq: torch.Tensor,
        b_seq: torch.Tensor,
        frame_weights: Optional[torch.Tensor] = None,
        reduce: bool = True,
        flow: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Frame-wise divergence for (B, T, H, W) sequences.

        Returns (B,) when ``reduce`` else the raw per-frame values (B, T)
        so callers can apply frame-level logic (e.g. dry-frame handling).

        Transport happens inside each lead time (position error), never
        across lead times; timing error pricing is a deliberate extension
        point, not an accident.
        """
        if a_seq.dim() != 4:
            raise ValueError("Expected (B, T, H, W) sequences.")
        bsz, t_len = a_seq.shape[:2]

        flat_flow = None
        if flow is not None:
            # One motion field per sample, shared across that sample's lead
            # times: the flow is estimated from the *input* window, so it is a
            # property of the event, not of the lead.  Expanding it here keeps
            # that explicit instead of letting a per-lead flow sneak in and
            # leak future information.
            if flow.dim() == 4 and flow.shape[1] == 2:            # (B,2,H,W)
                flat_flow = flow.unsqueeze(1).expand(
                    bsz, t_len, *flow.shape[1:]
                ).reshape(bsz * t_len, *flow.shape[1:])
            elif flow.dim() == 2:                                  # (B,2)
                flat_flow = flow.unsqueeze(1).expand(bsz, t_len, 2).reshape(-1, 2)
            else:
                raise ValueError(
                    f"flow must be (B,2) or (B,2,H,W), got {tuple(flow.shape)}"
                )

        flat = self.forward(
            a_seq.reshape(bsz * t_len, *a_seq.shape[2:]),
            b_seq.reshape(bsz * t_len, *b_seq.shape[2:]),
            flow=flat_flow,
        ).reshape(bsz, t_len)
        if not reduce:
            return flat
        if frame_weights is None:
            return flat.mean(dim=1)
        frame_weights = frame_weights.to(flat.device, flat.dtype)
        return (flat * frame_weights).sum(dim=1) / frame_weights.sum().clamp_min(1e-12)


# ---------------------------------------------------------------------- #
# dense reference (tests only)
# ---------------------------------------------------------------------- #
def dense_uot_reference(
    a: torch.Tensor,
    b: torch.Tensor,
    blur: float,
    reach: float,
    n_iters: int = 200,
    spacing: float = 1.0,
    debiased: bool = False,
) -> torch.Tensor:
    """O(N^2) float64 reference of the same divergence, for unit tests."""
    if a.dim() != 2:
        raise ValueError("Reference implementation takes a single (H, W) field.")
    device = a.device
    h, w = a.shape
    eps = float(blur) ** 2
    rho = float(reach) ** 2
    lam = rho / (rho + eps)

    ys, xs = torch.meshgrid(
        torch.arange(h, device=device, dtype=torch.float64) * spacing,
        torch.arange(w, device=device, dtype=torch.float64) * spacing,
        indexing="ij",
    )
    pts = torch.stack([ys.reshape(-1), xs.reshape(-1)], dim=1)
    cost = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1)

    def solve(av, bv):
        log_a = torch.log(av.clamp_min(1e-300))
        log_b = torch.log(bv.clamp_min(1e-300))
        f = torch.zeros_like(av)
        g = torch.zeros_like(bv)
        for _ in range(n_iters):
            f = -lam * eps * torch.logsumexp(
                log_b[None, :] + (g[None, :] - cost) / eps, dim=1
            )
            g = -lam * eps * torch.logsumexp(
                log_a[None, :] + (f[None, :] - cost.T) / eps, dim=1
            )
        return f, g

    def value(av, bv, f, g):
        log_a = torch.log(av.clamp_min(1e-300))
        log_b = torch.log(bv.clamp_min(1e-300))
        term_a = (av * rho * (1.0 - torch.exp(-f / rho))).sum()
        term_b = (bv * rho * (1.0 - torch.exp(-g / rho))).sum()
        log_plan = (
            log_a[:, None] + log_b[None, :] + (f[:, None] + g[None, :] - cost) / eps
        )
        plan_mass = torch.exp(torch.logsumexp(log_plan.reshape(-1), dim=0))
        return term_a + term_b - eps * (plan_mass - av.sum() * bv.sum())

    av = a.reshape(-1).double()
    bv = b.reshape(-1).double()
    f, g = solve(av, bv)
    val = value(av, bv, f, g)
    if not debiased:
        return val
    f_aa, g_aa = solve(av, av)
    f_bb, g_bb = solve(bv, bv)
    val_aa = value(av, av, f_aa, g_aa)
    val_bb = value(bv, bv, f_bb, g_bb)
    return val - 0.5 * val_aa - 0.5 * val_bb + 0.5 * eps * (av.sum() - bv.sum()) ** 2
