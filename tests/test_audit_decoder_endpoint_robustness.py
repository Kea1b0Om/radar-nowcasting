"""Pins for the decoder endpoint-robustness audit's pure math (VE-Loss
diagnostic B).

Properties pinned:
  * every control direction is genuinely norm-matched to the real error
    (the whole comparison is meaningless otherwise), and the two shuffles
    preserve exactly what they claim to preserve (channel shuffle: spatial
    field per channel; spatial shuffle: per-site channel vectors);
  * flip rate / area ratio / peak ratio / A_D hit their closed-form anchors,
    with the identity case exact (0.0 flips, 0.0 amplification);
  * the metric view reproduces the evaluator's CIKM crop and clamp;
  * threshold comparison is '>=' (the published-protocol operator matters
    at exactly 30.0 dBZ on CIKM);
  * the two pre-registered gates flip on exactly their documented
    boundaries (kill: ratio < 1.2 strict; structure: ratio >= 1.25).
"""

import os
import sys

import numpy as np
import pytest
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audit_decoder_endpoint_robustness import (  # noqa: E402
    area_ratio,
    channel_shuffle,
    contingency,
    decoder_amplification,
    evaluate_endpoint_gates,
    flip_rate,
    match_norm,
    metric_view,
    peak_ratio,
    refuse_test_path,
    spatial_shuffle,
    summarize,
)

SHAPE = (3, 2, 4, 4, 4)  # (B, T, h, w, c) latent layout


def _rand(seed, shape=SHAPE):
    return torch.randn(shape, generator=torch.Generator().manual_seed(seed))


def test_match_norm_equalises_per_sample():
    direction = _rand(0)
    reference = 3.0 * _rand(1)
    matched = match_norm(direction, reference)
    d = matched.reshape(3, -1).norm(dim=1)
    r = reference.reshape(3, -1).norm(dim=1)
    assert torch.allclose(d, r, rtol=1e-5)


def test_match_norm_guards():
    with pytest.raises(ValueError):
        match_norm(torch.zeros(SHAPE), _rand(2))
    matched = match_norm(_rand(3), torch.zeros(SHAPE))
    assert torch.allclose(matched, torch.zeros(SHAPE), atol=1e-6)


def test_channel_shuffle_deranges_and_preserves_norm():
    delta = _rand(4)
    shuf = channel_shuffle(delta)
    assert torch.allclose(shuf.norm(), delta.norm())
    for c in range(SHAPE[-1]):
        assert torch.equal(shuf[..., c], delta[..., (c - 1) % SHAPE[-1]])
    with pytest.raises(ValueError):
        channel_shuffle(_rand(5, (2, 2, 4, 4, 1)))


def test_spatial_shuffle_preserves_site_vectors_and_norm():
    delta = _rand(6)
    gen = torch.Generator().manual_seed(7)
    shuf = spatial_shuffle(delta, generator=gen)
    assert shuf.shape == delta.shape
    assert torch.allclose(shuf.norm(), delta.norm(), rtol=1e-6)
    # per-site channel vectors survive as a multiset per (sample, frame)
    for b in range(SHAPE[0]):
        for t in range(SHAPE[1]):
            orig = delta[b, t].reshape(-1, SHAPE[-1])
            got = shuf[b, t].reshape(-1, SHAPE[-1])
            orig_sorted = orig[np.lexsort(orig.numpy().T)]
            got_sorted = got[np.lexsort(got.numpy().T)]
            assert torch.allclose(orig_sorted, got_sorted)


def test_spatial_shuffle_same_perm_across_frames_and_channels():
    # encode the site index in the values: shuffling must move frame 0 and
    # frame 1 identically.
    b, t, h, w, c = 1, 2, 3, 3, 2
    site = torch.arange(h * w, dtype=torch.float32).reshape(1, 1, h, w, 1)
    delta = site.expand(b, t, h, w, c).contiguous()
    shuf = spatial_shuffle(delta, generator=torch.Generator().manual_seed(8))
    assert torch.equal(shuf[0, 0], shuf[0, 1])
    assert torch.equal(shuf[0, 0, :, :, 0], shuf[0, 0, :, :, 1])


