# CLAUDE.md

Repository of team O(1/n) (Miguel, Victor, Ben, Pedro) at SciTeCh '26 (BEST Porto, FCUP,
24–25 Oct 2026). Two challenges, each with 6 h of work: `hackathon/` (Coreflux,
**Saturday 24**) and `team-design/` (Arduino, **Sunday 25**). See `README.md` and `regulamento.pdf`.

## Conventions (mandatory)

- **Everything in English**: code (identifiers, file/folder names, Serial messages, MQTT topics,
  names of LoT Actions/Models/Connectors), code comments and documentation (READMEs, this file).
- Trunk-based git: small commits straight to `main`; `git pull --rebase` before pushing.
- Never commit secrets (`.env` is in `.gitignore`).
- Hackathon: solutions go through plagiarism detection. Do not copy the Coreflux training labs
  (`CorefluxCommunity/weather-station-hackathon`); use them only as a syntax reference.

## team-design/ (PlatformIO, Arduino Uno)

```bash
cd team-design && source .venv/bin/activate
pio test -e native     # Unity tests of the pure logic on the PC — run after any change
pio run -e uno         # build
pio run -e uno -t upload && pio device monitor   # real board, Serial at 9600
wokwi-cli --scenario test/wokwi/mode_cycle.yaml --timeout 10000   # needs WOKWI_CLI_TOKEN
```

Architecture: **pure logic** in `lib/Control/` (no `Arduino.h`, testable with `-e native`) vs.
**hardware layer** in `src/main.cpp` (pins, Servo, Serial). New logic goes into `lib/` with tests
in `test/test_control/`; `main.cpp` should stay thin.

Invariants that are easy to break:
- `include/pins.h`, `diagram.json` (Wokwi) and the real wiring must match.
- Servo uses Timer1 → **no PWM on pins 9/10**; motor PWM is on 5/6.
- The `KEY=value` Serial output (e.g. `MODE=FORWARD A=200 B=200 SERVO=90`) is checked verbatim by
  `test/wokwi/mode_cycle.yaml`. If you change the format, update the scenario.
- Wokwi has no L298N/DC motors: in `diagram.json` the H-bridge signals are LEDs.

## hackathon/ (Coreflux)

Coreflux MQTT broker + HUB in Docker (`hackathon/broker/`). The logic lives in the broker as LoT
(Actions, Models, Connectors, Rules, Panels); the source of truth is the `.lotnb` files in
`hackathon/lot/` (mounted read-only in the broker at `/lot`). LoT rules for the AI are in `hackathon/AGENTS.md`
(auto-loaded via `hackathon/CLAUDE.md`). **Never write LoT from memory**: use the Coreflux skills in
`.claude/skills/` (pinned to broker 2.22.0) and the `coreflux-docs` MCP server, check against the live broker with
the `coreflux-broker` MCP server (`validate_lot`/`validate_lotnb`), and deploy with `/lot-deploy`.
Setup: `hackathon/AI.md`. The team has an unlimited
licence (`CFLX-...`, in `hackathon/broker/.env`, outside git); without it, the Community edition only allows
**3 Connectors**, no custom Rules and no `TYPE LLM`.
The pitch (5 min + up to 3 min of questions; problem → demo → architecture → maturity) is in
`hackathon/PITCH.md`.

### Web app ↔ backend contract (`hackathon/app/`, Rota Livre)

Static page (no build), UI in European Portuguese, live at <https://accessible-routes.benlubetzky.workers.dev>
(`?demo` simulates a walking position). Every push to `main` touching `hackathon/app/` redeploys it
(`.github/workflows/deploy-app.yml` → Cloudflare Worker; `.assetsignore` lists what is not published).
The backend plugs in through `hackathon/app/config.js` only: `valhallaUrl`, `brokerUrl`, `topicPrefix` (`access`).
Broker credentials go in `config.local.js` (gitignored) and are visible to any browser, so give the page a broker
user limited to `access/barriers/#`. The page is served over HTTPS: **both endpoints must be HTTPS/WSS and send
CORS headers** (`Access-Control-Allow-Origin: *`), or the browser blocks them. All routing calls are in
`routeService` in `app.js`; if the contract below changes, update that code, `hackathon/app/README.md` and the
topic map in `hackathon/README.md` in the same commit.

