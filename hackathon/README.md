# Hackathon — Coreflux solution

> **Status:** idea changed on 23/10 (evening) from *Vale* (energy copilot, see git history up to `8245603`) to
> **Rua Viva**. The structure follows the 4 points the jury judges on (Rules, Art. 1, 3):
> **problem → demo → architecture → maturity**. Anything marked ⚠️ **verify** must be confirmed in the first hour.

**Product name:** **Rua Viva** (Portuguese for "living street"): a street whose problems are seen, planned and fixed.
**One sentence:** *Rua Viva turns reports about public space into maintenance plans. It organizes reports, finds
likely duplicates and helps the municipality decide what each crew can fix today with the resources it has.*

---

## 1. The problem

- **Who:** the municipal maintenance manager (and the crews) who receive citizen reports about broken benches,
  dark streetlights and loose paving stones, plus the citizens who report them and never hear back.
- **The pain:**
  - The same problem arrives many times, through different channels, with different words. Five reports of one
    broken bench become five tickets, and someone has to merge them by hand.
  - A report is not a job. Someone still has to work out where it is, what it is, who is responsible, how urgent it is,
    how long it takes and what material it needs.
  - The daily crew plan is built by hand, from what the manager remembers. When a part is missing or a crew is short,
    the plan breaks and is rebuilt by phone.
  - The citizen who reported it is rarely told it was fixed.
  - `[TODO Victor: one verified number, e.g. yearly reports in a Portuguese municipal app such as "Na Minha Rua LX", with source]`
- **Why it is automation:** it **integrates** reports from several channels, **organizes** them (dedup, triage),
  **optimizes** the use of crews and materials and **reacts** to events in the field, with a human approving each step
  that has consequences.

## 2. The solution

The path of one problem through Rua Viva:

1. **Report.** A citizen takes a photo, **confirms the location** on a map (a photo alone does not say where it was
   taken) and adds a short description: *"O banco junto ao parque infantil tem uma tábua partida e um parafuso exposto."*
   Rua Viva suggests the category and writes a structured description. If essential information is missing, it asks one
   concrete question: *"Which of the two playgrounds on this street?"*
   Devices are a second channel: a smart streetlight controller that reports a lamp failure enters the same pipeline.
2. **Already reported?** Rua Viva compares the report with open issues by **distance, category, asset and text**
   (and photo, with the LLM, when available). A likely match is attached to the existing issue; ambiguous cases go to the
   manager. Five people follow **one intervention**, and the five reports stay as evidence. A problem that comes back
   after being fixed is flagged as a possible **recurrence**.
3. **Ready for analysis.** Each issue has a card: photos, location, description, category, linked reports, history and
   status. Rua Viva suggests the responsible crew from configured rules (or says it is **outside municipal competence**)
   and a priority from explicit criteria (risk, sensitive area, impact on use, waiting time), always with the reason:
   *"Priority review suggested: a sharp element was reported next to a children's play area."*
   The number of reports is one extra signal, never the only one. The manager approves.
4. **Daily plan (the core).** The manager states the resources of the day: crews, shifts, skills, materials, vehicles.
   Rua Viva proposes who does what, in which order, with duration, materials and route, and explains **why each job was
   included or left pending**: *"Not scheduled: needs an LED lamp and there is none in stock."* The manager edits and
   approves the plan.
5. **Field work.** On a phone, each technician sees their jobs (location, photos, instructions) and marks them
   **started**, **done**, **blocked** (with the reason) or **needs another crew/material**. When a job overruns or a
   part is missing, Rua Viva **recomputes the rest of the plan and explains the changes**; the manager approves them.
6. **Close and inform.** The technician adds an after photo and a note. Rua Viva checks that everything needed to close
   is there (a photo does not prove the repair is safe, so a human approves the closure). Then **every citizen linked to
   the issue** gets an update, and the history stays with the asset for future interventions.

**Where the automation is, and who decides:**

| Moment | Automated | Decided by |
|--------|-----------|------------|
| Intake | Extract information and suggest the category from text (and image) | the citizen confirms location |
| Organization | Find likely duplicates, recurrences, ask for missing information | the manager, in ambiguous cases |
| Triage | Suggest the responsible crew and the priority, with a reason | the manager approves |
| Planning | Assign jobs by skills, shifts, materials, location and duration | the manager approves the plan |
| Execution | Propose plan changes when something blocks a job | the manager approves the changes |
| Communication | Prepare and send updates from approved state changes | automatic after approval |

