"""Flow-aligned ground cost for the grid UOT divergence.

Why the ground cost should not be Euclidean here
------------------------------------------------
The squared-Euclidean cost prices every displacement the same way.  For a
moving precipitation field that conflates two errors a forecaster treats very
differently:

* displacement **along** the storm motion is largely a *timing* error -- the
  right structure arriving early or late;
* displacement **across** the motion is a *track* error -- the storm going
  somewhere it did not go.

Pricing them identically is what leaves the UOT transport term as a proxy for
"advection" rather than a measurement of it.  Aligning the cost to the motion
field makes the split explicit: what the transport term charges for is the
displacement advection cannot explain, and what the marginal relaxation charges
for is genuine growth and decay.

The metric
----------
For a flow ``v`` (pixels per lead step) with unit direction ``u``, the ground
cost between grid points ``x_i`` and ``x_j`` becomes the quadratic form

    c(i, j) = d^T M d,      d = x_j - x_i,
    M       = I - s * u u^T,
    s       = alpha * |v|^2 / (blur^2 + |v|^2)   in [0, alpha].

``M`` has eigenvalue ``1 - s`` along the flow and ``1`` across it, so it is
positive definite for ``alpha < 1`` and the cost stays a genuine (squared)
metric -- Sinkhorn needs that.  ``s`` saturates: a storm moving much faster
than the entropic blur length cannot buy unbounded along-track tolerance.

**alpha = 0 gives M = I exactly**, i.e. the current Euclidean cost, bit for bit.
That is the identity arm; every experiment on this axis is a dose-response in
``alpha`` against it.

Separability
------------
The Euclidean cost on a grid factorises across the two axes, which is what makes
the existing Sinkhorn O(N sqrt(N)).  A flow-aligned metric does **not**: the
cross term ``2 * M01 * d_h * d_w`` is not a sum of a function of ``d_h`` and a
function of ``d_w``, and that holds even for a spatially uniform flow unless it
happens to be axis-aligned.  So any ``alpha > 0`` has to go through the dense
O(N^2) path.  At the working resolution (128 -> downsample 4 -> 32x32 = 1024
points) the dense cost matrix is 1024^2 float32 = 4 MB, which is affordable;
this module does not try to hide that trade-off.

Modes
-----
``global``  one flow vector per (sample, frame).  ``M`` is constant over the
            grid, so the cost is symmetric by construction.  Captures bulk storm
            motion, which is the dominant term.
``local``   a flow vector per grid point.  ``M_i`` varies, which would make
            ``c(i,j) != c(j,i)`` and quietly break the symmetry the debiasing
            terms assume, so the metric is symmetrised as ``(M_i + M_j) / 2``.
"""

from dataclasses import dataclass
from typing import Optional

import torch


@dataclass
class MotionCostConfig:
    """alpha is the single dose knob; 0 disables the mechanism entirely.

    alpha:  maximum along-flow discount, in [0, 1).  s -> alpha as the flow
            speed grows past ``blur``.  alpha = 0 reproduces the Euclidean cost.
    mode:   "global" (one vector per sample-frame) or "local" (per grid point).
    max_speed: optional clamp on |v| in original-pixel units, applied before the
            metric is built.  Optical flow on near-empty frames can return
            nonsense; an unclamped outlier would make a whole direction free.
    """

    alpha: float = 0.0
    mode: str = "global"
    max_speed: Optional[float] = None

    def __post_init__(self):
        if not (0.0 <= self.alpha < 1.0):
            raise ValueError(f"alpha must be in [0, 1), got {self.alpha}")
        if self.mode not in ("global", "local"):
            raise ValueError(f"mode must be 'global' or 'local', got {self.mode!r}")
        if self.max_speed is not None and self.max_speed <= 0:
            raise ValueError("max_speed must be positive when set")

    @property
    def enabled(self) -> bool:
        return self.alpha > 0.0


