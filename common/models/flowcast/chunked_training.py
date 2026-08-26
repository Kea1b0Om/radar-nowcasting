"""Chunked FlowCast training objective with optional RMLF conditioning."""

import torch

from .rflow_objective import rflow_training_loss


def compute_chunked_rflow_loss(
    model_forward,
    normalizer_model,
    inputs,
    outputs,
    input_length,
    output_length,
    num_train_timesteps,
    decode_fn=None,
    uot_loss=None,
    uot_params=None,
    rmlf_controller=None,
    rmlf_teacher=None,
    global_step=0,
    return_rmlf_stats=False,
):
    """Compute the chunked RF objective, optionally with training-only RMLF.

    The original teacher-forced path is preserved whenever ``rmlf_controller``
    is absent or disabled.  For later chunks, RMLF constructs the previous
    condition with a no-gradient teacher rollout bridge and can couple its
    corruption level to the current target Flow time and within-chunk lead.
    Inference remains unchanged.
    """
    normalized_inputs = normalizer_model.normalize(inputs)
    normalized_outputs = normalizer_model.normalize(outputs)
    num_chunks = output_length // input_length
    loss = normalized_outputs.new_tensor(0.0)
    uot_stats = []
    rmlf_records = []

    rmlf_enabled = (
        rmlf_controller is not None
        and rmlf_controller.enabled
        and num_chunks > 1
    )
    if rmlf_enabled and rmlf_teacher is None:
        raise ValueError("RMLF is enabled but no rollout teacher was provided.")

    # Condition used by the teacher when constructing the next bridge.  For
    # chunk 1 this is the observed history; for longer rollouts it is the
    # clean/rollout mixture actually seen by the preceding target chunk.
    previous_training_condition = normalized_inputs.detach()

    for chunk_idx in range(num_chunks):
        start = chunk_idx * input_length
        end = (chunk_idx + 1) * input_length
        target_chunk = normalized_outputs[:, start:end]
        t_override = None
        lead_weights = None

        if chunk_idx == 0:
            cond = normalized_inputs
        else:
            clean_previous = normalized_outputs[:, start - input_length : start]
            cond = clean_previous

            if rmlf_enabled:
                requested_mask = rmlf_controller.sample_rollout_mask(
                    inputs.shape[0],
                    global_step=global_step,
                    device=inputs.device,
                )
                if torch.any(requested_mask):
                    plan = rmlf_controller.sample_plan(
                        batch_size=inputs.shape[0],
                        chunk_index=chunk_idx + 1,
                        chunk_length=input_length,
                        num_train_timesteps=num_train_timesteps,
                        device=inputs.device,
                        dtype=normalized_outputs.dtype,
                    )
                    built = rmlf_controller.build_condition(
                        teacher_model=rmlf_teacher,
                        clean_previous_chunk=clean_previous,
                        teacher_condition=previous_training_condition,
                        generated_chunk_index=chunk_idx,
                        corruption=plan.corruption,
                        rollout_mask=requested_mask,
                        num_train_timesteps=num_train_timesteps,
                    )
                    cond = built.condition
                    active_mask = built.rollout_mask

                    # `independent` coupling changes the CONDITION and nothing
                    # else.  Overriding the Flow time there -- even with an
                    # identically distributed uniform draw -- would stop the
                    # objective from consuming the base RF `torch.randint`, so
                    # the global RNG would fork at the first rollout batch and
                    # R1/R2 would see different target noise and timesteps
                    # from R0 for the whole run.  On a single run measuring a
                    # ~0.01 CSI effect that confound is larger than the effect.
                    # Leaving both hooks at None keeps R0/R1/R2 on one common
                    # random-number stream; `a` and tau are still independent,
                    # because the base draw is already uniform.
                    couples_flow_time = (
                        rmlf_controller.config.coupling_mode != "independent"
                    )
                    if couples_flow_time and torch.any(active_mask):
                        # Clean-anchor samples keep a uniform Flow-time draw and
                        # equal lead reduction, taken from RMLF's own stream.
                        clean_t = torch.randint(
                            1,
                            num_train_timesteps,
                            (inputs.shape[0],),
                            device=inputs.device,
                            dtype=torch.long,
                            generator=rmlf_controller.generator(
                                inputs.device, "clean_t"
                            ),
                        )
                        t_override = torch.where(
                            active_mask, plan.target_t, clean_t
                        )
                        clean_weights = torch.ones_like(plan.lead_weights)
                        lead_weights = torch.where(
                            active_mask[:, None], plan.lead_weights, clean_weights
                        )

                    accepted_requested = built.bridge_accepted[requested_mask]
                    effective_corruption = (
                        torch.ones_like(plan.corruption)
                        if rmlf_controller.config.condition_mode == "self_forcing"
                        else plan.corruption
                    )
                    focus_mask = active_mask & (plan.focus_lead >= 0)
                    rmlf_records.append(
                        {
                            "requested_fraction": float(requested_mask.float().mean()),
                            "rollout_fraction": float(active_mask.float().mean()),
                            "gate_acceptance": float(
                                accepted_requested.float().mean()
                            ),
                            "relative_l2": float(
                                built.relative_l2[requested_mask].float().mean()
                            ),
                            "corruption": (
                                float(
                                    effective_corruption[active_mask]
                                    .float()
                                    .mean()
                                )
                                if torch.any(active_mask)
                                else 0.0
                            ),
                            # -1 = the plan's Flow time was NOT applied, i.e.
                            # `independent` coupling left the base RF draw in
                            # place.  Logging the unused plan value here would
                            # suggest the run reweighted tau when it did not.
                            "target_tau": (
                                float(
                                    plan.target_t[active_mask].float().mean()
                                    / float(num_train_timesteps - 1)
                                )
                                if (couples_flow_time and torch.any(active_mask))
                                else -1.0
                            ),
                            "focus_lead": (
                                float(
                                    plan.focus_lead[focus_mask].float().mean()
                                    + 1.0
                                )
                                if (couples_flow_time and torch.any(focus_mask))
                                else 0.0
                            ),
                        }
                    )
                else:
                    # No teacher forward and no base-RF RNG consumption on a
                    # clean warm-up/mixing batch.
                    rmlf_records.append(
                        {
                            "requested_fraction": 0.0,
                            "rollout_fraction": 0.0,
                            "gate_acceptance": 1.0,
                            "relative_l2": 0.0,
                            "corruption": 0.0,
                            "target_tau": 0.0,
                            "focus_lead": 0.0,
                        }
                    )

        t_seq = torch.full(
            (inputs.shape[0],),
            chunk_idx + 1,
            dtype=torch.long,
            device=inputs.device,
        )
        chunk_loss, uot_stat = rflow_training_loss(
            model=model_forward,
            x_start=target_chunk,
            cond=cond,
            t_seq=t_seq,
            num_train_timesteps=num_train_timesteps,
            decode_fn=decode_fn,
            uot_loss=uot_loss,
            uot_params=uot_params,
            t_override=t_override,
            lead_weights=lead_weights,
        )
        loss = loss + chunk_loss
        if uot_stat is not None:
            uot_stats.append(uot_stat)
        previous_training_condition = cond.detach()

    mean_uot = sum(uot_stats) / len(uot_stats) if uot_stats else None
    if rmlf_records:
        keys = rmlf_records[0].keys()
        rmlf_stats = {
            f"rmlf_{key}": sum(record[key] for record in rmlf_records)
            / len(rmlf_records)
            for key in keys
        }
    else:
        rmlf_stats = None

    result = (loss / num_chunks, mean_uot)
    if return_rmlf_stats:
        return result[0], result[1], rmlf_stats
    return result
