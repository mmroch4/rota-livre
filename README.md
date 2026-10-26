# Rota Livre — accessible routes in Porto

Rota Livre plans walking routes in Porto under a person's limits (slope, steps, surface) and goes around barriers
that anyone reports or that the Câmara has registered, shared live through a Coreflux MQTT broker.

Built by team **O(1/n)** (Miguel, Victor, Ben, Pedro) at [SciTeCh '26](https://scitech.bestporto.org/index.html)
(Science and Technology Challenge), organized by BEST Porto at FCUP: 6 hours of work on 24 October 2026, judged
on a 5-minute pitch with a live demo.

> **Result: 1st place** in the SciTeCh '26 Hackathon (Coreflux challenge).
> Rota Livre now goes on to a further stage of the competition, **mentored by Coreflux**, competing for a place at
> **Hannover Messe**: see [Next phase](#next-phase-coreflux-mentoring-and-hannover-messe).
>
> Sections 1–5 describe the system as demonstrated on 24/10, in the order the jury judged it (Rules, Art. 1, 3):
> **problem → demo → architecture → maturity**. Event-day planning is kept in [PLAN.md](PLAN.md) and
> [PITCH.md](PITCH.md).

## 1. The problem

People with reduced mobility need walking routes that respect their limits (how steep, whether there are steps,
how rough the surface is) and that react to what is in the way on the day: road works, a car on the pavement,
a broken lift. Porto's historic centre is steep, with steps and cobbled streets.

## 2. The solution

Rota Livre is a web app (in European Portuguese) where a person picks how they get around, from wheelchair to no
mobility difficulties, plans a walking route in Porto under those limits and is guided along it. Anyone can report
a barrier in a few taps: it reaches every open map at once and routes go around it. The Câmara do Porto's registered
road works are imported as barriers automatically. Screens and behaviour: [app/README.md](app/README.md).

Public page: <https://accessible-routes.benlubetzky.workers.dev> (`?demo` walks along the route by itself).
It routes and shares barriers only while the team's Valhalla and broker are running behind their Cloudflare tunnels
(see "Web app over the internet" below); on 26/10 the page was up but its Valhalla tunnel did not answer.

## 3. Architecture

```text
 Browser: app/ (static page, Cloudflare Worker)
   │ HTTPS: /route, /trace_attributes            │ MQTT over WSS, user `web` (access/barriers/# only)
   ▼                                             ▼
 Valhalla (runtime/valhalla/)              Coreflux broker (broker/, LoT in lot/)
 pedestrian costing with a                   ├─ retained barrier per topic, durable across restarts
 slope cap (max_grade), steps,               ├─ PortoUrbanPlatform (REST, every 10 min) → ImportCityAlerts → city-* barriers
 surface; barriers sent as                   ├─ StoreBarrierFeedback: "Já não está" answers and counts
 exclude_polygons                            ├─ OpsSummary* → access/ops/summary → HUB panel RotaLivreOps
                                             ├─ NotifyNewBarrier / NotifyGoneThreshold → TeamTelegram (Telegram)
                                             └─ RouteBarrierMessage → BarriersDB (PostgreSQL) → Supabase (db/)
```

- **Web app** ([`app/`](app/README.md)): all routing calls are in `routeService` in `app.js`. When no route fits
  the slope limit it says so and offers the gentlest one; it never relaxes steps, surface or barriers.
- **Routing** ([`runtime/valhalla/`](runtime/valhalla/README.md)): Valhalla built from
  [`projects/valhalla`](projects/valhalla) with one costing fix, so that `max_grade` is applied to uphill and
  downhill edges ([handoff](docs/accessibility_routing_project_handoff.md), "Core 2 verified" in
  [`docs/runtime-baseline.md`](docs/runtime-baseline.md)).
- **Broker** ([`broker/`](#environment-setup-linux--macos)): Coreflux in Docker. The logic is LoT, one notebook per
  feature in [`lot/`](lot/):

  | Notebook | Entities | What it does |
  |----------|----------|--------------|
  | `city_alerts.lotnb` | `PortoUrbanPlatform`, `ImportCityAlerts`, `SwitchCityAlerts`, Python `CityAlerts` | Imports the Câmara's active road works near the demo route (FIWARE) as barriers; on/off switch |
  | `barrier_feedback.lotnb` | `StoreBarrierFeedback` | Stores "it's gone" answers and a count per barrier; removes nothing |
  | `ops_panel.lotnb` | `OpsSummaryOnBarrier`, `OpsSummaryOnFeedback`, `OpsSummaryRefresh`, Python `OpsSummary` | Live summary for the read-only HUB panel `RotaLivreOps` |
  | `telegram_notify.lotnb` | `TeamTelegram`, `NotifyNewBarrier`, `NotifyGoneThreshold`, Python `TelegramNotify` | New reports to a public channel; 3 "gone" answers to the team group |
  | `10-barriers-db.lotnb` | `RouteBarrierMessage`, `BarriersDB` | Keeps reports and answers in Supabase ([`db/`](db/README.md)) |
  | `web_access.lotnb` | `AllowBarrierPublish`, `AllowBarrierSubscribe`, `DenyWebPublishElsewhere`, `DenyWebSubscribeElsewhere` | Limits the public page's user `web` to `access/barriers/#` |

### MQTT topic map

| Topic | Producer | Consumer | Payload |
|-------|----------|----------|---------|
| `access/barriers/<id>` (retained) | web app; broker: `ImportCityAlerts` (`city-*` ids) | web app; broker: `RouteBarrierMessage` (app ids → Supabase) | `{id, kind, description, lat, lon, reported_at, expires_at}`, city ones add `source: "cm-porto"`; empty retained payload removes the barrier (only clients can send it: the broker retires a barrier by republishing it with `expires_at` = now) |
| `access/barriers/<barrier id>/feedback` (not retained) | web app ("Já não está") | broker: `StoreBarrierFeedback` (`lot/barrier_feedback.lotnb`); connector `BarriersDB` → Supabase `barrier_feedback` | `{id, barrier_id, answer: "gone", answered_at, lat?, lon?}`; does not remove the barrier. Two stores on purpose: Supabase is the long-term record and review for app reports (`b…` ids only, `schema.sql` rejects others); the broker store below gives live counts over MQTT and is the only one for `city-*` / `demo-*` barriers |
| `access/feedback/<barrier id>/answers/<feedback id>` (retained) | broker: `StoreBarrierFeedback` | team, end-of-day review; live counts | the feedback payload, unchanged; one per distinct `id` (resends count once) |
| `access/feedback/<barrier id>/gone_count` (retained) | broker: `StoreBarrierFeedback` | team, end-of-day review | number of distinct "gone" answers for that barrier |
| `access/feedback/<barrier id>/last_answered_at` (retained) | broker: `StoreBarrierFeedback` | team, end-of-day review | `answered_at` of the latest stored answer (ISO 8601) |
| `access/db/barriers/upsert` (internal) | broker Action `RouteBarrierMessage` | connector `BarriersDB` → Supabase `barriers` | the report's JSON, unchanged |
| `access/db/barriers/deleted` (internal) | broker Action `RouteBarrierMessage` | connector `BarriersDB` → sets `deleted_at` | the barrier id (checked: `b` + letters/digits) |
| `access/city/alerts/fetch` (not retained) | anyone (manual refresh); broker: `SwitchCityAlerts` on `on` | broker: `PortoUrbanPlatform` connector | any payload; the connector also fetches every 10 min |
| `access/city/alerts/raw` (not retained) | broker: `PortoUrbanPlatform` | broker: `ImportCityAlerts` | FIWARE NGSI v2 `Alert` entities (keyValues), or `{"success": false, ...}` on an HTTP error |
| `access/city/alerts/last_ok`, `.../last_error` (retained) | broker: `ImportCityAlerts` | team, demo checks | ISO time of the latest successful import / failed fetch |
| `access/city/alerts/enabled` (retained, QoS 1) | team (demo switch) | broker: `SwitchCityAlerts`, `ImportCityAlerts` | `on` or `off`. `off` retires every imported `city-*` barrier (`expires_at` = now) and makes the import ignore fetches; `on` fetches at once and republishes them. Missing = `on` |
| `access/state/city_alerts` (internal, retained, QoS 1) | broker: `ImportCityAlerts`, `SwitchCityAlerts` | broker: the same two Actions | `{<barrier id>: barrier}` of the `city-*` barriers imported last time (`{}` after `off`); what `off` retires and what the next import compares against. Retained so it survives a restart with the barriers |
| `access/ops/summary` (retained, QoS 1) | broker: `OpsSummaryOnBarrier`, `OpsSummaryOnFeedback`, `OpsSummaryRefresh` (`lot/ops_panel.lotnb`, every 15 s too) | operator panel `RotaLivreOps` (HUB) | `{updated_at, active: {app, city, demo, total}, barriers: [{id, source, kind, description, expires_at, gone_count}], feedback: [{barrier_id, gone_count, last_answered_at}]}`; `barriers` = active only; source `city-*` → city, `demo-*` → demo, else app |
| `access/notify/telegram/send` (internal, not retained) | broker: `NotifyNewBarrier` (new app report), `NotifyGoneThreshold` (`gone_count` reaches 3) (`lot/telegram_notify.lotnb`) | connector `TeamTelegram` → Telegram `sendMessage` | `{chat_id, text, disable_web_page_preview}`; token = broker secret `TELEGRAM_BOT_TOKEN`; new reports go to the public channel (env `TELEGRAM_CHANNEL_ID`, `@username`), the "gone" threshold to the team group (env `TELEGRAM_CHAT_ID`) |
| `access/notify/telegram/result` (internal, not retained) | connector `TeamTelegram` | team, debugging | Telegram's answer (`{"ok": true, ...}`) or `{"success": false, "statusCode", "endpoint", ...}`; **an error's `endpoint` holds the bot token**: root only |
| `access/notify/telegram/sent/<barrier id>` (internal, retained, QoS 1) | broker: `NotifyNewBarrier` | broker: `NotifyNewBarrier` | ISO time the report was sent to Telegram; stops republished/retired reports from sending again |

## 4. Demo

Victor owned the pitch; Ben and Miguel supported the technical demo. As decided on 24/10, the demo ran on Miguel's
laptop: locally served app, local broker and local Valhalla. It was prepared on São Bento → Batalha with the
wheelchair profile (slopes up to 6 %): plan the route, switch the city's road works on and off and watch the route
and the operator panel change, then report a barrier from the app and see it reach the panel.

- Step-by-step setup and checks for the hour before: [`docs/demo-day-broker-checklist.md`](docs/demo-day-broker-checklist.md)
- What the broker does, in plain language for the slides: [`docs/broker-for-pitch.md`](docs/broker-for-pitch.md)
- Rehearsal of the panel moment, with recordings: [`docs/demo-rehearsal-2026-10-24.md`](docs/demo-rehearsal-2026-10-24.md)
- Every verified number (routes, timings, restarts): [`docs/runtime-baseline.md`](docs/runtime-baseline.md)

## 5. Maturity

Verified on 24/10 ([`docs/broker-for-pitch.md`](docs/broker-for-pitch.md) gives the source of each claim):

- **Live sharing:** a report made in one browser appears in another without a reload, and the route goes around it.
- **City data:** the broker polls the Porto Urban Platform every 10 minutes; 24 road works were kept near the demo
  route. São Bento → Batalha at 6 %: 2.164 km with them, 1.302 km without.
- **Feedback:** "Já não está" answers are stored and counted per barrier (a resent answer counts once).
- **Durability:** after a broker restart every report, answer, count and the city switch came back.
- **Operator panel:** `RotaLivreOps` in the HUB shows active barriers per source and the "gone" counts, live.
- **Honest routing:** our Valhalla enforces the slope cap uphill and downhill ("Core 2 verified" in
  [`docs/runtime-baseline.md`](docs/runtime-baseline.md)). When no route fits, the app says so, offers the gentlest
  one and marks where it is steeper than asked. Steps, surface and barriers are never relaxed.
- **Tests:** `pytest` for the Python cells (`services/tests/`) and the route checks (`runtime/demo/`), plus
  `broker/redeploy_lot.py --check` to compare the broker with git.

## Next phase: Coreflux mentoring and Hannover Messe

After the win, Rota Livre goes on to a further stage of the competition, with mentoring from Coreflux, competing for
a place at Hannover Messe. Dates, format and deliverables will be recorded here when the team receives them.

Where the hackathon version leaves off, from the notes in this folder:

- **Hosting.** Everything ran on one laptop. The public page reaches Valhalla and the broker through Cloudflare
  quick tunnels (`*.trycloudflare.com`), whose address changes whenever the tunnel container is recreated, and
  `app/config.js` must then be updated and pushed. A lasting deployment needs fixed hosts.
- **Broker restarts.** Every boot of broker 2.22.0 restores an older `ImportCityAlerts`;
  `python3 broker/redeploy_lot.py --fix` repairs it by hand ([`AGENTS.md`](AGENTS.md), boot-revert quirk).
- **Concurrent updates.** An Action's triggers run concurrently, so a read-change-publish counter can lose an update.
  The operator summary is protected with a lock in Python; `gone_count` is not ([`AGENTS.md`](AGENTS.md)).
- **City data.** These are road works on file at the Câmara, not checked on the street. They are polled, not pushed,
  and each one is a single square at the middle of its works area, so a long street is only partly covered.
- **Not shared yet.** A report's photo and address stay on the reporting device. Sharing them means adding optional
  `photo`/`address` fields to the contract, the database schema and the connector's query first.
- **Not built.** The LLM that turns free text or a photo into a report, weather effects and lift status. Kerb height
  cannot be filtered: Valhalla's pedestrian costing has no option for it.

---

## Repository layout

```text
scitech-2026/
├── README.md            # this file: product, architecture, topic map, setup
├── CLAUDE.md            # context for AI agents (imports AGENTS.md, the LoT rules)
├── AI.md                # AI tooling setup: MCP servers, Coreflux skills, token
├── LOT_CHEATSHEET.md    # LoT syntax reference
├── app/                 # web app: static page, deployed as a Cloudflare Worker
├── broker/              # Coreflux broker + HUB in Docker; redeploy_lot.py
├── lot/                 # LoT notebooks: the broker's logic (git is the source of truth)
├── db/                  # Supabase Postgres schema and its tests
├── runtime/             # slope-aware Valhalla (valhalla/) and demo tools (demo/)
├── services/tests/      # pytest for the notebooks' Python cells and the scripts
├── scripts/             # MCP token, Coreflux skills sync
├── docs/                # verified results, demo-day notes, pitch media, routing handoff
├── projects/            # source trees: Valhalla (with the slope-cap fix) and the OSM website
├── PLAN.md, PITCH.md    # event-day plan and pitch (historical)
└── regulamento.pdf      # official SciTeCh '26 rules (Portuguese)
```

SciTeCh '26 also had a Team Design challenge (25/10). That entry was removed from this repo; its last state is the
git tag `team-design-final`.

## How we work

- **Everything in English:** code, identifiers, file names, MQTT topics and payloads, comments and documentation.
  The app's interface is in European Portuguese by design.
- **Trunk-based git:** small, frequent commits straight to `main`; `git pull --rebase` before every push. Every push
  that touches `app/` redeploys the public page.
- **Never commit secrets** (Coreflux licence code, API keys, passwords): they live in `broker/.env`,
  `app/config.local.js` and the broker's secrets, all outside git.
- **Our own code:** SciTeCh solutions went through plagiarism detection; the Coreflux training labs are a syntax
  reference only (see [References](#references)).

## Environment setup (Linux / macOS)

Prerequisites: `git`, `python3`, **Docker** and **Docker Compose v2** (`docker --version`, `docker compose version`).
Every command below runs from the repo root unless it says otherwise.

```bash
git clone git@github.com:mmroch4/scitech-2026.git && cd scitech-2026
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # paho-mqtt, pytest
cd broker
cp .env.example .env          # optional: event licence code
chmod 777 exports             # the broker (uid 10001) writes the audit log here; git can't store this
docker compose up -d
```

| Service | Address | Credentials |
|---------|---------|-------------|
| Coreflux HUB | <http://localhost:3000> | pre-filled connection: host `broker`, port `1883`, `root` / `coreflux` |
| MQTT broker (from outside Docker) | `localhost:1883` | `root` / `coreflux` |
| MQTT over WebSocket (opt-in, `docker-compose.ws.yml`) | `ws://localhost:9001/mqtt` | a limited dashboard user, not root |
| MQTT over secure WebSocket on the internet (opt-in, `docker-compose.tunnel.yml`) | `wss://<random>.trycloudflare.com/mqtt` | `web`, limited to `access/barriers/#` |
| Mailpit (test email inbox) | <http://localhost:8025> | — |
| Broker health | <http://localhost:9100/health> | — |
| Broker MCP server (AI agents) | <http://localhost:6278/mcp> (`/health` without a token) | bearer token, see [`AI.md`](AI.md) |

- `docker compose down` stops and keeps the data; `docker compose down -v` **wipes everything, including the licence**.
- Durability is on (`COREFLUX_DURABILITY_*` in `docker-compose.yml`): retained messages (barriers, feedback, the city
  switch) survive a restart. The log lives on the `broker-data` volume, so `down -v` wipes it too.
- **After every broker restart**, repair the LoT the boot restores stale (see the boot-revert quirk in
  [`AGENTS.md`](AGENTS.md)), from the repo root with the broker login in `BROKER_USERNAME` / `BROKER_PASSWORD`:
  `docker restart o1n-broker && sleep 10 && python3 broker/redeploy_lot.py --fix`.
  `redeploy_lot.py --check` only reports (exit 1 on any mismatch, or when the operator summary `access/ops/summary`
  is more than 45 s old or missing). Reload app and HUB tabs opened during the restart.
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

### Web app over the internet (Cloudflare tunnel)

The hosted app is served over HTTPS, so it can only reach the broker through `wss://`. The opt-in tunnel container
gives the local broker a public `wss://` address. Do steps 1–3 once per broker (they survive restarts, not
`docker compose down -v`):

1. **Change the root password.** In the HUB Command Console run `-changeUserPassword root <new password>`. Once
   the tunnel is up, anyone on the internet can try `root` / `coreflux`.
2. **Create the page's user.** Run `-addUser web <password>`. This password ends up in `app/config.js`, which is
   public, so do not reuse it anywhere.
3. **Deploy the Rules** in [`lot/web_access.lotnb`](lot/web_access.lotnb), which keep `web` on `access/barriers/#`.
   Rules need the licence (see below). Use `/lot-deploy` or run the cells.
4. **Start the tunnel.** Run it from `broker`:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d
   docker compose -f docker-compose.yml -f docker-compose.tunnel.yml logs tunnel
   ```
   The log prints `https://<random>.trycloudflare.com`.
5. **Point the app at it.** In `app/config.js`, set `brokerUrl: "wss://<random>.trycloudflare.com/mqtt"`,
   `brokerUsername: "web"` and the password from step 2. Push to `main`: the page redeploys in about a minute.
6. **Check it.** Open the app: the barrier panel should say "Obstáculos atualizados em tempo real.". To check
   the user and the Rules without the browser, run this from the repo root (PowerShell: set the variables with
   `$env:BROKER_USERNAME="web"` and so on first):
   `BROKER_USERNAME=web BROKER_PASSWORD=<password> python runtime/demo/barriers.py seed`, then `list` and `clear`.

The address changes every time the tunnel container is recreated, for example by `docker compose down`. When it
does, repeat steps 4 and 5. `docker compose stop` / `start` and laptop restarts keep the same container, and with
it the same address. To close the broker to the internet again, run `docker compose -f docker-compose.yml -f docker-compose.tunnel.yml rm -sf tunnel`.

### Event licence

The organizers give us a **licence code** (`CFLX-...`). Without it, the broker runs as
**Community Edition**, which only allows **3 Connectors** and **no custom `DEFINE RULE`**.
With the licence we get more Connectors and can use Rules, which count as a
**maturity/security** argument in the pitch.

Activate it in one of two ways:
- put `COREFLUX_ACTIVATION_CODE=CFLX-...` in `broker/.env` (outside git) **before** the first `docker compose up`;
- HUB → `root` → Broker Settings → License, or `-activateLicense CFLX-...` in the Command Console.

Each activation uses up a *seat*, so avoid `docker compose down -v` after activating.
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
Layout: **one notebook per feature, one owner per notebook**, so two people never edit the same `.lotnb`
(they are JSON and merge badly).

### Useful tools

- **MQTT Explorer** or `mosquitto_sub -h localhost -u root -P coreflux -t '#' -v` to see every topic.
- **Python tests:** `.venv/bin/python -m pytest services/tests runtime/demo` (the virtual environment from
  the setup above).
- Broker variables and secrets: `-setEnv NAME=value`, `-setSecret NAME=value` (no spaces around the `=`),
  then `{env.NAME}` or `GET ENV "NAME"` / `GET SECRET "NAME"` in LoT.

## Documents

- [`AI.md`](AI.md): AI tooling setup (MCP servers, Coreflux skills, token) and the daily loop.
- [`AGENTS.md`](AGENTS.md): LoT rules for AI assistants (Claude Code reads it through `CLAUDE.md`).
- [`regulamento.pdf`](regulamento.pdf): the official SciTeCh '26 rules (Portuguese).
- [`LOT_CHEATSHEET.md`](LOT_CHEATSHEET.md): LoT syntax reference (Actions, Models, Connectors, Rules, Panels).
- [`app/README.md`](app/README.md): the web app's screens, routing calls, settings and deployment.
- [`db/README.md`](db/README.md): the Supabase schema, its tests and how the broker connects to it.
- [`runtime/valhalla/README.md`](runtime/valhalla/README.md): building and running the slope-aware Valhalla;
  [`runtime/demo/README.md`](runtime/demo/README.md): demo barriers and route checks.
- [`docs/`](docs/): verified results ([`runtime-baseline.md`](docs/runtime-baseline.md),
  [`integration-check-2026-10-24.md`](docs/integration-check-2026-10-24.md)), demo-day notes, pitch media and
  the [routing handoff](docs/accessibility_routing_project_handoff.md) of the Valhalla slope-cap work.
- [`PLAN.md`](PLAN.md) and [`PITCH.md`](PITCH.md): the event-day plan and pitch structure (historical).

## References

- Coreflux documentation: <https://docs.coreflux.org>
- Training repo (reference only, **do not copy**: there is plagiarism detection):
  <https://github.com/CorefluxCommunity/weather-station-hackathon>
