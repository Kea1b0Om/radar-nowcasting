"""Core WFR / BOT+FR interpolation machinery for the CIKM hidden-frame oracle (K1).

Everything here is *oracle* machinery: it sees both endpoints and produces the
intermediate measure. No network, no prediction.

Conventions
-----------
Measures are discrete: atoms at physical coordinates X (km) with non-negative
proxy masses a. delta is the WFR length scale in km.

WFR / Hellinger-Kantorovich, entropy-transport form (Liero-Mielke-Savare;
Chizat et al. 2018). For phi = d / (2 delta):

    C(x, y) = -4 delta^2 log cos(phi)     if d < pi * delta, else +inf
    WFR^2   = min_gamma <C, gamma> + 2 delta^2 [ KL(gamma_1 | a) + KL(gamma_2 | b) ]

Two closed-form checks this parameterisation must satisfy (see tests):
  * same location, masses m0, m1 -> transported mass sqrt(m0 m1),
    WFR^2 = 2 delta^2 (sqrt(m0) - sqrt(m1))^2
  * equal masses m at distance d -> transported mass m cos(phi),
    WFR^2 = 4 delta^2 m (1 - cos(phi))

Geodesic: lift each edge to the cone. With u0 = sqrt(m0), u1 = sqrt(m1),

    m(t)     = ((1-t) u0)^2 + (t u1)^2 + 2 t (1-t) u0 u1 cos(phi)
    alpha(t) = atan2( t u1 sin(phi), (1-t) u0 + t u1 cos(phi) )
    x(t)     = x0 + (alpha(t) / phi) (x1 - x0)

Edge endpoint masses come from the proportional (cone) lift of the plan:

    m0_ij = gamma_ij * a_i / gamma1_i,   m1_ij = gamma_ij * b_j / gamma2_j

which satisfies the semi-coupling marginals sum_j m0_ij = a_i, sum_i m1_ij = b_j.
Atoms whose whole pi*delta neighbourhood is empty get gamma1_i = 0 exactly and
are handled as pure death ((1-t)^2 m0) / pure birth (t^2 m1).
"""

import numpy as np
import torch


# --------------------------------------------------------------------------
# fields <-> measures
# --------------------------------------------------------------------------

def field_to_atoms(field, cell_km=1.0, device="cpu"):
    """Positive cells of a (H, W) field -> (coords_km [N,2], mass [N])."""
    idx = np.argwhere(field > 0)
    if idx.size == 0:
        return (torch.zeros((0, 2), device=device), torch.zeros((0,), device=device))
    mass = field[idx[:, 0], idx[:, 1]].astype(np.float32)
    coords = idx.astype(np.float32) * cell_km
    return (torch.as_tensor(coords, device=device),
            torch.as_tensor(mass, device=device))


def splat_bilinear(pos_km, mass, shape, cell_km=1.0):
    """Conservative bilinear scatter of particles onto the grid.

    Mass leaving the domain is dropped and returned as `lost` so the caller can
    account for it instead of silently renormalising.
    """
    h, w = shape
    device = pos_km.device
    field = torch.zeros(h * w, device=device, dtype=torch.float32)
    if pos_km.numel() == 0:
        return field.view(h, w), torch.tensor(0.0, device=device)

    p = pos_km / cell_km
    r0 = torch.floor(p[:, 0]).long()
    c0 = torch.floor(p[:, 1]).long()
    fr = p[:, 0] - r0.float()
    fc = p[:, 1] - c0.float()

    total = mass.sum()
    for dr in (0, 1):
        for dc in (0, 1):
            wr = (1 - fr) if dr == 0 else fr
            wc = (1 - fc) if dc == 0 else fc
            rr, cc = r0 + dr, c0 + dc
            ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
            if ok.any():
                flat = (rr[ok] * w + cc[ok])
                field.index_add_(0, flat, (mass * wr * wc)[ok])
    return field.view(h, w), total - field.sum()


def gaussian_blur(field, sigma_cells):
    """Separable Gaussian smoothing, mass preserving except at the border."""
    if sigma_cells <= 0:
        return field
    radius = max(1, int(round(3 * sigma_cells)))
    x = torch.arange(-radius, radius + 1, device=field.device, dtype=torch.float32)
    k = torch.exp(-0.5 * (x / sigma_cells) ** 2)
    k = k / k.sum()
    f = field[None, None]
    f = torch.nn.functional.conv2d(f, k.view(1, 1, -1, 1), padding=(radius, 0))
    f = torch.nn.functional.conv2d(f, k.view(1, 1, 1, -1), padding=(0, radius))
    return f[0, 0]