def flow_to_metric(
    flow: torch.Tensor,
    blur: float,
    config: MotionCostConfig,
) -> torch.Tensor:
    """Build the 2x2 metric ``M`` from a flow field.

    flow: ``(B, 2, H, W)`` in (dh, dw) original-pixel units per lead step, or
          ``(B, 2)`` for ``mode="global"``.
    Returns ``(B, 1, 1, 2, 2)`` for global, ``(B, H, W, 2, 2)`` for local.

    Never in-place on ``flow`` -- callers may hold a cached tensor.
    """
    if config.mode == "global":
        if flow.dim() == 4:
            # reduce a field to its mass-agnostic mean vector
            v = flow.mean(dim=(-1, -2))
        elif flow.dim() == 2:
            v = flow
        else:
            raise ValueError(f"global mode expects (B,2) or (B,2,H,W), got {tuple(flow.shape)}")
        v = v[:, None, None, :]                                # (B,1,1,2)
    else:
        if flow.dim() != 4 or flow.shape[1] != 2:
            raise ValueError(f"local mode expects (B,2,H,W), got {tuple(flow.shape)}")
        v = flow.permute(0, 2, 3, 1)                            # (B,H,W,2)

    v = v.float()
    speed = torch.linalg.vector_norm(v, dim=-1, keepdim=True)   # (...,1)
    if config.max_speed is not None:
        scale = (config.max_speed / speed.clamp_min(1e-12)).clamp(max=1.0)
        v = v * scale
        speed = speed.clamp(max=config.max_speed)

    eps_len = float(blur) ** 2
    sq = speed ** 2
    s = config.alpha * sq / (eps_len + sq)                      # (...,1), in [0, alpha)
    u = v / speed.clamp_min(1e-12)                              # (...,2) unit, 0 if speed 0

    eye = torch.eye(2, device=v.device, dtype=v.dtype).expand(*v.shape[:-1], 2, 2)
    outer = u[..., :, None] * u[..., None, :]                   # (...,2,2)
    return eye - s[..., None] * outer                           # (...,2,2)


def metric_cost_matrix(
    metric: torch.Tensor,
    height: int,
    width: int,
    spacing: float,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Dense ``(B, N, N)`` ground cost, ``N = height * width``.

    metric: ``(B,1,1,2,2)`` (global) or ``(B,H,W,2,2)`` (local).  For the local
    case the metric is symmetrised across the pair, ``(M_i + M_j) / 2``, so the
    returned matrix satisfies ``C == C.transpose(-1,-2)`` exactly -- the
    debiasing terms and the ``g`` update both assume that, and an asymmetric
    cost would break them silently rather than loudly.
    """
    device = metric.device
    ys, xs = torch.meshgrid(
        torch.arange(height, device=device, dtype=dtype) * spacing,
        torch.arange(width, device=device, dtype=dtype) * spacing,
        indexing="ij",
    )
    pts = torch.stack([ys.reshape(-1), xs.reshape(-1)], dim=-1)   # (N,2)
    d = pts[None, :, :] - pts[:, None, :]                          # (N,N,2) = x_j - x_i

    b = metric.shape[0]
    if metric.shape[1] == 1 and metric.shape[2] == 1:
        m = metric.reshape(b, 1, 1, 2, 2).to(dtype)
        # d^T M d, broadcast over the single metric
        return torch.einsum("ijp,bxypq,ijq->bij", d, m, d)

    n = height * width
    m = metric.reshape(b, n, 2, 2).to(dtype)                       # per-source metric
    # (M_i + M_j)/2 contracted with d without materialising (B,N,N,2,2)
    left = torch.einsum("ijp,bipq,ijq->bij", d, m, d)              # d^T M_i d
    right = torch.einsum("ijp,bjpq,ijq->bij", d, m, d)             # d^T M_j d
    return 0.5 * (left + right)


def euclidean_cost_matrix(
    height: int, width: int, spacing: float,
    device: torch.device, dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """``(N, N)`` squared-Euclidean reference cost -- what ``alpha = 0`` must
    reproduce, kept separate so the equivalence is testable rather than assumed."""
    ys, xs = torch.meshgrid(
        torch.arange(height, device=device, dtype=dtype) * spacing,
        torch.arange(width, device=device, dtype=dtype) * spacing,
        indexing="ij",
    )
    pts = torch.stack([ys.reshape(-1), xs.reshape(-1)], dim=-1)
    return ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1)
