# Passo Livre runtime baseline

## Update: local custom Valhalla verified (24 October 2026, ~10:30 UTC)

The custom Valhalla runtime now runs locally at **http://127.0.0.1:8003**. Setup,
data provenance and commands are in [`../runtime/valhalla/README.md`](../runtime/valhalla/README.md).
The rest of this document is the earlier pre-setup baseline, kept as a record. See the "Core 1 verified" section at the end for the integrated check
and "Core 2 verified" for the slope-cap validation, which **corrects the slope units below**.

| Item | Verified result |
|---|---|
| Image | `passolivre-valhalla:9f6f67e`, ID `2cbb4732c5bb`, built from `projects/valhalla` with the slope fix below; `/status` reports `3.9.1-passolivre-9f6f67e` |
| Data | BBBike Porto PBF (MD5 matches the published checksum) and Skadi cells `N40W009`, `N41W009`; hashes in `data-manifest.json` |
| Graph | `setup.sh tiles` built in ~35 s; elevation added to all 13 tiles; 62 MB `tiles.tar`. No admin/timezone DBs (warnings expected) |
| Service | Compose container `passolivre-valhalla`, loopback only, 2 CPUs / 2 GiB; `/route` and `/trace_attributes` answer |
| CORS | Responses carry `Access-Control-Allow-Origin: *`, so a locally served app can call it |
| Smoke | `setup.sh smoke` passes: Aliados pedestrian route 0.388 km (matches the public instance), trace with 30 edges, slope-cap case |

**Slope fix.** With the image as first built, every pedestrian route failed with error
442 while `auto` worked. Cause, in `PedestrianCost::Allowed`/`AllowedReverse`:
`max_down_slope()` is a negative `int` and `max_grade_` a `uint32_t`, so the comparison
converted e.g. -3 to ~4.29e9 and rejected every edge with any downhill. The cap was also
in percent while edge slopes are in degrees. The fix converts `max_grade` once with the
existing `grade_percent_to_degrees` helper and compares `max_up_slope()` and
`-max_down_slope()` against it. Tiles were not rebuilt (costing is evaluated at query time).

Observed cap behaviour (foot and wheelchair identical):

| Route | 90 % | 12 % | 8 % | 6 % and below |
|---|---|---|---|---|
| Aliados (66 → 94 m over 334 m, ~8.4 %) | 0.388 km | 0.388 km | 0.388 km | no route |
| Ribeira → Sé | 0.89–1.00 km (edges up to 13°/-16°) | no route | no route | no route |
| Ribeira → Batalha | 1.42–1.50 km (edges up to 13°/-16°) | no route | no route | no route |

The cap is enforced and monotonic. `trace_attributes` `max_upward_grade` /
`max_downward_grade` are in **degrees** (4° ≈ 7 %); the app already converts them
with `degreesToPercent`.

> **Corrected by Core 2:** edge slopes are stored as **percent**, not degrees, so this
> conversion made every cap about twice as strict as labelled. The table above reflects
> that bug. The costing now compares percent directly; see "Core 2 verified".

**Still open at the time (see Core 2 for the current status):**
- The origin and destination partial edges are not checked against the cap (Aliados has
  11° end edges and still routes at 8 %).
- Missing elevation is stored as slope 0, so unknown segments pass any cap.
- Slopes above 15° are quantized in 4° steps; the per-edge maximum is sensitive to DEM
  resolution (~30 m) on short edges.
- No route is returned when the cap cannot be met (by design: the app does not relax it).
  For the demo, choose an origin/destination pair where a stricter cap *changes* the route
  rather than blocks it.
- Coreflux WebSocket transport and the `access/barriers/<id>` exchange are still untested.
- The app's `valhallaUrl` is still empty; Ben sets it (locally `http://127.0.0.1:8003`).

## Original baseline (pre-setup)

Observed on 24 October 2026, approximately 08:55–09:00 UTC, on Miguel's workstation.
Repository baseline: `9f6f67e`. Initial `git status --short` was empty.
This session only added this document: no app edits, service changes, deployments,
broker writes, package installs, builds, dataset downloads, commits or pushes.

## Result

**Local Coreflux is healthy. The intended custom Valhalla runtime is not available
at the documented local endpoints. The documented public fallback successfully
answered one basic Porto route request.** That public result does not establish
custom slope enforcement or an integrated working app.

Sources read: `hackathon/AGENTS.md`, `hackathon/PLAN.md`, `hackathon/README.md`,
`hackathon/app/README.md`, the routing handoff (especially sections 2.4–4.5 and 7),
the broker Compose files, app configuration, and specific Valhalla build/config files.
The handoff describes another machine; its old upload warnings and old website
setup are not the current app baseline. Miguel owns runtime recovery; Pedro is
not an ongoing dependency. Ben owns `hackathon/app/`.

## Available versus actually verified