# --------------------------------------------------------------------------
# costs and solvers
# --------------------------------------------------------------------------

def pairwise_sq_dist(x0, x1):
    return torch.cdist(x0, x1, p=2) ** 2


def wfr_cost(x0, x1, delta):
    """(C, valid_mask) with C = -4 delta^2 log cos(d / 2delta), cut at d >= pi delta."""
    d = torch.cdist(x0, x1, p=2)
    phi = d / (2.0 * delta)
    valid = phi < (np.pi / 2 - 1e-6)
    cos_phi = torch.cos(torch.clamp(phi, max=np.pi / 2 - 1e-6))
    c = -4.0 * delta ** 2 * torch.log(torch.clamp(cos_phi, min=1e-12))
    c = torch.where(valid, c, torch.full_like(c, float("inf")))
    return c, valid


def sinkhorn_unbalanced(a, b, cost, valid, lam, eps, n_iter=400, tol=1e-7):
    """Log-domain scaling iterations for

        min_gamma <C,gamma> + lam[KL(gamma_1|a) + KL(gamma_2|b)] + eps KL(gamma|a (x) b)

    Returns the dense plan gamma (zeros outside `valid`).
    """
    log_a = torch.log(torch.clamp(a, min=1e-30))
    log_b = torch.log(torch.clamp(b, min=1e-30))
    f = torch.zeros_like(a)
    g = torch.zeros_like(b)
    damp = lam / (lam + eps)

    neg_c = torch.where(valid, -cost / eps, torch.full_like(cost, -float("inf")))

    for it in range(n_iter):
        f_prev = f
        # f_i = -damp * eps * logsumexp_j[(g_j - C_ij)/eps + log b_j]
        f = -damp * eps * torch.logsumexp(neg_c + (g / eps + log_b)[None, :], dim=1)
        g = -damp * eps * torch.logsumexp(neg_c + (f / eps + log_a)[:, None], dim=0)
        if it % 25 == 0:
            err = (f - f_prev).abs().max().item()
            if err < tol:
                break

    log_gamma = neg_c + (f / eps + log_a)[:, None] + (g / eps + log_b)[None, :]
    gamma = torch.where(valid, torch.exp(log_gamma), torch.zeros_like(cost))
    return gamma


def sinkhorn_balanced(p, q, cost, eps, n_iter=400, tol=1e-9):
    """Entropic balanced OT between normalised measures; returns the plan."""
    log_p = torch.log(torch.clamp(p, min=1e-30))
    log_q = torch.log(torch.clamp(q, min=1e-30))
    f = torch.zeros_like(p)
    g = torch.zeros_like(q)
    neg_c = -cost / eps
    for it in range(n_iter):
        f_prev = f
        f = -eps * torch.logsumexp(neg_c + (g / eps + log_q)[None, :], dim=1)
        g = -eps * torch.logsumexp(neg_c + (f / eps + log_p)[:, None], dim=0)
        if it % 25 == 0 and (f - f_prev).abs().max().item() < tol:
            break
    return torch.exp(neg_c + (f / eps + log_p)[:, None] + (g / eps + log_q)[None, :])


# --------------------------------------------------------------------------
# geodesics
# --------------------------------------------------------------------------

def semi_coupling_lift(gamma, a, b, mass_floor=1e-12):
    """Proportional cone lift -> per-edge endpoint masses (m0, m1) + leftovers."""
    g1 = gamma.sum(dim=1)
    g2 = gamma.sum(dim=0)
    alive0 = g1 > mass_floor
    alive1 = g2 > mass_floor

    scale0 = torch.where(alive0, a / torch.clamp(g1, min=mass_floor),
                         torch.zeros_like(a))
    scale1 = torch.where(alive1, b / torch.clamp(g2, min=mass_floor),
                         torch.zeros_like(b))
    m0 = gamma * scale0[:, None]
    m1 = gamma * scale1[None, :]

    dead_mass = torch.where(alive0, torch.zeros_like(a), a)   # pure death atoms
    born_mass = torch.where(alive1, torch.zeros_like(b), b)   # pure birth atoms
    return m0, m1, dead_mass, born_mass


