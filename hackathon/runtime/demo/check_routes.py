#!/usr/bin/env python3
"""Read-only regression check for the demo's Valhalla barrier detours.

Run: python3 hackathon/runtime/demo/check_routes.py [http://127.0.0.1:8003]
Uses the standard library; does not publish MQTT messages or change broker state.
This checks routing responses, not browser/MQTT integration or accessibility safety.
"""
import argparse
import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from barriers import CONTROL_BARRIER, DEMO_BARRIERS


def exclusion(barrier):
    """Match the app's closed 15 metre half-width square, in longitude/latitude."""
    lat, lon = barrier["lat"], barrier["lon"]
    dy = 15 / 111320
    dx = dy / math.cos(math.radians(lat))
    return [[lon - dx, lat - dy], [lon + dx, lat - dy],
            [lon + dx, lat + dy], [lon - dx, lat + dy], [lon - dx, lat - dy]]


def post(base, path, body):
    request = Request(base + path, data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"{path}: HTTP {error.code}: {error.read().decode()}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures = []
    results = {}

    def check(label, condition):
        print(f"{'PASS' if condition else 'FAIL'}: {label}")
        if not condition:
            failures.append(label)

    cases = [("baseline", []), ("control", [CONTROL_BARRIER])]
    cases += [(b["id"], [b]) for b in DEMO_BARRIERS]
    cases += [("both", DEMO_BARRIERS), ("reset", [])]
    for name, barriers in cases:
        options = {"pedestrian": {"type": "wheelchair", "max_grade": 6,
                                  "step_penalty": 43200}}
        trip = post(base, "/route", {
            "locations": [{"lat": 41.1455, "lon": -8.6105},
                          {"lat": 41.1459, "lon": -8.6064}],
            "costing": "pedestrian", "costing_options": options,
            "exclude_polygons": [exclusion(b) for b in barriers],
            "units": "kilometers", "language": "pt-PT",
        })["trip"]
        shape = trip["legs"][0]["shape"]
        length = trip["summary"]["length"]
        results[name] = (shape, length)
        print(f"{name}: {length:.3f} km, {trip['summary']['time'] / 60:.1f} min")
        edges = post(base, "/trace_attributes", {
            "encoded_polyline": shape, "shape_match": "edge_walk",
            "costing": "pedestrian", "costing_options": options,
            "filters": {"action": "include", "attributes": [
                "edge.max_upward_grade", "edge.max_downward_grade"]},
        })["edges"][1:-1]
        # Custom local Valhalla stores these grades as percent. Endpoint partial
        # edges bypass the cap, so this deliberately checks only interior edges.
        check(f"{name}: interior grades within 6%", bool(edges) and all(
            0 <= e["max_upward_grade"] <= 6 and -6 <= e["max_downward_grade"] <= 0
            for e in edges))

    baseline_shape, baseline_length = results["baseline"]
    for name in [b["id"] for b in DEMO_BARRIERS] + ["both"]:
        shape, length = results[name]
        check(f"{name}: different, longer route", shape != baseline_shape and length > baseline_length)
    check("off-route control leaves geometry unchanged", results["control"] == results["baseline"])
    check("removing exclusions restores baseline", results["reset"] == results["baseline"])
    if failures:
        return 1
    print("PASS: demo detours and interior slope caps; browser/MQTT integration not checked.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, URLError, ValueError, KeyError, IndexError, TypeError, RuntimeError) as error:
        raise SystemExit(f"FAIL: {error}") from error
