"""Tests for the UOT-only (Innovation 2) build on the clean FlowCast base.

Run from the FlowCast_uot repo root:  python tests/test_uot_only.py
"""

import math
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.losses.uot import (
    GridUOTConfig,
    GridUnbalancedSinkhorn,
    dense_uot_reference,
    mass_from_field,
    sum_pool2d,
)
from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper, rflow_training_loss

torch.manual_seed(0)
np.random.seed(0)


def gaussian_blob(h, w, cy, cx, sigma, mass=100.0):
    ys, xs = torch.meshgrid(
        torch.arange(h, dtype=torch.float32),
        torch.arange(w, dtype=torch.float32),
        indexing="ij",
    )
    blob = torch.exp(-((ys - cy) ** 2 + (xs - cx) ** 2) / (2 * sigma ** 2))
    return blob / blob.sum() * mass


def test_separable_matches_dense():
    h = w = 16
    a = gaussian_blob(h, w, 5.0, 6.0, 2.0, mass=40.0) + 0.05
    b = gaussian_blob(h, w, 9.0, 10.0, 2.5, mass=55.0) + 0.05
    for debiased in (False, True):
        cfg = GridUOTConfig(
            blur=2.0, reach=6.0, downsample=1, n_iters=300, debiased=debiased,
            self_iters=300, tol=0.0,
        )
        fast = GridUnbalancedSinkhorn(cfg)(a[None], b[None]).item()
        ref = dense_uot_reference(
            a.double(), b.double(), blur=2.0, reach=6.0, n_iters=300,
            debiased=debiased,
        ).item()
        rel = abs(fast - ref) / max(abs(ref), 1e-9)
        assert rel < 5e-3, f"debiased={debiased}: fast={fast} ref={ref} rel={rel}"
    print("PASS separable solver matches dense float64 reference")


def test_sparse_far_shift_matches_dense():
    h = w = 64
    a = torch.zeros(h, w)
    b = torch.zeros(h, w)
    a[32, 16] = 100.0
    b[32, 48] = 100.0
    for blur, reach in ((2.0, 48.0), (3.0, 16.0)):
        cfg = GridUOTConfig(blur=blur, reach=reach, downsample=1, n_iters=400,
                            self_iters=400, debiased=False, tol=0.0)
        fast = GridUnbalancedSinkhorn(cfg)(a[None], b[None]).item()
        ref = dense_uot_reference(a.double(), b.double(), blur=blur, reach=reach,
                                  n_iters=400).item()
        rel = abs(fast - ref) / max(abs(ref), 1e-9)
        assert rel < 1e-2, f"(blur={blur},reach={reach}): {fast} vs {ref} rel={rel}"
    print("PASS sparse far-shift (strict zeros) matches dense reference")


def test_ranking_flip_mse_vs_uot():
    """The core claim: pixel MSE prefers the smear, UOT prefers the
    displaced sharp core."""
    h = w = 64
    truth = gaussian_blob(h, w, 32.0, 32.0, 3.0, mass=100.0)
    shifted = gaussian_blob(h, w, 32.0, 42.0, 3.0, mass=100.0)
    blurred = gaussian_blob(h, w, 32.0, 32.0, 20.0, mass=100.0)
    uot = GridUnbalancedSinkhorn(
        GridUOTConfig(blur=2.0, reach=48.0, downsample=1, n_iters=150, self_iters=150)
    )
    mse_shift = ((shifted - truth) ** 2).mean().item()
    mse_blur = ((blurred - truth) ** 2).mean().item()
    uot_shift = uot(shifted[None], truth[None]).item()
    uot_blur = uot(blurred[None], truth[None]).item()
    assert mse_blur < mse_shift and uot_shift < uot_blur, (
        f"MSE: blur {mse_blur} vs shift {mse_shift}; "
        f"UOT: shift {uot_shift} vs blur {uot_blur}"
    )
    print("PASS ranking flip (MSE prefers blur, UOT prefers displaced sharp core)")


def test_mass_creation_priced_by_reach():
    h = w = 32
    a = gaussian_blob(h, w, 16.0, 16.0, 3.0, mass=100.0) + 0.01
    b = a * 1.5
    vals = []
    for reach in (4.0, 12.0, 36.0):
        uot = GridUnbalancedSinkhorn(
            GridUOTConfig(blur=2.0, reach=reach, downsample=1, n_iters=200,
                          self_iters=200)
        )
        vals.append(uot(a[None], b[None]).item())
    assert vals[0] < vals[1] < vals[2] and vals[0] > 0, vals
    print(f"PASS mass creation priced by reach: {vals}")