| Component | Evidence observed now | Limit of the evidence |
|---|---|---|
| Docker | Engine CLI 29.9.1; Compose v5.6.0; daemon accessible | No new containers started |
| Coreflux | `o1n-broker`, image `coreflux/coreflux-mqtt-broker:2.22.0`, running; `GET http://127.0.0.1:9100/health` returned HTTP 200, `status: healthy`, `version: 2.22.0` | Health is not a barrier integration test |
| Coreflux version | `/health` supplies version; `/version` on port 9100 returned HTTP 404 | No standalone version endpoint verified |
| Broker MCP | `GET http://127.0.0.1:6278/health` returned HTTP 200, healthy, `CorefluxBroker`, version 2.22.0, 98 tools | No authenticated MCP operations performed |
| MQTT TCP | `127.0.0.1:1883` accepted a TCP connection | No authenticated MQTT session, subscription, publish or retained-message test |
| MQTT WebSocket | Compose override declares `127.0.0.1:9001:5000`, intended URL `ws://127.0.0.1:9001/mqtt` | Override is not active: no host mapping, TCP connection refused on 9001; browser transport unavailable locally |
| HUB / Mailpit | `o1n-hub` (2.12.0) and `o1n-mailpit` (`latest`) running and Docker-healthchecked healthy; ports 3000 and 8025 bound to loopback | No UI workflow tested; port 3000 belongs to the HUB, not the old OSM website |
| Custom Valhalla | No Valhalla-named image or container in local Docker inventory; no service/build tools on PATH | Both `http://127.0.0.1:8003/status` (historical service) and `:8002/status` (source default) refused connections |
| Public fallback | `https://valhalla1.openstreetmap.de/status`: HTTP 200, version `3.9.1-618cad5`; actions include `route`, `trace_attributes`, `height`, `status` | An advertised action is not a test of that action; this is not the team's custom build |
| Public route | POST `/route`: HTTP 200; `trip.status: 0`, `Found route between points`; one leg, 0.388 km, 324.654 seconds | Plain pedestrian route only; no slope, wheelchair, barrier, CORS or browser integration validation |
| App configuration | Committed `valhallaUrl` and `brokerUrl` are empty; `config.local.js` absent; topic prefix `access` | No actual cloud Coreflux endpoint or custom Valhalla tunnel URL identified |

The public request used origin `(41.1466, -8.6110)` and destination
`(41.1496, -8.6109)`, pedestrian costing, kilometers. No slope cap was submitted.
The app's documentation explicitly says the public fallback does not implement
the custom cap; do not turn this smoke test into an accessibility claim.

`hackathon/broker/.env` exists and is ignored. Only setting names were checked;
it contains an obsolete ORS key setting, not a routing endpoint. Its value is
neither needed nor recorded. Do not restore ORS. No credentials are required for
the reproducible probes below.

## Startup requirements and missing artifacts

### Coreflux

The checked-in base stack uses:

- `coreflux/coreflux-mqtt-broker:2.22.0`, `coreflux/coreflux-hub:2.12.0`,
  and `axllent/mailpit:latest`. All are already local and running.
- Broker persistent volume mounted at `/etc/project` (actual volume
  `broker_broker-data`); `templates` and `../lot` mounted read-only;
  `exports` writable at `/data/exports`. These mounts were inspected without
  dumping container environment or broker data. Preserve the persistent volume.
- MCP enabled with container-internal bind `0.0.0.0`, but published on host
  loopback only. MQTT, health, HUB and Mailpit host mappings are also loopback.
- Optional licence configuration through ignored local configuration. No licence
  activation or entitlement check was performed; do not infer a tier from health.
- For browser use, the WebSocket Compose override plus a suitable existing
  login restricted to `access/barriers/#`. User/rule provisioning was not checked
  or changed. HTTPS-hosted clients also need a reachable secure WebSocket endpoint;
  a localhost plain WebSocket endpoint is only a local integration option.

Base startup command, documented here but **not run** because the services already
exist:

```bash
cd hackathon/broker
docker compose up -d
```

The separate next-session transport change would be:

```bash
cd hackathon/broker
docker compose -f docker-compose.yml -f docker-compose.ws.yml up -d broker
```

That may recreate the broker; plan it as an explicit integration step. Keep
loopback bindings and existing volumes. Do not use `down -v` or overwrite `.env`.
The optional export mount is currently writable; email/export automation is not
needed to establish routing and barrier transport.

### Valhalla

The original handoff reports a local image `valhalla-slope:local`, config
`/custom_files/slope-build/valhalla.json`, an Andorra PBF, elevation tile
`elevation_data/N42/N42E001.hgt`, and seven loaded tiles on version 3.9.1.
**These are historical claims, not artifacts verified on this workstation.**
Andorra data would not cover the Porto demo.

Checked locations absent here: `/home/peteryellow/valhalla/custom_files`,
`/home/miguel/valhalla`, `/data/valhalla`, `projects/valhalla/custom_files`,
`projects/valhalla/valhalla_tiles`, `projects/valhalla/build`, and `hackathon/data`.
The source root has no runtime data/config directory. Tracked test PBFs and
binding-test JSON files exist; they are not a Porto runtime bundle. No graph,
Porto PBF, DEM coverage or deployment config was identified in the inspected
locations. This was a targeted inspection, not a whole-disk artifact search.

A usable custom runtime requires all of:

1. **Executable/image built from the modified source.**
   `projects/valhalla/docker/Dockerfile` is a concrete source-build recipe, with
   build context `projects/valhalla`, Ubuntu 24.04 stages, and dependency setup
   via `scripts/install-linux-deps.sh`. It builds/install binaries and Python
   bindings. A stock scripted image would not prove the team's modifications
   are present. The original custom image's provenance/digest is unknown.
2. **Compatible routing graph covering the intended points.** Serve prebuilt
   graph tiles or their tile archive; a PBF is a build input, not a directly
   routable graph. Reusing a compatible elevation-enhanced Porto bundle is the
   smallest setup path if one can be obtained with provenance.