The **LLM only interprets unstructured input** (text, photo). Skills, shifts and materials are handled by **rules and
planning logic**, which are deterministic and testable.

**Prototype scope:** one neighbourhood (Lordelo do Ouro, Porto: real map, **fictional assets and reports, labelled as
such**), three categories, two crews, three interfaces (citizen form, manager dashboard, technician job list).

| Category | Example job types | Crew |
|----------|-------------------|------|
| `street_furniture` | `bench_repair` (45 min, 1 plank + 1 bolt kit), `fence_inspection` (20 min) | `furniture_crew` (2 technicians, van) |
| `pavement` | `paving_repair` (60 min, 20 paving stones + sand) | `furniture_crew` |
| `lighting` | `lamp_replacement` (40 min, 1 LED lamp, bucket truck) | `lighting_crew` (2 electricians, bucket truck) |

## 3. Architecture

```text
 [channels]                         [Coreflux Broker: the logic lives here]                     [outputs]

 citizen form ──reports/new──► AnalyzeReport ──analysis──► MatchReport ───────► ruaviva/issues/events
 (photo + pin + text)          (CALL LLM; plan B           (CALL PYTHON           (created, report_attached)
                                service; keyword            Matcher: dedup,       or review/... → manager
 streetlight controller         fallback offline)           recurrence, asset     or question  → citizen
 (simulator) ──status──► SensorIntake ──reports/new──►       question)                  │
                                                                                         ▼
 manager ──issues/decisions──► HandleDecision ──events──► ApplyIssueEvent ──► ruaviva/state/issues (every card)
                                                         (CALL PYTHON IssueTools:  ruaviva/kpi ──► dashboard
                                                          fold, triage, KPIs)      AuditLog (JSON file)
                                                                 │                 Notify ──► Mailer ──► citizens
                                                                 ▼                 (on closed / out of scope)
 manager ──plan/request, resources/events──► UpdateResources ──► ruaviva/state/resources
                                             BuildPlan (CALL PYTHON Planner) ──► plans/<date>/proposed ──► manager
                                             ApprovePlan ──► plans/<date>/approved ──► technician list
 technician ──jobs/<id>/status──► HandleJobStatus ──► issue events + resource events + replan request

                Rules: each role (citizen, technician, manager) publishes only its own topics;
                only broker Actions write issue state, resources and approved plans
```

**Split of responsibilities:**
- **Broker (LoT):** the whole event pipeline: intake, matching, issue state, triage, planning requests, approvals,
  field updates, notifications, audit and security.
- **Python inside the broker (`CALL PYTHON`):** what LoT does badly. **`Matcher`** (distance, category, asset and
  text similarity, recurrence, the "which playground?" question), **`IssueTools`** (folds an event into the issue card,
  triage with reasons, KPIs, close check) and **`Planner`** (assignment and routing with explanations, plan diff on
  replan). All functions are **pure and stateless**, return `json.dumps(...)` and have `pytest` tests outside the broker.
- **LLM (`CALL LLM`, `PROVIDER "anthropic"`):** only turns text (and a photo) into a structured analysis. It never
  decides: the matcher, triage and planner are deterministic and the manager approves.
