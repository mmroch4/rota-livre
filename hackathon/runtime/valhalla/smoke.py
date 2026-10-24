#!/usr/bin/env python3
"""Verify service, a basic Porto route and the slope cap; does not certify accessibility."""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8003"
with urlopen(base + "/status", timeout=10) as response:
    status = json.load(response)
print("Service:", json.dumps(status, sort_keys=True))
payload = {
    "locations": [
        {"lat": 41.1466, "lon": -8.6110},
        {"lat": 41.1496, "lon": -8.6109},
    ],
    "costing": "pedestrian",
    "units": "kilometers",
}
request = Request(
    base + "/route", data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
with urlopen(request, timeout=20) as response:
    route = json.load(response)
trip = route["trip"]
if trip["status"] != 0 or not trip.get("legs"):
    raise SystemExit("Route smoke test failed: " + json.dumps(route))
print("Route:", json.dumps({
    "status": trip["status"], "summary": trip["summary"],
    "legs": len(trip["legs"]),
}, sort_keys=True))
trace_request = Request(
    base + "/trace_attributes",
    data=json.dumps({
        "encoded_polyline": trip["legs"][0]["shape"],
        "shape_match": "edge_walk",
        "costing": "pedestrian",
        "filters": {"action": "include", "attributes": [
            "edge.length", "edge.max_upward_grade", "edge.max_downward_grade",
        ]},
    }).encode(),
    headers={"Content-Type": "application/json"},
)
with urlopen(trace_request, timeout=20) as response:
    trace = json.load(response)
if not trace.get("edges"):
    raise SystemExit("Trace smoke test returned no edges")
print("Trace:", json.dumps({"edges": len(trace["edges"]), "first_edge": trace["edges"][0]}))


def capped_route_found(max_grade):
    """Route the same pair with a slope cap; True if a path exists."""
    capped = dict(payload, costing_options={"pedestrian": {"max_grade": max_grade}})
    request = Request(
        base + "/route", data=json.dumps(capped).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=20):
            return True
    except HTTPError as error:
        if json.load(error).get("error_code") == 442:  # no path found
            return False
        raise


# Aliados climbs ~8% (inner edges peak at 4 degrees, ~7%) on the pinned Porto data:
# an 8% cap must allow it and a 6% cap must block it.
if not capped_route_found(8) or capped_route_found(6):
    raise SystemExit("Slope cap smoke test failed: expected 8% allowed, 6% blocked")
print("Slope cap: max_grade=8 allowed, max_grade=6 blocked")
print("PASS: routing and slope cap on one known case; not an accessibility certification.")