3. **Elevation used during graph construction.** For slope claims the graph
   needs valid elevation-derived attributes. HGTs use latitude directories and
   names such as `N41/N41W009.hgt` for the tested Porto coordinates; obtain all
   cells covering the chosen extract. Merely adding DEM files beside an existing
   graph does not retrofit slope attributes. Missing-elevation policy remains
   a separate task. Raw DEMs are also needed if serving elevation queries from
   local elevation data; a basic route can work without proving any of this.
4. **Explicit JSON config and matching mounts.** Generate with
   `valhalla_build_config`; set `mjolnir.tile_dir`, `mjolnir.tile_extract`,
   `additional_data.elevation`, and `httpd.service.listen`. Source defaults are
   `/data/valhalla`, `/data/valhalla/tiles.tar`, `/data/valhalla/elevation/`, and
   `tcp://*:8002`. Admin/timezone database paths must match any supplied bundle;
   they support administrative/time-dependent behavior. Check enabled actions
   and service limits for `/route` and `/trace_attributes`.
5. **Correct service port.** The historical command maps 8003 to 8003 and assumes
   its missing JSON listens on 8003. Generated defaults instead listen on 8002.
   Choose one explicitly, e.g. host `127.0.0.1:8003` to container 8002; run
   `valhalla_service <container-config-path> 1`. Do not reuse the old absolute
   machine paths or an unmatched port mapping.

Candidate image-build command for a later, explicitly budgeted setup session
(recipe inspected, **not built or validated**):

```bash
docker build -f projects/valhalla/docker/Dockerfile \
  --build-arg CONCURRENCY=2 -t valhalla-slope:local projects/valhalla
```

The recipe requires network package downloads and compilation, including
`prime_server` 0.12.0. No build or download was started. A native build needs
CMake >=3.15, a C++20 compiler, Boost >=1.71, Protobuf/compiler, zlib, curl,
prime_server/ZeroMQ, SQLite/SpatiaLite, LuaJIT, GEOS and OpenSSL; optional/default
features add GeoTIFF/TIFF, LZ4 and Python development requirements. The exact
package list is in the installer script. Keep `ENABLE_SERVICES` and
`ENABLE_DATA_TOOLS` enabled when building the service and graph tools.

Host preflight: GCC/G++, Python 3, curl and pkg-config exist; CMake, Ninja,
`protoc`, `valhalla_service`, `valhalla_build_tiles`, `valhalla_build_config`,
`valhalla_build_elevation`, and `valhalla_build_extract` are not on PATH.
pkg-config finds zlib 1.3 and expat 2.6.1; it does not find libcurl, protobuf,
libprime_server, sqlite3, spatialite, luajit, geos, openssl or liblz4. This is
not a full native dependency audit (CMake-only packages were not resolved).
Docker can supply build dependencies without installing them on the host.
Approximately 235 GiB disk space was available; build memory/time were not assessed.

If no reusable bundle exists, obtaining a bounded Porto OSM extract and matching
DEM coverage, generating config, building/enhancing tiles, and producing the
extract are separate next actions. The handoff's build → elevation download →
enhance → extract sequence is historical guidance, not a build verified here.
The scripted image can automatically download/build on startup, so it was not launched.

## Reproducible read-only checks

Run from the repository root. These commands do not include credentials.

```bash
git status --short
git rev-parse --short HEAD
docker --version
docker compose version
docker ps -a --filter name=o1n --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker ps -a --filter name=valhalla
docker image ls '*valhalla*'
curl --max-time 5 -sS -i http://127.0.0.1:9100/health
curl --max-time 5 -sS -i http://127.0.0.1:9100/version
curl --max-time 5 -sS -i http://127.0.0.1:6278/health
curl --max-time 5 -sS -i http://127.0.0.1:8003/status
curl --max-time 5 -sS -i http://127.0.0.1:8002/status
```

The HTTP probes above were executed with Python's standard-library HTTP client;
curl equivalents are provided for convenience. Check TCP transport without login:

```bash
python3 - <<'PY'
import socket
for port in (1883, 9001):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=3):
            print(port, 'TCP connected')
    except OSError as error:
        print(port, error)
PY
```

Repeat the public smoke test (or replace the base URL with a verified custom
service once it has Porto coverage). These are public coordinates, not user data:

```bash
curl --max-time 15 -sS https://valhalla1.openstreetmap.de/status
curl --max-time 15 -sS https://valhalla1.openstreetmap.de/route \
  -H 'Content-Type: application/json' \
  --data '{"locations":[{"lat":41.1466,"lon":-8.6110},{"lat":41.1496,"lon":-8.6109}],"costing":"pedestrian","units":"kilometers"}'
```

Avoid dumping `.env`, full `docker inspect`, rendered Compose environment,
broker logs or stored broker data into shared output; none is needed to reproduce
these checks. The execution sandbox failed before its first command with a
network-namespace initialization error; subsequent checks ran with approved host
access. Connection refusals reported above are from that host context.

## Blockers and smallest next actions

| Blocker | Smallest next action |
|---|---|
| No intended custom Valhalla endpoint/artifact bundle | Miguel identifies an accessible existing custom service or obtains a compatible image + config + Porto graph bundle with provenance. If neither exists, time-box a separate local build/data setup task before starting downloads. |
| Browser MQTT transport unavailable locally | In a separate integration task, enable the existing WebSocket override, confirm port 9001 and an authenticated MQTT-over-WebSocket connection with a suitable existing account. |
| App endpoints blank; no verified limited browser login | Coordinate with Ben on endpoint values and ignored local configuration; Miguel supplies verified URLs. Human-managed account setup may be needed; do not use user-management tools. |
| Barrier exchange and retention untested | Once transport/login work, test one `access/barriers/<id>` report across two sessions and reload, then remove only that test report. No automation needed for this check. |
| Slope behavior unverified | After a custom service is reproducible, schedule a distinct units/downhill/missing-elevation validation task with known cases. Do not claim success based on a route response. |

