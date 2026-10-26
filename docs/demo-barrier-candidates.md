# Demo barrier candidates with the city works on (24 October 2026, ~13:50 UTC)

Read-only proposal for `runtime/demo/barriers.py` (owner: Codex). Nothing was published for it and the switch was not
touched. Problem: with the 24 `city-*` barriers active, the two current demo barriers no longer change São Bento →
Batalha, wheelchair 6 % ("City alerts verified", caveats). Measured on the local Valhalla (`127.0.0.1:8003`).

> **Correction (14:10 UTC): the app sends at most 20 barriers.** `excludedAreas()` in `app/app.js` (origin/main)
> keeps only the `MAX_EXCLUDED = 20` barriers nearest the straight start–destination line; the numbers below send
> all of them. With the 24 city works (48–394 m from that line) the app drops 4 city barriers (still 2.164 km), and
> candidate **A (467 m from the line) is dropped too**: in the app, city + A + B = city + all 4 = **2.236 km** (B
> only), not 2.333 km. So A as proposed does nothing in the app. Either raise `MAX_EXCLUDED` for the local
> Valhalla (it allows 1000 vertices = 200 squares) or pick positions within ~300 m of the line. Owner of
> `app.js`: Ben.

## Result

**No single point on the 2.164 km route adds ≥ 150 m.** The city detour runs through a dense grid (Aliados, Bonjardim,
Firmeza, Alves da Veiga): out of 102 on-route points, the best adds +94 m, and several make the route *shorter*
(Valhalla then picks a cheaper path, e.g. 1.234 km with a point on Rua da Firmeza). The two Praça da Liberdade points
leave no route at all (442). The best pair below adds **+169 m together**, and either one moves 0.84–0.96 km of the
drawn line onto other streets. On the map that reroute is plain to see, even though the length changes little.

| Barriers excluded (6 %) | Route | Drawn line on new streets¹ |
|---|---|---|
| none | 1.302 km, 21.4 min | — |
| 24 city only | 2.164 km, 34.5 min | — |
| city + current `demo-roadworks` | 2.164 km (no change) | — |
| city + current `demo-parked-car` | 2.164 km (no change) | — |
| city + both current | 2.164 km (no change, confirmed) | — |
| city + **A** `demo-blocked-sidewalk` | 2.258 km, 36.0 min (+94 m) | 955 m |
| city + **B** `demo-damaged-pavement` | 2.236 km, 35.7 min (+72 m) | 843 m |
| city + **A + B** | **2.333 km, 37.2 min (+169 m)** | 1 056 m |
| no city + A + B | 1.302 km (no change) | — |
| no city + current 2 | 1.856 km | — |
| no city + all 4 (current + A + B) | 1.856 km | — |
| city + all 4 | 2.333 km | — |

¹ Metres of the new route farther than 20 m from the city-only route.

So **A + B fall short of the ≥ 150 m per-barrier bar**; as a pair they pass. Appending them to the current two works
in both modes: city off 1.302 → 1.856 km (the current pair does it), city on 2.164 → 2.333 km (the new pair does it).
With A alone, the route leaves Alves da Veiga for Rua de Dom João IV / Santo Ildefonso; with both, it also passes
Largo do Padrão.

**Caveat, same as the rehearsal:** while the real app report `bmvmf2lix8tqd` (41.1466, -8.6110) is active, city on
gives **no 6 % route** (442), with or without these candidates. At 8 %: city 1.474 km, city + A + B 1.557 km (with
the report: 1.477 / 1.560 km). See [`demo-rehearsal-2026-10-24.md`](demo-rehearsal-2026-10-24.md).

## Proposed barriers

| id | kind | lat, lon | street | distance |
|---|---|---|---|---|
| `demo-blocked-sidewalk` | `blocked_sidewalk` | 41.14934, -8.60322 | Rua do Doutor Alves da Veiga | 745 m from start, 467 m from end, 545 m from the nearest city barrier |
| `demo-damaged-pavement` | `damaged_pavement` | 41.14648, -8.60402 | Rua de Santo Ildefonso | 554 m from start, 210 m from end, 396 m from the nearest city barrier |

Both sit mid-segment on the route (≥ 8 m from a shape node) and are not part of the Praça da Liberdade bottleneck.

Ready to paste into `DEMO_BARRIERS` (after the current two entries; `clear` already removes them via the `demo-`
prefix):

```python
    # City works on (24 city-* barriers): 2.164 -> 2.258 / 2.236 km alone, 2.333 km together.
    # They do not change the route with the city works off (1.302 km).
    {"id": "demo-blocked-sidewalk", "kind": "blocked_sidewalk", "lat": 41.14934, "lon": -8.60322,
     "description": "Passeio bloqueado por contentores: não há passagem."},  # city on: 2.164 -> 2.258 km
    {"id": "demo-damaged-pavement", "kind": "damaged_pavement", "lat": 41.14648, "lon": -8.60402,
     "description": "Calçada levantada, com buracos no passeio."},           # city on: 2.164 -> 2.236 km
```

The comment above `DEMO_BARRIERS` ("both together give 1.856 km") still holds for the city-off case; with all four
seeded and the city on, the route is 2.333 km.

## Probe method

Script in the session scratchpad (not in the repo); stdlib only, broker read through `barriers.connect()`.

1. Read the retained `access/barriers/+` and keep the 24 `city-*` positions (their `lat`/`lon` are there even when
   retired).
2. `POST http://127.0.0.1:8003/route` as the app does: locations São Bento (41.1455, -8.6105) → Batalha (41.1459,
   -8.6064), `costing: "pedestrian"`, `costing_options.pedestrian` = `type: "wheelchair"`, `max_grade: 6`,
   `step_penalty: 43200`; `exclude_polygons` = one closed `[lon, lat]` square per barrier, ±15 m built like
   `squareAround` in `app.js` (`dLat = 15/111320`, `dLon = 15/(111320·cos lat)`); `units: "kilometers"`,
   `language: "pt-PT"`; body sent as `text/plain`.
3. Decode `trip.legs[0].shape` (polyline, precision 6) of the city-only route and name each shape index from the
   maneuvers' `begin_shape_index`/`end_shape_index`/`street_names`.
4. Candidates: points at ¼, ½ and ¾ of every segment ≥ 24 m (½ for 10–24 m), skipping the first and last 150 m
   of the route and anything within 20 m of a city barrier: 102 points, 8 of them 442.
5. For each: route with city + candidate, length difference from 2.164 km. Then the best two on different streets
   (rounded to 5 decimals) in every combination above, plus "new street" metres (new route segments whose midpoint
   is > 20 m from every point of the city-only route).
