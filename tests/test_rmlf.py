"""Unit tests for Rollout-Matched Lead--Flow Coupling.

Run from the repository root:
    python tests/test_rmlf.py
"""

from __future__ import annotations

import copy
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.rflow_objective import rflow_training_loss
from common.models.flowcast.chunked_training import compute_chunked_rflow_loss
from common.models.flowcast.rmlf import (
    RMLFConfig,
    RMLFController,
    build_joint_from_surface,
    freeze_module,
    iterative_proportional_fitting,
    interaction_residual,
    log_loss_ratio,
    parameter_fingerprint,
    relative_l2_per_sample,
    sample_rollout_bridge,
)
from common.models.flowcast.schedule import build_sampling_timesteps


torch.manual_seed(0)
np.random.seed(0)


class PerfectBridgeModel(nn.Module):
    """Analytic rectified-flow model when ``cond`` equals the target chunk."""

    def __init__(self, num_train_timesteps: int):
        super().__init__()
        self.num_train_timesteps = num_train_timesteps
        self.dummy = nn.Parameter(torch.zeros(()))

    def forward(self, z, t, cond, t_seq):
        del t_seq
        tau = t.to(dtype=z.dtype) / float(self.num_train_timesteps - 1)
        tau = tau.view(z.shape[0], *([1] * (z.ndim - 1))).clamp_min(1e-8)
        return (cond - z) / tau + self.dummy * 0.0


class ZeroModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.scale = nn.Parameter(torch.zeros(()))

    def forward(self, x_t, t, cond, t_seq):
        del t, cond, t_seq
        return torch.zeros_like(x_t) + self.scale * 0.0


class RecordingZeroModel(ZeroModel):
    def __init__(self):
        super().__init__()
        self.conditions = []
        self.timesteps = []
        self.chunk_indices = []

    def forward(self, x_t, t, cond, t_seq):
        self.conditions.append(cond.detach().clone())
        self.timesteps.append(t.detach().clone())
        self.chunk_indices.append(t_seq.detach().clone())
        return torch.zeros_like(x_t) + self.scale * 0.0


class VelocityProbe(nn.Module):
    """Deterministic velocity field that records the Euler grid it walked.

    Any disagreement between the bridge grid and the deployment grid shows up
    twice: in `seen_timesteps` and in the integrated output.
    """

    def __init__(self):
        super().__init__()
        self.scale = nn.Parameter(torch.zeros(()))
        self.seen_timesteps = []

    def forward(self, z, t, cond, t_seq):
        del t_seq
        self.seen_timesteps.append(int(t.reshape(-1)[0].item()))
        t_norm = t.to(dtype=z.dtype).view(z.shape[0], *([1] * (z.ndim - 1)))
        return 0.1 * (cond - z) + 1e-4 * t_norm + self.scale * 0.0


class IdentityNormalizer:
    @staticmethod
    def normalize(x):
        return x


def test_bridge_endpoints_and_no_grad():
    n = 101
    model = PerfectBridgeModel(n)
    target = torch.randn(4, 3, 5, 5, 2)
    noise = torch.randn_like(target)

    clean = sample_rollout_bridge(
        model=model,
        x_start=target,
        cond=target,
        chunk_idx=1,
        corruption=torch.zeros(4),
        num_train_timesteps=n,
        euler_steps=4,
        noise=noise,
    )
    assert torch.equal(clean, target)

    bridged = sample_rollout_bridge(
        model=model,
        x_start=target,
        cond=target,
        chunk_idx=1,
        corruption=torch.tensor([0.2, 0.4, 0.7, 1.0]),
        num_train_timesteps=n,
        euler_steps=5,
        noise=noise,
    )
    assert torch.allclose(bridged, target, atol=2e-5, rtol=2e-5)
    assert not bridged.requires_grad
    assert all(p.grad is None for p in model.parameters())
    print("PASS bridge endpoints, arbitrary starts, and stop-gradient")