Existing code includes forward/reverse pedestrian slope comparisons and an unused
conversion helper in `projects/valhalla/src/sif/pedestriancost.cc`. The handoff
flags units, negative downhill comparisons and missing elevation. Those checks
were located, not fixed or executed. The app's route, trace and barrier behavior
is described in its README; no browser flow was tested in this baseline.

## Recommended next session

Take **one bounded routing-runtime recovery task**: establish a usable custom
Valhalla service with known image/source provenance, valid configuration and
Porto graph coverage; verify `/status` and the same basic route; record the exact
artifact paths and startup command. First time-box reuse discovery; if rebuilding
is necessary, state the data/build budget before proceeding. Stop before slope
fixes, broker automation, frontend edits, deployments or end-to-end demo work.
Then take WebSocket/barrier integration as its own task with Ben. Keep the current
Valhalla architecture and `access/barriers/<id>` contract.

## Core 1 verified (24 October 2026, ~10:40 UTC)

Locally served app → custom Valhalla + local Coreflux over WebSocket, in Chrome 155 on Miguel's laptop.
All ports stay on 127.0.0.1.

| Check | Result |
|---|---|
| Broker WebSocket | Broker recreated with `docker-compose.ws.yml` (same `broker_broker-data` volume); `ws://127.0.0.1:9001/mqtt` accepts MQTT sessions |
| App endpoints | Two tabs of `http://127.0.0.1:8765/` load `config.local.js` (gitignored, in `.assetsignore`) and report the broker online |
| Route | Aliados pair (41.1466,-8.6110 → 41.1496,-8.6109): 6 % cap shows the app's no-route message (cap not raised); 8 % draws the route |
| Barrier | Retained `access/barriers/core1-test` appeared live in both tabs, was back after reloading one, and vanished from both after an empty retained publish |
| Exclusion | With that barrier active the same route grew from 0.388 to 0.437 km (its polygon was avoided) |

**Fix needed on the way.** Valhalla's built-in HTTP server answers the CORS preflight (`OPTIONS`) with
405, so browser `POST`s with `Content-Type: application/json` never left the page (`Failed to fetch`;
curl and the smoke test do not preflight). `app/app.js` now sends both Valhalla requests as
`text/plain` (body unchanged), a simple CORS request. The public fallback accepts it too.

Setup on the demo laptop (no secrets here; the broker login goes only in `app/config.local.js`):

```bash
bash hackathon/runtime/valhalla/setup.sh start && bash hackathon/runtime/valhalla/setup.sh smoke
cd hackathon/broker && docker compose -f docker-compose.yml -f docker-compose.ws.yml up -d broker && cd -
# hackathon/app/config.local.js: valhallaUrl http://127.0.0.1:8003, brokerUrl ws://127.0.0.1:9001/mqtt, broker login
python3 -m http.server 8765 --bind 127.0.0.1 --directory hackathon/app
```

**Hosting decision: serve the app locally for the demo.** The Cloudflare HTTPS page
(`accessible-routes.benlubetzky.workers.dev`) ships `config.js` only: public Valhalla (no custom slope cap)
and no broker, so its barriers stay in each browser. Requests from that page to `http://127.0.0.1:8003`
and `ws://127.0.0.1:9001` hung for 8 s without a result, consistent with Chrome's local-network-access
gate for a public origin calling loopback. Even if allowed, it would only work on this laptop, and it would
need the broker login in committed config. A tunnel (HTTPS Valhalla + `wss` broker) is only worth it if a
phone or second laptop must join; it exposes the broker beyond loopback, so it is not set up.

**Remaining blockers / caveats**
- Broker is Community tier (no licence active, `.env` holds no code): 0 custom Rules, so no topic-scoped
  browser user. For the prototype the local config uses the default broker login, loopback only.
- Retained barriers do not survive a broker restart (durability off by default): re-seed before the demo.
- `access/barriers/<id>/feedback` (non-retained, published by the app) is missing from the topic map.
- The default 6 % cap blocks the Aliados pair: Core 2 needs a demo pair where a stricter cap changes the route.

## Core 2 verified (24 October 2026, ~11:30 UTC)

Accessible route validation against the custom Valhalla at `http://127.0.0.1:8003`, image
`passolivre-valhalla:9f6f67e` ID `14d5aa490f12` (rebuilt from commit `f47093b`; tiles unchanged).
`setup.sh smoke` passes all 23 checks. Probes are reproducible with `smoke.py`.

### Slope units: percent, not degrees (fixed)

`DirectedEdge::max_up_slope()`/`max_down_slope()` are documented as degrees, but
`mjolnir/elevationbuilder.cc` feeds them `skadi::weighted_grade`, which returns
`Δh × 100 / 60 m`: percent over a 60 m posting, rounded up when stored. Replicating that
formula with `/height` matched 92 of 95 Porto edges (±1, integer DEM), against 50 of 95 for
the degree reading. The Core 1 conversion (`atan(max_grade)` in degrees) therefore made a 6 %
cap admit only edges ≤ 3. Commit `f47093b` compares `max_grade` with the stored values directly.
`/trace_attributes` `max_upward_grade`/`max_downward_grade` are the same stored values, so
**they are already percent**.