- **Outside the broker:** the three web interfaces and the streetlight simulator (in the real world, a lighting
  management system or the municipality's existing reporting app).

**LLM licence:** the Community broker refuses `TYPE LLM` (verified 23/10). If the event licence does not unlock it,
plan B is `services/report_analyzer.py` (Claude API via the `anthropic` SDK, can also read the photo), which reads
`ruaviva/reports/new` and publishes `ruaviva/reports/<id>/analysis` with the same contract. With no internet at all, a
keyword classifier (`Matcher.classify`) gives a lower-quality analysis so the demo never stops.

**Photos:** the browser downscales to ≤ 800 px JPEG (≤ 150 KB) and publishes it once, retained, on
`ruaviva/photos/<photo_id>`. Every other message refers to the `photo_id`. The demo photos are fixtures.

### MQTT topic map

The contract between every part of the system, **drafted on 23/10 for Rua Viva: review it together at kickoff, then
freeze it**. Every row has an example message in [`fixtures/messages/`](fixtures/messages/), and
`scripts/replay.py` publishes them, so each track can be built before its producer exists. **Change a row only with
the whole team, and update its fixture in the same commit.**

| Topic | Published by | Read by | Payload | Retained |
|-------|--------------|---------|---------|:--------:|
| `config/categories` | setup | `IssueTools`, `Matcher`, dashboard | `{categories: {<category>: {name, crew_id, job_types, keywords, hazard_words}}, out_of_scope: [{keywords, entity}], sensitive_tags, priority_weights, priority_thresholds}` | ✅ |
| `config/job_types` | setup | `Planner`, dashboard | `{<job_type>: {category, name, duration_min, skills, materials: {item: qty}, vehicle, instructions}}` | ✅ |
| `config/assets` | setup | `Matcher`, `IssueTools`, dashboard | `[{asset_id, type, name, lat, lon, tags}]` (tags: `playground`, `school`, `crossing`) | ✅ |
| `ruaviva/photos/<photo_id>` | citizen form, technician | dashboard, plan B analyzer | `data:image/jpeg;base64,...` | ✅ |
| `ruaviva/reports/new` | citizen form, `SensorIntake` | `AnalyzeReport` | Model `Report`: `report_id`, `channel` (`citizen`\|`sensor`), `submitted_at`, `text`, `photo_id`, `lat`, `lon`, `location_confirmed`, `contact` | |
| `ruaviva/reports/<report_id>/analysis` | `AnalyzeReport` (LLM / plan B / keywords) | `MatchReport`, citizen form | `{report_id, source, category, job_type, asset_type, summary, hazards: [...], confidence}` | |
| `ruaviva/reports/<report_id>/question` | `MatchReport` | citizen form | `{report_id, question, options: [{asset_id, label}]}` | |
| `ruaviva/reports/<report_id>/answer` | citizen form | `MatchReport` | `{report_id, asset_id}` | |
| `ruaviva/reports/<report_id>/match` | `MatchReport` | citizen form, dashboard | `{report_id, decision` (`new`\|`attach`\|`review`\|`recurrence`\|`needs_info`), `issue_id, asset_id, candidates: [{issue_id, score, distance_m, why}]}` | |
| `ruaviva/review/duplicates/<report_id>` | `MatchReport` | dashboard (manager) | `{report_id, analysis, candidates}`; cleared after the decision | ✅ |
| `ruaviva/review/duplicates/<report_id>/decision` | dashboard (manager) | `MatchReport` | `{issue_id}` to attach, or `{issue_id: null}` for a new issue | |
| `ruaviva/issues/events` | `MatchReport`, `HandleDecision`, `HandleJobStatus`, `ApprovePlan` | `ApplyIssueEvent` | `{issue_id` (or `issue_ids` for plan events), `type, at, by, data}`, `type` ∈ `created`, `report_attached`, `approved`, `rejected`, `out_of_scope`, `scheduled`, `unscheduled`, `started`, `blocked`, `work_done`, `closed`, `reopened` | |
| `ruaviva/issues/decisions` | dashboard (manager) | `HandleDecision` | `{issue_id, decision` (`approve`\|`reject`\|`close`\|`reopen`), `by, note, priority?, crew_id?}` | |
| `ruaviva/state/issues` | `ApplyIssueEvent` | `BuildPlan`, `MatchReport`, dashboard, technician | `{<issue_id>: Issue}`: **the** issue store, rebuilt by folding every event | ✅ |
| `ruaviva/kpi` | `ApplyIssueEvent` | dashboard | `{new_to_review, possible_duplicates, approved_unscheduled, in_progress, blocked, closed_today, reports_merged, avg_triage_min, avg_resolution_h, block_reasons: {...}}` | ✅ |
| `ruaviva/resources/events` | dashboard (manager), `HandleJobStatus` | `UpdateResources` | `{type` (`crew_available`\|`member_absent`\|`stock_set`\|`stock_used`), `crew_id, data, at, by}` | |
| `ruaviva/state/resources` | `UpdateResources` | `BuildPlan`, dashboard | `{date, depot: {name, lat, lon}, crews: {<crew_id>: {name, members, skills, shift: ["08:00","16:00"], vehicle, available, stock: {item: qty}}}}` | ✅ |
| `ruaviva/plan/request` | dashboard (manager), `UpdateResources`, `HandleJobStatus` | `BuildPlan` | `{date, now: "HH:MM", trigger` (`daily`\|`replan`), `reason}` | |
| `ruaviva/plans/<date>/proposed` | `BuildPlan` | dashboard (manager) | Plan (see below) with `status: "proposed"` and `changes` vs. the approved version | ✅ |
| `ruaviva/plans/<date>/decision` | dashboard (manager) | `ApprovePlan` | `{version, decision` (`approve`\|`discard`), `by, edits?: [{issue_id, crew_id?, drop?}]}` | |
| `ruaviva/plans/<date>/approved` | `ApprovePlan` | `HandleJobStatus`, dashboard, technician list (filters its crew) | Plan with `status: "approved"` | ✅ |
| `ruaviva/jobs/<job_id>/status` | technician list | `HandleJobStatus` | `{status` (`started`\|`done`\|`blocked`\|`needs`), `at, by, reason?, need?: {material?, qty?, crew?}, note?, photo_id?}` | |
| `ruaviva/devices/<device_id>/status` | streetlight simulator | `SensorIntake` | `{device_id, asset_id, lamp_ok, fault?, at}` | ✅ |
| `ruaviva/notifications/email` | `Notify` | Connector `Mailer` | `{to, subject, body, issue_id}` (one message per recipient) | |
| `ruaviva/audit/events` | `ApplyIssueEvent`, `ApprovePlan` | Connector `AuditLog` (JSON file) | `{at, issue_id?, type, by, data}` | |
| `ruaviva/errors` | any Action | dashboard | text | |

**Model `Issue`:** `issue_id`, `title`, `summary`, `category`, `job_type`, `asset_id`, `lat`, `lon`, `photo_ids`,
`report_ids`, `reporters` (contacts, never shown to crews), `status` (`new` → `approved` → `scheduled` →
`in_progress` ⇄ `blocked` → `awaiting_close` → `closed`; or `rejected`, `out_of_scope`), `priority` (`high`\|`normal`\|`low`),
`priority_score` (0–100), `priority_reasons` (list of text), `priority_summary` (one sentence), `crew_id`, `out_of_scope_entity`, `recurrence_of`,
`created_at`, `triaged_at`, `closed_at`, `history` (`[{at, type, by, text}]`).

**Plan:** `{date, version, now, generated_at, status, crews: [{crew_id, shift, capacity_min, load_min, jobs: [Job]}],
unscheduled: [{issue_id, reason}], changes: [{issue_id, change` (`added`\|`dropped`\|`moved`\|`reassigned`),
`explanation}], assumptions: [...]}`. **Job:** `{job_id, issue_id, job_type, title, lat, lon, start, end,
duration_min, travel_min, materials, instructions, photo_ids, why}` (no citizen contacts: crews never see them).

Rules of the contract:
- `job_id` = `<date>-<issue_id>`, so a job keeps its id across replans.
- One store per kind (`ruaviva/state/issues`, `ruaviva/state/resources`, one plan per date), each with **a single writer
  Action**. LoT has no easy loop over JSON lists, so we publish whole documents instead of one topic per item.
- The planner never schedules a job whose skills, materials or vehicle the crew does not have, and always says why.
  Travel = straight-line distance × 1.3 at 20 km/h + 5 min to park (a visible assumption, listed in `assumptions`).
- A replan only moves jobs that are not `started` or `done`, and starts from `now`.
- The LLM only *proposes* (`analysis`); the matcher, triage and planner are deterministic; plans and closures need the
  manager's approval.
- Topics in English, lowercase, `snake_case`, under `ruaviva/` or `config/` (retained); errors on `ruaviva/errors`.

### Components

| Component | Where | Technology |
|-----------|-------|------------|
| Automation logic | `lot/` | LoT: Actions, Models, Connectors (`EMAIL`, `FILE_STORAGE`; `LLM` if the licence allows), Rules |
| Matcher, IssueTools, Planner | `lot/` (`CALL PYTHON` scripts) + tests in `services/tests/` | Python (standard library only) |
| Report analyzer, plan B | `services/report_analyzer.py` | Python + `paho-mqtt` + `anthropic` (only if the LLM connector is not licensed) |
| Streetlight simulator | `services/streetlight_sim.py` | Python + `paho-mqtt` |
| Three interfaces | `report-site/` (citizen form, started by Ben on 23/10), `dashboard/` (`manager.html`, `technician.html`) | Plain HTML + JS, MQTT over WebSocket (`mqtt.js`), Leaflet map; no build step |
| Infrastructure | `broker/` | Docker Compose: Coreflux Broker 2.22, HUB 2.12, Mailpit |

WebSocket: verified on 23/10. The broker serves MQTT over WebSocket on container port 5000, path `/mqtt`; it is **opt-in** via `broker/docker-compose.ws.yml` → `ws://localhost:9001/mqtt`. Read that file's warning first: any web page on the laptop can reach a localhost WebSocket, so change the root password (or use limited users per role) before enabling it.

## 4. Demo

Full script and plan B in [`PITCH.md`](PITCH.md#demo-script-140). Summary:
1. A citizen reports the broken bench on the phone view: the category, the hazard and a **high priority with its
   reason** appear.
2. More reports arrive (and a streetlight controller reports a dead lamp): Rua Viva attaches the duplicates, sends one
   ambiguous case to the manager and asks a citizen "which playground?". **Many reports, few issues.**
3. The manager approves and asks for **today's plan**: two crews, routes on the map, durations, materials, and one job
   left pending *with the reason*.
4. **The key moment:** an electrician is called away (or a technician marks a job *blocked: no LED lamp*). Rua Viva
   **recomputes a feasible plan and explains every change**; the manager approves it.
5. The bench is fixed (after photo + note), the manager closes it, and **every citizen who reported it** gets an email
   (Mailpit).

## 5. Maturity and next steps

- **End to end and real:** intake, LLM analysis, dedup, triage, planning, replanning, approvals, notifications and the
  audit log all run in the broker.
- **Fictional / simulated:** the neighbourhood's assets, reports, crews and stock (clearly labelled), and the
  streetlight controller. Real integrations (the municipality's reporting app, asset inventory, lighting management
  system) plug into the same topics.
- **Human in the loop by design:** the AI interprets, the rules and planner propose, the manager approves anything with
  safety or resource implications. The report count never decides priority alone.
- **Explainable:** every priority, every scheduled or pending job and every replan change has a written reason.
- **Reliability:**
  - no internet → keyword classifier instead of the LLM, map without tiles, everything else local;
  - state is retained and rebuilt from events; the audit log records every event;
  - a replan never touches started or finished work.
- **Security (Rules, if the licence allows):** one user per role. Citizens only publish reports, answers and photos;
  technicians only job status and photos; the manager only decisions, resources and plan requests; only broker Actions
  write issues, state and approved plans. Citizens' contacts never reach the crews' view.
- **Tests:** `pytest` for the matcher (duplicate, recurrence, ambiguous asset), triage (reasons, out of scope) and planner
  (skills, missing material, shift overflow, replan stability, empty day).
- **Scale:** categories, job types, assets and crews are configuration, not code. One broker per municipality; parishes
  (*juntas de freguesia*) as more crews and assets.
- **Business model:** a subscription per municipality, priced by population; it complements, not replaces, the
  existing reporting apps.
- **With more time:** real integrations, failure prediction from asset history, detection by cameras, photo comparison
  for closure checks, travel times from a real road network.

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
Layout: **one notebook per feature, one owner per notebook** (see [`PLAN.md`](PLAN.md#notebooks)), so two
people never edit the same `.lotnb` (they are JSON and merge badly).

### Useful tools

- **MQTT Explorer** or `mosquitto_sub -h localhost -u root -P coreflux -t '#' -v` to see every topic.
- **Python:** `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (paho-mqtt, pytest)
  for services, simulators and tests in `services/` (`anthropic` only for the plan B analyzer).
- Broker variables and secrets: `-setEnv NAME=value`, `-setSecret NAME=value` (no spaces around the `=`),
  then `{env.NAME}` or `GET ENV "NAME"` / `GET SECRET "NAME"` in LoT.

## Documents in this folder

- [`AI.md`](AI.md): AI tooling setup (MCP servers, Coreflux skills, token) and the daily loop.
- [`AGENTS.md`](AGENTS.md): LoT rules for AI assistants (Claude Code reads it through `CLAUDE.md`).
- [`LOT_CHEATSHEET.md`](LOT_CHEATSHEET.md): LoT syntax reference (Actions, Models, Connectors, Rules, Panels).
- [`PLAN.md`](PLAN.md): who builds what, notebooks, timeline, licence decision and spike results.
- [`PITCH.md`](PITCH.md): presentation structure and demo checklist.
- [`fixtures/`](fixtures/): one example message per topic (`messages/`), published by `scripts/replay.py`.

## References

- Coreflux documentation: <https://docs.coreflux.org>
- Training repo (reference only, **do not copy**: there is plagiarism detection):
  <https://github.com/CorefluxCommunity/weather-station-hackathon>
