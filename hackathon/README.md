# Hackathon — Coreflux solution

> **Status:** idea chosen (23/10): **LLM energy copilot for SMEs**. The structure follows the
> 4 points the jury judges on (Rules, Art. 1, 3): **problem → demo → architecture → maturity**.
> Anything marked ⚠️ **verify** must be confirmed in the first hour of the event.

**Product name:** **Vale** (Portuguese for "valley"): it finds the *valleys* in the electricity price curve and puts consumption there.
**One sentence:** For small businesses on an indexed tariff, who pay for electricity at a price that changes
every 15 minutes, **Vale** understands what each appliance needs to do (from a sentence in Portuguese),
schedules it for the cheapest quarter-hours and switches it on by itself, without ever putting operations at risk.

---

## 1. The problem

- **Who:** small businesses (restaurants, mini-markets, bakeries) on an **OMIE-indexed tariff**, with
  appliances whose consumption can move in time without hurting operations: cold rooms (thermal
  inertia), industrial dishwashers, water heaters and electric delivery vans.
- **The pain, in real numbers** (REN DataHub, day-ahead market price in Portugal):
  - **22/10/2026:** between **€0.28/MWh** and **€286.76/MWh** on the same day, about **1000×**. The hourly
    average was about €1/MWh at 12:00–15:00 and about €245/MWh at 18:00–19:00.
  - **The cheapest hour changes every day:** from 15 to 23/10 it was at 12:00, 13:00, 11:00, 11:00, **01:00**, 14:00, 14:00, 14:00.
    The intuition behind two-period tariffs ("off-peak is at night") no longer matches the market: with solar,
    the valley is often at midday, and the night can be among the most expensive hours.
