"""Rectified-flow training objective shared by FlowCast training and tests.

This module intentionally has no dependency on the STDiT implementation so
objective-level tests can run in lightweight environments.
"""

import torch


def rflow_training_loss(
    model,
    x_start,
    cond,
    t_seq,
    num_train_timesteps,
    decode_fn=None,
    uot_loss=None,
    uot_params=None,
    t_override=None,
    lead_weights=None,
    noise_override=None,
):
    """Rectified-flow training loss, optionally augmented with a field-wise
    unbalanced optimal transport term (Innovation 2).

    The UOT term is computed between the decoded pixel reconstruction and
    the decoded ground truth: transport prices displacement smoothly
    (removing the pointwise double penalty that makes blur loss-optimal),
    while the marginal relaxation prices creation/destruction of
    precipitation mass. With decode_fn/uot_loss left as None the function
    is byte-for-byte the original objective.

    ``t_override`` and ``lead_weights`` are training-only hooks used by
    Rollout-Matched Lead--Flow Coupling.  Both default to ``None`` so every
    existing configuration follows the original code path.

    Returns (loss, uot_term_mean_or_None).
    """
    if num_train_timesteps < 2:
        raise ValueError("num_train_timesteps must be at least 2.")

    batch_size = x_start.shape[0]
    device = x_start.device
    if noise_override is None:
        noise = torch.randn_like(x_start, device=device)
    else:
        if noise_override.shape != x_start.shape:
            raise ValueError(
                f"noise_override shape {noise_override.shape} does not match "
                f"x_start shape {x_start.shape}."
            )
        noise = noise_override.to(device=device, dtype=x_start.dtype)

    if t_override is None:
        t = torch.randint(
            1,
            num_train_timesteps,
            (batch_size,),
            device=device,
            dtype=torch.long,
        )
    else:
        if t_override.shape != (batch_size,):
            raise ValueError(
                f"t_override must have shape ({batch_size},); "
                f"got {tuple(t_override.shape)}."
            )
        t = t_override.to(device=device, dtype=torch.long)
        if torch.any(t < 1) or torch.any(t >= num_train_timesteps):
            raise ValueError(
                "t_override values must lie in [1, num_train_timesteps - 1]."
            )
    t_norm = t.to(dtype=x_start.dtype) / float(num_train_timesteps - 1)
    t_norm = t_norm.view(batch_size, 1, 1, 1, 1)
    x_t = t_norm * noise + (1.0 - t_norm) * x_start
    velocity = model(x_t, t, cond, t_seq)

    residual_target = x_start - noise
    velocity_sq = (velocity - residual_target) ** 2
    reconstruction = x_t + velocity * t_norm
    reconstruction_sq = (reconstruction - x_start) ** 2

    if lead_weights is None:
        # Keep the disabled/default path exactly identical to the original
        # objective.  RMLF only changes reduction when explicit lead weights
        # are supplied for a later autoregressive chunk.
        loss = torch.mean(velocity_sq) + torch.mean(reconstruction_sq)
        normalized_lead_weights = None
    else:
        if lead_weights.shape != (batch_size, x_start.shape[1]):
            raise ValueError(
                "lead_weights must have shape "
                f"({batch_size}, {x_start.shape[1]}); got "
                f"{tuple(lead_weights.shape)}."
            )
        normalized_lead_weights = lead_weights.to(
            device=device, dtype=x_start.dtype
        ).clamp_min(0.0)
        weight_sum = normalized_lead_weights.sum(dim=1).clamp_min(1e-8)
        reduce_dims = tuple(range(2, x_start.ndim))
        velocity_per_lead = velocity_sq.mean(dim=reduce_dims)
        reconstruction_per_lead = reconstruction_sq.mean(dim=reduce_dims)
        loss = (
            (velocity_per_lead * normalized_lead_weights).sum(dim=1) / weight_sum
        ).mean()
        loss = loss + (
            (reconstruction_per_lead * normalized_lead_weights).sum(dim=1)
            / weight_sum
        ).mean()

    uot_stat = None
    if decode_fn is not None and uot_loss is not None and uot_params is not None:
        from common.losses.uot import mass_from_field

        with torch.amp.autocast(device_type=device.type, enabled=False):
            pixel_pred = decode_fn(reconstruction)
            with torch.no_grad():
                pixel_true = decode_fn(x_start).detach()
            mass_pred = mass_from_field(
                pixel_pred.float(), **uot_params["mass_kwargs"]
            )
            mass_true = mass_from_field(
                pixel_true.float(), **uot_params["mass_kwargs"]
            )
            per_frame = uot_loss.sequence(mass_pred, mass_true, reduce=False)  # (B, T)
            # Dry TRUE frames: Sinkhorn against an (almost) empty target is
            # numerically meaningless. Follow the counting-UOT practice
            # (AAAI'21) and directly penalize the predicted total mass on
            # those frames instead.
            true_frame_mass = mass_true.sum(dim=(2, 3)).detach()  # (B, T)
            dry = true_frame_mass < float(uot_params.get("dry_frame_mass", 1e-3))
            if torch.any(dry):
                pred_frame_mass = mass_pred.sum(dim=(2, 3))
                per_frame = torch.where(dry, pred_frame_mass, per_frame)
            if normalized_lead_weights is None:
                uot_val = per_frame.mean(dim=1)  # (B,)
            else:
                uot_weight_sum = normalized_lead_weights.sum(dim=1).clamp_min(1e-8)
                uot_val = (
                    per_frame * normalized_lead_weights.float()
                ).sum(dim=1) / uot_weight_sum.float()
            if uot_params.get("normalize_by_mass", False):
                # LEGACY per-sample normalization. Kept only for ablation:
                # it gives drizzle and extreme events near-equal weight,
                # erasing exactly the mass signal UOT should price.
                uot_val = uot_val / (mass_true.sum(dim=(1, 2, 3)).detach() + 1.0)
            # Fixed climatological scale (Francis-style M_ref): a CONSTANT
            # across the dataset, so heavy-rain samples keep proportionally
            # larger UOT loss. Calibrate once so that the logged
            # uot_term / training_loss ratio lands in the 5-20% band.
            uot_val = uot_val / float(uot_params.get("value_scale_ref", 1.0))
        # reconstruction at high flow time is mostly noise: weight the
        # transport term toward low-noise samples
        t_weight = (1.0 - t_norm.reshape(-1)) ** float(uot_params.get("t_power", 2.0))
        uot_term = float(uot_params["weight"]) * t_weight * uot_val
        loss = loss + uot_term.mean()
        uot_stat = float(uot_term.detach().mean())
    return loss, uot_stat
