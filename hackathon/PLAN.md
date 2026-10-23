# Development plan: ZelAR (Sat 24/10, 6 h)

How four people build [ZelAR](README.md) in parallel. **Product and contract:** [`README.md`](README.md) (the topic
map is drafted; freeze it at kickoff). **Pitch:** [`PITCH.md`](PITCH.md). **Task board:** GitHub Issues, one per
piece below (#1 setup, #2 licence decision, #3–#19 the pieces), labelled by track and milestoned by checkpoint.

## How we parallelize

1. **The contract is frozen before we start.** Every topic in the map has an example message in
   `fixtures/messages/`. `scripts/replay.py` publishes them, so nobody waits for anybody: the manager dashboard draws
   a plan that no planner made yet, the planner reads issues that no matcher created yet.
2. **One notebook per feature, one owner per notebook.** `.lotnb` files are JSON, so two people editing one
   notebook means a painful merge. You may *read* any notebook; you only *write* yours.
3. **LoT ↔ Python by signature.** Track A writes the Actions that call Track B's Python; the function signatures below
   are part of the contract. B tests them with `pytest` on the fixtures, without a broker.
4. **Everyone develops on their own broker** (`localhost`, ports bound to 127.0.0.1). The **integration broker**
   is the presentation laptop: at each checkpoint it does `git pull` + `/lot-deploy` and we run the demo path.
5. **Small commits to `main`**, `git pull --rebase` before pushing, `fixes #N` in the message to close the issue.

## Tracks and owners

| Track | Owner | Pieces (in order) | Notebooks / files it owns |
|-------|-------|-------------------|---------------------------|
| **A: pipeline** (LoT) | _TBD_ | P1 Issue store → P3a Intake → P3b LLM → P6 Field updates → P7 Notify + audit → P10 Rules | `10-intake`, `30-issues`, `50-field`, `60-notify`, `70-rules`, `services/report_analyzer.py` (plan B) |
| **B: brains** (Python + its Actions) | _TBD_ | P2 IssueTools → P4 Planner → P5 Matcher → P8 Replan with explanations | `20-match`, `35-issue-tools`, `40-planner`, `services/tests/` |
| **C: faces** (web) | _TBD_ | P9a Manager dashboard → P9b Technician list → P9c Citizen form | `dashboard/` |
| **D: story** | **Victor** | P0 Demo world (config, assets, photos) → P12a Demo script + deck → P11 Streetlight simulator → P12b Video + rehearsals (pitch owner from H+0) | `00-setup`, `services/streetlight_sim.py`, `dashboard/photos/`, slides |

D is deliberately light on code: the pitch is worth as much as the product. Victor writes the demo script first
(it decides what has to work), keeps the slides in step with what really runs, and leads the rehearsals. The demo
world (which bench, which playground, which crew is short) **is** the story, so it is his.

## Pieces

| # | Issue | Piece | Done when (verifiable) | Needs only |
|---|-------|-------|------------------------|------------|
| P0 | #3 | Demo world | `00-setup` publishes `config/categories`, `config/job_types`, `config/assets`, the day's `zelar/state/resources` and ~8 seed reports; 6 demo photos in `dashboard/photos/`; `ResetDemo` restores it | — |
| P1 | #4 | Issue store | `ApplyIssueEvent` folds every `zelar/issues/events` message into retained `zelar/state/issues` and `zelar/kpi` via `IssueTools.apply`; `HandleDecision` turns manager decisions into events | P2 (stub first) |
| P2 | #5 | IssueTools | `pytest` green: fold of every event type, history, triage (crew, priority score, **reasons**, out of scope), close check, KPIs | config fixtures |
| P3a | #6 | Intake | `reports/new` → `analysis` (`Matcher.classify` keywords) → `MatchReport` → `created` event; `SensorIntake` turns a lamp fault into a report | P5 (stub: always `new`) |
| P3b | #19 | LLM analysis | `AnalyzeReport` uses the LLM connector if licensed, else the plan B service; falls back to keywords | request fixture |
| P4 | #7 | Planner | `pytest` green: skills, shift capacity, missing material → `unscheduled` with reason, nearest-neighbour route, empty day; `BuildPlan` publishes `plans/<date>/proposed`; `ApprovePlan` publishes `approved` + `scheduled` events | issues + resources fixtures |
| P5 | #8 | Matcher | `pytest` green: same bench → `attach`, two playgrounds → `needs_info` with options, closed < 30 days → `recurrence`, grey zone → `review`; keyword `classify` | issues + assets fixtures |
| P6 | #9 | Field updates | `HandleJobStatus`: started/done/blocked/needs → issue events; blocked or needs material → `resources/events` + `plan/request` (`replan`); `UpdateResources` folds resource events | approved plan fixture |
| P7 | #10 | Notify + audit | Close or out of scope → one email per linked citizen in Mailpit; every event lands in `broker/exports/audit.json` | issue fixtures |
| P8 | #11 | Replan | Replan keeps started/done jobs, starts at `now`, and `changes` explains every added/dropped/moved/reassigned job | P4 |
| P9a | #12 | Manager dashboard | Map + issue list (filters: to review, duplicates, approved unscheduled, in progress, blocked), issue card with history, review/approve buttons, plan view with *why* and pending reasons, resource toggles, KPIs | all fixtures |
| P9b | #13 | Technician list | Phone layout: today's jobs for one crew, start/done/blocked/needs buttons, after photo + note | plan fixture |
| P9c | #14 | Citizen form | Photo (pick a demo photo or upload), pin confirmed on the map, text; shows the analysis, the question and the outcome ("joined 4 other reports") | analysis/question fixtures |
| P10 | #15 | Rules | Rules as in README §5 (only if the licence allows Rules) | everything |
| P11 | #16 | Streetlight simulator | `streetlight_sim.py` publishes `devices/<id>/status`; a key press breaks a lamp | — |
| P12a | #17 | Demo script + deck | Click-by-click demo script, new deck with speaker notes, verified hook number | README, PITCH |
| P12b | #18 | Video + rehearsals | Backup video at H+4:30, 3 timed rehearsals, Q&A drill | demo script |

## Python signatures (contract between A and B)

Every argument is a JSON **string** and every function returns `json.dumps(...)` (broker 2.22.0 quirk, see `AGENTS.md`).

| Function | Arguments | Returns |
|----------|-----------|---------|
| `IssueTools.apply` | `index, event, categories, assets` | `{"index": {...}, "kpi": {...}, "audit": {...}, "notify": [{"to","subject","body","issue_id"}], "error": null}` |
| `Matcher.classify` | `report, categories` | an `analysis` payload with `source: "keywords"` |
| `Matcher.match` | `report, analysis, index, assets` (+ `answer` or manager `decision`, may be `""`) | the `match` payload, plus `event` (to publish on `zelar/issues/events`) or `question` or `review` |
| `Planner.build` | `request, index, resources, job_types, previous_plan` (`""` if none) | the Plan, with `changes` vs. `previous_plan` |
| `Planner.apply_resource_event` | `resources, event` | the new `resources` document |

## Notebooks

| Notebook | Owner | Contents |
|----------|-------|----------|
| `00-setup.lotnb` | D | Retained config and the day's resources; seed reports; the `ResetDemo` Action |
| `10-intake.lotnb` | A | `Report` Model, `AnalyzeReport`, `SensorIntake`, LLM Connector (if licensed) |
| `20-match.lotnb` | B | `MatchReport`, `Matcher` Python |
| `30-issues.lotnb` | A | `Issue` Model, `ApplyIssueEvent`, `HandleDecision` |
| `35-issue-tools.lotnb` | B | `IssueTools` Python only |
| `40-planner.lotnb` | B | `BuildPlan`, `ApprovePlan`, `UpdateResources`, `Planner` Python |
| `50-field.lotnb` | A | `HandleJobStatus` |
| `60-notify.lotnb` | A | `Notify`, `Mailer` and `AuditLog` Connectors |
| `70-rules.lotnb` | A | Rules (if licensed) |

## Timeline

| When | Goal (verifiable) | Integration check on the presentation laptop |
|------|-------------------|----------------------------------------------|
| **H+0:00** | 15-min kickoff: walk the topic map, **freeze it**, confirm owners, `replay.py` works on every laptop | — |
| **H+0:30** | Licence activated, tier read → LLM in broker vs plan B, Rules yes/no (see below) | `curl localhost:9100/license` |
| **H+1:00** | P0 demo world · P2 fold + triage tests green · P1 store from fixture events · P9a issues on the map from fixtures | seed reports become issues on the map |
| **H+2:00** | **MVP:** report (keyword analysis) → issue → approve → **daily plan** → technician sees the jobs. *From here there is always a demo.* | full path, no LLM, no dedup |
| **H+3:00** | P5 duplicates + question + review · P6 blocked → replan · P3b LLM analysis · lunch · Victor assigns pitch blocks | demo path with duplicates and a blocker |
| **H+4:00** | P8 explained changes · P7 emails · P9c citizen form · P11 streetlight · P10 Rules · polish | full demo path, timed |
| **H+4:30** | **Feature freeze.** Record the backup video. Only bug fixes from here. | backup video recorded |
| **H+4:30 → 6:00** | Pitch: 3 timed rehearsals on the presentation laptop, Q&A drill, `ResetDemo` | — |

## H+0:30 decision: what the licence unlocks

Put the code in `broker/.env` (`COREFLUX_ACTIVATION_CODE=CFLX-...`) **only on the integration laptop**, or activate
it from the HUB (each activation uses a seat). Then `curl -s localhost:9100/license` and read `tier` and `effectiveLimits`:

| If… | Then |
|-----|------|
| `TYPE LLM` deploys | P3b in the broker: `CALL LLM` in `AnalyzeReport` (best architecture story) |
| `TYPE LLM` is refused | P3b plan B: `services/report_analyzer.py` with the `anthropic` SDK, same topics. Say so honestly in the pitch |
| `maxRules` > 0 | P10 Rules go in; one user per role is a maturity/security slide |
| `maxRules` = 0 | Drop P10; "Rules per role" moves to "next steps" in the pitch |
| `maxRoutes` = 3 | `Mailer`, `AuditLog` + the LLM connector: exactly 3. Ask the team before adding a 4th |

Developer laptops stay on Community: fine for everything except the LLM connector and Rules.

## Spikes still to run (tonight or H+0)

| Risk | Why it matters | Fallback |
|------|----------------|----------|
| `CALL PYTHON` with a ~50 KB JSON argument (the issue store) | every fold and plan passes the whole store | keep closed issues out of the store after 1 day; trim `history` |
| One email per recipient from a list | `Notify` gets a list from `IssueTools.apply` | `REPEAT … UNTIL` + a Python indexer, or a comma-separated `RECIPIENT`, or a self-draining queue topic |
| Payload size of a retained photo over WebSocket | citizen upload | photos are fixtures only; upload becomes "next step" |
| Leaflet tiles on the event Wi-Fi | the map is the manager's main view | markers on a blank background (offline) |
| `GET TOPIC` of a retained JSON document as `STRING` inside an Action | every Action reads a store | read it as `STRING` and pass it to Python as is (`AS ARRAY` fails, see the skill) |

Already verified with Vale on broker 2.22.0 (still valid): `CALL PYTHON` speed and the `str` return rule, MQTT over
WebSocket (opt-in), EMAIL to Mailpit, FILE_STORAGE as JSON, notebook per feature, LLM connector refused on Community.

## Entity budget (Community worst case)

Actions 24 (Connector events and Python scripts count): ~11 Actions (`AnalyzeReport`, `SensorIntake`, `MatchReport`,
`ApplyIssueEvent`, `HandleDecision`, `BuildPlan`, `ApprovePlan`, `UpdateResources`, `HandleJobStatus`, `Notify`,
`ResetDemo`) + 3 Python scripts + 2–3 Connector events ≈ **17/24**. Connectors **2–3/3**. Models ~3/24 (`Report`,
`Issue`, maybe `Job`).

## Tonight (23/10): prep only, no product code

- [x] New idea written into the docs, contract drafted, fixtures + `replay.py`
- [ ] Everyone: read README §2–3 and the topic map; bring objections to the kickoff
- [ ] Everyone: `git pull`, `chmod 777 hackathon/broker/exports`, `docker compose up -d`,
      `scripts/mcp_token.py`, then `scripts/replay.py --list` works
- [ ] Assign tracks A, B, C (fill the table above)
- [x] Task board rewritten for ZelAR: issues #1–#19
- [ ] Anthropic API key with credit, tested with `curl` (plan B analyzer and LLM connector); keep it out of git
- [ ] Victor: new slide deck (the Vale deck is obsolete), first draft of the click-by-click demo script, demo photos
- [ ] Track C: Leaflet + mqtt.js over `ws://localhost:9001/mqtt`; Track B: the `python-scripts` skill and the
      [Python integration](https://docs.coreflux.org/latest/lot-language/actions/python-integration.md) page
- [ ] Sleep
