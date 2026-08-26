import math

import torch
import torch.nn as nn

from .rflow_objective import rflow_training_loss
from .schedule import build_sampling_timesteps, make_chunk_index
from .stdit import STDiT, STDiTConfig

__all__ = [
    "FlowCastSTDiTWrapper",
    "autoregressive_sample",
    "build_sampling_timesteps",
    "make_chunk_index",
    "rflow_training_loss",
    "sample_chunk_euler",
]


class FlowCastSTDiTWrapper(nn.Module):
    def __init__(
        self,
        latent_channels,
        hidden_size,
        depth,
        num_heads,
        patch_size,
        mlp_ratio=4.0,
        drop_path=0.0,
        qk_norm=True,
        mean=0.0,
        std=1.0,
    ):
        super().__init__()
        if depth % 2 != 0:
            raise ValueError("stdit.depth must be even.")

        config = STDiTConfig(
            in_channels=latent_channels,
            hidden_size=hidden_size,
            depth=depth,
            num_heads=num_heads,
            patch_size=tuple(patch_size),
            mlp_ratio=mlp_ratio,
            drop_path=drop_path,
            qk_norm=qk_norm,
        )
        self.backbone = STDiT(config)

        mean_tensor = torch.as_tensor(mean, dtype=torch.float32).clone().detach()
        std_tensor = torch.as_tensor(std, dtype=torch.float32).clone().detach()
        self.register_buffer("mean", mean_tensor)
        self.register_buffer("std", std_tensor)

    def normalize(self, x):
        return (x - self.mean) / self.std

    def denormalize(self, x):
        return x * self.std + self.mean

    def forward(self, x_t, t, cond, t_seq):
        if t_seq is None:
            raise ValueError("t_seq must not be None.")
        if t.device != x_t.device:
            t = t.to(device=x_t.device)
        if t_seq.device != x_t.device:
            t_seq = t_seq.to(device=x_t.device)
        t = t.long()
        t_seq = t_seq.long()

        x_t_bcthw = x_t.permute(0, 4, 1, 2, 3).contiguous()
        cond_bcthw = cond.permute(0, 4, 1, 2, 3).contiguous()
        output = self.backbone(x_t_bcthw, t, cond_bcthw, idx=t_seq)
        return output.permute(0, 2, 3, 4, 1).contiguous()