**Routing (Valhalla HTTP API).** Today `valhallaUrl` is the public FOSSGIS instance, which ignores the slope cap.
- `POST {valhallaUrl}/route` with `locations` (start, destination), `costing: "pedestrian"`,
  `costing_options.pedestrian` = `type` (`"wheelchair"` when avoiding rough surfaces, else `"foot"`), `max_grade`
  (percent, 2–14; **omitted** for "no limit"), `step_penalty: 43200` when avoiding steps; `exclude_polygons`
  (one closed `[lon, lat]` square of ±15 m around each active barrier); `units: "kilometers"`, `language: "pt-PT"`.
- Read from the response: `trip.summary.{length,time}`, `trip.legs[0].shape` (polyline, 6 decimals),
  `legs[0].maneuvers[].{type, instruction, street_names, length, begin_shape_index, end_shape_index}`
  (types 4–6 = arrival). Errors: `error_code` 442/443 = no route under the limits (the page offers +2 % and **never
  relaxes the limit itself**), 170/171 = point too far from a path, anything else = "try again".
- `POST {valhallaUrl}/trace_attributes` with `encoded_polyline`, `shape_match: "edge_walk"`, the same costing and
  `filters.attributes` = `edge.length`, `edge.use`, `edge.max_upward_grade`, `edge.max_downward_grade`,
  `edge.begin_shape_index`, `edge.end_shape_index`. Grades are read as **degrees** (shown as % via tan);
  32768 = no elevation. Used for the "steeper than you asked" warning; if it fails, the route still shows.

**Barriers (Coreflux MQTT over secure WebSocket).** With `brokerUrl` empty (today) reports stay on the device
(`localStorage` key `access.barriers`) and nobody else sees them; setting `brokerUrl` switches to the broker.
- Topic `access/barriers/<id>`, one **retained** message per barrier, QoS 1. The page subscribes to
  `access/barriers/+` and publishes new reports itself. Only the device that made a report may delete it
  ("Apagar o meu reporte"), by publishing an **empty retained** payload on its topic.
- **"Is it still there?" answers:** while guiding, passing within 30 m of a barrier asks "Ainda está aí?" (once per
  barrier per trip; gone after 10 s without an answer). "Ainda está" sends nothing. "Já não está" (from that card
  or from a barrier's popup) **does not remove the barrier**: it publishes a **non-retained**, QoS 1 message on
  `access/barriers/<barrier id>/feedback` = `{"id", "barrier_id", "answer": "gone", "answered_at", "lat"?, "lon"?}`
  (`lat`/`lon` = where the person was, when known). **The backend must store these** (the page does not keep them
  once sent); the team reviews the counts per barrier at the end of the day and decides. The broker Action
  `StoreBarrierFeedback` (`hackathon/lot/barrier_feedback.lotnb`) stores them under `access/feedback/<barrier id>/`
  (see the topic map in `hackathon/README.md`). Until a broker is
  connected, answers wait in the device outbox (`localStorage` key `access.feedbackOutbox`) and are sent on connect.
- Payload: `{"id", "kind", "description", "lat", "lon", "reported_at", "expires_at"}` (ISO 8601 times; `id` like
  `b<base36 time><random>`; `description` may be `""`; expiry = report + 24 h). `kind` is one of `works`,
  `blocked_sidewalk`, `parked_car`, `broken_lift`, `damaged_pavement`, `other`. Unknown kinds show as `other`;
  messages without numeric `lat`/`lon` are ignored, extra fields are ignored.
- The page hides barriers past `expires_at` itself; the broker may also clear them (empty retained message).
  Barriers published by the backend (city alerts, lift status) appear and are avoided like any report.
- Not sent to the broker (device-only for now): the report's photo (≤ 800 px JPEG data URL) and the address text.
  Sharing them means adding optional `photo`/`address` fields to this contract first.

**Storage (Supabase Postgres, written by Coreflux).** Coreflux is the backend: `hackathon/lot/10-barriers-db.lotnb`
(Action `RouteBarrierMessage` + PostgreSQL connector `BarriersDB`) stores reports in `barriers` (a reporter's
delete sets `deleted_at`, rows are never removed) and answers in `barrier_feedback`; the view `barrier_review`
is the end-of-day count. Schema, tests and setup: `hackathon/db/` (`schema.sql`, `README.md`). Internal topics
`access/db/barriers/upsert` and `access/db/barriers/deleted` are for the broker only. The connector's
credentials are broker env/secrets (`SUPABASE_DB_HOST`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`), never git.
If you add a field to a payload above, add the column in `schema.sql` and the value in the connector's QUERY.
