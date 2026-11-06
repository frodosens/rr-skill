#!/usr/bin/env python3
"""Pure-Python left-traffic convention checks and planning-schema preflight.

No Godot integration, rendering, legal certification, or external file writes.
"""
import argparse
import json
import math
from pathlib import Path


def frame(forward_xz, direction, lane_center_m):
    x, z = forward_xz
    length = math.hypot(x, z)
    if not math.isfinite(length) or length <= 0 or direction not in (-1, 1):
        raise ValueError("Nonzero finite tangent and direction +1/-1 required")
    if not math.isfinite(lane_center_m) or lane_center_m <= 0:
        raise ValueError("Positive finite lane center distance required")
    f = (x / length, z / length)
    right = (-f[1], f[0])  # F cross UP, projected into XZ.
    return {"lane_xz": tuple(v * -direction * lane_center_m for v in right),
            "driver_forward_xz": tuple(v * direction for v in f),
            "driver_right_xz": tuple(v * direction for v in right)}


def dash_on(station, dash_m=3.0, gap_m=5.0, phase_m=0.0):
    return (station - phase_m) % (dash_m + gap_m) < dash_m


def example():
    return {"roads": [{"road_id": "sample", "station_basis": "planar_xz_metres",
        "start_m": 0, "end_m": 80, "road_width_m": 7,
        "two_way_left_traffic_design": True, "center_guidance": True,
        "priority": None, "stop_required": None, "speed_limit": None,
        "allowed_turns": None, "turnaround_allowed": None,
        "source_rule": "game_design", "review_status": "proposed"}]}


def validate(data):
    errors = []
    roads = data.get("roads") if isinstance(data, dict) else None
    if not isinstance(roads, list) or not roads:
        return ["roads must be a nonempty list"]
    seen = set()
    required = set(example()["roads"][0])
    for i, row in enumerate(roads):
        prefix = f"roads[{i}]"
        if not isinstance(row, dict):
            errors.append(prefix + " must be an object")
            continue
        missing = required - set(row)
        if missing:
            errors.append(prefix + " missing: " + ", ".join(sorted(missing)))
            continue
        rid = row["road_id"]
        if not isinstance(rid, str) or not rid or rid in seen:
            errors.append(prefix + " road_id must be a unique nonempty string")
        else:
            seen.add(rid)
        if row["station_basis"] not in ("planar_xz_metres", "curve3d_baked_metres"):
            errors.append(prefix + " has an unknown station basis")
        nums = [row[k] for k in ("start_m", "end_m", "road_width_m")]
        if any(type(n) not in (int, float) or not math.isfinite(n) for n in nums):
            errors.append(prefix + " requires finite numeric range and width")
            continue
        start, end, width = nums
        if not 0 <= start < end or width <= 0:
            errors.append(prefix + " requires 0 <= start < end and positive width")
        if type(row["center_guidance"]) is not bool or type(row["two_way_left_traffic_design"]) is not bool:
            errors.append(prefix + " guidance and traffic-design flags must be booleans")
        if row["center_guidance"] and (width < 6 or row["two_way_left_traffic_design"] is not True):
            errors.append(prefix + " fails the 016-style design gate (not a legal rule)")
        if row["review_status"] not in ("proposed", "reviewed", "implemented", "verified_scope"):
            errors.append(prefix + " has unknown review_status")
        if not isinstance(row["source_rule"], str) or not row["source_rule"].strip():
            errors.append(prefix + " needs a source_rule")
        for flag in ("stop_required", "turnaround_allowed"):
            if row[flag] is not None and type(row[flag]) is not bool:
                errors.append(prefix + " " + flag + " must be true, false, or null")
    return errors


def self_test():
    for forward in ((0, -1), (1, 0), (0, 1), (-1, 0), (3, -4)):
        for d in (-1, 1):
            f = frame(forward, d, 1.75)
            lane, right = f["lane_xz"], f["driver_right_xz"]
            assert math.isclose(sum(a*b for a, b in zip(lane, right)), -1.75)
            # Rotating both text axes 180 degrees does not reflect glyphs.
            front = f["driver_forward_xz"]
            assert math.isclose(sum(a*b for a, b in zip(front, right)), 0, abs_tol=1e-12)
            other = frame(forward, -d, 1.75)
            assert all(math.isclose(a, -b) for a, b in zip(front, other["driver_forward_xz"]))
            assert all(math.isclose(a, -b) for a, b in zip(right, other["driver_right_xz"]))
    assert frame((0, -1), 1, 1.75)["lane_xz"] == (-1.75, -0.0)
    assert frame((0, -1), -1, 1.75)["lane_xz"] == (1.75, 0.0)
    assert dash_on(128) == dash_on(0) and not dash_on(131)
    assert dash_on(127.9) is False and dash_on(128.1) is True
    assert not validate(example())
    invalid = example()
    invalid["roads"][0]["road_width_m"] = 4.4
    assert validate(invalid)
    assert validate({"roads": [{"road_id": "missing-fields"}]})
    invalid = example()
    invalid["roads"][0]["stop_required"] = 1
    assert validate(invalid)
    for bad in ((0, 0), (float("nan"), 1)):
        try:
            frame(bad, 1, 1.75)
        except ValueError:
            pass
        else:
            raise AssertionError("Bad tangent must fail")
    print("PASS: convention self-tests; no game-world validation claimed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--example", action="store_true")
    parser.add_argument("--rules", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
    if args.example:
        print(json.dumps(example(), ensure_ascii=False, indent=2))
    if args.rules:
        try:
            problems = validate(json.loads(args.rules.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            problems = [str(exc)]
        print(json.dumps({"status": "FAIL" if problems else "PREFLIGHT_PASS",
                          "errors": problems,
                          "scope": "Planning schema only; no legal, geometric, or runtime acceptance"}, indent=2))
        raise SystemExit(bool(problems))
    if not (args.self_test or args.example or args.rules):
        parser.print_help()
