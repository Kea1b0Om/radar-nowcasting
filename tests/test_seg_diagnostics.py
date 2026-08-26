"""Synthetic gates for the segmentation-theoretic diagnostics.

Each test pins the property the corresponding figure will be read for:
PQ must separate "detected but displaced" from "not detected"; the
fragmentation counter must fire where pixel CSI cannot; best-member must be
a max, not an average; GED must vanish for a perfect collapsed ensemble.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.seg_diagnostics import (  # noqa: E402
    binary_components,
    iou_pair,
    panoptic_stats,
)


def square(h=64, w=64, r0=10, c0=10, rs=10, cs=10):
    f = np.zeros((h, w), dtype=bool)
    f[r0:r0 + rs, c0:c0 + cs] = True
    return f


def test_pq_separates_displacement_from_miss():
    obs = square()
    shifted3 = square(c0=13)          # IoU = 70/130 ~ 0.538 > 0.5: matched
    iou_sum, tp, fp, fn = panoptic_stats(shifted3, obs)
    assert (tp, fp, fn) == (1, 0, 0)          # RQ = 1: detected
    assert abs(iou_sum - 70.0 / 130.0) < 1e-9  # SQ carries the displacement
    # pixel CSI books the same case as half miss + half false alarm
    assert abs(iou_pair(shifted3, obs) - 70.0 / 130.0) < 1e-9

    shifted6 = square(c0=16)          # IoU = 40/160 = 0.25 < 0.5: unmatched
    iou_sum, tp, fp, fn = panoptic_stats(shifted6, obs)
    assert (tp, fp, fn) == (0, 1, 1)          # RQ = 0: counted as miss + FA


def test_fragmentation_fires_where_csi_is_blind():
    obs = np.zeros((32, 200), dtype=bool)
    obs[10:20, 5:195] = True                       # one long band
    pred = obs.copy()
    pred[:, 5:195:10] = False                      # slice into shards
    csi = iou_pair(pred, obs)
    assert csi > 0.85                              # pixel overlap barely moves
    _, n_obs = binary_components(obs)
    _, n_pred = binary_components(pred)
    assert n_obs == 1 and n_pred >= 15             # fragmentation explodes


def test_speckle_filter():
    f = np.zeros((32, 32), dtype=bool)
    f[2:12, 2:12] = True                           # real object
    f[20, 20] = True                               # 1-px speckle
    _, n = binary_components(f)
    assert n == 1


def test_best_member_is_max_and_ged_zero_when_perfect():
    obs = square()
    members = np.stack([square(c0=16), obs.copy(), square(c0=13)])
    ious = [iou_pair(m, obs) for m in members]
    assert max(ious) == 1.0 and np.mean(ious) < 1.0
    # perfect collapsed ensemble: accuracy term 0, diversity term 0 -> GED 0
    perfect = np.stack([obs, obs, obs])
    acc = np.mean([1.0 - iou_pair(m, obs) for m in perfect])
    div = np.mean([1.0 - iou_pair(perfect[i], perfect[j])
                   for i in range(3) for j in range(i + 1, 3)])
    assert 2.0 * acc - div == 0.0
