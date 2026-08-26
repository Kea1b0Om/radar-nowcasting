"""Gate for the offline flow cache.

The tests that matter are the ones about *what the flow is allowed to see*: it
must be a function of the input window only, and the estimate must recover a
known translation with the right sign and the right axis.  A flow with a flipped
sign would tilt the ground cost the wrong way and every downstream number would
still look plausible.
"""

import numpy as np
import pytest

from tools.precompute_flow import sample_flow

pytest.importorskip("skimage", reason="optical flow estimator not installed")

H = W = 48


def _blob(cy, cx, r=6, amp=40.0):
    y, x = np.mgrid[0:H, 0:W]
    return (amp * np.exp(-(((y - cy) ** 2 + (x - cx) ** 2) / (2.0 * r ** 2)))).astype(np.float32)


def _translating(dh, dw, t=5, start=(24, 16)):
    return np.stack([_blob(start[0] + dh * k, start[1] + dw * k) for k in range(t)])


# ------------------------------------------------------------------ recovery
def test_recovers_a_pure_horizontal_translation():
    flow, ok = sample_flow(_translating(0, 3), n_pairs=2)
    assert ok
    core = flow[:, 12:36, 8:40]                       # away from the boundary
    assert core[1].mean() > 1.5                       # dw positive, right order
    assert abs(float(core[0].mean())) < 1.0           # no spurious dh


def test_recovers_a_pure_vertical_translation():
    flow, ok = sample_flow(_translating(3, 0), n_pairs=2)
    assert ok
    core = flow[:, 8:40, 12:36]
    assert core[0].mean() > 1.5
    assert abs(float(core[1].mean())) < 1.0


def test_sign_follows_the_direction_of_travel():
    """A storm moving left must not produce a rightward flow."""
    right = sample_flow(_translating(0, 3), n_pairs=2)[0][1, 12:36, 8:40].mean()
    left = sample_flow(_translating(0, -3), n_pairs=2)[0][1, 12:36, 8:40].mean()
    assert right > 0 > left


# --------------------------------------------------------------- no leakage
def test_flow_depends_only_on_the_input_window():
    """Changing frames after the window must not change the estimate at all --
    this is the property that makes the cache leak-proof by construction."""
    seq = _translating(0, 3, t=5)
    a, _ = sample_flow(seq, n_pairs=2)
    tampered = np.concatenate([seq, np.random.default_rng(0).normal(
        0, 50, size=(4, H, W)).astype(np.float32)])
    b, _ = sample_flow(tampered[:5], n_pairs=2)
    np.testing.assert_array_equal(a, b)


def test_n_pairs_uses_only_the_most_recent_frames():
    seq = _translating(0, 3, t=5)
    one = sample_flow(seq, n_pairs=1)[0]
    corrupted = seq.copy()
    corrupted[0] = np.random.default_rng(1).normal(0, 50, size=(H, W))
    np.testing.assert_array_equal(one, sample_flow(corrupted, n_pairs=1)[0])


# ------------------------------------------------------------- degeneracies
def test_dry_window_returns_zero_flow_and_is_flagged():
    """Zero flow is the safe fallback: M = I, i.e. the Euclidean cost."""
    flow, ok = sample_flow(np.zeros((5, H, W), dtype=np.float32), n_pairs=2)
    assert not ok
    np.testing.assert_array_equal(flow, np.zeros_like(flow))


def test_static_scene_gives_near_zero_flow():
    seq = np.stack([_blob(24, 24)] * 5)
    flow, ok = sample_flow(seq, n_pairs=2)
    assert ok
    assert float(np.abs(flow).max()) < 1.0


def test_rejects_a_window_that_is_too_short():
    with pytest.raises(ValueError):
        sample_flow(np.zeros((1, H, W), dtype=np.float32), n_pairs=2)


def test_n_pairs_is_clamped_to_the_window():
    flow, ok = sample_flow(_translating(0, 3, t=3), n_pairs=99)
    assert ok and flow.shape == (2, H, W)


def test_output_shape_and_finiteness():
    flow, ok = sample_flow(_translating(1, 2), n_pairs=3)
    assert flow.shape == (2, H, W) and np.isfinite(flow).all() and ok


# ------------------------------------------------------- dataset layout
def test_infer_time_last_matches_cikm_and_nthw():
    from tools.precompute_flow import infer_time_last
    assert infer_time_last((8000, 128, 128, 15))     # CIKM 'vil': time last
    assert not infer_time_last((8000, 15, 128, 128))  # (N,T,H,W)
    assert not infer_time_last((8000, 15, 128))


def test_read_input_window_honours_the_time_axis(tmp_path):
    """Slicing (N,H,W,T) as if it were (N,T,H,W) cuts along height and yields a
    flow estimated from image rows -- wrong, and entirely plausible-looking."""
    import h5py
    from tools.precompute_flow import read_input_window

    seq = _translating(0, 3, t=15)                       # (T,H,W)
    path = tmp_path / "d.h5"
    with h5py.File(path, "w") as f:
        f.create_dataset("vil", data=np.transpose(seq, (1, 2, 0))[None])  # (1,H,W,T)
    with h5py.File(path, "r") as f:
        got = read_input_window(f, "vil", 0, 5, time_last=True)
    assert got.shape == (5, H, W)
    np.testing.assert_allclose(got, seq[:5], rtol=0, atol=0)


def test_cikm_layout_end_to_end_recovers_the_translation(tmp_path):
    import h5py
    from tools.precompute_flow import read_input_window

    seq = _translating(0, 3, t=15)
    path = tmp_path / "d.h5"
    with h5py.File(path, "w") as f:
        f.create_dataset("vil", data=np.transpose(seq, (1, 2, 0))[None])
    with h5py.File(path, "r") as f:
        frames = read_input_window(f, "vil", 0, 5, time_last=True)
    flow, ok = sample_flow(frames, n_pairs=2)
    assert ok and flow[1, 12:36, 8:40].mean() > 1.5


# ------------------------------------------------- untrusted-estimate guard
def test_reject_speed_zeroes_impossible_vectors():
    """Measured CIKM max was 122 px/frame on a 128 px domain -- an estimator
    failure.  Those must fall back to Euclidean (zero flow), not be shortened:
    a clamped outlier keeps ~96% of the discount along a wrong direction."""
    seq = _translating(0, 3, t=5)
    ref, _ = sample_flow(seq, n_pairs=2)
    kept, ok = sample_flow(seq, n_pairs=2, reject_speed=100.0)
    assert ok
    np.testing.assert_array_equal(kept, ref)          # normal motion untouched

    dropped, ok2 = sample_flow(seq, n_pairs=2, reject_speed=0.5)
    assert not ok2                                     # everything rejected
    np.testing.assert_array_equal(dropped, np.zeros_like(dropped))


def test_reject_is_per_pixel_not_per_sample():
    """Needs a genuinely mixed field: TV-L1 is total-variation regularised, so a
    single blob yields a near-uniform flow and every pixel would be rejected
    together -- which is what a first version of this test tripped over."""
    def frame(k):
        return _blob(12, 12 + 6 * k) + _blob(36, 36)     # one moving, one static

    seq = np.stack([frame(k) for k in range(5)])
    flow, ok = sample_flow(seq, n_pairs=2, reject_speed=3.0)
    speed = np.linalg.norm(flow, axis=0)
    assert ok
    assert float(speed.max()) <= 3.0 + 1e-6              # fast pixels zeroed
    assert float(speed[30:44, 30:44].max()) < 3.0        # static blob survives
