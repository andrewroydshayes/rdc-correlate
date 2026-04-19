"""Pearson correlation between wire-record streams and cloud-field streams,
restricted to a time window and optionally to engine-running samples."""

import math
from collections import defaultdict


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def best_scale(xs, ys):
    """If y = k * x, return k (median ratio for robustness) and the Pearson r."""
    ratios = []
    for x, y in zip(xs, ys):
        if x != 0:
            ratios.append(y / x)
    if not ratios:
        return 1.0, 0.0
    ratios.sort()
    k = ratios[len(ratios) // 2]
    r = pearson(xs, ys)
    return k, r


def group_wire_by_param(rows):
    """rows: iterable of (ts, param_id, vlen, v32, v64) tuples."""
    out = defaultdict(list)
    for ts, pid, vlen, v32, v64 in rows:
        val = v32 if v32 is not None else v64
        if val is None:
            continue
        out[pid].append((ts, val))
    return out


def group_cloud_by_path(rows):
    """rows: iterable of (ts, path, value, value_text) tuples (only numeric values)."""
    out = defaultdict(list)
    for ts, path, value, value_text in rows:
        if value is None:
            continue
        out[path].append((ts, float(value)))
    return out


def align_nearest(a, b, max_gap_s=60):
    """Given two sorted lists of (ts, v), pair each a-entry with the nearest b
    entry within max_gap_s. Returns (xs, ys) as aligned lists."""
    xs, ys = [], []
    j = 0
    for ts, va in a:
        while j + 1 < len(b) and abs(b[j + 1][0] - ts) <= abs(b[j][0] - ts):
            j += 1
        if not b:
            break
        if abs(b[j][0] - ts) <= max_gap_s:
            xs.append(va)
            ys.append(b[j][1])
    return xs, ys


def correlate_all(wire_series, cloud_series, min_n=20, r_threshold=0.90):
    """For every (param_id, cloud_path) pair, compute Pearson r on time-aligned samples.
    Returns sorted list of dicts for the best match per param_id above r_threshold."""
    per_param_best = {}
    for pid, wire_pts in wire_series.items():
        for path, cloud_pts in cloud_series.items():
            xs, ys = align_nearest(wire_pts, cloud_pts)
            if len(xs) < min_n:
                continue
            k, r = best_scale(xs, ys)
            if r < r_threshold:
                continue
            existing = per_param_best.get(pid)
            if existing is None or r > existing["r"]:
                per_param_best[pid] = {
                    "param_id": pid,
                    "cloud_path": path,
                    "n": len(xs),
                    "r": round(r, 4),
                    "scale": round(k, 4),
                }
    out = list(per_param_best.values())
    out.sort(key=lambda d: (-d["r"], d["param_id"]))
    return out
