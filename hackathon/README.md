# Hackathon — Coreflux solution

> **Status:** idea changed on 23/10 (late evening) from *Rua Viva* (citizen reports → crew plans, see git history up
> to `c101ca9`) to **Passo Livre**. Before that it was *Vale* (up to `8245603`). The structure follows the 4 points
> the jury judges on (Rules, Art. 1, 3): **problem → demo → architecture → maturity**. Anything marked ⚠️ **verify**
> must be confirmed tonight or in the first hour.

**Product name:** **Passo Livre** (Portuguese for "free step" / "clear way").
**One sentence:** *Passo Livre gives people with reduced mobility in Porto a route they can actually take, and changes
it while they walk when the street changes.*

---

## 1. The problem

- **Who:** people with reduced mobility in Porto: wheelchair users, people who walk with a walker or a cane, and
  everyone in a similar situation for a while (a broken leg, a pushchair, old age).
- **The pain:**
  - Porto is steep, paved with granite setts that get slippery in the rain, and full of steps. The shortest route on a
    normal map is often impossible for a wheelchair.
  - Accessibility is not static. A pavement blocked by works, a lift out of service or a hole in the pavement turns an
    accessible route into a dead end, and the person only finds out when they get there.
  - The information exists but is scattered: the City Council publishes road works and restrictions, IPMA publishes
    weather warnings, citizens report problems on ReportaPorto, and none of it reaches the person at the moment they
    need it.
  - **Number for the hook:** in the history of *unplanned* traffic restrictions that the City Council of Porto publishes as
    open data, **26 586 records are of type "Ocupação do passeio"** (pavement occupied).
    Source: [dadosabertos.cm-porto.pt, *condicionamentos-nao-programados*](https://dadosabertos.cm-porto.pt/dataset/condicionamentos-nao-programados)
    (counted on 23/10 from the GeoJSON export).
- **Why it is automation:** it **integrates** live sources (City Council, IPMA, citizens, lifts), **normalizes** them
  into one map of barriers, **decides** which barriers matter for each mobility profile and **reacts**: when a barrier
  appears on an active trip, the route is recomputed and the person is told why.

## 2. The solution

The path of one trip through Passo Livre:

1. **Plan.** The person picks a mobility profile (`wheelchair` or `walker`) and a destination. Passo Livre returns a
   route that respects the profile's limits (maximum slope, kerb height, surface, no steps) and **avoids every active
   barrier**. The route comes with its reasons: *"Avoids Rua de Mouzinho da Silveira (slope above 6%). Avoids the pavement
   occupied on Av. Gustavo Eiffel (source: Câmara Municipal do Porto)."*
2. **Live barrier map.** The broker keeps one map of barriers, fed by:
   - **Câmara Municipal do Porto (real):** road works, pavement occupation and holes, from the Porto Digital urban
     platform (FIWARE), with location and validity window;
   - **IPMA and city weather stations (real):** rain warnings and observed precipitation. Rain makes the profile
     stricter (lower maximum slope, smoother surface only), because wet granite is slippery;
   - **citizens (in the app):** *"pavement blocked by a parked van"*, with a photo and a confirmed pin. The LLM
     suggests the kind of obstacle from the text and photo; the matcher attaches it to an existing barrier or opens a new one;
   - **lifts (simulated):** a lift that reports a fault becomes a barrier.

   Each source has a rule table that says what a record means **for a pedestrian**: a closed parking lane does not
   matter, an occupied pavement blocks a wheelchair, a hole is a penalty for a walker. Every barrier keeps its reason
   and its source.
3. **The route that reacts (the core).** While a trip is active, every new barrier is checked against its route. If it
   crosses it, Passo Livre recomputes the route **from where the person is** and explains the change:
   *"New route: +4 min. The pavement on Av. Gustavo Eiffel is occupied by works until 10:45 (Câmara Municipal do Porto)."*
   If no accessible alternative exists, it says so instead of offering a route that cannot be taken.
4. **Report and pass it on.** A citizen's report helps everyone else immediately, and Passo Livre also prepares it for
   the City Council's own channel (**ReportaPorto**: category, location, description and photo, ready to submit), so the
   problem gets fixed, not only avoided. Passo Livre does not replace the city's channel: it feeds it.
5. **(Stretch) Accessible places.** Along the route: lifts, accessible toilets, accessible parking, pharmacies (real
   points of interest from the urban platform).

**Where the automation is, and who decides:**

| Moment | Automated | Decided by |
|--------|-----------|------------|
| City and weather intake | Poll the sources, translate each record into a barrier with an impact and a reason | the rule table (configuration) |
| Citizen report | Suggest the kind of obstacle from text (and photo); attach it to an existing barrier or open one | the citizen confirms the location; ambiguous matches go to review |
| Routing | Profile restrictions + avoided barriers + rain adjustment, with reasons | the person chooses the profile and accepts the route |
| Reaction | Detect active trips crossed by a new barrier; reroute and explain the difference | automatic; the person sees why |
| Hand-off | Prepare the ReportaPorto submission | the citizen submits it |

The **LLM only interprets unstructured input** (a citizen's text and photo). What a barrier means for each profile and
which route is chosen come from **rules and the routing engine**, which are deterministic and testable.

**Prototype scope:** Porto's Baixa and Ribeira (Aliados, São Bento, Sé, Ribeira, Av. Gustavo Eiffel): steep, paved
with granite, with metro lifts and real City Council alerts. Two profiles, four barrier sources, two web views (the
phone app and a live operator map). **City and weather data are real; lifts, citizen reports and trips in the demo are
simulated and labelled as such.**

| Barrier kind | Example source | `wheelchair` | `walker` |
|--------------|----------------|--------------|----------|
| `sidewalk_blocked` | City "Ocupação do passeio", citizen | block | block |
| `works` | City "Corte total" or "Estreitamento" for works | block | penalty |
| `broken_pavement` | City "pothole"/"Aluimento", citizen | block | penalty |
| `lift_out` | lift controller (simulated), citizen | block | block |
| `missing_ramp` | citizen | block | info |
| `event` | City "Corte total" / "Estreitamento" for *Eventos e lazer* (crowds, stages) | penalty | penalty |
| `crossing_unsafe` | City "Desativação de semáforos" | penalty | penalty |
| *(ignored)* | City "Estacionamento", "Alteração de sentidos" (cars only) | — | — |
| *rain* (a condition, not a barrier) | IPMA warning or precipitation > 0 at a zone station | stricter limits | stricter limits |

## 3. Architecture

```text
 [sources]                                   [Coreflux Broker: the logic lives here]                   [outputs]

 Porto urban platform (FIWARE, real)
   road alerts ──REST Connector CityAlerts──► IngestCityAlerts ──┐       (CALL PYTHON BarrierTools:
                                                                   │        impact rules, sync, expiry)
 lift controller (simulated) ──devices/<id>/status──► LiftIntake ─┼─► passolivre/barriers/events ──► ApplyBarrierEvent
                                                                   │   (sync, opened, confirmed,              │
 phone app ──reports/new──► AnalyzeReport ──► MatchReport ────────┘    cleared, expired)                     ▼
 (photo + pin + text)       (CALL LLM;        (CALL PYTHON Matcher)              passolivre/state/barriers ──► operator map
                             keywords offline)      │                            passolivre/kpi                (live)
                                                    └──► reports/<id>/handoff ──► ReportaPorto (prepared by us,
                                                         Mailer ──► city inbox      sent by the citizen)
 Porto urban platform (FIWARE, real)                       (Mailpit)
   rain warnings + stations ──REST Connector Weather──► IngestWeather ──► passolivre/state/conditions

 phone app ──trips/<id>/request──► PlanTrip ──ors/request──► OrsDirections (REST Connector) ──► OpenRouteService
                                   (CALL PYTHON Router:       ◄──ors/response──                 (wheelchair profile)
                                    restrictions + avoid areas)
                                          │
                                          ▼
                                   ExplainRoute (CALL PYTHON Router) ──► trips/<id>/route ──► phone app

 phone app ──trips/<id>/status──► HandleTripStatus ──► passolivre/state/trips

 new barrier event or rain change ──► CheckActiveTrips (CALL PYTHON Router.affected) ──► trips/<id>/request (reroute)
                                                                                    └──► trips/<id>/alert ──► phone app

             Rules: each role (traveller, reporter, operator) publishes only its own topics;
             only broker Actions write barriers, conditions, trips and routes
```

**Split of responsibilities:**
- **Broker (LoT):** the whole event pipeline: polling the city and weather sources, intake of reports and lift
  states, the barrier store, trip state, the call to the routing engine, reacting to new barriers, notifications,
  audit and security.
- **Python inside the broker (`CALL PYTHON`):** what LoT does badly. **`BarrierTools`** (city alert → barrier with
  the rule table, weather → conditions, fold of barrier events, expiry, KPIs), **`Matcher`** (citizen report ↔
  existing barrier by distance and kind; keyword classifier), **`Router`** (builds the routing request from the profile,
  the conditions and the blocking barriers; explains the result; diff between two versions of a route; which active
  trips a barrier affects; the ReportaPorto hand-off). All functions are **pure and stateless**, return `json.dumps(...)`
  and have `pytest` tests outside the broker.
- **Routing engine: [OpenRouteService](https://openrouteservice.org/) (`wheelchair` profile)**, called by a REST
  Connector. It covers Porto's whole network and already applies `maximum_incline`, `maximum_sloped_kerb`,
  `surface_type`, `smoothness_type` and `minimum_width`; the broker adds `avoid_polygons` built from the live
  barriers. **We do not write a routing engine: we decide what it must avoid, and when to ask again.**
- **LLM (`CALL LLM`, `PROVIDER "anthropic"`):** only turns a citizen's text (and photo) into a suggested barrier kind
  and a summary. It never decides what blocks a route.
- **Outside the broker:** the two web views (`report-site/` grows into the phone app; `dashboard/operator.html`) and
  the lift simulator.

⚠️ **Verify tonight / H+0:30:**
1. **ORS key and behaviour:** free key from <https://openrouteservice.org/dev/#/signup> (stored with `-setSecret
   ORS_API_KEY=...`, never in git). Ask for São Bento → Praça da Ribeira with the `wheelchair` profile and
   `extra_info: ["steepness", "surface"]`: does it actually avoid the steep streets? If not, `Router.explain` warns
   about every segment above the profile limit and we say it in the pitch.
2. **REST Connector with a POST body taken from the payload** (`avoid_polygons` changes per request). If it cannot,
   plan B is `services/ors_gateway.py` (Python + `paho-mqtt`), which reads `passolivre/ors/request` and publishes
   `passolivre/ors/response` with the same contract.
3. **Licence:** we have an unlimited key; the local broker was still **Community** on 23/10. After activating,
   `curl localhost:9100/license` must show more Connectors, Rules and `TYPE LLM`.

**Offline plan B:** the routes of the demo trips are cached as fixtures (`source: "cache"`); city alerts and weather
fall back to a recorded snapshot (`fixtures/messages/1*-sources.*`). The barrier pipeline, the reaction and the
explanations still run in the broker.

**Photos:** the browser downscales to ≤ 800 px JPEG (≤ 150 KB) and publishes it once, retained, on
`passolivre/photos/<photo_id>`. Every other message refers to the `photo_id`.

### MQTT topic map

The contract between every part of the system, **drafted on 23/10 for Passo Livre: review it together at kickoff, then
freeze it**. Every row has an example message in [`fixtures/messages/`](fixtures/messages/), and
`scripts/replay.py` publishes them, so each piece can be built before its producer exists. **Change a row only with
the whole team, and update its fixture in the same commit.**

| Topic | Published by | Read by | Payload | Retained |
|-------|--------------|---------|---------|:--------:|
| `config/profiles` | setup | `Router`, phone app | `{<profile>: {name, ors: {maximum_incline, maximum_sloped_kerb, surface_type, smoothness_type, minimum_width}, rain: {...same keys, stricter}, walk_speed_kmh}}` | ✅ |
| `config/barrier_kinds` | setup | `BarrierTools`, `Matcher`, `Router`, both views | `{<kind>: {label, impact: {<profile>: "block"\|"penalty"\|"info"}, radius_m, default_ttl_h, keywords}}` | ✅ |
| `config/impact_rules` | setup | `BarrierTools` | `{city: [{match: {sub_category?, detail?, text_any?}, kind` (`null` = ignore), `reason}], default: {kind, reason}, hours_in_description}`: what a city alert means for a pedestrian, in order, first match wins | ✅ |
| `config/zone` | setup | everything with a map, `IngestWeather` | `{name, center: [lat, lon], bbox: [s, w, n, e], weather_stations: [name], demo_trips: [{trip_id, from, to, profile}]}` | ✅ |
| `config/places` | setup | phone app, operator map | `[{place_id, type` (`lift`\|`train_station`\|`metro_station`\|`pharmacy`\|`parking`\|`accessible_wc`\|`accessible_parking`), `name, lat, lon, device_id?, source?}]` | ✅ |
| `passolivre/sources/city/alerts` | Connector `CityAlerts` (FIWARE poll) | `IngestCityAlerts` | FIWARE NGSI v2 `Alert` list, `options=keyValues`, as received | |
| `passolivre/sources/weather` | Connector `Weather` (FIWARE poll) | `IngestWeather` | `{alerts: [Alert…], observed: [WeatherObserved…]}` (weather alerts in Porto + the stations in the zone) | |
| `passolivre/devices/<device_id>/status` | lift simulator | `LiftIntake` | `{device_id, place_id, ok, fault?, at}` | ✅ |
| `passolivre/photos/<photo_id>` | phone app | operator map, LLM analysis | `data:image/jpeg;base64,...` | ✅ |
| `passolivre/reports/new` | phone app | `AnalyzeReport` | Model `Report`: `report_id, submitted_at, text, photo_id, lat, lon, location_confirmed, kind_hint?, contact?` | |
| `passolivre/reports/<report_id>/analysis` | `AnalyzeReport` (LLM / keywords) | `MatchReport`, phone app | `{report_id, source` (`llm`\|`keywords`), `kind, summary, confidence}` | |
| `passolivre/reports/<report_id>/match` | `MatchReport` | phone app, operator map | `{report_id, decision` (`new`\|`confirm`\|`clear`\|`review`), `barrier_id, candidates: [{barrier_id, distance_m, why}]}` | |
| `passolivre/reports/<report_id>/handoff` | `MatchReport` | phone app, `Mailer` | `{report_id, target: "reportaporto", category, title, description, lat, lon, photo_id, url}` | |
| `passolivre/barriers/events` | `IngestCityAlerts`, `LiftIntake`, `MatchReport`, `ExpireBarriers` | `ApplyBarrierEvent`, `CheckActiveTrips` | `{type` (`sync`\|`opened`\|`confirmed`\|`cleared`\|`expired`), `at, source, barrier_id?, data}`; `sync` replaces every barrier of one source at once | |
| `passolivre/state/barriers` | `ApplyBarrierEvent` | `Router`, `MatchReport`, operator map, phone app | `{<barrier_id>: Barrier}`: **the** barrier store, rebuilt by folding every event | ✅ |
| `passolivre/state/conditions` | `IngestWeather` | `Router`, `CheckActiveTrips` (on change), both views | `{rain: {active, since, source, precipitation_mm, station}, updated_at}` | ✅ |
| `passolivre/kpi` | `ApplyBarrierEvent`, `HandleTripStatus` | operator map | `{active_barriers: {<source>: n}, blocking: n, reports_today, reroutes_today, trips_active, sources_age_min: {<source>: n}}` | ✅ |
| `passolivre/trips/<trip_id>/request` | phone app, `CheckActiveTrips` | `PlanTrip` | `{trip_id, from: {lat, lon, label}, to: {lat, lon, label}, profile, trigger` (`new`\|`reroute`), `reason?, at}` | |
| `passolivre/ors/request` | `PlanTrip` | Connector `OrsDirections` (or `ors_gateway.py`) | `{trip_id, version, body: <ORS POST body>}` | |
| `passolivre/ors/response` | Connector `OrsDirections` (or `ors_gateway.py`) | `ExplainRoute` | `{trip_id, version, status, geojson: <ORS FeatureCollection>}` | |
| `passolivre/trips/<trip_id>/route` | `ExplainRoute` | phone app, operator map, `HandleTripStatus` | Route (see below) | ✅ |
| `passolivre/trips/<trip_id>/status` | phone app | `HandleTripStatus` | `{status` (`started`\|`position`\|`finished`\|`cancelled`), `at, lat?, lon?}` | |
| `passolivre/state/trips` | `HandleTripStatus` | `CheckActiveTrips`, operator map | `{<trip_id>: {profile, status, route_version, from, to, last_position, corridor: [[lon, lat], …], started_at}}` | ✅ |
| `passolivre/trips/<trip_id>/alert` | `CheckActiveTrips`, `ExplainRoute` | phone app | `{trip_id, at, barrier_id, text, new_version?}` | |
| `passolivre/notifications/email` | `MatchReport` | Connector `Mailer` | `{to, subject, body, report_id}` (the city inbox is Mailpit in the demo) | |
| `passolivre/audit/events` | `ApplyBarrierEvent`, `ExplainRoute` | Connector `AuditLog` (JSON file) | `{at, type, source, barrier_id?, trip_id?, data}` | |
| `passolivre/errors` | any Action | operator map | text | |

**Model `Barrier`:** `barrier_id`, `source` (`city`\|`weather`\|`citizen`\|`device`), `source_ref` (e.g. the FIWARE id),
`kind`, `impact` (`{<profile>: block|penalty|info}`), `lat`, `lon`, `radius_m` (or `polygon`), `valid_from`,
`valid_to`, `reason` (one sentence, shown to the person), `label` (the street, from the source), `report_ids`,
`photo_ids`, `status` (`active` → `cleared`\|`expired`), `history` (`[{at, type, by, text}]`).

**Route:** `{trip_id, version, profile, generated_at, source` (`ors`\|`cache`), `from, to, summary: {distance_m,
duration_min, climb_m, max_steepness_class}, geometry: [[lon, lat], …], avoided: [{barrier_id, why}], warnings:
[{text, barrier_id?}], explanation: [text…], changes?: {from_version, delta_min, text}, feasible}`. If `feasible` is
`false`, `explanation` says what blocks every accessible option and `geometry` is empty.

Rules of the contract:
- `barrier_id` = `<source>-<source_ref>` for city/device barriers (stable across polls) and `cit-<report_id>` for
  citizen ones, so a barrier keeps its id while it exists.
- City alerts are applied as one `sync` event per poll (all city barriers at once): LoT has no easy loop over JSON
  lists, so we publish whole documents instead of one message per item.
- One store per kind (`state/barriers`, `state/conditions`, `state/trips`, one route per trip), each with **a single
  writer Action**.
- Only `block` barriers become `avoid_polygons`; `penalty` barriers on the route become `warnings`; `info` is shown on
  the map only. Rain switches the profile to its `rain` restrictions.
- A reroute starts from the trip's `last_position` and keeps the destination. A route version never changes after it is
  published; a new version carries `changes` against the previous one.
- The LLM only *suggests* (`analysis`); the impact table, the matcher and the routing engine decide.
- Topics in English, lowercase, `snake_case`, under `passolivre/` or `config/` (retained). Texts shown to people
  (`reason`, `explanation`, `text`) are in European Portuguese; keys stay in English.

### Components

| Component | Where | Technology |
|-----------|-------|------------|
| Automation logic | `lot/` | LoT: Actions, Models, Connectors (`REST` ×3: `CityAlerts`, `Weather`, `OrsDirections`; `LLM`; `EMAIL`; `FILE_STORAGE`), Rules |
| BarrierTools, Matcher, Router | `lot/` (`CALL PYTHON` scripts) + tests in `services/tests/` | Python (standard library only) |
| ORS gateway, plan B | `services/ors_gateway.py` | Python + `paho-mqtt` (only if the REST Connector cannot send a dynamic body) |
| Lift simulator | `services/lift_sim.py` | Python + `paho-mqtt` |
| Phone app | `report-site/` (started by Ben on 23/10 as the report form; grows into plan + report) | Plain HTML + JS, MQTT over WebSocket (`mqtt.js`), Leaflet map; no build step |
| Operator map | `dashboard/operator.html` | Same stack |
| Infrastructure | `broker/` | Docker Compose: Coreflux Broker 2.22, HUB 2.12, Mailpit |

WebSocket: verified on 23/10. The broker serves MQTT over WebSocket on container port 5000, path `/mqtt`; it is **opt-in** via `broker/docker-compose.ws.yml` → `ws://localhost:9001/mqtt`. Read that file's warning first: any web page on the laptop can reach a localhost WebSocket, so change the root password (or use limited users per role) before enabling it.

### Data sources (checked on 23/10)

| Source | Access | Used for |
|--------|--------|----------|
| Porto Digital urban platform, FIWARE NGSI v2: `https://broker.fiware.urbanplatform.portodigital.pt/v2/entities` | Public, no key. `type=Alert&q=category==traffic` (City Council road alerts, with `subCategoryDetailed`, `validFrom`/`validTo`), `type=Alert&q=category==weather` (IPMA), `type=WeatherObserved` (stations incl. *Aliados*, *Bolhão*, *Hospital S.António*, every 5 min), `type=PointOfInterest` | barriers, rain, places |
| City Council open data (CKAN): `https://dadosabertos.cm-porto.pt/api/3/action/package_list` | Public; files are periodic exports, not live | the hook number, historical analysis |
| OpenRouteService directions, `wheelchair` profile | Free key (daily quota) | routing |
| ReportaPorto: `https://reportaporto.cm-porto.pt` | **No public API**: we prepare the submission, the citizen sends it. We do not scrape it | hand-off |

Quirks seen on 23/10 (encoded in `config/impact_rules` and the fixtures):
- programmed alerts (`RoadAlerts`) carry **day-level** `validFrom`/`validTo`; the real hours are in `description`
  (*"Das 08:00 às 14:00 de 24/10"*). Unplanned ones (`RoadAlertsUnscheduled`) have exact times;
- geometry is a `Point` for unplanned alerts and a `Polygon`/`MultiPolygon` for programmed ones;
- IPMA publishes a `low` (green) entry for every warning type all the time: `low` alone means no warning;
- some weather stations stopped reporting months ago: use a reading only if it is less than 20 min old;
- there were **real road closures in the Baixa for an event on 24/10, 08:00–14:00** (e.g. `cmp4442951`): expect
  them in the live data during the hackathon.

## 4. Demo

Full script and plan B in [`PITCH.md`](PITCH.md#demo-script-140). Summary:
1. On the phone, a wheelchair user asks for São Bento → Ribeira. The route appears **with its reasons** (steep streets
   avoided, a real City Council restriction avoided).
2. The operator map shows the live barrier map: **real** City Council alerts and the weather from the Aliados station.
3. A citizen reports *"passeio bloqueado por obras"* with a photo: the LLM suggests the kind, the matcher opens a
   barrier, and the ReportaPorto hand-off is ready (and lands in the city inbox in Mailpit).
4. **The key moment:** that barrier is on the active trip. The broker notices, reroutes from the current position and
   the phone shows *"Nova rota: +4 min, porque…"*.
5. It starts raining (a weather message): the profile becomes stricter and the route changes again, with the reason.
6. The HUB shows the Actions, Python scripts and Connectors running in the broker.

## 5. Maturity and next steps

- **End to end and real:** live City Council and IPMA data, the barrier pipeline, routing on Porto's real network,
  reroute on change, the hand-off, notifications and the audit log all run in the broker.
- **Simulated / fictional:** the lift controller, the citizen reports and the trips of the demo (labelled).
- **Explainable:** every barrier has a source and a reason; every route says what it avoided; every reroute says
  what changed and why.
- **Honest about limits:** if no accessible route exists, Passo Livre says so. The impact table is configuration and
  can be reviewed with associations of people with disabilities.
- **Reliability:**
  - no internet → cached demo routes and a recorded snapshot of the sources; the barrier pipeline and reroute logic
    are local;
  - state is retained and rebuilt from events; barriers expire on their own (`valid_to`, `default_ttl_h`);
  - a source that fails keeps its last barriers and shows its age on the operator map.
- **Security (Rules):** one user per role. Travellers publish only their own trips; reporters only reports and photos;
  only broker Actions write barriers, conditions, trips and routes. A traveller's position is never published outside
  their own trip topics.
- **Tests:** `pytest` for the impact rules (every city alert type), weather → conditions, barrier fold and expiry,
  matcher (same obstacle, cleared obstacle, grey zone), routing request (avoid polygons, rain restrictions), route diff
  and the affected-trips check.
- **Scale:** sources, profiles, kinds and rules are configuration. Porto publishes its alerts in FIWARE NGSI, an open
  European standard: another city that uses it plugs in by changing the Connector's URL and the rule table.
- **Business model:** free for people; the city (or the metro operator) pays for the operator map, the live barrier
  data and the reports it receives. It complements ReportaPorto and existing navigation apps.
- **With more time:** real lift status from the metro operator, official integration with ReportaPorto, our own
  slope model from elevation data, crowd-confirmed barriers, voice guidance, more profiles (visual impairment).

---

## Environment setup (Linux / macOS)

Prerequisites: **Docker** and **Docker Compose v2** (`docker --version`, `docker compose version`).

```bash
cd hackathon/broker
cp .env.example .env          # optional: licence code
chmod 777 exports             # the broker (uid 10001) writes the audit log here; git can't store this
docker compose up -d
```

| Service | Address | Credentials |
|---------|---------|-------------|
| Coreflux HUB | <http://localhost:3000> | pre-filled connection: host `broker`, port `1883`, `root` / `coreflux` |
| MQTT broker (from outside Docker) | `localhost:1883` | `root` / `coreflux` |
| MQTT over WebSocket (opt-in, `docker-compose.ws.yml`) | `ws://localhost:9001/mqtt` | a limited web user, not root |
| Mailpit (test email inbox, the "city inbox" of the demo) | <http://localhost:8025> | — |
| Broker health | <http://localhost:9100/health> | — |
| Broker MCP server (AI agents) | <http://localhost:6278/mcp> (`/health` without a token) | bearer token, see [`AI.md`](AI.md) |

- `docker compose down` stops and keeps the data; `docker compose down -v` **wipes everything, including the licence**.
- The HUB connects to `broker` (the Docker service name), not `localhost`.
- Port taken? Change the host port number in `docker-compose.yml` (e.g. `"127.0.0.1:3001:3000"`).

### Security on the event network

At FCUP we are on the same network as the other teams, and the default password (`root` / `coreflux`)
is the same for everyone. That is why **every port is bound to `127.0.0.1` only** (this machine only).
For an Arduino/ESP32 or a teammate's laptop to publish to our broker:

1. **First** change the `root` password (or create a dedicated user for the devices)
   in the HUB: see the [broker documentation](https://docs.coreflux.org/latest/mqtt-broker/overview).
2. Then set `MQTT_BIND=0.0.0.0` in `broker/.env` and run `docker compose up -d`.

The HUB, Mailpit and the health endpoint always stay on localhost only.

### Licence

We have an **unlimited licence code** (`CFLX-...`, kept outside git). Without it, the broker runs as
**Community Edition**, which only allows **3 Connectors**, **no custom `DEFINE RULE`** and no `TYPE LLM`. Passo Livre
needs more than 3 Connectors (3 REST + LLM + EMAIL + FILE_STORAGE), so the licence is required on the presentation
laptop.

Activate it in one of two ways:
- put `COREFLUX_ACTIVATION_CODE=CFLX-...` in `broker/.env` (outside git) **before** the first `docker compose up`;
- HUB → `root` → Broker Settings → License, or `-activateLicense CFLX-...` in the Command Console (works on a broker
  that is already running).

The licence is bound to the machine (`fingerprintSource: hostname+mac`) and each activation uses up a *seat*, so
activate it on the presentation laptop first and avoid `docker compose down -v` afterwards.
Check the tier in the badge next to `root` or at <http://localhost:9100/license>.

### LoT code workflow

The **source of truth is git**: the `.lotnb` files in `lot/`, which are mounted read-only in the broker at `/lot`.

**With AI (recommended):** Claude Code is connected to the Coreflux docs and to our broker over MCP,
with the official LoT skills. See [`AI.md`](AI.md) for the one-time setup. Edit a notebook, then
`/lot-deploy` validates it and reloads the `lot` project from git.

**By hand:**

1. Install the **LoT Notebooks** VS Code extension
   ([VSCodeLotNotebook](https://github.com/CorefluxCommunity/VSCodeLotNotebook/releases/tag/v1.0.0), `.vsix` file):
   `code --install-extension vscode-lot-notebooks-1.0.0.vsix`
2. Open a `.lotnb` from `lot/` and connect to `localhost:1883` (`root` / `coreflux`).
3. Run the cells (▷) to deploy to the local broker; commit the `.lotnb` files.

If someone edits directly in the HUB, they must copy the final code into the matching `.lotnb` before committing.
Layout: **one notebook per feature, one writer per notebook at a time** (see [`PLAN.md`](PLAN.md#notebooks)), so two
people never edit the same `.lotnb` (they are JSON and merge badly).

### Useful tools

- **MQTT Explorer** or `mosquitto_sub -h localhost -u root -P coreflux -t '#' -v` to see every topic.
- **Python:** `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (paho-mqtt, pytest)
  for services, simulators and tests in `services/`.
- Broker variables and secrets: `-setEnv NAME=value`, `-setSecret NAME=value` (no spaces around the `=`),
  then `{env.NAME}` or `GET ENV "NAME"` / `GET SECRET "NAME"` in LoT. The ORS key is the secret `ORS_API_KEY`.
- Peek at the live city alerts: `curl -s "https://broker.fiware.urbanplatform.portodigital.pt/v2/entities?type=Alert&q=category==traffic&orderBy=!dateIssued&limit=5&options=keyValues"`.

## Documents in this folder

- [`AI.md`](AI.md): AI tooling setup (MCP servers, Coreflux skills, token) and the daily loop.
- [`AGENTS.md`](AGENTS.md): LoT rules for AI assistants (Claude Code reads it through `CLAUDE.md`).
- [`LOT_CHEATSHEET.md`](LOT_CHEATSHEET.md): LoT syntax reference (Actions, Models, Connectors, Rules, Panels).
- [`PLAN.md`](PLAN.md): who builds what, notebooks, timeline, licence check and spikes.
- [`PITCH.md`](PITCH.md): presentation structure and demo checklist.
- [`fixtures/`](fixtures/): one example message per topic (`messages/`), published by `scripts/replay.py`.

## References

- Coreflux documentation: <https://docs.coreflux.org>
- OpenRouteService API: <https://giscience.github.io/openrouteservice/api-reference/>
- Porto Digital urban platform (FIWARE) and open data: <https://dadosabertos.cm-porto.pt>
- Training repo (reference only, **do not copy**: there is plagiarism detection):
  <https://github.com/CorefluxCommunity/weather-station-hackathon>
