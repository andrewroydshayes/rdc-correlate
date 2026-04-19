import math

from rdc_correlate.correlate import (
    align_nearest,
    best_scale,
    correlate_all,
    group_cloud_by_path,
    group_wire_by_param,
    pearson,
)


def test_pearson_perfect_positive():
    assert abs(pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) - 1.0) < 1e-9


def test_pearson_perfect_negative():
    assert abs(pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2]) + 1.0) < 1e-9


def test_pearson_handles_short_sequences():
    assert pearson([1, 2], [3, 4]) == 0.0  # n<3


def test_best_scale_identifies_x10_ratio():
    xs = [120, 121, 122, 123]
    ys = [1200.0, 1210.0, 1220.0, 1230.0]
    k, r = best_scale(xs, ys)
    assert abs(k - 10.0) < 1e-6
    assert r > 0.99


def test_align_nearest_basic():
    a = [(0, 1.0), (10, 2.0), (20, 3.0)]
    b = [(1, 100.0), (11, 200.0), (21, 300.0)]
    xs, ys = align_nearest(a, b, max_gap_s=5)
    assert xs == [1.0, 2.0, 3.0]
    assert ys == [100.0, 200.0, 300.0]


def test_align_drops_samples_too_far_apart():
    a = [(0, 1.0), (100, 2.0)]
    b = [(1, 10.0), (1000, 20.0)]
    xs, ys = align_nearest(a, b, max_gap_s=10)
    # First a pairs with first b (gap 1). Second a's nearest is (1000) gap 900>10, skipped.
    assert xs == [1.0]
    assert ys == [10.0]


def test_group_wire_by_param_uses_i32_first():
    rows = [
        (1.0, 0x044C, 4, 3600, None),
        (2.0, 0x044C, 4, 3610, None),
        (1.0, 0x05DC, 8, None, 1234567890),
    ]
    out = group_wire_by_param(rows)
    assert out[0x044C] == [(1.0, 3600), (2.0, 3610)]
    assert out[0x05DC] == [(1.0, 1234567890)]


def test_correlate_all_finds_matching_pair():
    # 30 samples, y = x/10
    wire = {0x0453: [(t, 130 + t) for t in range(30)]}
    cloud = {"batteryVoltageV": [(t, 13.0 + t / 10.0) for t in range(30)]}
    findings = correlate_all(wire, cloud, min_n=10, r_threshold=0.9)
    assert len(findings) == 1
    f = findings[0]
    assert f["param_id"] == 0x0453
    assert f["cloud_path"] == "batteryVoltageV"
    assert f["r"] > 0.99


def test_correlate_all_skips_below_threshold():
    import random
    random.seed(0)
    wire = {0xAAAA: [(t, random.random()) for t in range(50)]}
    cloud = {"unrelated": [(t, random.random()) for t in range(50)]}
    findings = correlate_all(wire, cloud, min_n=10, r_threshold=0.9)
    assert findings == []
