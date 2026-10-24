# Rota Livre — accessible routes in Porto

> **Status (24/10):** Valhalla-based web interface implemented; endpoint configuration and end-to-end
> accessibility validation remain to be verified. See [PLAN.md](PLAN.md) for owners, priorities and checkpoints.
> The write-up follows the 4 points the jury judges on (Rules, Art. 1, 3):
> **problem → demo → architecture → maturity**.

## 1. The problem

People with reduced mobility need routes that respect their accessibility needs and react to obstacles.

## 2. The solution

Rota Livre lets people choose accessibility limits, plan a route and report barriers that update other users'
maps and trigger route recalculation. The current implementation is in [app/](app/README.md).

## 3. Architecture

The static web app calls Valhalla for routes and slope details. Coreflux MQTT over WebSocket distributes retained
barrier reports. The checked-in routing source and [handoff](../accessibility_routing_project_handoff.md) support
validation of the custom slope cap; correct enforcement still needs runtime verification.

### MQTT topic map

| Topic | Producer | Consumer | Payload |
|-------|----------|----------|---------|
| `access/barriers/<id>` (retained) | web app; broker: `ImportCityAlerts` (`city-*` ids) | web app; broker: `RouteBarrierMessage` (app ids → Supabase) | `{id, kind, description, lat, lon, reported_at, expires_at}`, city ones add `source: "cm-porto"`; empty retained payload removes the barrier (only clients can send it: the broker retires a barrier by republishing it with `expires_at` = now) |
| `access/barriers/<barrier id>/feedback` (not retained) | web app ("Já não está") | broker: `StoreBarrierFeedback` (`lot/barrier_feedback.lotnb`); connector `BarriersDB` → Supabase `barrier_feedback` | `{id, barrier_id, answer: "gone", answered_at, lat?, lon?}`; does not remove the barrier |
| `access/feedback/<barrier id>/answers/<feedback id>` (retained) | broker: `StoreBarrierFeedback` | team, end-of-day review | the feedback payload, unchanged; one per distinct `id` (resends count once) |
| `access/feedback/<barrier id>/gone_count` (retained) | broker: `StoreBarrierFeedback` | team, end-of-day review | number of distinct "gone" answers for that barrier |
| `access/feedback/<barrier id>/last_answered_at` (retained) | broker: `StoreBarrierFeedback` | team, end-of-day review | `answered_at` of the latest stored answer (ISO 8601) |
| `access/db/barriers/upsert` (internal) | broker Action `RouteBarrierMessage` | connector `BarriersDB` → Supabase `barriers` | the report's JSON, unchanged |
| `access/db/barriers/deleted` (internal) | broker Action `RouteBarrierMessage` | connector `BarriersDB` → sets `deleted_at` | the barrier id (checked: `b` + letters/digits) |
| `access/city/alerts/fetch` (not retained) | anyone (manual refresh); broker: `SwitchCityAlerts` on `on` | broker: `PortoUrbanPlatform` connector | any payload; the connector also fetches every 10 min |
| `access/city/alerts/raw` (not retained) | broker: `PortoUrbanPlatform` | broker: `ImportCityAlerts` | FIWARE NGSI v2 `Alert` entities (keyValues), or `{"success": false, ...}` on an HTTP error |
| `access/city/alerts/last_ok`, `.../last_error` (retained) | broker: `ImportCityAlerts` | team, demo checks | ISO time of the latest successful import / failed fetch |
| `access/city/alerts/enabled` (retained, QoS 1) | team (demo switch) | broker: `SwitchCityAlerts`, `ImportCityAlerts` | `on` or `off`. `off` retires every imported `city-*` barrier (`expires_at` = now) and makes the import ignore fetches; `on` fetches at once and republishes them. Missing = `on` |
| `access/state/city_alerts` (internal, retained, QoS 1) | broker: `ImportCityAlerts`, `SwitchCityAlerts` | broker: the same two Actions | `{<barrier id>: barrier}` of the `city-*` barriers imported last time (`{}` after `off`); what `off` retires and what the next import compares against. Retained so it survives a restart with the barriers |

## 4. Demo

Plan a route under the chosen accessibility limits, report an obstacle from a second session, and show the route
recalculate around it. Current-position rerouting and explanation of changes are planned next; demonstrate only
verified behavior. Victor owns the script, slides, recording and rehearsals with technical support from Ben and Miguel.

## 5. Maturity and next steps

Validate uphill/downhill slope limits and missing-elevation behavior, verify the deployed endpoints, and make the
demo repeatable. Prioritize the core route/report/reroute flow; LLM analysis and lift simulation are stretch work.
The app already exposes a no-route message without silently relaxing the user's settings.

---

## Environment setup (Linux / macOS)

Prerequisites: **Docker** and **Docker Compose v2** (`docker --version`, `docker compose version`).

```bash
cd hackathon/broker
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
4. **Start the tunnel.** Run it from `hackathon/broker`:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d
   docker compose -f docker-compose.yml -f docker-compose.tunnel.yml logs tunnel
   ```
   The log prints `https://<random>.trycloudflare.com`.
5. **Point the app at it.** In `app/config.js`, set `brokerUrl: "wss://<random>.trycloudflare.com/mqtt"`,
   `brokerUsername: "web"` and the password from step 2. Push to `main`: the page redeploys in about a minute.
6. **Check it.** Open the app: the barrier panel should say "Obstáculos atualizados em tempo real.". To check
   the user and the Rules without the browser, run this from `hackathon/` (PowerShell: set the variables with
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
- **Python:** `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (paho-mqtt, pytest)
  for services, simulators and tests in `services/`.
- Broker variables and secrets: `-setEnv NAME=value`, `-setSecret NAME=value` (no spaces around the `=`),
  then `{env.NAME}` or `GET ENV "NAME"` / `GET SECRET "NAME"` in LoT.

## Documents in this folder

- [`AI.md`](AI.md): AI tooling setup (MCP servers, Coreflux skills, token) and the daily loop.
- [`AGENTS.md`](AGENTS.md): LoT rules for AI assistants (Claude Code reads it through `CLAUDE.md`).
- [`LOT_CHEATSHEET.md`](LOT_CHEATSHEET.md): LoT syntax reference (Actions, Models, Connectors, Rules, Panels).
- [`PITCH.md`](PITCH.md): presentation structure and demo checklist.

## References

- Coreflux documentation: <https://docs.coreflux.org>
- Training repo (reference only, **do not copy**: there is plagiarism detection):
  <https://github.com/CorefluxCommunity/weather-station-hackathon>
