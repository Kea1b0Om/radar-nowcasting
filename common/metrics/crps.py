"""Proper empirical CRPS for ensemble forecasts, with member weights.

Replaces the previous Gaussian moment-matching approximation, which
collapsed the ensemble to (mean, std) before scoring - erasing exactly
the information (multi-modality, heavy tails, mode weights) that
probabilistic nowcasting experiments need to measure.

Weighted empirical CRPS for members x_1..x_M with weights w (sum 1):

    CRPS(F, y) = sum_i w_i |x_i - y|  -  c * 1/2 sum_ij w_i w_j |x_i - x_j|

- "biased" (NRG/PWM form):    c = 1
- "fair" (unbiased for iid members; Ferro 2014, generalized to weights):
                              c = 1 / (1 - sum_i w_i^2)
  (uniform weights w=1/M give the familiar M/(M-1) correction)
- "almost_fair" (Lang et al., AIFS-CRPS): (1-alpha)*fair + alpha*biased,
  avoiding the degenerate optimum of the exactly-fair score while keeping
  its bias correction. This is the recommended default.

Threshold-weighted CRPS (twCRPS) uses the chaining function
v(z) = max(z, t): score the transformed members/observation to emphasize
performance above threshold t (Allen et al.). twCRPS(t=-inf) == CRPS.

All functions are pure torch, differentiable, and return per-pixel maps
so callers choose their own reduction/streaming.
"""

from typing import Optional

import torch


def _normalize_weights(weights, batch, members, device, dtype):
    if weights is None:
        w = torch.full((batch, members), 1.0 / members, device=device, dtype=dtype)
        return w
    w = torch.as_tensor(weights, device=device, dtype=dtype)
    if w.dim() == 1:
        w = w.unsqueeze(0).expand(batch, -1)
    if w.shape != (batch, members):
        raise ValueError(f"weights shape {tuple(w.shape)} != ({batch}, {members})")
    w_sum = w.sum(dim=1, keepdim=True)
    if torch.any(w_sum <= 0):
        raise ValueError("weights must have positive sum")
    return w / w_sum


def crps_ensemble(
    obs: torch.Tensor,
    ens: torch.Tensor,
    weights: Optional[torch.Tensor] = None,
    estimator: str = "almost_fair",
    alpha: float = 0.05,
    batch_chunk: int = 8,
) -> torch.Tensor:
    """Per-pixel weighted empirical CRPS.

    obs: (B, *spatial); ens: (B, M, *spatial); weights: (B, M) or (M,) or
    None (uniform). Returns (B, *spatial).

    M == 1 degenerates to |x - y| (MAE) for every estimator (the fair
    correction is undefined and the spread term is zero).
    """
    if ens.dim() != obs.dim() + 1:
        raise ValueError(
            f"ens must have one extra member dim: obs {obs.shape}, ens {ens.shape}"
        )
    if estimator not in ("biased", "fair", "almost_fair"):
        raise ValueError(f"Unknown estimator: {estimator}")
    batch, members = ens.shape[0], ens.shape[1]
    w = _normalize_weights(weights, batch, members, ens.device, ens.dtype)

    out = torch.empty_like(obs)
    spatial_ones = [1] * (ens.dim() - 2)
    for start in range(0, batch, max(batch_chunk, 1)):
        sl = slice(start, min(start + max(batch_chunk, 1), batch))
        e = ens[sl]
        o = obs[sl]
        ww = w[sl]
        w_b = ww.reshape(ww.shape[0], members, *spatial_ones)
        term1 = (w_b * (e - o.unsqueeze(1)).abs()).sum(dim=1)

        if members > 1:
            pair = (e.unsqueeze(1) - e.unsqueeze(2)).abs()  # (b, M, M, *sp)
            pw = (ww.unsqueeze(1) * ww.unsqueeze(2)).reshape(
                ww.shape[0], members, members, *spatial_ones
            )
            spread = 0.5 * (pw * pair).sum(dim=(1, 2))
            if estimator == "biased":
                out[sl] = term1 - spread
            else:
                denom = (1.0 - (ww ** 2).sum(dim=1)).clamp_min(1e-12)
                fair_spread = spread / denom.reshape(-1, *spatial_ones)
                if estimator == "fair":
                    out[sl] = term1 - fair_spread
                else:  # almost_fair
                    out[sl] = term1 - ((1.0 - alpha) * fair_spread + alpha * spread)
        else:
            out[sl] = term1
    return out


def twcrps_ensemble(
    obs: torch.Tensor,
    ens: torch.Tensor,
    threshold: float,
    weights: Optional[torch.Tensor] = None,
    estimator: str = "almost_fair",
    alpha: float = 0.05,
    batch_chunk: int = 8,
) -> torch.Tensor:
    """Threshold-weighted CRPS with chaining v(z) = max(z, threshold):
    scores only the distribution of exceedances above ``threshold``."""
    return crps_ensemble(
        obs.clamp_min(threshold),
        ens.clamp_min(threshold),
        weights=weights,
        estimator=estimator,
        alpha=alpha,
        batch_chunk=batch_chunk,
    )


def crps_gaussian_reference(obs: torch.Tensor, mu: torch.Tensor, sigma: torch.Tensor):
    """Closed-form CRPS of a Gaussian N(mu, sigma^2) - kept ONLY as an
    analytic reference for unit tests of the empirical estimator."""
    import math

    z = (obs - mu) / sigma
    normal = torch.distributions.Normal(0.0, 1.0)
    pdf = torch.exp(normal.log_prob(z))
    cdf = normal.cdf(z)
    return sigma * (z * (2 * cdf - 1) + 2 * pdf - 1.0 / math.sqrt(math.pi))