def cone_interpolate(x0, x1, m0, m1, delta, t):
    """Cone (WFR) geodesic for a batch of edges. Returns (pos [E,2], mass [E])."""
    d = torch.linalg.norm(x1 - x0, dim=-1)
    phi = torch.clamp(d / (2.0 * delta), max=np.pi / 2 - 1e-6)
    u0 = torch.sqrt(torch.clamp(m0, min=0))
    u1 = torch.sqrt(torch.clamp(m1, min=0))
    cos_phi = torch.cos(phi)
    sin_phi = torch.sin(phi)

    mass = ((1 - t) * u0) ** 2 + (t * u1) ** 2 + 2 * t * (1 - t) * u0 * u1 * cos_phi
    alpha = torch.atan2(t * u1 * sin_phi, (1 - t) * u0 + t * u1 * cos_phi)
    frac = torch.where(phi > 1e-8, alpha / torch.clamp(phi, min=1e-8),
                       torch.full_like(phi, t))
    pos = x0 + frac[:, None] * (x1 - x0)
    return pos, mass


def wfr_interpolate(x0, x1, a, b, delta, t, eps_rel=0.02, n_iter=400,
                    prune_rel=1e-6):
    """Full WFR oracle interpolation at time t. Returns (pos, mass, diagnostics)."""
    cost, valid = wfr_cost(x0, x1, delta)
    lam = 2.0 * delta ** 2
    eps = eps_rel * lam
    gamma = sinkhorn_unbalanced(a, b, cost, valid, lam, eps, n_iter=n_iter)
    m0, m1, dead, born = semi_coupling_lift(gamma, a, b)

    keep = gamma > (prune_rel * gamma.max().clamp(min=1e-30))
    ei, ej = torch.nonzero(keep, as_tuple=True)
    pruned_mass = (m0.sum() - m0[ei, ej].sum()).clamp(min=0)

    pos_e, mass_e = cone_interpolate(x0[ei], x1[ej], m0[ei, ej], m1[ei, ej], delta, t)

    # pure death / pure birth atoms follow the degenerate cone geodesic
    pos = [pos_e, x0[dead > 0], x1[born > 0]]
    mass = [mass_e, (1 - t) ** 2 * dead[dead > 0], t ** 2 * born[born > 0]]

    diag = {
        "n_edges": int(ei.numel()),
        "coupled_mass_frac": float((gamma.sum() / a.sum().clamp(min=1e-30)).item()),
        "dead_mass_frac": float((dead.sum() / a.sum().clamp(min=1e-30)).item()),
        "born_mass_frac": float((born.sum() / b.sum().clamp(min=1e-30)).item()),
        "pruned_mass_frac": float((pruned_mass / a.sum().clamp(min=1e-30)).item()),
    }
    return torch.cat(pos, dim=0), torch.cat(mass, dim=0), diag


def bot_fr_interpolate(x0, x1, a, b, t, eps_rel=0.01, n_iter=400, prune_rel=1e-6):
    """Balanced shape OT + global Fisher-Rao mass path (the geometry control).

    Shapes are normalised, coupled by balanced OT, positions move linearly, and
    the *global* mass follows the FR path M(t) = ((1-t)sqrt(M0) + t sqrt(M1))^2.
    Same supervision density as WFR (dense positions, velocities, path mass,
    non-zero growth) -- the only difference is that transport and reaction are
    not coupled in a local unbalanced geometry.
    """
    m0_tot, m1_tot = a.sum(), b.sum()
    p = a / m0_tot.clamp(min=1e-30)
    q = b / m1_tot.clamp(min=1e-30)
    cost = pairwise_sq_dist(x0, x1)
    eps = eps_rel * cost.mean().clamp(min=1e-12)
    pi = sinkhorn_balanced(p, q, cost, eps, n_iter=n_iter)

    keep = pi > (prune_rel * pi.max().clamp(min=1e-30))
    ei, ej = torch.nonzero(keep, as_tuple=True)
    w = pi[ei, ej]

    mass_total = ((1 - t) * torch.sqrt(m0_tot) + t * torch.sqrt(m1_tot)) ** 2
    pos = (1 - t) * x0[ei] + t * x1[ej]
    mass = mass_total * w / w.sum().clamp(min=1e-30)
    diag = {"n_edges": int(ei.numel()),
            "fr_mass_ratio": float((mass_total / m0_tot.clamp(min=1e-30)).item())}
    return pos, mass, diag


def linear_field_interpolate(f0, f1, t):
    """Lowest-effort path baseline: linear interpolation in mass space."""
    return (1 - t) * f0 + t * f1
