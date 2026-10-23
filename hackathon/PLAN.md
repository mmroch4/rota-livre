# Development plan: Passo Livre (Sat 24/10, 6 h)

How four people build [Passo Livre](README.md) in parallel. **Product and contract:** [`README.md`](README.md) (the
topic map is drafted; freeze it at kickoff). **Pitch:** [`PITCH.md`](PITCH.md). **Task board:** GitHub Issues, one per
piece below (#1 setup, #2 licence and spikes, #3–#19 the pieces), labelled by area and milestoned by checkpoint.

## How we parallelize

1. **The contract is frozen before we start.** Every topic in the map has an example message in
   `fixtures/messages/`. `scripts/replay.py` publishes them, so nobody waits for anybody: the phone app draws a route
   that no router made yet, the router reads barriers that no intake created yet.
2. **No fixed tracks: take a task, do it, take the next.** See [How we take tasks](#how-we-take-tasks).
3. **One writer per notebook at a time.** `.lotnb` files are JSON, so two people editing one notebook means a painful
   merge. Whoever holds the open issue that touches a notebook is its only writer until the issue is closed; anyone may
   *read* any notebook. If two open issues need the same notebook, the second waits or pairs.
4. **LoT ↔ Python by signature.** An Action and the Python it calls may be written by different people; the function
   signatures below are part of the contract. The Python is tested with `pytest` on the fixtures, without a broker.
5. **Everyone develops on their own broker** (`localhost`, ports bound to 127.0.0.1). The **integration broker**
   is the presentation laptop (the only one with the licence): at each checkpoint it does `git pull` + `/lot-deploy`
   and we run the demo path.
6. **Small commits to `main`**, `git pull --rebase` before pushing, `fixes #N` in the message to close the issue.

## How we take tasks

1. **Take** the open, unassigned issue from the **earliest milestone** (prefer the MVP path below), and assign it to
   yourself *before* starting: `gh issue edit N --add-assignee @me`. One issue per person at a time.
2. **Stuck for 15 minutes?** Comment on the issue and say it out loud; someone pairs with you.
3. **Done** = every box in the issue ticked, pushed with `fixes #N`. Then take the next one.
4. **Too big?** Split it: open a new issue with the same labels and milestone, and link it.

**MVP path (H+2:00), in dependency order:** #3 demo world and #5 BarrierTools → #4 barrier store → #6 city intake →
#7 router, in parallel with #13 phone app and #12 operator map (they work on fixtures from minute one).
#2 (licence and spikes) is done by whoever is at the presentation laptop at H+0:30.

The pitch is worth as much as the product: from H+3:00 at least one person is on #17 (demo script + deck), and from
H+4:30 everyone is on #18 (video + rehearsals).

Labels say what **kind** of work an issue is, not who does it: `area:lot`, `area:python`, `area:web`, `area:demo`.

## Pieces

| # | Issue | Piece | Done when (verifiable) | Needs only |
|---|-------|-------|------------------------|------------|
| P0 | #3 | Demo world | `00-setup` publishes `config/profiles`, `config/barrier_kinds`, `config/impact_rules`, `config/zone` (with the demo trips) and `config/places`; the demo trips' routes are cached (`source: "cache"`); a recorded snapshot of city alerts and weather exists; `ResetDemo` restores it | — |
| P1 | #4 | Barrier store | `ApplyBarrierEvent` folds every `passolivre/barriers/events` message into retained `passolivre/state/barriers` and `passolivre/kpi` via `BarrierTools.apply`; `ExpireBarriers` (every minute) emits `expired` | P2 (stub first) |
| P2 | #5 | BarrierTools | `pytest` green: impact rule for every city alert type in the snapshot (with **reasons**), `sync` replaces only one source, fold of every event type, expiry, weather → conditions, KPIs | config fixtures |
| P3a | #6 | City + weather intake | Connectors `CityAlerts` and `Weather` poll the urban platform; `IngestCityAlerts` → one `sync` event; `IngestWeather` → `state/conditions`. **Real data on the operator map** | P2 |
| P3b | #19 | LLM report analysis | `AnalyzeReport` uses the LLM Connector to suggest `kind` + `summary` from text (and photo); falls back to `Matcher.classify` keywords | report fixture |
| P4 | #7 | Router | `pytest` green: profile → ORS restrictions, rain → stricter restrictions, `block` barriers → `avoid_polygons`, `penalty` on the route → `warnings`, explanation texts, infeasible route; `PlanTrip` → `OrsDirections` → `ExplainRoute` publishes `trips/<id>/route` | barriers + profiles fixtures |
| P5 | #8 | Matcher | `pytest` green: same obstacle 20 m away → `confirm`, "já não está lá" → `clear`, grey zone → `review`, new → `opened` event; keyword `classify`; ReportaPorto hand-off + city email | barriers fixture |
| P6 | #9 | Trips | `HandleTripStatus` folds start/position/finish into `state/trips`; `CheckActiveTrips` runs on every barrier event and on a rain change, and publishes a reroute request + an alert for each affected trip | trips + barrier event fixtures |
| P7 | #10 | Notify + audit | The hand-off email lands in Mailpit (the "city inbox"); every barrier event and route lands in `broker/exports/audit.json` | hand-off fixture |
| P8 | #11 | Reroute with explained changes | `pytest` green: `Router.affected` (route corridor × barrier), reroute starts at `last_position`, `changes` says `+N min` and why, infeasible case explained | P4 |
| P9a | #12 | Operator map | Live map: barriers by source (colour) and impact, age of each source, rain banner, active trips with their route, KPIs, review queue for ambiguous reports | all fixtures |
| P9b | #13 | Phone app: plan + travel | Profile + destination (demo trips one tap away), route with reasons and warnings, *Start* (simulated walk along the route publishing `position`), reroute alert with the new route; stretch: places along the route | route + alert fixtures |
| P9c | #14 | Phone app: report an obstacle | `report-site/` publishes `passolivre/reports/new` (photo, confirmed pin, text) and shows the analysis, the match and the ReportaPorto hand-off | analysis/match/handoff fixtures |
| P10 | #15 | Rules | Rules as in README §5 (licensed) | everything |
| P11 | #16 | Lift simulator | `lift_sim.py` publishes `devices/<id>/status`; a key press breaks a lift; `LiftIntake` → barrier `lift_out` | — |
| P12a | #17 | Demo script + deck | Click-by-click demo script, new deck with speaker notes | README, PITCH |
| P12b | #18 | Video + rehearsals | Backup video at H+4:30, 3 timed rehearsals, Q&A drill | demo script |

## Python signatures (contract between LoT and Python)

Every argument is a JSON **string** and every function returns `json.dumps(...)` (broker 2.22.0 quirk, see `AGENTS.md`).
`now` is an ISO 8601 string.

| Function | Arguments | Returns |
|----------|-----------|---------|
| `BarrierTools.sync_city` | `alerts, impact_rules, barrier_kinds, now` | `{"event": {type: "sync", source: "city", at, data: {barriers: [Barrier]}}, "skipped": n, "error": null}` (alerts already expired or `info` for every profile are skipped) |
| `BarrierTools.conditions` | `weather, previous, zone, now` | `{"conditions": {...}, "changed": true/false}` |
| `BarrierTools.from_device` | `status, places, barrier_kinds` | `{"event": opened/cleared event or null}` |
| `BarrierTools.apply` | `index, event` | `{"index": {...}, "kpi": {...}, "audit": {...}, "error": null}` |
| `BarrierTools.expire` | `index, now` | `{"event": {type: "expired", data: {barrier_ids: [...]}} or null}` |
| `Matcher.classify` | `report, barrier_kinds` | an `analysis` payload with `source: "keywords"` |
| `Matcher.match` | `report, analysis, index, barrier_kinds` | `{"match": {...}, "event": {...} or null, "handoff": {...}, "email": {...}}` |
| `Router.build_request` | `request, profiles, barrier_kinds, index, conditions, version` | `{"ors": {trip_id, version, body}, "avoided": [{barrier_id, why}]}` |
| `Router.explain` | `request, response, index, barrier_kinds, conditions, previous_route` (`""` if none) | the Route, with `changes` vs. `previous_route` |
| `Router.affected` | `trips, trigger, index, conditions` (`trigger` = the barrier event or the new conditions) | `{"requests": [trip request], "alerts": [alert]}` |

## Notebooks

| Notebook | Issues | Contents |
|----------|--------|----------|
| `00-setup.lotnb` | #3 | Retained config; the `ResetDemo` Action |
| `10-sources.lotnb` | #6 | Connectors `CityAlerts`, `Weather`; Actions `IngestCityAlerts`, `IngestWeather` |
| `15-barrier-tools.lotnb` | #5 | `BarrierTools` Python only |
| `20-barriers.lotnb` | #4 | `Barrier` Model, `ApplyBarrierEvent`, `ExpireBarriers` |
| `30-reports.lotnb` | #19 | `Report` Model, `AnalyzeReport`, LLM Connector |
| `35-match.lotnb` | #8 | `MatchReport`, `Matcher` Python |
| `40-router.lotnb` | #7, #11 | `PlanTrip`, `ExplainRoute`, Connector `OrsDirections`, `Router` Python |
| `50-trips.lotnb` | #9 | `HandleTripStatus`, `CheckActiveTrips` |
| `60-notify.lotnb` | #10 | `Mailer` and `AuditLog` Connectors |
| `65-devices.lotnb` | #16 | `LiftIntake` |
| `70-rules.lotnb` | #15 | Rules |

## Timeline

| When | Goal (verifiable) | Integration check on the presentation laptop |
|------|-------------------|----------------------------------------------|
| **H+0:00** | 15-min kickoff: walk the topic map, **freeze it**, everyone takes a first issue, `replay.py` works on every laptop | — |
| **H+0:30** | Licence active; spikes answered (REST POST body, ORS steepness, `TYPE LLM`) → plan B decided (see below) | `curl localhost:9100/license` |
| **H+1:00** | P0 demo world · P2 impact rules + fold tests green · P1 store from fixture events · P9a barriers on the map from fixtures · P9b route drawn from the fixture | fixture barriers on the operator map |
| **H+2:00** | **MVP:** real city alerts → barriers → trip request → ORS route that avoids them, **with reasons**, on the phone. *From here there is always a demo.* | full path, no reroute, no LLM |
| **H+3:00** | P6 + P8 **reroute on a new barrier** (the key moment) · P5 citizen report → barrier · P3b LLM · lunch · someone takes #17 (pitch) | demo path with a reroute |
| **H+4:00** | Rain → stricter route · P7 hand-off email · P9c report form · P11 lifts · P10 Rules · polish | full demo path, timed |
| **H+4:30** | **Feature freeze.** Record the backup video. Only bug fixes from here. | backup video recorded |
| **H+4:30 → 6:00** | Pitch: 3 timed rehearsals on the presentation laptop, Q&A drill, `ResetDemo` | — |

## H+0:30: licence and spikes

The licence code goes in `broker/.env` (`COREFLUX_ACTIVATION_CODE=CFLX-...`) **only on the presentation laptop**, or is
activated from the HUB (each activation uses a seat, and it is bound to the machine). Then `curl -s
localhost:9100/license` and read `tier` and `effectiveLimits`.

| If… | Then |
|-----|------|
| The REST Connector can POST a body built from the payload | `OrsDirections` in the broker (best architecture story) |
| It cannot | `services/ors_gateway.py`, same two topics (`ors/request` → `ors/response`); say so honestly in the pitch |
| ORS `wheelchair` avoids the steep streets of the demo trips | Use it as is |
| It does not (incline from OSM tags is sparse) | `Router.explain` reads `extra_info.steepness` and warns on every segment above the profile limit; slope model from elevation goes to "next steps" |
| `TYPE LLM` deploys | P3b in the broker: `CALL LLM` in `AnalyzeReport` |
| It is refused | keywords only (`Matcher.classify`); the LLM goes to "next steps" |

Developer laptops stay on Community: fine for everything except more than 3 Connectors, the LLM Connector and Rules.
Develop with the Connectors you own and stub the rest with `replay.py`.

## Spikes still to run (tonight or H+0)

| Risk | Why it matters | Fallback |
|------|----------------|----------|
| REST Connector: dynamic POST body, and polling every N seconds | `OrsDirections` and the two source Connectors | `ors_gateway.py`; a time-triggered Action (`ON EVERY …`, check the `lot-actions` skill) that triggers the GET |
| ORS response size in `CALL PYTHON` | the GeoJSON of a route can be large | `instructions: false`, `geometry_simplify: true`, `elevation: false` unless needed |
| ORS on the event Wi-Fi / quota | routing is the core | cached routes for the demo trips (`source: "cache"`) |
| FIWARE on the event Wi-Fi | the "real data" argument | recorded snapshot, replayed with its original timestamps |
| One message per affected trip from a list | `Router.affected` returns a list | the demo has one active trip; `REPEAT … UNTIL` + a Python indexer; or a self-draining queue topic |
| Simulated walk along the route | the reroute must start "from where the person is" | the phone app advances along `geometry` on a timer and publishes `position` |
| Leaflet tiles on the event Wi-Fi | both views are maps | markers and route on a blank background (offline) |
| `GET TOPIC` of a retained JSON document as `STRING` inside an Action | every Action reads a store | read it as `STRING` and pass it to Python as is (`AS ARRAY` fails, see the skill) |

Already verified with earlier ideas on broker 2.22.0 (still valid): `CALL PYTHON` speed and the `str` return rule,
MQTT over WebSocket (opt-in), EMAIL to Mailpit, FILE_STORAGE as JSON, REST Connector with `{payload.json.x}` in the
endpoint, notebook per feature, LLM Connector refused on Community.

## Entity budget (licensed)

Actions: ~12 (`IngestCityAlerts`, `IngestWeather`, `LiftIntake`, `AnalyzeReport`, `MatchReport`, `ApplyBarrierEvent`,
`ExpireBarriers`, `PlanTrip`, `ExplainRoute`, `HandleTripStatus`, `CheckActiveTrips`, `ResetDemo`) + 3 Python scripts.
Connectors: 6 (`CityAlerts`, `Weather`, `OrsDirections`, LLM, `Mailer`, `AuditLog`): **above the Community limit of 3**,
so the integration broker must be licensed. Models: `Report`, `Barrier`, maybe `TripRequest`.

## Tonight (23/10): prep only, no product code

- [x] New idea written into the docs, contract drafted, fixtures + `replay.py`
- [x] Task board rewritten for Passo Livre: issues #1–#19
- [ ] Everyone: read README §2–3 and the topic map; bring objections to the kickoff
- [ ] Everyone: `git pull`, `chmod 777 hackathon/broker/exports`, `docker compose up -d`,
      `scripts/mcp_token.py`, then `scripts/replay.py --list` works
- [ ] Presentation laptop: activate the licence, check `localhost:9100/license`
- [ ] **OpenRouteService key** (free sign-up), tested with `curl` on São Bento → Praça da Ribeira, `wheelchair`
      profile; keep it out of git
- [ ] Anthropic API key with credit (LLM Connector); keep it out of git
- [ ] Optional head start on #17 (new deck and first demo script) and #3 (demo trips that show a visible detour)
- [ ] Skim what you might take: web → Leaflet + mqtt.js over `ws://localhost:9001/mqtt`; Python → the `python-scripts`
      skill and the [Python integration](https://docs.coreflux.org/latest/lot-language/actions/python-integration.md) page;
      LoT → the `lot-actions`, `lot-models` and `lot-routes` skills
- [ ] Sleep