### Downhill applies in the direction of travel

Footway way 1302664398 climbs 13 % northbound (48 m). South point (41.141857,-8.614406),
north point (41.142476,-8.614126):

| Direction | No cap | Cap 15 % | Cap 12 % |
|---|---|---|---|
| South → north (uphill) | 0.073 km, up 13 | 0.073 km, up 13 | 0.130 km detour, max 10 |
| North → south (downhill) | 0.118 km, down 15 | 0.118 km, down 15 | 0.130 km detour, max 10 |

The same results come from the default search, `date_time` type 1 (depart_at →
`timedep_forward`, only `Allowed`) and type 2 (arrive_by → `timedep_reverse`, only
`AllowedReverse`, which checks `opp_edge`, the edge in the direction of travel). The two
paths agree. Both magnitudes are compared with the same cap, so a steep edge is closed in both
directions.

### Demo route: São Bento → Batalha

Origin (41.1455,-8.6105), Estação de São Bento; destination (41.1459,-8.6064), Batalha.
Options as the app sends them (`type: wheelchair`, `step_penalty: 43200` when capped):

| Cap | Length | Steepest interior edge |
|---|---|---|
| No limit (`foot`) | 0.49 km | 20 % |
| 10 % | 0.97 km | 10 % |
| 8 % | 1.04 km | 8 % |
| 6 % (wheelchair profile) | 1.30 km | 6 % |

The stricter cap changes the route and never removes it. In the locally served app the
wheelchair profile draws the 1.3 km / 21 min route. Before the units fix, São Bento → Sé
(0.38 → 0.60 km) played this role; with correct units its wheelchair route is the direct one.

**App display bug (for Ben, not changed here):** `degreesToPercent` in `app/app.js` applies
`tan()` to values that are already percent. The same route therefore shows "Subida mais
inclinada: 11 %" and flags 7 segments in orange as steeper than requested, although none
exceeds 6 %. Fix: make it the identity (keep the 32768 no-elevation check), and in the same
commit update the contract line in `CLAUDE.md` ("Grades are read as degrees") and
`app/README.md`.

### Missing elevation: measured, explicit policy

- **DEM:** 0 void cells (−32768) in about 4.2 M samples of `N40W009`/`N41W009` inside the bbox.
  All 13 tiles have the elevation flag. Today no edge gets a "no data" slope.
- **What counts as flat without being measured** (directed edges found by `/locate` on a 40 m grid over central
  Porto: 3,682 edges, 196 km):
  - edges shorter than 10 m are stored as 0 by design (`kMinimumInterval`): 593 edges (16 %),
    but only 1.6 % of length;
  - bridges and tunnels are interpolated between their ends and clamped to ±3: 93 edges (2.5 %).
- **Short edges are underestimated:** edges under 60 m get only end samples but are still divided by
  60 m, so their grade is scaled by L/60 (a 20 m ramp at 15 % is stored as 5 %): 52 % of
  edges, 32 % of length. Steeper stretches above 15 are stored in 4-point steps.

**Agreed policy:** under a cap (`max_grade` below 90), edges in tiles built without elevation are
**rejected** (fail closed; commit `f47093b`). This guards against a graph built without a DEM. Edges
under 10 m, bridges/tunnels and the L/60 underestimate are **accepted and disclosed** as known
limits. The 60 m window also smooths a 30 m, integer-metre DEM, and using the true spacing would
make short edges noisy (±1 m over 10 m = ±10 %). The fail-closed branch was not exercised
end to end: every tile here has elevation, and testing it needs a separate tileset built without
a DEM.

### Still open

- **Origin/destination partial edges are not capped.** Example: Sta Catarina → Bolhão at 6 % has
  a 16 % end edge. The app's trace-based warning flags such edges (after the display fix
  above, with correct numbers).
- No route is returned when a cap cannot be met; the app offers +2 % and never relaxes it itself.
- Valhalla minimises cost, not length, so a stricter cap can occasionally give a *shorter* route
  than a looser one. The demo pair is monotonic.
- An image rebuild is a full C++ compile (~40 min, two workers). A ccache mount would make later
  costing changes take minutes.

## Demo barriers verified (24 October 2026, ~11:45 UTC)

`runtime/demo/barriers.py` seeds and clears the demo barriers (usage and table in
`runtime/demo/README.md`). São Bento → Batalha, wheelchair profile (6 %), ±15 m exclusion squares:

| Barriers | Route |
|---|---|
| none | 1.302 km, 21.4 min |
| `demo-roadworks` (41.14384, -8.60766) | 1.721 km |
| `demo-parked-car` (41.14494, -8.61080) | 1.437 km |
| both | 1.856 km, 29.4 min |
| `demo-control` (41.1468, -8.6085), off the route | 1.302 km, no change |

Checked in two Chrome tabs of the locally served app (`127.0.0.1:8765`) with the route already drawn:
after `seed` both tabs showed "2 obstáculos no mapa" and rerouted to 1.856 km without a reload; a
reloaded tab got both barriers back from the retained messages and routed to 1.856 km; after `clear`
both tabs dropped to no barriers and 1.302 km. `clear` was also checked not to touch a non-demo retained
barrier (a throwaway `zz-other-test` survived and was removed by hand). The control barrier was checked
against Valhalla directly (and in the seed/list/clear round trip), not drawn in the browser.