def test_gradients_reduce_loss():
    h = w = 24
    truth = gaussian_blob(h, w, 12.0, 15.0, 2.5, mass=60.0)
    logits = torch.full((1, h, w), -4.0, requires_grad=True)
    uot = GridUnbalancedSinkhorn(
        GridUOTConfig(blur=2.0, reach=16.0, downsample=1, n_iters=100, self_iters=100)
    )
    opt = torch.optim.Adam([logits], lr=0.15)
    first = None
    for _ in range(30):
        loss = uot(torch.nn.functional.softplus(logits), truth[None]).mean()
        if first is None:
            first = loss.item()
        opt.zero_grad()
        loss.backward()
        assert torch.isfinite(logits.grad).all()
        opt.step()
    assert loss.item() < 0.5 * first, (first, loss.item())
    print(f"PASS envelope gradients optimize masses ({first:.1f} -> {loss.item():.1f})")


def test_zr_mass_transform_and_soft_threshold():
    dbz = torch.tensor([[0.0, 20.0, 40.0, 55.0]])
    rain = mass_from_field(dbz, transform="zr_dbz", low_threshold=0.1,
                           threshold_mode="hard")
    assert rain[0, 0] < 0.1 and rain[0, 3] > rain[0, 2] > rain[0, 1]

    # missed extreme core must still get a gradient under the soft threshold
    h = w = 32
    truth = gaussian_blob(h, w, 16.0, 16.0, 2.5, mass=100.0) * 40 + 30.0
    pred = torch.full((h, w), 10.0, requires_grad=True)
    uot = GridUnbalancedSinkhorn(
        GridUOTConfig(blur=2.0, reach=16.0, downsample=1, n_iters=60, self_iters=30)
    )
    kwargs = dict(transform="vil", low_threshold=16.0, threshold_softness=4.0)
    for mode, expect in (("hard", False), ("soft", True)):
        if pred.grad is not None:
            pred.grad = None
        loss = uot(
            mass_from_field(pred[None], threshold_mode=mode, **kwargs),
            mass_from_field(truth[None], threshold_mode=mode, **kwargs),
        ).mean()
        loss.backward()
        grad_mag = float(pred.grad.abs().sum())
        assert (grad_mag > 0) == expect, (mode, grad_mag)
    print("PASS Z-R transform; soft threshold keeps gradients below the mass cut")


def test_sum_pool_conserves_mass():
    x = torch.rand(2, 32, 32) * 3.0
    pooled = sum_pool2d(x, 4)
    assert torch.allclose(pooled.sum(dim=(-1, -2)), x.sum(dim=(-1, -2)), rtol=1e-5)
    print("PASS sum-pool conserves mass")


# ---------------------------------------------------------------------- #
# single-output training loss integration (the actual IP2 wiring)
# ---------------------------------------------------------------------- #
def tiny_decode_fn(latent):
    """Differentiable stand-in for the VAE decoder: (B,T,8,8,4) ->
    dBZ-scale pixel fields (B,T,16,16)."""
    x = latent[..., 0]
    b, t, h, w = x.shape
    x = torch.nn.functional.interpolate(
        x.reshape(b * t, 1, h, w), scale_factor=2, mode="bilinear",
        align_corners=False,
    )
    return (torch.sigmoid(x) * 90.0).reshape(b, t, 2 * h, 2 * w)


def build_tiny_model():
    return FlowCastSTDiTWrapper(
        latent_channels=4, hidden_size=64, depth=2, num_heads=4,
        patch_size=(1, 2, 2), mean=0.0, std=1.0,
    )


UOT_PARAMS = {
    "weight": 0.05,
    "t_power": 2.0,
    "normalize_by_mass": True,
    "mass_kwargs": {
        "transform": "zr_dbz",
        "low_threshold": 0.5,
        "threshold_mode": "soft",
        "threshold_softness": 1.0,
        "mass_scale": 10.0,
    },
}


