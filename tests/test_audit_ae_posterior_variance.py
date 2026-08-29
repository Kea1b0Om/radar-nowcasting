"""Pins for the posterior-variance audit's pure math (VE-Loss diagnostic A).

Properties pinned:
  * band edges follow the repo's '>=' convention exactly (20.0 dBZ is wet,
    19.99 is dry) -- the CIKM uint8 code 85 lands on exactly 30.0 dBZ, so
    the operator matters;
  * receptive-patch pooling takes the max over the latent site's 8x8 pixel
    footprint (here scaled down);
  * the two pre-registered gates split the sigma^2 axis into
    collapse (< 1e-3) / inconclusive / premise-absent (>= 1e-2) with the
    boundaries landing on the documented sides.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audit_ae_posterior_variance import (  # noqa: E402
    assign_bands,
    evaluate_posterior_gates,
    patch_pool_max,
    refuse_test_path,
    select_event_rows,
    summarize_sigma2,
)


def test_patch_pool_max():
    frame = np.zeros((1, 4, 4), dtype=np.float32)
    frame[0, 0, 0] = 5.0   # patch (0, 0)
    frame[0, 1, 1] = 7.0   # same patch, larger
    frame[0, 2, 3] = 9.0   # patch (1, 1)
    pooled = patch_pool_max(frame, 2)
    assert pooled.shape == (1, 2, 2)
    assert pooled[0, 0, 0] == 7.0
    assert pooled[0, 0, 1] == 0.0
    assert pooled[0, 1, 1] == 9.0


def test_patch_pool_max_rejects_indivisible():
    with pytest.raises(ValueError):
        patch_pool_max(np.zeros((1, 5, 4)), 2)


@pytest.mark.parametrize("dbz,band", [
    (0.0, 0), (19.99, 0),          # dry
    (20.0, 1), (29.99, 1),         # '>=' at the left edge
    (30.0, 2), (34.99, 2),
    (35.0, 3), (39.99, 3),
    (40.0, 4), (90.0, 4),
])
def test_assign_bands_edge_convention(dbz, band):
    assert assign_bands(np.asarray([dbz]))[0] == band


def test_summarize_sigma2():
    stats = summarize_sigma2(np.arange(1, 101, dtype=np.float64))
    assert stats["count"] == 100
    assert stats["median"] == pytest.approx(50.5)
    assert stats["p10"] == pytest.approx(np.percentile(np.arange(1, 101), 10))
    assert summarize_sigma2(np.asarray([])) == {"count": 0}


@pytest.mark.parametrize("median,present,absent,inconclusive", [
    (1e-4, True, False, False),     # collapsed -> VE premise present
    (5e-3, False, False, True),     # between the gates
    (5e-2, False, True, False),     # healthy variance -> VE premise absent
    (1e-3, False, False, True),     # boundary: collapse is strict '<'
    (1e-2, False, True, False),     # boundary: absence is '>='
])
def test_posterior_gates(median, present, absent, inconclusive):
    v = evaluate_posterior_gates(median)
    assert v["gates"]["V1_variance_collapse_premise_present"] is present
    assert v["gates"]["V2_premise_absent_VE_NOGO"] is absent
    assert v["inconclusive"] is inconclusive


def test_select_event_rows_is_stable():
    a = select_event_rows(500, 50)
    assert a == select_event_rows(500, 50) == sorted(a)
    assert len(a) == 50


def test_refuse_test_path():
    with pytest.raises(SystemExit):
        refuse_test_path("nowcast_testing_full.h5")
    refuse_test_path("nowcast_validation_full.h5", None)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