def sample_chunk_euler(
    model,
    cond,
    chunk_idx,
    num_train_timesteps,
    euler_steps,
    generator=None,
    sde_noise_scale=None,
    sde_final_step_noise=False,
    sde_drift_compensation=True,
):
    """Euler sampler for one chunk; optionally a marginal-preserving SDE.

    With ``sde_noise_scale`` left as ``None`` (or ``0.0``) this is the original
    deterministic sampler, byte for byte, and it draws **exactly one** tensor
    from ``generator`` -- so the production RNG stream is untouched and any
    ``kappa=0`` arm reproduces a stored baseline bitwise (pinned by tests).

    Derivation of the stochastic path, in this repository's conventions
    (``rflow_objective``): with ``s = t / (num_train_timesteps - 1)``,
    ``x_s = s * eps + (1 - s) * x_0`` and the network predicting
    ``v = E[x_0 - eps | x_s]``.  Then ``x_s | x_0 ~ N((1-s) x_0, s^2 I)``, so

        E[eps | x_s] = x_s - (1 - s) v            (algebra on the interpolant)
        score(x_s)   = grad log p_s(x_s) = -E[eps | x_s] / s

    Any diffusion coefficient ``sigma_s`` admits a reverse update with the same
    marginals as the probability-flow ODE:

        x <- x + [v + (sigma_s^2 / 2) * score] * ds + sigma_s * sqrt(ds) * zeta

    Choosing ``sigma_s = kappa * sqrt(s)`` keeps both pieces bounded as
    ``s -> 0``: the drift correction collapses to ``-(kappa^2 / 2) * E[eps|x_s]``
    and the injected noise scales as ``kappa * sqrt(s * ds)``.  ``kappa`` is
    therefore an exploration knob that (to first order in ``ds``) leaves every
    marginal, and hence the terminal distribution, unchanged -- verified against
    a closed-form Gaussian target in the tests, including a sign-flip control
    that shows the check has power.

    The step that lands on ``s = 0`` is deterministic by default: noise added
    there has no remaining step to be absorbed by, so it would corrupt the
    returned sample and confound "the SDE is wrong" with "the model degrades".
    Set ``sde_final_step_noise=True`` to follow the SDE literally instead.

    ``sde_drift_compensation=False`` drops the ``-(kappa^2/2) E[eps|x_s]`` term
    and injects the noise bare.  That is **deliberately off-distribution** and is
    the only setting in this function that actually widens the terminal spread -
    the compensated form provably cannot, since it preserves every marginal.  It
    exists so the price of exploration can be measured rather than assumed: the
    sign-flip control in the tests shows an uncompensated-style error doubling
    the terminal standard deviation on a closed-form target.
    """
    batch_size = cond.shape[0]
    device = cond.device
    dtype = cond.dtype
    timesteps = build_sampling_timesteps(num_train_timesteps, euler_steps, device)
    chunk_index = make_chunk_index(batch_size, chunk_idx, device)
    z = torch.randn(
        cond.shape,
        device=device,
        dtype=dtype,
        generator=generator,
    )

    kappa = 0.0 if sde_noise_scale is None else float(sde_noise_scale)
    if kappa < 0.0:
        raise ValueError(f"sde_noise_scale must be non-negative, got {kappa}.")
    time_scale = float(num_train_timesteps - 1)

    for current_t, next_t in zip(timesteps[:-1], timesteps[1:]):
        t = torch.full(
            (batch_size,),
            int(current_t.item()),
            device=device,
            dtype=torch.long,
        )
        velocity = model(z, t, cond, chunk_index)
        delta_t = (current_t - next_t).to(dtype=dtype) / float(num_train_timesteps - 1)
        if kappa == 0.0:
            z = z + velocity * delta_t
            continue

        s_cur = float(current_t.item()) / time_scale
        s_next = float(next_t.item()) / time_scale
        ds = s_cur - s_next
        # E[eps | x_s] must be evaluated at the *current* x_s: taking it after
        # the velocity step leaves an O(ds^2) error that a fine-step test cannot
        # see but the deployed 10-step schedule can.
        eps_hat = z - (1.0 - s_cur) * velocity
        z = z + velocity * delta_t
        if sde_drift_compensation:
            z = z - (0.5 * kappa * kappa * ds) * eps_hat
        if s_next > 0.0 or sde_final_step_noise:
            std = kappa * math.sqrt(max(s_cur * ds, 0.0))
            if std > 0.0:
                z = z + std * torch.randn(
                    z.shape, device=device, dtype=dtype, generator=generator
                )
    return z


def autoregressive_sample(
    model,
    initial_cond,
    input_length,
    output_length,
    num_train_timesteps,
    euler_steps,
    generator=None,
    sde_noise_scale=None,
    sde_final_step_noise=False,
    sde_drift_compensation=True,
):
    if output_length % input_length != 0:
        raise ValueError("output_length must be divisible by input_length.")

    num_chunks = output_length // input_length
    cond = initial_cond
    predictions = []

    for chunk_idx in range(1, num_chunks + 1):
        pred_chunk = sample_chunk_euler(
            model=model,
            cond=cond,
            chunk_idx=chunk_idx,
            num_train_timesteps=num_train_timesteps,
            euler_steps=euler_steps,
            generator=generator,
            sde_noise_scale=sde_noise_scale,
            sde_final_step_noise=sde_final_step_noise,
            sde_drift_compensation=sde_drift_compensation,
        )
        predictions.append(pred_chunk)
        cond = pred_chunk

    return torch.cat(predictions, dim=1)