def test_zero_anchored_mass_kills_background_carpet():
    """v2 regression: a no-echo (0 dBZ) field must carry EXACTLY zero
    transport mass. Without the anchor, softplus gives every zero pixel
    ~0.0488 mass -> ~800 fake units per 128x128 frame, dwarfing a real
    storm's ~117 and drowning the transport geometry."""
    kw = dict(transform="zr_dbz", low_threshold=0.5, threshold_mode="soft",
              threshold_softness=1.0, mass_scale=10.0)
    zero_field = torch.zeros(1, 64, 64)
    m_old = mass_from_field(zero_field, **kw)
    assert m_old.sum() > 100.0 / 10.0, "test premise: un-anchored carpet exists"
    m_new = mass_from_field(zero_field, **kw, zero_point=0.0)
    assert float(m_new.sum()) == 0.0, f"carpet not zeroed: {m_new.sum()}"

    # sub-threshold but above-zero pixels must KEEP a gradient (the whole
    # point of the soft threshold: pull missed cores up through it)
    field = torch.full((1, 8, 8), 10.0, requires_grad=True)  # 10 dBZ < thr
    m = mass_from_field(field, **kw, zero_point=0.0)
    assert float(m.sum()) > 0
    m.sum().backward()
    assert field.grad.abs().sum() > 0, "sub-threshold gradient lost"

    # storm mass barely affected by the anchor (floor is tiny vs storm)
    storm = torch.full((1, 8, 8), 35.0)  # 35 dBZ core
    m_storm_old = mass_from_field(storm, **kw)
    m_storm_new = mass_from_field(storm, **kw, zero_point=0.0)
    rel = float((m_storm_old.sum() - m_storm_new.sum()) / m_storm_old.sum())
    assert rel < 0.11, f"anchor distorted storm mass by {rel:.2%}"
    print("PASS zero-anchored mass: carpet=0, sub-threshold grad alive, storm intact")


def test_sequence_reduce_false_and_dry_frame_logic():
    """sequence(reduce=False) returns per-frame values so the loss can
    replace dry-true-frame Sinkhorn with a predicted-mass penalty."""
    uot = GridUnbalancedSinkhorn(
        GridUOTConfig(blur=2.0, reach=8.0, downsample=1, n_iters=20, self_iters=10)
    )
    a = torch.rand(2, 3, 16, 16)
    b = torch.rand(2, 3, 16, 16)
    per_frame = uot.sequence(a, b, reduce=False)
    assert per_frame.shape == (2, 3)
    assert torch.allclose(per_frame.mean(dim=1), uot.sequence(a, b), atol=1e-5)

    # dry-frame replacement logic (mirrors the rf_stdit block)
    mass_true = b.clone()
    mass_true[:, 1] = 0.0  # frame 1 dry in truth
    true_frame_mass = mass_true.sum(dim=(2, 3))
    dry = true_frame_mass < 1e-3
    assert dry[:, 1].all() and not dry[:, 0].any()
    pred_frame_mass = a.sum(dim=(2, 3))
    replaced = torch.where(dry, pred_frame_mass, per_frame)
    assert torch.allclose(replaced[:, 1], pred_frame_mass[:, 1])
    assert torch.allclose(replaced[:, 0], per_frame[:, 0])
    print("PASS sequence(reduce=False) + dry-frame replacement logic")


def test_loss_backward_and_uot_contribution():
    torch.manual_seed(1)
    model = build_tiny_model()
    x_start = torch.randn(3, 2, 8, 8, 4)
    cond = torch.randn(3, 2, 8, 8, 4)
    t_seq = torch.full((3,), 1, dtype=torch.long)
    uot = GridUnbalancedSinkhorn(
        GridUOTConfig(blur=2.0, reach=8.0, downsample=1, n_iters=25, self_iters=25)
    )

    torch.manual_seed(7)
    loss_plain, stat_plain = rflow_training_loss(
        model, x_start, cond, t_seq, num_train_timesteps=50
    )
    assert stat_plain is None, "plain path must not report a UOT term"

    torch.manual_seed(7)  # identical noise/t draws
    loss_uot, stat_uot = rflow_training_loss(
        model, x_start, cond, t_seq, num_train_timesteps=50,
        decode_fn=tiny_decode_fn, uot_loss=uot, uot_params=UOT_PARAMS,
    )
    assert stat_uot is not None and stat_uot > 0
    assert torch.isfinite(loss_uot)
    # identical randomness -> the difference IS the UOT term
    assert abs((loss_uot - loss_plain).item() - stat_uot) < 1e-4, (
        loss_plain.item(), loss_uot.item(), stat_uot
    )
    loss_uot.backward()
    grads = [p.grad for p in model.parameters() if p.grad is not None]
    assert grads and all(torch.isfinite(g).all() for g in grads)
    print(
        f"PASS single-output loss: plain={loss_plain.item():.4f} "
        f"+UOT={loss_uot.item():.4f} (uot term {stat_uot:.4f}), backward OK"
    )


def test_plain_path_unchanged_without_uot():
    """With UOT disabled the objective must be numerically identical to
    the original (regression guard for the signature change)."""
    torch.manual_seed(2)
    model = build_tiny_model()
    x_start = torch.randn(2, 2, 8, 8, 4)
    cond = torch.randn(2, 2, 8, 8, 4)
    t_seq = torch.full((2,), 1, dtype=torch.long)

    torch.manual_seed(11)
    loss_a, _ = rflow_training_loss(model, x_start, cond, t_seq, 50)

    # reference: re-execute the original computation inline
    torch.manual_seed(11)
    noise = torch.randn_like(x_start)
    t = torch.randint(1, 50, (2,))
    t_norm = (t.float() / 49.0).view(2, 1, 1, 1, 1)
    x_t = t_norm * noise + (1.0 - t_norm) * x_start
    velocity = model(x_t, t, cond, t_seq)
    ref = torch.mean((velocity - (x_start - noise)) ** 2) + torch.mean(
        ((x_t + velocity * t_norm) - x_start) ** 2
    )
    assert torch.allclose(loss_a, ref, atol=1e-6), (loss_a.item(), ref.item())
    print("PASS plain objective is byte-identical with UOT disabled")