- **How it is solved today:** it isn't, or with fixed timers. The owner is not going to check OMIE
  every day at 13:00 (when tomorrow's price comes out) to reprogram 4 appliances.
- **Why it is automation:** it needs to **integrate** prices with the appliances, **optimize** the schedule
  and **act** every 15 minutes, while respecting constraints such as food temperature or the van's departure time.
- **Honesty:** Vale only touches the **energy** component of the bill. Grid fees, contracted power and taxes do not change.
  The savings figures we present always refer to that component.

## 2. The solution

1. **Say what you need, in plain language:** *"The van arrives at 9:00 and must leave at 17:00 with 30 kWh; cold room 1
   must stay between 0 and 5 °C."* An LLM turns this into a **structured task**, which is validated
   (Model `Task`) and shown to the owner to confirm.
2. **Vale fetches** today's and tomorrow's **prices** from REN (every day after 13:00) and **schedules** each task
   in the cheapest quarter-hours within the constraints.
3. **Advise or act:** each appliance is in `advise` mode ("run the machine at 14:15, saves €1.80")
   or `auto` mode (Vale switches the appliance on and off by itself).
4. **Never puts operations at risk:** the *guardrails* in the broker override the plan (e.g. the cold room
   above 5 °C turns on **now**, whatever the price) and notify the owner by email.
5. **Shows what it saved:** a counter of € saved versus "turn it on right away", and an audit log (CSV) with each decision and its reason.

## 3. Architecture

```text
 [sources]                        [Coreflux Broker: the logic lives here]              [outputs]

 REN DataHub ◄──REST_API──── Connector RenPrices ──► Action ParsePrices ──────┐
 (15-min prices)                                     (CALL PYTHON PriceTools) │
                                                                              ▼
 dashboard ──"free text"────► Action ParseIntent ──► Model Task ──► Action PlanTask ──► copilot/plans/<id>
                              (CALL LLM Assistant)    (validation)  (CALL PYTHON Planner)        │
                                                                                                 ▼
 Action SimClock ──copilot/clock/slot──► Action Dispatch ─────► auto mode:   .../command ──► appliances
 (1 s = 15 min in the demo)             (plan + mode)   └─────► advise mode: copilot/advice ──► dashboard
                                                                                 │
 appliances ──telemetry──► Action Guard (guardrails, alert 1×/episode) ──────────┼──► Connector Mailer (email)
 (Python simulator)        Action Meter (real cost vs. naive)                    └──► Connector DecisionLog (CSV)
                                                                                      web dashboard + HUB Panel
                           Rules: only broker Actions may publish commands to the appliances
```

**Split of responsibilities:**
- **Broker (LoT):** price ingestion, clock, state, dispatch, *guardrails*, accounting, alerts,
  auditing and security.
- **Python inside the broker (`CALL PYTHON`):** what LoT does not do well, such as sorting 96 prices and picking the
  N cheapest quarter-hours before a deadline. The functions are **pure and stateless** (target: under 100 ms) and testable with `pytest` outside the broker.
- **LLM inside the broker (`CALL LLM`, `PROVIDER "anthropic"`):** only translates text into JSON. It **never decides**
  anything on its own: the task is validated by the Model and the plan is deterministic.
- **Outside the broker:** only the **appliance simulator** (in the real world these would be relays/PLCs) and the **dashboard**.

⚠️ **Verify:** according to the docs, the `TYPE LLM` Connector needs a **Growth/Enterprise** licence. If the
event licence does not include it, plan B is `services/intent_parser.py` (Claude API via the `anthropic` SDK), which reads
`copilot/assistant/request` and publishes to `copilot/tasks/new`, with the same topic contract.

### MQTT topic map

The contract between every part of the system. **Always update it when you create a topic.**
`<id>` ∈ `cold_room_1`, `dishwasher_1`, `van_1` (the demo appliances).

| Topic | Published by | Read by | Payload | Retained |
|-------|--------------|---------|---------|:--------:|
| `copilot/market/request` | Action `FetchPrices` (daily at 13:30 and on startup) | Connector `RenPrices` | `{"date":"2026-10-24"}` | |
| `copilot/market/raw` | Connector `RenPrices` | Action `ParsePrices` | REN JSON (`series[].data`) | |
| `copilot/market/prices` | Action `ParsePrices` | `PlanTask`, `Dispatch`, `Meter`, dashboard | `{"date","unit":"EUR/MWh","step_min":15,"prices":[96 values]}` | ✅ |
| `config/clock/mode` | setup / dashboard | `SimClock` | `sim` \| `real` | ✅ |
| `copilot/clock/slot` | Action `SimClock` | `Dispatch`, `Meter`, dashboard | `0`–`95` (current quarter-hour) | ✅ |
| `config/devices/<id>` | `00-setup` | `PlanTask`, dashboard | Model `Device`: `type` (`thermal`\|`block`\|`energy`), `power_kw`, limits | ✅ |
| `config/devices/<id>/mode` | dashboard (owner) | `Dispatch` | `advise` \| `auto` | ✅ |
| `copilot/assistant/request` | dashboard | Action `ParseIntent` | `{"text":"..."}` | |
| `copilot/tasks/new` | `ParseIntent` or form (plan B) | Action `PlanTask` | Model `Task`: `device_id`, `kind`, `energy_kwh`, `duration_slots`, `earliest_slot`, `deadline_slot` | |
| `copilot/assistant/errors` | `ParseIntent` | dashboard | validation error text | |
| `copilot/plans/<id>` | Action `PlanTask` | `Dispatch`, dashboard | `{"slots":[...],"cost_eur","naive_cost_eur","savings_eur","reason"}` | ✅ |
| `copilot/devices/<id>/command` | `Dispatch` (`auto` mode), `Guard` | simulator / relay | `on` \| `off` | ✅ |
| `copilot/advice/<id>` | `Dispatch` (`advise` mode) | dashboard | `"Turn on at 14:15 (saves €1.80)"` | |
| `copilot/devices/<id>/telemetry` | simulator (`services/device_sim.py`) | `Guard`, `Meter`, dashboard | `{"on":true,"power_kw":3.0,"temp_c":3.4}` | |
| `copilot/alerts/guardrail` | Action `Guard` (on transition only) | Connector `Mailer`, dashboard | Model `Alert` | |
| `copilot/alerts/guardrail/<id>/active` | Action `Guard` | Action `Guard` | `on` \| `off` | ✅ |
| `copilot/audit/decisions` | `Dispatch`, `Guard` | Connector `DecisionLog` (CSV) | Model `Decision`: `slot`, `device_id`, `action`, `price`, `reason` | |
| `copilot/kpi/savings` | Action `Meter` | dashboard, Panel | `{"cost_eur","naive_cost_eur","saved_eur"}` | ✅ |
| `copilot/errors` | any Action | dashboard | text | |

Conventions: topics in English, lowercase, `snake_case`, hierarchy `<domain>/<entity>/<measure>`;
configuration under `config/...` (retained); errors under `.../errors`.

### Components

| Component | Where | Technology |
|-----------|-------|------------|
| Automation logic | `lot/` | LoT: Actions, Models, Connectors (`REST_API`, `LLM`, `EMAIL`, `FILE_STORAGE`), Rules, Panel |
| Optimizer and price parsing | `lot/` (`CALL PYTHON` scripts) + tests in `services/tests/` | Python (standard library only) |
| Appliance simulator | `services/device_sim.py` | Python + `paho-mqtt` (simple thermal model of the cold room) |
| Dashboard | `dashboard/` | Our own web app (HTML + MQTT over WebSocket + price chart with the plan overlaid); HUB Panel as the technical view and plan B |
| Infrastructure | `broker/` | Docker Compose: Coreflux Broker 2.22, HUB 2.12, Mailpit |

⚠️ **Verify:** the broker's WebSocket port for the dashboard. If there isn't one, the alternative is a minimal MQTT → SSE *bridge* in Python.

## 4. Demo

Full script and plan B in [`PITCH.md`](PITCH.md#demo-script-140). Summary:
1. The chart of **today's real prices** (REN) shows the midday valley.
2. The owner types a sentence, the LLM turns it into tasks (the JSON appears on screen) and the plans appear over the chart, with the expected savings.
3. **▶ Simulate the day** (1 s = 15 min): the appliances switch on by themselves in the valleys and the € counter goes up.
4. **The cold room door is opened:** the temperature goes above 5 °C, the *guardrail* turns the cold room on even at a high price, an
   email arrives in Mailpit and a line appears in the audit CSV.

## 5. Maturity and next steps

- **End to end and real:** prices (REN public API, no key), the LLM, scheduling, dispatch, *guardrails*, emails
  and auditing all run in the broker.
- **Simulated:** the appliances (Python simulator with a thermal model) and the accelerated clock. Connecting to real
  hardware means swapping the simulator for a relay/PLC subscribing to the **same** `.../command` topic.
- **Reliability:**
  - prices are retained and cached: with no internet, Vale uses the last known plan;
  - with no prices at all, it falls back to a safe mode (the appliance's normal behaviour);
  - the LLM never acts directly;
  - the *guardrails* take priority over the plan;
  - the alert is sent only once per episode.
- **Security (Rules):**
  - only broker Actions publish to `copilot/devices/+/command`;
  - the dashboard user can only publish requests and change the mode;
  - each appliance only publishes its own telemetry.
- **Tests:** the optimizer has `pytest` tests, including edge cases: an impossible deadline, missing prices and the **100**-quarter-hour day
  at the clock change (25/10!).
- **Scale:** appliances are configuration (`config/devices/<id>`), and a new type is a new strategy in the planner.
  For multiple shops, one broker per shop, linked to a central broker.
- **Business model:** a subscription per establishment. Vale starts with a **bill simulator** ("on the indexed tariff,
  with your appliances, you would save X €/month"), which is also the sales tool.
- **With more time:**
  - a residential profile (the same engine for a family with an electric car);
  - price forecasting before 13:00;
  - optimizing **contracted power** and solar self-consumption;
  - Modbus integration with the refrigeration controllers.

---

## Environment setup (Linux / macOS)

Prerequisites: **Docker** and **Docker Compose v2** (`docker --version`, `docker compose version`).

```bash
cd hackathon/broker
cp .env.example .env          # optional: event licence code
docker compose up -d
```

| Service | Address | Credentials |
|---------|---------|-------------|
| Coreflux HUB | <http://localhost:3000> | pre-filled connection: host `broker`, port `1883`, `root` / `coreflux` |
| MQTT broker (from outside Docker) | `localhost:1883` | `root` / `coreflux` |
| Mailpit (test email inbox) | <http://localhost:8025> | — |
| Broker health | <http://localhost:9100/health> | — |

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

The **source of truth is git**: the `.lotnb` files in `lot/`.

1. Install the **LoT Notebooks** VS Code extension
   ([VSCodeLotNotebook](https://github.com/CorefluxCommunity/VSCodeLotNotebook/releases/tag/v1.0.0), `.vsix` file):
   `code --install-extension vscode-lot-notebooks-1.0.0.vsix`
2. Open a `.lotnb` from `lot/` and connect to `localhost:1883` (`root` / `coreflux`).
3. Run the cells (▷) to deploy to the local broker; commit the `.lotnb` files.

If someone edits directly in the HUB, they must copy the final code into the matching `.lotnb` before committing.
Suggested layout, one notebook per responsibility:
`lot/00-setup.lotnb` (variables, secrets, retained config), `lot/10-models.lotnb`, `lot/20-actions.lotnb`,
`lot/30-connectors.lotnb`, `lot/40-rules.lotnb`, `lot/50-panel.lotnb`.

### Useful tools

- **MQTT Explorer** or `mosquitto_sub -h localhost -u root -P coreflux -t '#' -v` to see every topic.
- **Python:** `pip install paho-mqtt` for services and simulators in `services/`.
- Broker variables and secrets: `-setEnv NAME=value`, `-setSecret NAME=value` (no spaces around the `=`),
  then `{env.NAME}` or `GET ENV "NAME"` / `GET SECRET "NAME"` in LoT.

## Documents in this folder

- [`LOT_CHEATSHEET.md`](LOT_CHEATSHEET.md): LoT syntax reference (Actions, Models, Connectors, Rules, Panels).
- [`PITCH.md`](PITCH.md): presentation structure and demo checklist.

## References

- Coreflux documentation: <https://docs.coreflux.org>
- Training repo (reference only, **do not copy**: there is plagiarism detection):
  <https://github.com/CorefluxCommunity/weather-station-hackathon>