def test_flip_rate_anchor():
    base = torch.zeros(1, 1, 4, 4)
    pert = torch.zeros(1, 1, 4, 4)
    pert[0, 0, 0, :2] = 50.0                      # 2 of 16 pixels flip at 40
    assert flip_rate(base, pert, 40.0).item() == pytest.approx(2.0 / 16.0)
    assert flip_rate(base, base, 40.0).item() == 0.0


def test_area_ratio_anchor_and_nan():
    base = torch.zeros(2, 1, 4, 4)
    base[0, 0, :2, :2] = 45.0                     # 4 pixels above 40
    pert = torch.zeros(2, 1, 4, 4)
    pert[0, 0, :2, :] = 45.0                      # 8 pixels above 40
    ratios = area_ratio(base, pert, 40.0)
    assert ratios[0].item() == pytest.approx(2.0)
    assert torch.isnan(ratios[1])                 # no base exceedance


def test_peak_ratio_anchor_and_nan():
    base = torch.full((2, 1, 2, 2), 50.0)
    base[1] = 0.0                                 # all-dry base decode
    pert = torch.full((2, 1, 2, 2), 40.0)
    ratios = peak_ratio(base, pert)
    assert ratios[0].item() == pytest.approx(0.8)
    assert torch.isnan(ratios[1])                 # undefined, not ~1e13


def test_decoder_amplification_anchor_and_identity():
    base = torch.zeros(1, 2, 4, 4)
    pert = base.clone()
    pert[0, 0, 0, 0] = 3.0                        # pixel diff norm = 3
    delta = torch.zeros(1, 2, 4, 4, 1)
    delta[0, 0, 0, 0, 0] = 1.5                    # latent norm = 1.5
    assert decoder_amplification(base, pert, delta).item() == pytest.approx(2.0)
    # identity: zero perturbation -> exactly 0.0, not NaN
    assert decoder_amplification(base, base, torch.zeros_like(delta)).item() == 0.0


def test_metric_view_crop_and_clamp():
    pixels = torch.full((1, 2, 128, 128), 120.0)
    pixels[0, 0, 0, 0] = -5.0
    out = metric_view(pixels, is_cikm=True, pixel_scale=90.0)
    assert out.shape == (1, 2, 101, 101)
    assert out.max().item() == 90.0
    assert out.min().item() >= 0.0
    same = metric_view(pixels, is_cikm=False, pixel_scale=90.0)
    assert same.shape == (1, 2, 128, 128)


def test_contingency_uses_geq():
    pred = torch.tensor([[30.0, 29.9]])
    obs = torch.tensor([[30.0, 30.0]])
    tp, fp, fn = contingency(pred, obs, 30.0)
    assert (tp, fp, fn) == (1, 0, 1)


@pytest.mark.parametrize("s4,s10,gauss,kill,structure,go", [
    (1.19, 1.0, 0.5, True, True, False),   # ratio 1.19 < 1.2 -> kill
    (1.20, 1.0, 0.5, False, True, True),   # boundary: 1.2 passes
    (2.00, 1.0, 1.7, False, False, False),  # amplified but unstructured
    (2.00, 1.0, 1.6, False, True, True),   # 2.0/1.6 = 1.25 boundary passes
])
def test_endpoint_gates(s4, s10, gauss, kill, structure, go):
    v = evaluate_endpoint_gates(s4, s10, gauss)
    assert v["gates"]["K1_amp_ratio_kill"] is kill
    assert v["gates"]["K2_directional_structure"] is structure
    assert v["tokenizer_route_go"] is go


def test_summarize_filters_nonfinite():
    stats = summarize([1.0, 2.0, float("nan"), 3.0])
    assert stats["count"] == 3
    assert stats["median"] == pytest.approx(2.0)
    assert summarize([float("nan")]) == {"count": 0}


def test_refuse_test_path():
    with pytest.raises(SystemExit):
        refuse_test_path("nowcast_testing_full.h5")
    refuse_test_path("nowcast_validation_full.h5")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