```bash
export BROKER_USERNAME=... BROKER_PASSWORD=...   # same login as app/config.local.js
python3 hackathon/runtime/demo/barriers.py seed      # list / clear likewise
```

Caveats:
- Seeded barriers expire after 24 h: seed again before the demo. (They used to be lost on a broker restart too;
  durability is on since 12:40, see "Broker durability verified".)
- The script uses the default broker login over plain MQTT on loopback (Community tier, no per-user rules).
- The slope warning in the app still overstates grades (the `degreesToPercent` bug above): the detour screenshot
  showed orange "steeper than asked" segments although every edge is within 6 %.
- `access/barriers/<id>/feedback` is already in the topic map in `README.md`; the "missing from the topic
  map" caveat under "Core 1 verified" is out of date.


## City alerts verified (24 October 2026, ~12:10 UTC)

`lot/city_alerts.lotnb` (connector `PortoUrbanPlatform`, Action `ImportCityAlerts`, Python `CityAlerts`) loaded as
project `lot` with no warnings; `diagnose` clean.

| Check | Result |
|---|---|
| Source | FIWARE `type=Alert&q=category==traffic`, `near;maxDistance:500` of (41.1450, -8.6085), `orderBy=!validTo`, 100 rows (82 KB): 48 still valid on 24/10 |
| Filter | 24 kept ("Obras particulares" / "Obras públicas"); loading bays, events and concrete pumping dropped |
| Broker | `access/city/alerts/fetch` → 24 retained `access/barriers/city-*` in the contract format, `last_ok` set, snapshot kept |
| Repeat | Same answer again publishes 0 barriers (unit test and offline run); retiring an alert that leaves the source is unit-tested only |
| Routing, wheelchair 6 % | São Bento → Batalha: none 1.302 km; 2 demo barriers 1.856 km; 24 city barriers 2.164 km; city + demo 2.164 km |

**Valhalla limit fixed on the way.** The default `service_limits.max_exclude_polygons_vertices` is 100: with the
app's 5-vertex squares, more than 20 active barriers made every route fail with error 176 ("Exceeded maximum number
of vertices for exclude_polygons"), city alerts or not. `setup.sh config` now sets 1000 vertices and 50 km of perimeter;
the existing `data/valhalla.json` was patched the same way and the container restarted (no tile rebuild);
`setup.sh smoke` passes. The public FOSSGIS fallback keeps the default limit.

Caveats:
- With the city barriers active, the two demo barriers no longer change the route (the city detour already avoids
  them). The demo sequence needs new demo barrier positions on the 2.164 km route, or the city import off.
- These are works registered by the Câmara, not confirmed obstacles. A barrier is a ±15 m square at the polygon's
  vertex centroid, so a long street polygon ("Ambos os lados, em toda a sua extensão") is only partly covered.
- ~~Retained city barriers are lost on a broker restart until the next import.~~ Superseded: durability is on and the
  import snapshot is retained (see "Broker durability verified").

## City alerts switch verified (24 October 2026, ~12:30 UTC)

Retained `access/city/alerts/enabled` = `on` | `off` (QoS 1), Action `SwitchCityAlerts` and a gate in
`ImportCityAlerts` (`lot/city_alerts.lotnb`). Python `CityAlerts.retire_all` added, with tests (11 pass).
Deployed with `add_python` + `deploy_lot` into the running project; **no project swap**, so Ben's
`10-barriers-db.lotnb` (valid, but the broker has no `SUPABASE_*` env/secret) is still not loaded. The live Action
sources were compared with the notebook cells: identical. `diagnose` clean after every step.

São Bento → Batalha, wheelchair 6 %, local Valhalla, every active (non-expired) retained barrier excluded as the app does:

| Step | Active `city-*` | Route |
|---|---|---|
| before (no flag) | 24 | 2.164 km |
| `off` | 0 (24 republished with `expires_at` = now) | 1.302 km |
| manual fetch while `off` | 0, `last_ok` unchanged | 1.302 km |
| `on` | 24 (fetch at once, real expiry back) | 2.164 km |
| repeat fetch, no changes | 24, `last_ok` advanced, `last_error` unchanged | 2.164 km |

**Broker bug found on the way (now in `AGENTS.md`).** A block ending with `UNTIL` mis-scopes the lines after it
by one level. The first `SwitchCityAlerts` had its `ELSE IF "on"` swallowed (`run_action` published nothing),
and the original `ImportCityAlerts` had published `last_error` instead of `last_ok` on every import with no changes
(the `last_error` of 12:21:19 UTC). Both loops now run without the `IF {count} > 0` guard.
Reproduced and characterised with throwaway `Zz*` Actions, since removed.

Commands (default broker login, loopback; uses the stdlib client in `runtime/demo/barriers.py`, read-only):

```bash
# off: city barriers retired, import paused. Use "on" to resume and republish them at once.
python3 -c "import sys; sys.path.insert(0,'hackathon/runtime/demo'); from barriers import connect; c=connect(); c.publish('access/city/alerts/enabled', sys.argv[1].encode()); c.close()" off
```

`connect()` reads `BROKER_USERNAME` / `BROKER_PASSWORD` like `barriers.py`.

Caveats:
- ~~The flag is lost on a broker restart (durability off).~~ Superseded: the flag survives a restart now (see
  "Broker durability verified"), but the switch needed the snapshot fix recorded there.
- While `off`, the connector keeps polling FIWARE every 10 min; only the import is skipped.
- That a fetch actually produced a FIWARE answer while `off` was not observed directly: the proof is that nothing
  was imported and `last_ok` did not move, while the same manual fetch while `on` did advance it.