def test_ddp_buffer_broadcast_regression():
    """DDP broadcasts module buffers IN-PLACE at every forward. If the
    decode path reads mean/std from the module buffers inside the UOT
    graph, the buffer saved for backward by chunk 1 is version-bumped by
    chunk 2's forward and backward dies with 'modified by an inplace
    operation'. The fixed decode fn captures mean/std as plain floats."""
    import torch.distributed as dist
    from torch.nn.parallel import DistributedDataParallel as DDP

    if not dist.is_available():
        print("SKIP DDP buffer regression: torch.distributed unavailable")
        return
    os.environ.setdefault("MASTER_ADDR", "127.0.0.1")
    os.environ.setdefault("MASTER_PORT", "29541")
    created = False
    if not dist.is_initialized():
        dist.init_process_group("gloo", rank=0, world_size=1)
        created = True
    try:
        uot = GridUnbalancedSinkhorn(
            GridUOTConfig(blur=2.0, reach=8.0, downsample=1, n_iters=15, self_iters=10)
        )

        def run_two_chunk_backward(decode_fn_factory):
            torch.manual_seed(3)
            model = FlowCastSTDiTWrapper(
                latent_channels=4, hidden_size=64, depth=2, num_heads=4,
                patch_size=(1, 2, 2), mean=0.5, std=2.0,
            )
            ddp = DDP(model, find_unused_parameters=True)
            decode_fn = decode_fn_factory(ddp.module)
            loss = torch.zeros(())
            for chunk in range(2):
                # DDP with world_size > 1 broadcasts buffers IN-PLACE at
                # the start of every forward; at world_size 1 the broadcast
                # is skipped, so emulate its in-place write explicitly
                with torch.no_grad():
                    ddp.module.mean.copy_(ddp.module.mean.clone())
                    ddp.module.std.copy_(ddp.module.std.clone())
                x_start = torch.randn(2, 2, 8, 8, 4)
                cond = torch.randn(2, 2, 8, 8, 4)
                t_seq = torch.full((2,), chunk + 1, dtype=torch.long)
                chunk_loss, _ = rflow_training_loss(
                    ddp, x_start, cond, t_seq, num_train_timesteps=50,
                    decode_fn=decode_fn, uot_loss=uot, uot_params=UOT_PARAMS,
                )
                loss = loss + chunk_loss
            loss.backward()

        def buggy_factory(module):
            # reads the live buffers inside the differentiable graph
            def decode_fn(latent_norm):
                lat = module.denormalize(latent_norm.float())
                return tiny_decode_fn(lat)
            return decode_fn

        def fixed_factory(module):
            mean_val = float(module.mean)
            std_val = float(module.std)
            def decode_fn(latent_norm):
                lat = latent_norm.float() * std_val + mean_val
                return tiny_decode_fn(lat)
            return decode_fn

        crashed = False
        try:
            run_two_chunk_backward(buggy_factory)
        except RuntimeError as exc:
            assert "inplace" in str(exc), f"unexpected error: {exc}"
            crashed = True
        assert crashed, (
            "buggy buffer-reading decode fn no longer crashes - if DDP "
            "semantics changed, re-evaluate whether the float capture is needed"
        )

        run_two_chunk_backward(fixed_factory)  # must NOT raise
        print("PASS DDP buffer-broadcast regression (buggy crashes, fixed passes)")
    finally:
        if created:
            dist.destroy_process_group()


if __name__ == "__main__":
    tests = [
        test_separable_matches_dense,
        test_sparse_far_shift_matches_dense,
        test_ranking_flip_mse_vs_uot,
        test_mass_creation_priced_by_reach,
        test_gradients_reduce_loss,
        test_zr_mass_transform_and_soft_threshold,
        test_sum_pool_conserves_mass,
        test_zero_anchored_mass_kills_background_carpet,
        test_sequence_reduce_false_and_dry_frame_logic,
        test_plain_path_unchanged_without_uot,
        test_loss_backward_and_uot_contribution,
        test_ddp_buffer_broadcast_regression,
    ]
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        sys.exit(f"{failures}/{len(tests)} tests failed")
    print(f"\nAll {len(tests)} UOT-only tests passed.")