def test_independent_plan_bounds_and_lead_normalization():
    cfg = RMLFConfig(
        enabled=True,
        coupling_mode="independent",
        corruption_min=0.2,
        corruption_max=0.6,
        lead_power=2.0,
    )
    controller = RMLFController(cfg)
    plan = controller.sample_plan(
        batch_size=64,
        chunk_index=2,
        chunk_length=5,
        num_train_timesteps=1000,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    assert torch.all((plan.corruption >= 0.2) & (plan.corruption <= 0.6))
    assert torch.all((plan.target_t >= 1) & (plan.target_t <= 999))
    assert torch.allclose(plan.lead_weights.mean(dim=1), torch.ones(64))
    assert torch.all(plan.lead_weights[:, -1] > plan.lead_weights[:, 0])
    assert torch.all(plan.focus_lead == -1)
    print("PASS independent plan bounds and normalized late-lead weighting")


def test_diagonal_coupling_is_correlated():
    cfg = RMLFConfig(
        enabled=True,
        coupling_mode="diagonal",
        coupling_strength=0.95,
        diagonal_direction="same",
        corruption_min=0.0,
        corruption_max=1.0,
    )
    controller = RMLFController(cfg)
    plan = controller.sample_plan(
        batch_size=4096,
        chunk_index=2,
        chunk_length=5,
        num_train_timesteps=1000,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    tau = plan.target_t.float() / 999.0
    corr = torch.corrcoef(torch.stack([plan.corruption, tau]))[0, 1]
    assert float(corr) > 0.9, corr
    print(f"PASS diagonal plan correlation ({float(corr):.3f})")


def test_amplification_table_sampling_and_focus_weights():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "table.npz"
        amp = np.zeros((1, 5, 3, 4), dtype=np.float32)
        amp[0, 4, 2, 3] = 1.0e6
        np.savez(
            path,
            interaction_signed_score=amp,
            interaction_gated=amp,
            interaction=amp,
            amplification=amp,
            a_centers=np.array([0.1, 0.4, 0.8], dtype=np.float32),
            tau_centers=np.array([0.1, 0.3, 0.6, 0.9], dtype=np.float32),
            source_checkpoint_sha256=np.asarray(["deadbeef"]),
            source_weight_key=np.asarray(["model_state_dict"]),
            bridge_steps=np.asarray(["10"]),
            sampler_surface_key=np.asarray(["interaction"]),
            sampler_temperature=np.asarray([repr(1.0)]),
            sampler_marginal_mode=np.asarray(["raw"]),
        )
        # `raw` is the ablation whose sampler follows the surface directly,
        # so it is the mode where a single hot cell should dominate.  The
        # default `matched` mode deliberately does NOT concentrate -- see T21.
        cfg = RMLFConfig(
            enabled=True,
            coupling_mode="amplification_table",
            marginal_mode="raw",
            amplification_key="interaction",
            amplification_table=str(path),
            amplification_floor=1e-12,
            focus_lead_mass=0.8,
        )
        # The default surface is the gated SIGNED score, not raw amplification:
        # R3 must be reproducible neither by hard-timestep oversampling nor by
        # finite-sample noise.
        assert RMLFConfig().amplification_key == "interaction_signed_score"
        assert RMLFConfig().marginal_mode == "matched"
        controller = RMLFController(cfg)
        plan = controller.sample_plan(
            batch_size=512,
            chunk_index=2,
            chunk_length=5,
            num_train_timesteps=1000,
            device=torch.device("cpu"),
            dtype=torch.float32,
        )
        assert float((plan.focus_lead == 4).float().mean()) > 0.99
        assert float((plan.corruption == 0.8).float().mean()) > 0.99
        assert float((plan.target_t == round(0.9 * 999)).float().mean()) > 0.99
        assert torch.allclose(plan.lead_weights.mean(dim=1), torch.ones(512))
        assert torch.all(plan.lead_weights[:, 4] > plan.lead_weights[:, 0])

        # The table is bound to the checkpoint it was measured on.
        controller.verify_table_provenance("deadbeef")
        try:
            controller.verify_table_provenance("cafebabe")
        except ValueError as exc:
            assert "DIFFERENT checkpoint" in str(exc)
        else:
            raise AssertionError("mismatched table provenance was accepted")
    print("PASS amplification-table joint sampling and focused lead weights")


def test_controller_rng_state_roundtrip():
    cfg = RMLFConfig(
        enabled=True, coupling_mode="independent", random_seed=1234
    )
    first = RMLFController(cfg)
    _ = first.sample_plan(
        batch_size=7,
        chunk_index=2,
        chunk_length=5,
        num_train_timesteps=1000,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    _ = first.sample_rollout_mask(
        7, global_step=10_000, device=torch.device("cpu")
    )
    _ = torch.randn(
        (3, 4), generator=first.generator(torch.device("cpu"), "bridge")
    )
    _ = torch.randint(
        1,
        1000,
        (7,),
        generator=first.generator(torch.device("cpu"), "clean_t"),
    )
    state = first.state_dict()
    expected = first.sample_plan(
        batch_size=7,
        chunk_index=2,
        chunk_length=5,
        num_train_timesteps=1000,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    expected_mask = first.sample_rollout_mask(
        7, global_step=10_000, device=torch.device("cpu")
    )
    expected_bridge = torch.randn(
        (3, 4), generator=first.generator(torch.device("cpu"), "bridge")
    )
    expected_clean_t = torch.randint(
        1,
        1000,
        (7,),
        generator=first.generator(torch.device("cpu"), "clean_t"),
    )

    resumed = RMLFController(cfg)
    resumed.load_state_dict(state)
    got = resumed.sample_plan(
        batch_size=7,
        chunk_index=2,
        chunk_length=5,
        num_train_timesteps=1000,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    got_mask = resumed.sample_rollout_mask(
        7, global_step=10_000, device=torch.device("cpu")
    )
    got_bridge = torch.randn(
        (3, 4), generator=resumed.generator(torch.device("cpu"), "bridge")
    )
    got_clean_t = torch.randint(
        1,
        1000,
        (7,),
        generator=resumed.generator(torch.device("cpu"), "clean_t"),
    )
    assert torch.equal(got.corruption, expected.corruption)
    assert torch.equal(got.target_t, expected.target_t)
    assert torch.equal(got.lead_weights, expected.lead_weights)
    assert torch.equal(got_mask, expected_mask)
    assert torch.equal(got_bridge, expected_bridge)
    assert torch.equal(got_clean_t, expected_clean_t)
    print("PASS RMLF RNG state roundtrip")


def test_rng_streams_isolate_ablation_draws():
    cfg = RMLFConfig(enabled=True, random_seed=2026)
    reference = RMLFController(cfg)
    expected_mask = reference.sample_rollout_mask(
        32, global_step=10_000, device=torch.device("cpu")
    )
    expected_bridge = torch.randn(
        (2, 2, 2), generator=reference.generator(torch.device("cpu"), "bridge")
    )

    perturbed = RMLFController(cfg)
    # Consume a different number of plan draws.  Mask and bridge-noise streams
    # must stay identical so R1/R2/R3 comparisons do not gain an RNG confound.
    _ = perturbed.sample_plan(
        batch_size=257,
        chunk_index=2,
        chunk_length=5,
        num_train_timesteps=1000,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    got_mask = perturbed.sample_rollout_mask(
        32, global_step=10_000, device=torch.device("cpu")
    )
    got_bridge = torch.randn(
        (2, 2, 2), generator=perturbed.generator(torch.device("cpu"), "bridge")
    )
    assert torch.equal(got_mask, expected_mask)
    assert torch.equal(got_bridge, expected_bridge)
    print("PASS independent RMLF RNG streams isolate ablation draws")


def test_rollout_probability_warmup_and_batch_mask():
    cfg = RMLFConfig(
        enabled=True,
        rollout_probability=0.8,
        warmup_steps=100,
        mix_granularity="batch",
    )
    controller = RMLFController(cfg)
    assert controller.effective_rollout_probability(0) == 0.0
    assert abs(controller.effective_rollout_probability(50) - 0.4) < 1e-8
    assert abs(controller.effective_rollout_probability(100) - 0.8) < 1e-8
    for _ in range(20):
        mask = controller.sample_rollout_mask(
            8, global_step=50, device=torch.device("cpu")
        )
        assert bool(mask.all()) or bool((~mask).all())
    print("PASS rollout warmup and batch-granularity mixing")


def test_latent_gate_falls_back_to_clean_condition():
    n = 101
    cfg = RMLFConfig(
        enabled=True,
        rollout_probability=1.0,
        condition_mode="bridge",
        max_relative_l2=0.05,
        bridge_euler_steps=1,
    )
    controller = RMLFController(cfg)
    teacher = ZeroModel()
    clean = torch.ones(3, 2, 4, 4, 1)
    cond = torch.zeros_like(clean)
    result = controller.build_condition(
        teacher_model=teacher,
        clean_previous_chunk=clean,
        teacher_condition=cond,
        generated_chunk_index=1,
        corruption=torch.full((3,), 0.8),
        rollout_mask=torch.ones(3, dtype=torch.bool),
        num_train_timesteps=n,
        noise=torch.zeros_like(clean),
    )
    assert not result.rollout_mask.any()
    assert torch.equal(result.condition, clean)
    assert torch.all(result.relative_l2 > 0.05)
    print("PASS conservative latent gate rejects out-of-basin bridge")


def test_rflow_default_path_is_unchanged():
    model = ZeroModel()
    x_start = torch.randn(3, 4, 3, 3, 2)
    cond = torch.randn_like(x_start)
    t_seq = torch.ones(3, dtype=torch.long)

    torch.manual_seed(77)
    got, _ = rflow_training_loss(
        model, x_start, cond, t_seq, num_train_timesteps=50
    )

    torch.manual_seed(77)
    noise = torch.randn_like(x_start)
    t = torch.randint(1, 50, (3,), dtype=torch.long)
    tau = (t.float() / 49.0).view(3, 1, 1, 1, 1)
    x_t = tau * noise + (1.0 - tau) * x_start
    velocity = model(x_t, t, cond, t_seq)
    expected = ((velocity - (x_start - noise)) ** 2).mean()
    reconstruction = x_t + velocity * tau
    expected = expected + ((reconstruction - x_start) ** 2).mean()
    assert torch.allclose(got, expected, atol=1e-7), (got, expected)
    print("PASS RMLF hooks leave the default RF objective unchanged")


def test_t_override_and_lead_weights_select_requested_region():
    model = ZeroModel()
    x_start = torch.zeros(2, 3, 1, 1, 1)
    # Make only the final lead non-zero so lead weighting has a deterministic
    # and easily checked effect.
    x_start[:, 2] = 4.0
    cond = torch.zeros_like(x_start)
    t_seq = torch.ones(2, dtype=torch.long)
    noise = torch.zeros_like(x_start)
    t = torch.tensor([25, 25], dtype=torch.long)

    uniform, _ = rflow_training_loss(
        model,
        x_start,
        cond,
        t_seq,
        101,
        t_override=t,
        noise_override=noise,
        lead_weights=torch.ones(2, 3),
    )
    final_only, _ = rflow_training_loss(
        model,
        x_start,
        cond,
        t_seq,
        101,
        t_override=t,
        noise_override=noise,
        lead_weights=torch.tensor([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
    )
    assert final_only > uniform * 2.9, (uniform.item(), final_only.item())
    print("PASS explicit Flow-time and lead-focused RF reduction")


def test_chunked_warmup_zero_is_exact_teacher_forcing():
    inputs = torch.randn(2, 2, 3, 3, 1)
    outputs = torch.randn(2, 4, 3, 3, 1)

    base_model = RecordingZeroModel()
    torch.manual_seed(991)
    base_loss, _, base_stats = compute_chunked_rflow_loss(
        model_forward=base_model,
        normalizer_model=IdentityNormalizer(),
        inputs=inputs,
        outputs=outputs,
        input_length=2,
        output_length=4,
        num_train_timesteps=101,
        return_rmlf_stats=True,
    )

    cfg = RMLFConfig(
        enabled=True, rollout_probability=0.8, warmup_steps=100, random_seed=7
    )
    controller = RMLFController(cfg)
    rmlf_model = RecordingZeroModel()
    torch.manual_seed(991)
    rmlf_loss, _, stats = compute_chunked_rflow_loss(
        model_forward=rmlf_model,
        normalizer_model=IdentityNormalizer(),
        inputs=inputs,
        outputs=outputs,
        input_length=2,
        output_length=4,
        num_train_timesteps=101,
        rmlf_controller=controller,
        rmlf_teacher=ZeroModel(),
        global_step=0,
        return_rmlf_stats=True,
    )
    assert base_stats is None
    assert stats["rmlf_rollout_fraction"] == 0.0
    assert torch.equal(base_loss, rmlf_loss)
    assert len(base_model.conditions) == len(rmlf_model.conditions) == 2
    assert torch.equal(rmlf_model.conditions[0], inputs)
    assert torch.equal(rmlf_model.conditions[1], outputs[:, :2])
    assert all(
        torch.equal(a, b)
        for a, b in zip(base_model.timesteps, rmlf_model.timesteps)
    )
    print("PASS zero-warmup RMLF is exact teacher forcing with unchanged RF RNG")


def test_chunked_bridge_changes_only_later_condition():
    inputs = torch.randn(2, 2, 3, 3, 1)
    outputs = torch.randn(2, 4, 3, 3, 1)
    cfg = RMLFConfig(
        enabled=True,
        condition_mode="bridge",
        rollout_probability=1.0,
        corruption_min=0.5,
        corruption_max=0.5,
        bridge_euler_steps=2,
        coupling_mode="independent",
        random_seed=13,
    )
    controller = RMLFController(cfg)
    model = RecordingZeroModel()
    loss, _, stats = compute_chunked_rflow_loss(
        model_forward=model,
        normalizer_model=IdentityNormalizer(),
        inputs=inputs,
        outputs=outputs,
        input_length=2,
        output_length=4,
        num_train_timesteps=101,
        rmlf_controller=controller,
        rmlf_teacher=ZeroModel(),
        global_step=100,
        return_rmlf_stats=True,
    )
    assert torch.isfinite(loss)
    assert len(model.conditions) == 2
    assert torch.equal(model.conditions[0], inputs)
    assert not torch.equal(model.conditions[1], outputs[:, :2])
    assert stats["rmlf_rollout_fraction"] == 1.0
    assert abs(stats["rmlf_corruption"] - 0.5) < 1e-6
    assert stats["rmlf_relative_l2"] > 0.0
    print("PASS bridge modifies only the later chunk condition and reports diagnostics")


def test_relative_l2_is_scale_stabilized():
    ref = torch.zeros(2, 3, 2, 2, 1)
    cand = ref.clone()
    cand[0] += 0.1
    cand[1] += 0.2
    score = relative_l2_per_sample(cand, ref, floor=0.1)
    assert torch.allclose(score, torch.tensor([1.0, 2.0]), atol=1e-6)
    print("PASS scale-stabilized relative L2 diagnostics")


# --------------------------------------------------------------------------
# T14-T17: added when the reference implementation was merged into the live
# repository.  Each one guards a claim that the R0-R3 ablation depends on.
# --------------------------------------------------------------------------


def test_bridge_at_a_one_equals_deployment_sampler():
    """T14: R1's condition IS the deployment condition, not a coarser proxy.

    If the bridge solved on its own grid, R1 would carry extra solver error and
    be beaten by R2 for a reason unrelated to scenario preservation.
    """
    from common.models.flowcast.rf_stdit import sample_chunk_euler

    num_train_timesteps = 1000
    euler_steps = 10
    torch.manual_seed(11)
    model = VelocityProbe()
    cond = torch.randn(3, 4, 5, 5, 2)
    noise = torch.randn_like(cond)

    # sample_chunk_euler draws z ~ N(0, I) internally from `generator`; drive
    # both paths from one generator state so the initial states coincide.
    generator = torch.Generator().manual_seed(4242)
    reference = sample_chunk_euler(
        model=model,
        cond=cond,
        chunk_idx=1,
        num_train_timesteps=num_train_timesteps,
        euler_steps=euler_steps,
        generator=generator,
    )
    deployment_grid = list(model.seen_timesteps)
    model.seen_timesteps = []

    replay = torch.Generator().manual_seed(4242)
    same_noise = torch.randn(cond.shape, generator=replay, dtype=cond.dtype)

    bridged = sample_rollout_bridge(
        model=model,
        x_start=torch.randn_like(cond),  # irrelevant at a=1
        cond=cond,
        chunk_idx=1,
        corruption=torch.ones(cond.shape[0]),
        num_train_timesteps=num_train_timesteps,
        euler_steps=euler_steps,
        noise=same_noise,
    )
    assert torch.allclose(reference, bridged, atol=0.0, rtol=0.0), (
        (reference - bridged).abs().max().item()
    )

    # ...and the grid the bridge walked really is the deployment grid.
    grid = build_sampling_timesteps(num_train_timesteps, euler_steps, cond.device)
    expected_grid = [int(v) for v in grid[:-1].tolist()]
    assert deployment_grid == expected_grid, deployment_grid
    assert model.seen_timesteps == expected_grid, model.seen_timesteps
    print("PASS T14 a=1 bridge reproduces the deployment Euler sampler exactly")


def test_log_ratio_is_invariant_to_flow_time_rescaling():
    """T15: the R3 statistic cannot be manufactured by a per-tau scale."""
    rng = np.random.default_rng(7)
    clean = rng.uniform(0.05, 2.0, size=(2, 5, 4, 6))
    bridge = clean * rng.uniform(1.0, 2.5, size=clean.shape)

    # An arbitrary Flow-time-only rescaling, e.g. the fact that velocity
    # regression is simply harder near pure noise.
    scale = rng.uniform(0.5, 40.0, size=(1, 1, 1, clean.shape[-1]))
    base = log_loss_ratio(bridge, clean, eps=0.0)
    scaled = log_loss_ratio(bridge * scale, clean * scale, eps=0.0)
    assert np.allclose(base, scaled, atol=1e-12)

    counts = np.full(clean.shape, 8, dtype=np.int64)
    assert np.allclose(
        interaction_residual(base, counts),
        interaction_residual(scaled, counts),
        atol=1e-12,
    )

    # The naive difference is NOT invariant -- this is the confound itself.
    naive = (bridge - clean).mean()
    naive_scaled = (bridge * scale - clean * scale).mean()
    assert not np.isclose(naive, naive_scaled, rtol=1e-3)
    print("PASS T15 log-ratio and interaction are invariant to per-tau rescaling")


def test_additive_surface_has_zero_interaction():
    """T16: 'corruption hurts' + 'high tau hurts' alone yields no coupling."""
    rng = np.random.default_rng(19)
    n_a, n_tau = 5, 7
    f_a = rng.uniform(-1.0, 1.0, size=(n_a, 1))
    g_tau = np.linspace(0.0, 3.0, n_tau).reshape(1, n_tau)
    additive = f_a + g_tau

    # The estimator visits every (a, tau) cell for every event, so the real
    # design is balanced; that is the case the annihilation property is
    # claimed for.
    counts = np.full((3, 4, n_a, n_tau), 37, dtype=np.int64)
    surface = np.broadcast_to(additive, counts.shape).copy()
    residual = interaction_residual(surface, counts)
    assert np.abs(residual).max() < 1e-10, np.abs(residual).max()
    # Unweighted reduction must agree with the balanced count-weighted one.
    assert np.allclose(residual, interaction_residual(surface), atol=1e-12)

    # A genuine interaction survives the same reduction.
    surface[..., -1, -1] += 5.0
    residual = interaction_residual(surface, counts)
    assert residual[..., -1, -1].min() > 1.0

    # Ragged counts stay finite and leave the empty cells at exactly zero, but
    # annihilation is only exact under balance -- documented, not silent.
    ragged = counts.copy()
    ragged[..., 0, 0] = 0
    ragged_residual = interaction_residual(
        np.broadcast_to(additive, counts.shape).copy(), ragged
    )
    assert np.all(np.isfinite(ragged_residual))
    assert np.all(ragged_residual[..., 0, 0] == 0.0)
    print("PASS T16 additive surfaces leave zero interaction residual")


def test_frozen_teacher_does_not_drift():
    """T17: the rollout teacher is immutable across student updates."""
    from common.utils.utils import ema

    torch.manual_seed(23)
    student = nn.Linear(6, 6)
    teacher = freeze_module(copy.deepcopy(student))
    eval_ema = copy.deepcopy(student)

    before = parameter_fingerprint(teacher)
    assert all(not p.requires_grad for p in teacher.parameters())
    assert not teacher.training

    optimizer = torch.optim.SGD(student.parameters(), lr=0.5)
    for _ in range(5):
        loss = student(torch.randn(4, 6)).pow(2).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        # The EVALUATION ema tracks the student; the teacher must not.
        ema(student, eval_ema, 0.999)

    assert parameter_fingerprint(teacher) == before
    assert parameter_fingerprint(eval_ema) != before
    assert parameter_fingerprint(student) != before
    print("PASS T17 frozen rollout teacher does not drift with the student")



def test_r0_matches_the_pre_merge_implementation_bitwise():
    """T18: R0 is the untouched control, verified against the ORIGINAL code.

    `_original_chunked_rflow_loss` below is a verbatim copy of the pre-merge
    `compute_chunked_rflow_loss` + `rflow_training_loss` pair (trainer and
    rf_stdit respectively).  Loss, gradients and the global RNG state must all
    match, or every R1/R2/R3 comparison is against a moved baseline.
    """
    from common.models.flowcast.schedule import make_chunk_index

    def _original_rflow_training_loss(
        model, x_start, cond, t_seq, num_train_timesteps
    ):
        batch_size = x_start.shape[0]
        device = x_start.device
        noise = torch.randn_like(x_start, device=device)
        t = torch.randint(
            1, num_train_timesteps, (batch_size,), device=device, dtype=torch.long
        )
        t_norm = t.to(dtype=x_start.dtype) / float(num_train_timesteps - 1)
        t_norm = t_norm.view(batch_size, 1, 1, 1, 1)
        x_t = t_norm * noise + (1.0 - t_norm) * x_start
        velocity = model(x_t, t, cond, t_seq)
        residual_target = x_start - noise
        loss = torch.mean((velocity - residual_target) ** 2)
        reconstruction = x_t + velocity * t_norm
        return loss + torch.mean((reconstruction - x_start) ** 2)

    def _original_chunked_rflow_loss(
        model_forward, normalizer_model, inputs, outputs,
        input_length, output_length, num_train_timesteps,
    ):
        normalized_inputs = normalizer_model.normalize(inputs)
        normalized_outputs = normalizer_model.normalize(outputs)
        num_chunks = output_length // input_length
        loss = normalized_outputs.new_tensor(0.0)
        for chunk_idx in range(num_chunks):
            start = chunk_idx * input_length
            end = (chunk_idx + 1) * input_length
            target_chunk = normalized_outputs[:, start:end]
            if chunk_idx == 0:
                cond = normalized_inputs
            else:
                cond = normalized_outputs[:, start - input_length : start]
            t_seq = make_chunk_index(inputs.shape[0], chunk_idx + 1, inputs.device)
            loss = loss + _original_rflow_training_loss(
                model=model_forward, x_start=target_chunk, cond=cond,
                t_seq=t_seq, num_train_timesteps=num_train_timesteps,
            )
        return loss / num_chunks

    class TinyNet(nn.Module):
        def __init__(self, channels):
            super().__init__()
            self.lin = nn.Linear(channels, channels)
            self.emb = nn.Embedding(1000, channels)
            self.chunk = nn.Embedding(8, channels)

        def forward(self, x_t, t, cond, t_seq):
            h = self.lin(x_t) + 0.3 * cond
            h = h + self.emb(t).view(x_t.shape[0], 1, 1, 1, -1)
            h = h + self.chunk(t_seq).view(x_t.shape[0], 1, 1, 1, -1)
            return torch.tanh(h)

    def _run(loss_fn, **kwargs):
        torch.manual_seed(20260802)
        model = TinyNet(3)
        torch.manual_seed(777)
        inputs = torch.randn(2, 5, 4, 4, 3)
        outputs = torch.randn(2, 10, 4, 4, 3)
        torch.manual_seed(99)  # the RF noise / timestep stream
        result = loss_fn(
            model_forward=model, normalizer_model=IdentityNormalizer(),
            inputs=inputs, outputs=outputs, input_length=5, output_length=10,
            num_train_timesteps=1000, **kwargs
        )
        loss = result[0] if isinstance(result, tuple) else result
        loss.backward()
        grad = torch.cat([p.grad.reshape(-1) for p in model.parameters()])
        return loss.detach().clone(), grad, torch.get_rng_state()

    original = _run(_original_chunked_rflow_loss)
    merged = _run(compute_chunked_rflow_loss, rmlf_controller=None)
    disabled = _run(
        compute_chunked_rflow_loss,
        rmlf_controller=RMLFController(RMLFConfig(enabled=False)),
    )
    for label, candidate in (("rmlf_controller=None", merged), ("enabled=false", disabled)):
        assert torch.equal(original[0], candidate[0]), (label, original[0], candidate[0])
        assert torch.equal(original[1], candidate[1]), label
        assert torch.equal(original[2], candidate[2]), f"{label}: global RNG diverged"
    print("PASS T18 R0 is bitwise identical to the pre-merge implementation")



def test_r0_matches_pre_merge_with_uot_enabled():
    """T19: R0 is the control for the *UOT* recipe, not just for plain RF.

    The arm configs run `uot_params.enabled: true`, so T18 alone would only
    lock the no-UOT branch.  This repeats the comparison with a deterministic
    decode stub and a deterministic UOT stub so the whole augmented objective
    -- including the t_weight ramp and the dry-frame replacement -- is
    covered.
    """

    class DeterministicUOT:
        """Stands in for the Sinkhorn loss with an exactly reproducible value."""

        @staticmethod
        def sequence(mass_pred, mass_true, reduce=False):
            assert reduce is False
            return (mass_pred - mass_true).abs().sum(dim=(2, 3)) + 0.5 * (
                mass_pred.sum(dim=(2, 3)) - mass_true.sum(dim=(2, 3))
            ).abs()

    def decode_fn(latent):
        # channel-last (B, T, H, W, C) -> pixel (B, T, H, W)
        return latent.mean(dim=-1) * 30.0 + 5.0

    uot_params = {
        "weight": 0.01,
        "t_power": 1.0,
        "normalize_by_mass": False,
        "value_scale_ref": 7.5,
        "dry_frame_mass": 1e-3,
        # The transform the CIKM arms actually run.
        "mass_kwargs": {
            "transform": "zr_dbz",
            "low_threshold": 0.5,
            "threshold_mode": "soft",
            "threshold_softness": 1.0,
            "zero_point": 0.0,
            "gamma": 1.0,
            "mass_scale": 10.0,
        },
    }

    from common.losses.uot import mass_from_field

    def original_objective(model, x_start, cond, t_seq, num_train_timesteps):
        """Verbatim pre-merge rflow_training_loss, UOT branch included."""
        batch_size = x_start.shape[0]
        device = x_start.device
        noise = torch.randn_like(x_start, device=device)
        t = torch.randint(
            1, num_train_timesteps, (batch_size,), device=device, dtype=torch.long
        )
        t_norm = t.to(dtype=x_start.dtype) / float(num_train_timesteps - 1)
        t_norm = t_norm.view(batch_size, 1, 1, 1, 1)
        x_t = t_norm * noise + (1.0 - t_norm) * x_start
        velocity = model(x_t, t, cond, t_seq)
        residual_target = x_start - noise
        loss = torch.mean((velocity - residual_target) ** 2)
        reconstruction = x_t + velocity * t_norm
        loss = loss + torch.mean((reconstruction - x_start) ** 2)

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
            per_frame = DeterministicUOT.sequence(mass_pred, mass_true, reduce=False)
            true_frame_mass = mass_true.sum(dim=(2, 3)).detach()
            dry = true_frame_mass < float(uot_params["dry_frame_mass"])
            if torch.any(dry):
                per_frame = torch.where(dry, mass_pred.sum(dim=(2, 3)), per_frame)
            uot_val = per_frame.mean(dim=1)
            uot_val = uot_val / float(uot_params["value_scale_ref"])
        t_weight = (1.0 - t_norm.reshape(-1)) ** float(uot_params["t_power"])
        uot_term = float(uot_params["weight"]) * t_weight * uot_val
        loss = loss + uot_term.mean()
        return loss, float(uot_term.detach().mean())

    def original_chunked(
        model_forward, normalizer_model, inputs, outputs,
        input_length, output_length, num_train_timesteps,
    ):
        from common.models.flowcast.schedule import make_chunk_index

        normalized_inputs = normalizer_model.normalize(inputs)
        normalized_outputs = normalizer_model.normalize(outputs)
        num_chunks = output_length // input_length
        loss = normalized_outputs.new_tensor(0.0)
        uot_stats = []
        for chunk_idx in range(num_chunks):
            start = chunk_idx * input_length
            target_chunk = normalized_outputs[:, start : start + input_length]
            if chunk_idx == 0:
                cond = normalized_inputs
            else:
                cond = normalized_outputs[:, start - input_length : start]
            t_seq = make_chunk_index(inputs.shape[0], chunk_idx + 1, inputs.device)
            chunk_loss, uot_stat = original_objective(
                model_forward, target_chunk, cond, t_seq, num_train_timesteps
            )
            loss = loss + chunk_loss
            if uot_stat is not None:
                uot_stats.append(uot_stat)
        return loss / num_chunks, sum(uot_stats) / len(uot_stats)

    class TinyNet(nn.Module):
        def __init__(self, channels):
            super().__init__()
            self.lin = nn.Linear(channels, channels)
            self.emb = nn.Embedding(1000, channels)

        def forward(self, x_t, t, cond, t_seq):
            del t_seq
            h = self.lin(x_t) + 0.2 * cond
            return torch.tanh(h + self.emb(t).view(x_t.shape[0], 1, 1, 1, -1))

    def _run(loss_fn, **kwargs):
        torch.manual_seed(4711)
        model = TinyNet(3)
        torch.manual_seed(31337)
        inputs = torch.randn(2, 5, 4, 4, 3)
        outputs = torch.randn(2, 10, 4, 4, 3)
        torch.manual_seed(2718)
        loss, uot = loss_fn(
            model_forward=model, normalizer_model=IdentityNormalizer(),
            inputs=inputs, outputs=outputs, input_length=5, output_length=10,
            num_train_timesteps=1000, **kwargs
        )
        loss.backward()
        grad = torch.cat([p.grad.reshape(-1) for p in model.parameters()])
        return loss.detach().clone(), uot, grad, torch.get_rng_state()

    original = _run(original_chunked)
    merged = _run(
        compute_chunked_rflow_loss,
        decode_fn=decode_fn,
        uot_loss=DeterministicUOT(),
        uot_params=uot_params,
        rmlf_controller=None,
    )
    assert original[1] is not None and original[1] != 0.0, "UOT branch never ran"
    assert torch.equal(original[0], merged[0]), (original[0], merged[0])
    assert original[1] == merged[1], (original[1], merged[1])
    assert torch.equal(original[2], merged[2]), "UOT-enabled gradients differ"
    assert torch.equal(original[3], merged[3]), "global RNG diverged"
    print(
        "PASS T19 R0 is bitwise identical to the pre-merge UOT-enabled objective"
    )



def test_independent_mode_shares_the_base_rf_random_stream():
    """T20: R0, R1 and R2 must see the SAME target noise and timesteps.

    `independent` coupling is defined as changing only the condition.  If it
    also drew the Flow time from an RMLF stream, the objective would stop
    consuming the base `torch.randint`, the global RNG would fork at the first
    rollout batch, and R1/R2 would differ from R0 in target noise for the rest
    of the run -- a confound larger than the ~0.01 CSI effect being measured.
    """

    class TimestepRecorder(nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner
            self.timesteps = []

        def forward(self, x_t, t, cond, t_seq):
            self.timesteps.append(t.detach().clone())
            return self.inner(x_t, t, cond, t_seq)

    def run(controller):
        torch.manual_seed(1234)
        teacher = ZeroModel()
        torch.manual_seed(4321)
        inputs = torch.randn(3, 5, 4, 4, 2)
        outputs = torch.randn(3, 10, 4, 4, 2)
        student = TimestepRecorder(ZeroModel())
        torch.manual_seed(2024)  # the base RF stream
        compute_chunked_rflow_loss(
            model_forward=student,
            normalizer_model=IdentityNormalizer(),
            inputs=inputs,
            outputs=outputs,
            input_length=5,
            output_length=10,
            num_train_timesteps=1000,
            rmlf_controller=controller,
            rmlf_teacher=teacher,
            global_step=10 ** 9,  # past any warmup
        )
        return student.timesteps, torch.get_rng_state()

    def controller(**kwargs):
        return RMLFController(
            RMLFConfig(
                enabled=True,
                coupling_mode="independent",
                rollout_probability=1.0,
                bridge_euler_steps=3,
                **kwargs,
            )
        )

    r0_t, r0_rng = run(None)
    r1_t, r1_rng = run(controller(condition_mode="self_forcing"))
    r2_t, r2_rng = run(controller(condition_mode="bridge"))

    assert len(r0_t) == 2, r0_t  # two chunks, student called once each
    for label, arm in (("R1", r1_t), ("R2", r2_t)):
        assert len(arm) == len(r0_t), (label, len(arm))
        for chunk, (a, b) in enumerate(zip(r0_t, arm)):
            assert torch.equal(a, b), (label, chunk, a, b)
    assert torch.equal(r0_rng, r1_rng), "R1 forked the global RNG"
    assert torch.equal(r0_rng, r2_rng), "R2 forked the global RNG"

    # ...while a coupling mode that is SUPPOSED to move tau still does.
    coupled = RMLFController(
        RMLFConfig(
            enabled=True,
            condition_mode="bridge",
            coupling_mode="diagonal",
            coupling_strength=1.0,
            rollout_probability=1.0,
            bridge_euler_steps=3,
        )
    )
    c_t, _ = run(coupled)
    assert not torch.equal(c_t[1], r0_t[1]), "diagonal coupling did not move tau"
    print("PASS T20 independent-mode RMLF shares R0's base RF random stream")



def _write_score_table(
    path,
    score,
    *,
    a_centers,
    tau_centers,
    surface_key="interaction_signed_score",
    temperature=1.0,
    marginal_mode="matched",
):
    np.savez(
        path,
        interaction_signed_score=np.asarray(score, dtype=np.float32),
        a_centers=np.asarray(a_centers, dtype=np.float32),
        tau_centers=np.asarray(tau_centers, dtype=np.float32),
        source_checkpoint_sha256=np.asarray(["sha"]),
        source_weight_key=np.asarray(["model_state_dict"]),
        bridge_steps=np.asarray(["10"]),
        sampler_surface_key=np.asarray([surface_key]),
        sampler_temperature=np.asarray([repr(float(temperature))]),
        sampler_marginal_mode=np.asarray([marginal_mode]),
        num_train_timesteps=np.asarray(["1000"]),
        precision_mode=np.asarray(["fp16_autocast"]),
    )


def _empirical_marginals(plan, chunk_length, a_centers, tau_centers):
    lead = np.bincount(plan.focus_lead.numpy(), minlength=chunk_length)
    a_idx = np.abs(
        plan.corruption.numpy()[:, None] - np.asarray(a_centers)[None, :]
    ).argmin(axis=1)
    tau = plan.target_t.numpy() / 999.0
    tau_idx = np.abs(tau[:, None] - np.asarray(tau_centers)[None, :]).argmin(axis=1)
    n = plan.focus_lead.numel()
    return (
        lead / n,
        np.bincount(a_idx, minlength=len(a_centers)) / n,
        np.bincount(tau_idx, minlength=len(tau_centers)) / n,
    )


def test_coupled_and_control_arms_share_every_marginal():
    """T21: R3 must differ from R2G in the COPULA and nothing else.

    A sampler built straight from a score surface changes the lead, corruption
    and Flow-time marginals all at once.  Then `R3 > R2G` would be explained by
    "trained more on hard leads / hard timesteps / hard corruption" -- ordinary
    hard-region curriculum, not coupling.  IPF pins all three marginals to the
    control's, leaving only the dependence structure free.
    """
    chunk_length, n_a, n_tau = 5, 5, 5
    a_centers = np.linspace(0.1, 0.7, n_a)
    tau_centers = np.linspace(0.1, 0.9, n_tau)
    rng = np.random.default_rng(5)
    # Big main effects AND a real interaction, i.e. the confounded case.
    score = (
        2.0 * rng.normal(size=(chunk_length, 1, 1))
        + 2.0 * rng.normal(size=(1, n_a, 1))
        + 2.0 * rng.normal(size=(1, 1, n_tau))
    )
    score[chunk_length - 1, n_a - 1, n_tau - 1] += 3.0
    score = score[None]

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "table.npz"
        _write_score_table(path, score, a_centers=a_centers, tau_centers=tau_centers)

        def draw(coupling, marginal_mode="matched", n=200_000):
            controller = RMLFController(
                RMLFConfig(
                    enabled=True,
                    coupling_mode=coupling,
                    marginal_mode=marginal_mode,
                    amplification_table=str(path),
                )
            )
            plan = controller.sample_plan(
                batch_size=n,
                chunk_index=2,
                chunk_length=chunk_length,
                num_train_timesteps=1000,
                device=torch.device("cpu"),
                dtype=torch.float32,
            )
            return _empirical_marginals(plan, chunk_length, a_centers, tau_centers)

        control = draw("grid_independent")
        coupled = draw("amplification_table")
        for axis, (c, k) in enumerate(zip(control, coupled)):
            assert np.abs(c - 1.0 / len(c)).max() < 0.01, (axis, c)
            assert np.abs(k - 1.0 / len(k)).max() < 0.01, (axis, k)

        # ...and the raw-marginal ablation really does move them, which is why
        # it cannot be the headline arm.
        raw = draw("amplification_table", marginal_mode="raw")
        assert max(np.abs(m - 1.0 / len(m)).max() for m in raw) > 0.1
    print("PASS T21 coupled and control arms share every marginal")


def test_additive_score_collapses_the_coupled_arm_onto_the_control():
    """T22: with no interaction, R3 IS R2G -- exactly, not approximately.

    This is the property that makes the claim falsifiable.  If the rollout
    penalty is additive in (lead, a, tau), the IPF joint is the uniform joint,
    so R3 samples identically to its own control and cannot win by
    construction.  Any observed R3 > R2G therefore has to come from
    non-additive structure.
    """
    chunk_length, n_a, n_tau = 4, 5, 6
    rng = np.random.default_rng(17)
    additive = (
        rng.normal(size=(chunk_length, 1, 1))
        + rng.normal(size=(1, n_a, 1))
        + rng.normal(size=(1, 1, n_tau))
    )
    joint = iterative_proportional_fitting(
        np.exp(additive),
        [np.ones(chunk_length), np.ones(n_a), np.ones(n_tau)],
    )
    uniform = 1.0 / (chunk_length * n_a * n_tau)
    assert np.abs(joint - uniform).max() < 1e-9, np.abs(joint - uniform).max()

    # A non-additive score must NOT collapse.
    interacting = additive.copy()
    interacting[0, 0, 0] += 2.0
    joint2 = iterative_proportional_fitting(
        np.exp(interacting),
        [np.ones(chunk_length), np.ones(n_a), np.ones(n_tau)],
    )
    assert np.abs(joint2 - uniform).max() > 1e-3
    print("PASS T22 an additive score collapses the coupled arm onto the control")



def test_strict_continuation_rejects_an_incomplete_parent():
    """T23: a parent missing ANY resumable field must stop the run.

    `global_step` is the one that used to slip through: it was read with a
    default of 0, so "absent" and "genuinely zero" were indistinguishable and
    the missing-field check could never see it.  R0 has no frozen teacher to
    catch it as a second line of defence, so a weights-only parent would have
    started an arm with a reset optimizer and a zeroed step counter while the
    log looked like a healthy continuation.
    """
    from common.utils.continuation import (
        REQUIRED_CONTINUATION_FIELDS,
        assert_strict_continuation,
        missing_continuation_fields,
    )

    complete = {
        "preload_model path": "/abs/parent.pt",
        "model_state_dict": {"w": 1},
        "optimizer_state_dict": {"state": {}},
        "scheduler_state_dict": {"last_epoch": 128},
        "epoch": 128,
        "global_step": 100000,
        "mean": 0.0,
        "std": 1.0,
    }
    assert set(complete) == set(REQUIRED_CONTINUATION_FIELDS)
    assert missing_continuation_fields(complete) == []
    assert_strict_continuation(complete, "/abs/parent.pt")

    # A genuine zero is a value, not an absence.
    zeroed = {**complete, "epoch": 0, "global_step": 0, "mean": 0.0}
    assert missing_continuation_fields(zeroed) == []

    for field in REQUIRED_CONTINUATION_FIELDS:
        broken = {**complete, field: None}
        assert missing_continuation_fields(broken) == [field], field
        try:
            assert_strict_continuation(broken, "/abs/parent.pt")
        except RuntimeError as exc:
            assert field in str(exc)
        else:
            raise AssertionError(f"missing {field!r} was accepted")

    # And the trainer really does read global_step without a 0 default.
    trainer = Path(__file__).resolve().parents[1] / (
        "experiments/sevir/runner/flowcast/dist_train_flowcast.py"
    )
    source = trainer.read_text()
    assert 'model_info.get("global_step", None)' in source
    assert 'model_info.get(\n                    "global_step", 0\n                )' not in source
    print("PASS T23 strict continuation rejects an incomplete parent")



def test_table_provenance_round_trip():
    """T24: estimator output -> controller load -> full provenance check.

    Every earlier provenance test built its own .npz by hand, so it could only
    ever exercise the fields the test author remembered.  That is exactly how
    `precision_mode` shipped broken: the estimator wrote it, the verifier
    demanded it, and the loader's whitelist silently dropped it in between --
    which would have made every R2G/R3 launch fail on a correctly generated
    table.  This test builds the payload from the estimator's OWN provenance
    key list and asserts the loader keeps all of it.
    """
    import ast

    from common.models.flowcast.rmlf import _TABLE_PROVENANCE_FIELDS

    # The estimator's `provenance = dict(...)` keys, read from its source so
    # the two lists cannot drift apart unnoticed.
    estimator = Path(__file__).resolve().parents[1] / (
        "tools/estimate_rmlf_amplification.py"
    )
    tree = ast.parse(estimator.read_text())
    written = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and getattr(node.targets[0], "id", None) == "provenance"
            and isinstance(node.value, ast.Call)
        ):
            written = {kw.arg for kw in node.value.keywords}
            break
    assert written, "could not find the estimator's provenance dict"
    assert written == set(_TABLE_PROVENANCE_FIELDS), (
        "estimator writes and controller reads different provenance fields:\n"
        f"  estimator only: {sorted(written - set(_TABLE_PROVENANCE_FIELDS))}\n"
        f"  controller only: {sorted(set(_TABLE_PROVENANCE_FIELDS) - written)}"
    )

    score = np.zeros((1, 5, 5, 5), dtype=np.float32)
    score[0, 4, 4, 4] = 2.0
    good = {
        "sampler_surface_key": "interaction_signed_score",
        "sampler_temperature": repr(1.0),
        "sampler_marginal_mode": "matched",
        "source_checkpoint_sha256": "SHA",
        "source_checkpoint_path": "/abs/parent.pt",
        "source_weight_key": "model_state_dict",
        "config_sha256": "CFG",
        "git_commit": "abc123",
        "bridge_steps": "10",
        "num_train_timesteps": "1000",
        "precision_mode": "fp16_autocast",
        "dataset_split": "training",
        "dataset_manifest_sha256": "MAN",
        "seed": "42",
    }

    def build(tmp, provenance):
        path = Path(tmp) / "table.npz"
        np.savez(
            path,
            interaction_signed_score=score,
            a_centers=np.linspace(0.1, 0.7, 5, dtype=np.float32),
            tau_centers=np.linspace(0.1, 0.9, 5, dtype=np.float32),
            **{key: np.asarray([value]) for key, value in provenance.items()},
        )
        return RMLFController(
            RMLFConfig(
                enabled=True,
                coupling_mode="amplification_table",
                amplification_table=str(path),
                teacher_checkpoint_type="raw",
                bridge_euler_steps=10,
            )
        )

    def verify(controller, sha="SHA"):
        controller.verify_table_provenance(
            sha, num_train_timesteps=1000, precision_mode="fp16_autocast"
        )

    with tempfile.TemporaryDirectory() as tmp:
        controller = build(tmp, good)
        # 1. every written field survives the loader
        assert set(controller.table_provenance) == set(good), (
            sorted(set(good) - set(controller.table_provenance))
        )
        verify(controller)  # 2. a complete, matching table is accepted

    # 3-5. dropping any operator field must fail closed, not pass silently
    for dropped in ("precision_mode", "bridge_steps", "num_train_timesteps"):
        with tempfile.TemporaryDirectory() as tmp:
            partial = {k: v for k, v in good.items() if k != dropped}
            try:
                verify(build(tmp, partial))
            except ValueError as exc:
                assert dropped in str(exc), (dropped, str(exc))
            else:
                raise AssertionError(f"table missing {dropped!r} was accepted")

    # 6-8. mismatched values must fail too
    mismatches = (
        ("weight key", {**good, "source_weight_key": "ema_model_state_dict"}, "SHA"),
        ("bridge steps", {**good, "bridge_steps": "4"}, "SHA"),
        ("timesteps", {**good, "num_train_timesteps": "500"}, "SHA"),
        ("precision", {**good, "precision_mode": "fp32"}, "SHA"),
        ("checkpoint sha", good, "OTHER"),
    )
    for label, provenance, sha in mismatches:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                verify(build(tmp, provenance), sha=sha)
            except ValueError:
                pass
            else:
                raise AssertionError(f"mismatched {label} was accepted")
    print("PASS T24 table provenance round-trips estimator -> controller")



def test_ipf_convergence_is_verified_not_assumed():
    """T25: an unconverged IPF must raise, never return a mismatched joint.

    R3's whole claim rests on it sharing the control's marginals.  If IPF hits
    its iteration cap and returns the last sweep anyway, R3 samples different
    marginals than R2G and a win could come from a marginal shift -- the exact
    confound IPF was added to remove, reintroduced silently.  A low
    `amplification_temperature` widens the kernel's dynamic range and is where
    the cap actually bites.
    """
    rng = np.random.default_rng(11)
    score = rng.normal(size=(5, 5, 5)) * 3.0
    uniform = [np.ones(5) / 5] * 3

    def marginal_error(joint):
        return max(
            float(
                np.abs(
                    joint.sum(axis=tuple(i for i in range(3) if i != axis))
                    - 0.2
                ).max()
            )
            for axis in range(3)
        )

    # A temperature that genuinely needs more than the old 500-sweep cap.
    hard_kernel = np.exp(np.clip(score / 0.25, -50.0, 50.0))
    try:
        iterative_proportional_fitting(hard_kernel, uniform, max_iters=500)
    except RuntimeError as exc:
        assert "did not converge" in str(exc)
        assert "max_marginal_error" in str(exc)
    else:
        raise AssertionError("a capped, unconverged IPF was returned silently")

    # With the real default it converges, and says so.
    joint, diagnostics = iterative_proportional_fitting(
        hard_kernel, uniform, return_diagnostics=True
    )
    assert diagnostics["ipf_max_marginal_error"] <= 1e-8
    assert diagnostics["ipf_iterations"] > 500  # i.e. the old cap was too low
    assert marginal_error(joint) <= 1e-8

    # Across temperatures the returned joint always matches the control.
    for temperature in (2.0, 1.0, 0.5, 0.25, 0.1):
        kernel = np.exp(np.clip(score / temperature, -50.0, 50.0))
        fitted = iterative_proportional_fitting(kernel, uniform)
        assert marginal_error(fitted) <= 1e-8, temperature

    # And the controller's own sampling path reports convergence.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "table.npz"
        _write_score_table(
            path,
            score[None] * 0.5,
            a_centers=np.linspace(0.1, 0.7, 5),
            tau_centers=np.linspace(0.1, 0.9, 5),
        )
        controller = RMLFController(
            RMLFConfig(
                enabled=True,
                coupling_mode="amplification_table",
                amplification_table=str(path),
                amplification_temperature=0.25,
            )
        )
        plan = controller.sample_plan(
            batch_size=64,
            chunk_index=2,
            chunk_length=5,
            num_train_timesteps=1000,
            device=torch.device("cpu"),
            dtype=torch.float32,
        )
        assert plan.corruption.numel() == 64
        diagnostics = controller.ipf_diagnostics
        assert diagnostics, "controller recorded no IPF diagnostics"
        for entry in diagnostics.values():
            assert entry["ipf_max_marginal_error"] <= 1e-8, entry
    print("PASS T25 IPF convergence is verified, not assumed")



def test_table_binds_the_treatment_definition_not_just_the_operator():
    """T26: a table is bound to the sampler settings it was reviewed under.

    The operator checks (checkpoint, weights, precision, bridge steps,
    timesteps) establish that the surface describes this run's *bridge*.  They
    say nothing about the *sampler*.  Without this binding, a table and its
    copula report could be generated at T=1.0, reviewed, and then trained at
    T=0.25: IPF still converges, the marginals still match the control, and
    nothing signals that the approved treatment strength is not the applied
    one.  The whole point of the copula report is to decide whether the
    treatment is strong enough to be worth running.
    """
    score = np.zeros((1, 5, 5, 5), dtype=np.float32)
    score[0, 4, 4, 4] = 2.0
    a_centers = np.linspace(0.1, 0.7, 5)
    tau_centers = np.linspace(0.1, 0.9, 5)

    def controller_for(table_kwargs, config_kwargs, coupling="amplification_table"):
        tmp = tempfile.mkdtemp()
        path = Path(tmp) / "table.npz"
        _write_score_table(
            path, score, a_centers=a_centers, tau_centers=tau_centers, **table_kwargs
        )
        return RMLFController(
            RMLFConfig(
                enabled=True,
                coupling_mode=coupling,
                amplification_table=str(path),
                teacher_checkpoint_type="raw",
                bridge_euler_steps=10,
                **config_kwargs,
            )
        )

    def verify(controller):
        controller.verify_table_provenance(
            "sha", num_train_timesteps=1000, precision_mode="fp16_autocast"
        )

    # Matching table and config: accepted.
    verify(controller_for({"temperature": 0.25}, {"amplification_temperature": 0.25}))

    # Each of the three treatment fields must be binding.
    mismatches = (
        ("temperature", {"temperature": 1.0}, {"amplification_temperature": 0.25}),
        (
            "surface key",
            {"surface_key": "interaction"},
            {"amplification_key": "interaction_signed_score"},
        ),
        (
            "marginal mode",
            {"marginal_mode": "raw"},
            {"marginal_mode": "matched"},
        ),
    )
    for label, table_kwargs, config_kwargs in mismatches:
        try:
            verify(controller_for(table_kwargs, config_kwargs))
        except ValueError as exc:
            assert "this run uses" in str(exc), (label, str(exc))
        else:
            raise AssertionError(f"mismatched {label} was accepted")

    # The control arm reads only the grid, so it need not match the coupled
    # arm's sampler settings -- but the fields must exist, or the two arms
    # cannot be shown to be reading the same table.
    verify(
        controller_for(
            {"temperature": 0.25, "marginal_mode": "raw"},
            {},
            coupling="grid_independent",
        )
    )

    # `allow_teacher_parent_mismatch` must not switch any of this off.
    strict = controller_for(
        {"temperature": 1.0},
        {"amplification_temperature": 0.25, "allow_teacher_parent_mismatch": True},
    )
    try:
        verify(strict)
    except ValueError as exc:
        assert "amplification_temperature" in str(exc)
    else:
        raise AssertionError(
            "allow_teacher_parent_mismatch disabled the treatment binding"
        )
    print("PASS T26 table binds the treatment definition, not just the operator")



def test_report_joint_equals_sampler_joint_for_every_surface_and_mode():
    """T27: the reviewed copula IS the sampled copula, for all five ablations.

    T26 binds the table's *labels* to the config.  That is not the same as the
    reported *numbers* being right: the estimator used to build its TV / KL /
    ratio / MI report from `interaction_signed_score` under `matched` no matter
    what the config said, so any ablation produced a report describing a
    distribution that was never sampled -- labels agreeing, numbers wrong.
    Both sides now call `build_joint_from_surface`, and this test pins that
    every (surface, marginal_mode) pair a config can name lands on the same
    joint the controller will draw from.
    """
    rng = np.random.default_rng(29)
    chunk_length, n_a, n_tau = 4, 5, 6
    a_centers = np.linspace(0.1, 0.7, n_a)
    tau_centers = np.linspace(0.1, 0.9, n_tau)

    combinations = (
        ("interaction_signed_score", "matched", 1.0),
        ("interaction_gated", "matched", 1.0),
        ("interaction", "matched", 0.5),
        ("log_ratio", "matched", 2.0),
        ("amplification", "raw", 1.0),
    )

    for surface_key, marginal_mode, temperature in combinations:
        # Distinct, clearly non-uniform surfaces so a mixed-up pairing cannot
        # accidentally agree.
        surface = rng.normal(size=(1, chunk_length, n_a, n_tau)) * 1.5
        if surface_key in {"interaction_gated", "amplification"}:
            surface = np.clip(surface, 0.0, None)  # positive-only surfaces
            surface[0, 0, 0, 0] = 3.0  # guarantee positive mass

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.npz"
            np.savez(
                path,
                **{surface_key: surface.astype(np.float32)},
                a_centers=a_centers.astype(np.float32),
                tau_centers=tau_centers.astype(np.float32),
                source_checkpoint_sha256=np.asarray(["sha"]),
                source_weight_key=np.asarray(["model_state_dict"]),
                bridge_steps=np.asarray(["10"]),
                num_train_timesteps=np.asarray(["1000"]),
                precision_mode=np.asarray(["fp16_autocast"]),
                sampler_surface_key=np.asarray([surface_key]),
                sampler_temperature=np.asarray([repr(temperature)]),
                sampler_marginal_mode=np.asarray([marginal_mode]),
            )
            controller = RMLFController(
                RMLFConfig(
                    enabled=True,
                    coupling_mode="amplification_table",
                    amplification_table=str(path),
                    amplification_key=surface_key,
                    marginal_mode=marginal_mode,
                    amplification_temperature=temperature,
                )
            )
            # The joint the controller will actually sample.
            sampler_joint = controller._joint_distribution(2, chunk_length).numpy()
            # The joint the estimator's report is computed from.
            report_joint = build_joint_from_surface(
                surface[0],
                marginal_mode=marginal_mode,
                temperature=temperature,
                floor=controller.config.amplification_floor,
            )
            assert np.allclose(sampler_joint, report_joint, atol=1e-12), (
                surface_key,
                marginal_mode,
                float(np.abs(sampler_joint - report_joint).max()),
            )

            # The two modes must not coincide by accident, or the test proves
            # nothing about `raw` vs `matched`.
            other_mode = "raw" if marginal_mode == "matched" else "matched"
            other = build_joint_from_surface(
                np.clip(surface[0], 0.0, None) if other_mode == "raw" else surface[0],
                marginal_mode=other_mode,
                temperature=temperature,
                floor=controller.config.amplification_floor,
            )
            assert not np.allclose(report_joint, other, atol=1e-6), (
                surface_key,
                "raw and matched produced the same joint",
            )

    # `matched` always lands on the control's marginals; `raw` need not.
    surface = rng.normal(size=(chunk_length, n_a, n_tau)) * 2.0
    matched = build_joint_from_surface(
        surface, marginal_mode="matched", temperature=0.5
    )
    for axis, size in enumerate(matched.shape):
        marginal = matched.sum(
            axis=tuple(i for i in range(matched.ndim) if i != axis)
        )
        assert np.abs(marginal - 1.0 / size).max() < 1e-8, axis
    raw = build_joint_from_surface(
        np.clip(surface, 0.0, None), marginal_mode="raw", temperature=0.5
    )
    deviations = [
        float(
            np.abs(
                raw.sum(axis=tuple(i for i in range(raw.ndim) if i != axis))
                - 1.0 / raw.shape[axis]
            ).max()
        )
        for axis in range(raw.ndim)
    ]
    assert max(deviations) > 1e-3, deviations
    print("PASS T27 report joint equals sampler joint for every surface/mode")



def test_ablation_verdict_follows_the_selected_surface():
    """T28: the main go/no-go and the selected treatment are separate calls.

    The estimator used to gate its whole joint report on the HEADLINE surface,
    so it mis-reported in both directions:

      * a `log_ratio` ablation was called No-Go whenever
        `interaction_signed_score` was empty -- even though `log_ratio` has a
        perfectly good joint and is a legitimate curriculum ablation;
      * an `interaction_gated` ablation whose positive part was empty was
        called a candidate -- even though its joint IPFs to exactly the
        uniform control, so the arm duplicates R2G and cannot differ from it.

    This drives the same decision logic the tool now uses.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "rmlf_estimator",
        Path(__file__).resolve().parents[1]
        / "tools/estimate_rmlf_amplification.py",
    )
    estimator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(estimator)

    shape = (1, 4, 5, 5)
    empty = np.zeros(shape)
    structured = np.zeros(shape)
    structured[0, 3, 4, 4] = 2.0
    structured[0, 0, 0, 4] = -1.5

    def verdict(signed_score, selected_surface, marginal_mode="matched", floor=1e-6):
        """Mirror of the tool's two independent decisions."""
        main_cells = int((np.abs(signed_score) > 0).sum())
        try:
            joint = np.mean(
                [
                    build_joint_from_surface(
                        selected_surface[t],
                        marginal_mode=marginal_mode,
                        temperature=1.0,
                        floor=floor,
                    )
                    for t in range(selected_surface.shape[0])
                ],
                axis=0,
            )
        except ValueError:
            return main_cells > 0, "unbuildable"
        strength = estimator.copula_strength(joint)
        equals_control = strength["total_variation"] < 1e-12
        return main_cells > 0, "control" if equals_control else "treatment"

    # 1. Headline empty, but a log-ratio ablation still has a real joint.
    main_go, treatment = verdict(empty, structured)
    assert main_go is False, "headline surface should be No-Go"
    assert treatment == "treatment", (
        "an ablation with structure was reported as No-Go because the "
        "headline surface was empty"
    )

    # 2. Headline has structure, but the positive-only surface is empty:
    #    the ablation's joint is exactly the control.
    negative_only = np.zeros(shape)
    negative_only[0, 2, 1, 3] = -2.0
    main_go, treatment = verdict(negative_only, np.clip(negative_only, 0.0, None))
    assert main_go is True, "headline surface has mass"
    assert treatment == "control", (
        "a positive-only ablation with no positive mass was reported as a "
        "treatment"
    )

    # 3. Both present: a genuine treatment.
    main_go, treatment = verdict(structured, structured)
    assert main_go is True and treatment == "treatment"

    # 4. `raw` weighting on an all-nonpositive surface: the floor makes every
    #    cell equal, so it degenerates to the control rather than erroring.
    #    Reporting it as a treatment would be the same mistake as case 2.
    main_go, treatment = verdict(structured, negative_only, marginal_mode="raw")
    assert treatment == "control", treatment

    # 5. ...and with no floor there is genuinely nothing to build.
    main_go, treatment = verdict(
        structured, negative_only, marginal_mode="raw", floor=0.0
    )
    assert treatment == "unbuildable", treatment
    print("PASS T28 ablation verdict follows the selected surface")



if __name__ == "__main__":
    tests = [
        test_bridge_endpoints_and_no_grad,
        test_independent_plan_bounds_and_lead_normalization,
        test_diagonal_coupling_is_correlated,
        test_amplification_table_sampling_and_focus_weights,
        test_controller_rng_state_roundtrip,
        test_rng_streams_isolate_ablation_draws,
        test_rollout_probability_warmup_and_batch_mask,
        test_latent_gate_falls_back_to_clean_condition,
        test_rflow_default_path_is_unchanged,
        test_t_override_and_lead_weights_select_requested_region,
        test_chunked_warmup_zero_is_exact_teacher_forcing,
        test_chunked_bridge_changes_only_later_condition,
        test_relative_l2_is_scale_stabilized,
        test_bridge_at_a_one_equals_deployment_sampler,
        test_log_ratio_is_invariant_to_flow_time_rescaling,
        test_additive_surface_has_zero_interaction,
        test_frozen_teacher_does_not_drift,
        test_r0_matches_the_pre_merge_implementation_bitwise,
        test_r0_matches_pre_merge_with_uot_enabled,
        test_independent_mode_shares_the_base_rf_random_stream,
        test_coupled_and_control_arms_share_every_marginal,
        test_additive_score_collapses_the_coupled_arm_onto_the_control,
        test_strict_continuation_rejects_an_incomplete_parent,
        test_table_provenance_round_trip,
        test_ipf_convergence_is_verified_not_assumed,
        test_table_binds_the_treatment_definition_not_just_the_operator,
        test_report_joint_equals_sampler_joint_for_every_surface_and_mode,
        test_ablation_verdict_follows_the_selected_surface,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        raise SystemExit(f"{failures}/{len(tests)} RMLF tests failed")
    print(f"\nAll {len(tests)} RMLF tests passed.")