- The city barriers are retired, not deleted: 24 expired retained messages stay on `access/barriers/city-*` until the
  next `on` overwrites them. The app hides them, and `barriers.py list` still shows them with a past `expires_at`.

## Broker durability verified (24 October 2026, ~12:40–12:55 UTC)

`broker/docker-compose.yml` sets `COREFLUX_DURABILITY_ENABLED=true` and `COREFLUX_DURABILITY_DATA_DIR=/etc/project/mqttwal`
(write-ahead log on the `broker-data` volume, defaults: JSON codec, fsync every 50 ms). Applied with a recreate:
`docker compose -f docker-compose.yml -f docker-compose.ws.yml up -d broker`. Every port still on 127.0.0.1
(`docker port o1n-broker`). `/metrics`: `coreflux_durability_enabled 1`. The recreate itself dropped the 27 retained
`access/*` messages (durability was off until then); the switch was set back to `on`, which re-imported 24 barriers.

**Restart 1 (`docker restart o1n-broker`, 12:43).** Before: 24 `city-*` + 2 `demo-*` barriers, `enabled`, `last_ok`,
and one test answer on `access/barriers/zz-test/feedback` (stored as `answers/zz-fb-1`, `gone_count` 1,
`last_answered_at`): 31 retained `access/*`. After: the same 31, byte for byte. After the restart a second answer took
`gone_count` to 2 and a resend of `zz-fb-1` was ignored. `zz-test` topics then cleared.

**The off switch broke on that restart (fixed).** Codex then published `off` and nothing was retired: the import
snapshot `access/state/city_alerts` was a `KEEP TOPIC`, memory only, so it came back empty while the barriers
survived. It is now a retained internal topic (QoS 1, topic map in `README.md`), written by both `ImportCityAlerts`
and `SwitchCityAlerts`. The live state was repaired with one `on` → `off` cycle (24 imported, 24 retired).

**Restart 2 (12:53), the snapshot fix.** `on` (24 active, snapshot with 24 entries) → restart → redeploy (below) →
manual fetch: **0** barriers republished and `last_ok` advanced, so the import compared against the restored snapshot
(an empty one republishes all 24) → `off`: all 24 retired (`expires_at` = now), snapshot `{}`. `diagnose` clean.
Broker log: "RetainedStore: recovered 49 retained message(s) from WAL".

