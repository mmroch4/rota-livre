#!/usr/bin/env python3
"""Verify service, a basic Porto route and the slope cap; does not certify accessibility.

Edge slopes from /trace_attributes (max_upward_grade, max_downward_grade) are labelled degrees
but are percent over a 60 m posting, the unit max_grade is compared with. The origin and
destination partial edges are not checked against the cap, so only interior edges are asserted.
"""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8003"
with urlopen(base + "/status", timeout=10) as response:
    status = json.load(response)
print("Service:", json.dumps(status, sort_keys=True))


def post(path, body):
    """POST JSON; return (body, None) or (None, Valhalla error code)."""
    request = Request(
        base + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response), None
    except HTTPError as error:
        return None, json.load(error).get("error_code")


def route(origin, destination, pedestrian=None, date_time_type=None):
    """Route a pair; returns the trip, or None when no path meets the limits (442)."""
    body = {
        "locations": [
            {"lat": origin[0], "lon": origin[1]},
            {"lat": destination[0], "lon": destination[1]},
        ],
        "costing": "pedestrian",
        "costing_options": {"pedestrian": pedestrian or {}},
        "units": "kilometers",
    }
    # depart_at runs the forward-only search (Allowed), arrive_by the reverse-only one
    # (AllowedReverse); without date_time a short route may use either.
    if date_time_type:
        body["date_time"] = {"type": date_time_type, "value": "2026-10-24T12:00"}
    result, error = post("/route", body)
    if error == 442:
        return None
    if error is not None:
        raise SystemExit(f"Route failed with error {error}: {origin} -> {destination}")
    return result["trip"]


def interior_grades(trip):
    """Steepest uphill and downhill (positive) over the interior edges of a route."""
    trace, error = post("/trace_attributes", {
        "encoded_polyline": trip["legs"][0]["shape"],
        "shape_match": "edge_walk",
        "costing": "pedestrian",
        "filters": {"action": "include", "attributes": [
            "edge.length", "edge.max_upward_grade", "edge.max_downward_grade",
        ]},
    })
    if error is not None or not trace.get("edges"):
        raise SystemExit(f"Trace failed with error {error}")
    edges = trace["edges"][1:-1]
    return (max([0] + [e["max_upward_grade"] for e in edges]),
            max([0] + [-e["max_downward_grade"] for e in edges]))


failures = []


def check(name, ok, detail):
    print(("ok   " if ok else "FAIL ") + name + ": " + detail)
    if not ok:
        failures.append(name)


def capped(name, origin, destination, cap, pedestrian=None, date_time_type=None):
    """Route under a cap and assert no interior edge exceeds it; returns the trip."""
    options = dict(pedestrian or {}, max_grade=cap)
    trip = route(origin, destination, options, date_time_type)
    if trip is None:
        print(f"     {name}: no route at {cap} %")
        return None
    up, down = interior_grades(trip)
    check(name, up <= cap and down <= cap,
          f"{trip['summary']['length']:.3f} km, steepest up {up} % / down {down} % at cap {cap} %")
    return trip


# 1. Basic route and trace: Aliados, the pair the public instance also answers (0.388 km).
aliados = ((41.1466, -8.6110), (41.1496, -8.6109))
trip = route(*aliados)
check("basic route", trip is not None and trip["legs"], f"{trip['summary']['length']:.3f} km")
up, down = interior_grades(trip)
print(f"     Aliados steepest interior edge: up {up} %, down {down} %")

# 2. Gentle case: the cap at the route's own steepest grade keeps the same route.
gentle = capped("gentle (cap = steepest)", *aliados, max(up, down))
check("gentle route unchanged", gentle is not None
      and gentle["legs"][0]["shape"] == trip["legs"][0]["shape"], "same geometry as uncapped")

# 3. Steep uphill and downhill on the same edge: a footway (way 1302664398) that climbs
#    ~13 % northbound. Both directions use it above the cap and avoid it below; forward
#    and reverse searches agree.
south, north = (41.141857, -8.614406), (41.142476, -8.614126)
STEEP = 13
for label, origin, destination in (("uphill", south, north), ("downhill", north, south)):
    over = capped(f"steep {label}, cap above", origin, destination, STEEP + 2)
    check(f"steep {label} uses the edge", over is not None
          and max(interior_grades(over)) >= STEEP, f"steepest interior >= {STEEP} %")
    for dt, search in ((None, "default"), (1, "forward"), (2, "reverse")):
        under = capped(f"steep {label}, cap below, {search} search", origin, destination,
                       STEEP - 1, date_time_type=dt)
        # A gentler detour exists (0.130 km), so no route here would mean an over-strict cap.
        check(f"steep {label} detours, {search} search",
              under is not None and max(interior_grades(under)) < STEEP,
              "no route" if under is None else f"{under['summary']['length']:.3f} km")

# 4. Demo pair (wheelchair profile, as the app sends it): a stricter cap makes the route
#    longer and gentler instead of returning no route.
sao_bento, batalha = (41.1455, -8.6105), (41.1459, -8.6064)
free = route(sao_bento, batalha)
wheelchair = {"type": "wheelchair", "step_penalty": 43200}
lengths = [free["summary"]["length"]]
for cap in (10, 8, 6):
    demo = capped(f"demo Sao Bento -> Batalha, {cap} %", sao_bento, batalha, cap, wheelchair)
    lengths.append(demo["summary"]["length"] if demo else float("inf"))
check("demo detour grows as the cap tightens", lengths == sorted(lengths) and lengths[-1]
      < float("inf") and lengths[-1] > lengths[0], " -> ".join(f"{x:.2f}" for x in lengths) + " km")

if failures:
    raise SystemExit("FAIL: " + ", ".join(failures))
print("PASS: routing and slope cap on known cases; not an accessibility certification.")
