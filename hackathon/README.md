# Passo Livre — accessible routes in Porto

> **Status (24/10):** Valhalla-based web interface implemented; endpoint configuration and end-to-end
> accessibility validation remain to be verified. See [PLAN.md](PLAN.md) for owners, priorities and checkpoints.
> The write-up follows the 4 points the jury judges on (Rules, Art. 1, 3):
> **problem → demo → architecture → maturity**.

## 1. The problem

People with reduced mobility need routes that respect their accessibility needs and react to obstacles.

## 2. The solution

Passo Livre lets people choose accessibility limits, plan a route and report barriers that update other users'
maps and trigger route recalculation. The current implementation is in [app/](app/README.md).

## 3. Architecture

The static web app calls Valhalla for routes and slope details. Coreflux MQTT over WebSocket distributes retained
barrier reports. The checked-in routing source and [handoff](../accessibility_routing_project_handoff.md) support
validation of the custom slope cap; correct enforcement still needs runtime verification.

### MQTT topic map

| Topic | Producer | Consumer | Payload |
|-------|----------|----------|---------|
| `access/barriers/<id>` (retained) | web app | web app; future broker automation | `{id, kind, description, lat, lon, reported_at, expires_at}`; empty retained payload removes the barrier |

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
| Mailpit (test email inbox) | <http://localhost:8025> | — |
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