**Every boot restores stale code (now in `AGENTS.md`).** After both the recreate and each restart, the live
`ImportCityAlerts` was an old one (no `enabled` gate, `UNTIL` bug), and `CityAlerts` was redeployed too since its live
source cannot be read back; `SwitchCityAlerts` (deployed ad hoc) survived. Cause, found later (see "Operator panel
verified"): the boot log says the persisted actions file holds duplicate `ImportCityAlerts` blocks and keeps the first,
oldest one. After each boot `add_python CityAlerts` + `deploy_lot ImportCityAlerts` from `lot/city_alerts.lotnb`,
then the live `$SYS/Coreflux/Actions/*` sources were compared with the notebook: identical. Ben's notebook is not in
the broker's project copy, so a boot does not load it.

Caveats:
- **After any broker restart, redeploy `CityAlerts` and `ImportCityAlerts`** (see above) before using the switch;
  the stale `ImportCityAlerts` ignores `off` and uses the old buggy loop.
- On restart 2, a client that subscribed ~4 s after `/health` turned healthy got no retained messages at all;
  5 s later all 27 were there. Reload browser tabs that were open during a restart.
- Ended with `enabled = off` (as Codex's last demo check left it): 0 active `city-*`, no demo barriers.
- Only retained messages were exercised; persistent sessions and queued QoS 1 were not tested (`durable_sessions 0`).

## Operator panel verified (24 October 2026, ~13:00–13:14 UTC)

`lot/ops_panel.lotnb`: Python `OpsSummary`, Actions `OpsSummaryOnBarrier` (`access/barriers/+`), `OpsSummaryOnFeedback`
(`access/feedback/+/last_answered_at`), `OpsSummaryRefresh` (every 15 s) → retained `access/ops/summary`; LoTV panel
`RotaLivreOps` (4 columns: gauges for app / city / demo, the `enabled` indicator, a trend of all active barriers,
`last_ok` / `last_error` / summary time, the active-barrier table and the "gone" table). Read-only. Deployed with
`add_python` / `deploy_lot` / `add_panel`, no warnings; live sources (Actions and `$SYS/Coreflux/Visus/RotaLivreOps`)
identical to the notebook. 23 pytest tests pass (`services/tests/`). `diagnose` clean.

**Lost updates found and fixed.** The first, pure version (each run reads the retained summary, changes it,
publishes it) counted **6 of 24** barriers on a city `on` burst: an Action's triggers run concurrently. Throwaway
`Zz*` Actions showed a plain LoT counter losing updates too (35/40 on one topic, once), that a Python script's module
persists between calls, and that a `threading.Lock` makes 30 concurrent calls exact. `OpsSummary` now keeps its state in
the module under a lock (agreed exception to "pure Python"), seeded from the retained summary after a restart.
Same burst after the change: **24/24**; `off` → 0.

| Check (live, through MQTT) | Result |
|---|---|
| Test barrier `zz-ops-1` published / cleared (empty retained) | app 1 → 0 |
| City `off` → `on` burst | city 0 → 24 |
| `zz-ops-2` with `expires_at` = now + 40 s, no further message | dropped by the 15 s refresh after it expired |
| 2 "gone" answers on `city-cmp1555559` | `gone_count` 2 in its row and in `feedback`; still listed after `off` retired the barrier |
| Restart (13:12), nothing redeployed | summary, answers and the switch survived; the module re-seeded from the summary |

**In the HUB** (<http://localhost:3000> → Dashboards → "Rota Livre: barrier operations", Chrome): rendered city 24,
indicator "On", 24 table rows with sources and kinds, "Gone answers 2". Then, without a reload, `off` + `barriers.py
seed`: city 0, demo 2, indicator grey "Off", the trend fell 24 → 2, 2 demo rows; after `clear` and clearing the test
answers: all 0, both tables "No data".

**Stale code at boot, cause found.** `remove_action` of a throwaway Action at 13:03 logged "Duplicate DEFINE ACTION
block for 'ImportCityAlerts' in actions file. Keeping the first definition", and every boot logs the same for
`ImportCityAlerts` and `StoreBarrierFeedback`. `remove_action` + `deploy_lot` of both ("2 duplicate definitions
cleaned up") did **not** help: the 13:12 boot logged the duplicates again and reverted `ImportCityAlerts`
(redeployed with `CityAlerts` afterwards). The `OpsSummary*` Actions (ad hoc only) came back current.
One live mismatch at 13:10 was a false alarm of the comparison script (a `$SYS/Coreflux/#` subscription), not a revert.

Caveats:
- After any broker restart, redeploy `CityAlerts` + `ImportCityAlerts` (`AGENTS.md`); the panel needs nothing.
- The summary only learns barriers from messages it sees: barriers retained before `OpsSummaryOnBarrier` existed were
  picked up by republishing them (`on`/`off`, `seed`). All current ones are in it.
- Two summary publishes can still arrive out of order; the 15 s refresh corrects that. The trend chart's history lives
  in the open HUB page only.
- A real app report, `bmvmf2lix8tqd` (parked car, 13:10), appeared during the session: not mine, left in place.
  End state: `enabled = off`, 0 active city, 0 demo, 1 app barrier, no test topics.

## Post-restart repair scripted (24 October 2026, ~13:20–13:25 UTC)

`broker/redeploy_lot.py` (stdlib, MQTT through `runtime/demo/barriers.py`) replaces the manual post-restart redeploy.
It reads only `barrier_feedback`, `city_alerts` and `ops_panel`, compares each Action with its retained
`$SYS/Coreflux/Actions/<Name>` (whether an entity exists comes from `-listEntities`; Python is checked for presence
only, since its source cannot be read back), and with `--fix` resends a mismatched notebook's Python cells, then its
mismatched Actions, through `$SYS/Coreflux/Command`, stopping on any `success:false`. 10 pytest tests for the pure
parts; `services/tests/` 33 pass.

| Step (live) | Result |
|---|---|
| `--check` before the restart | 8/8 IDENTICAL (6 Actions, 2 Python), exit 0 |
| `docker restart o1n-broker` (13:23:51, healthy 13:23:57) | boot log: duplicate blocks for `StoreBarrierFeedback` and `ImportCityAlerts`; "recovered 60 retained message(s) from WAL" |
| `--check` 10 s after `/health` | only `ImportCityAlerts` DIFFERS, exit 1 (`StoreBarrierFeedback`'s kept copy is current) |
| `--fix` | sent `CityAlerts`, then `ImportCityAlerts`; both replies `success:true`; re-check 8/8 IDENTICAL, exit 0 |
| `--check` again | 8/8 IDENTICAL, exit 0 |
| manual `access/city/alerts/fetch` with the switch `off` (13:24:33) | FIWARE answered (`raw`: 100 entities), **0** barrier messages, `last_ok` unchanged (13:04:41.587Z) |
| `diagnose` | 0 action errors, nothing pending |

This closes the caveat under "City alerts switch verified": a fetch while `off` now provably got a FIWARE answer and
imported nothing. End state as before: 29 retained `access/*`, switch `off`, 1 app barrier (`bmvmf2lix8tqd`), summary
`active` app 1, city 0, demo 0.

**Found on the way (now in `AGENTS.md`).** The command channel strips `//` outside string literals in Python too:
a throwaway `ZzSlash` with `int(x) // 2` failed with `'(' was never closed`; `f"{7 // 2:03d}"` deployed and returned
`003`. Both Python cells only use `//` inside an f-string. The `-addAction` source stored by the broker was
byte-identical to what was sent, and `-addAction` over an existing name replaces it. The throwaway `ZzSlash` /
`ZzSlashProbe` were removed; their `zz/redeploy/*` topics were never retained.

Caveats:
- Python is only checked for presence, so a stale script after a boot is not detected unless an Action of its notebook
  differs. On this boot `CityAlerts` was resent anyway (it shares the notebook with `ImportCityAlerts`); `OpsSummary` was
  not, and the panel kept working.
- The Action duplicates in the broker's persisted actions file are still there; the script repairs the effect, not the cause.
- Ben's `0b589ef` (13:22 UTC, pushed while this ran) keeps `10-barriers-db.lotnb` loaded. `-listEntities` showed neither
  `RouteBarrierMessage` nor `BarriersDB` at ~13:20 (before the restart) nor at ~13:30 (after it), and no
  `Routes/BarriersDB/status`; whether they were deployed in between is unknown. The script does not cover them: re-add
  them as `AGENTS.md` says.
