# Development plan: Vale (Sat 24/10, 6 h)

How four people build [Vale](README.md) in parallel. **Product and contract:** [`README.md`](README.md) (the topic
map is frozen). **Pitch:** [`PITCH.md`](PITCH.md). **Task board:** GitHub Issues, one per piece below, labelled by
track and milestoned by checkpoint.

## How we parallelize

1. **The contract is frozen before we start.** Every topic in the map has an example message in
   `fixtures/messages/`. `scripts/replay.py` publishes them, so nobody waits for anybody: the dashboard draws plans
   that no planner made yet, the planner reads prices that no connector fetched yet.
2. **One notebook per feature, one owner per notebook.** `.lotnb` files are JSON, so two people editing one
   notebook means a painful merge. You may *read* any notebook; you only *write* yours.
3. **Everyone develops on their own broker** (`localhost`, ports bound to 127.0.0.1). The **integration broker**
   is the presentation laptop: at each checkpoint it does `git pull` + `/lot-deploy` and we run the demo path.
4. **Small commits to `main`**, `git pull --rebase` before pushing, `fixes #N` in the message to close the issue.

## Tracks and owners

| Track | Owner | Pieces (in order) | Notebooks it owns |
|-------|-------|-------------------|-------------------|
| **A: broker core** (LoT) | _TBD_ | P1 Prices → P3 Clock + Dispatch → P5a Guard + email → P8 Rules | `10-prices`, `30-dispatch`, `40-guard`, `70-rules` |
| **B: brains** (Python + LoT) | _TBD_ | P2 Planner → P6 Intent (LLM or plan B) → P5b Meter + audit log | `20-planner`, `50-meter`, `60-intent` |
| **C: face** (UI) | _TBD_ | P7a HUB Panel (MVP by H+2) → P7b web dashboard | `80-panel`, `dashboard/` |
| **D: story** | **Victor** | P0 contract (done 23/10) → P4 Simulator → P9 Pitch (owner from H+0) | `00-setup`, `services/device_sim.py`, slides |

D is deliberately light on code: the pitch is worth as much as the product. Victor writes the demo script first
(it decides what has to work), keeps the slides in step with what really runs, and leads the rehearsals.

## Pieces

| # | Piece | Done when (verifiable) | Needs only |
|---|-------|------------------------|------------|
| P1 | Prices | `RenPrices` + `ParsePrices` publish retained `copilot/market/prices` for today; on 404 or no internet they fall back to the cached day (`source:"cache"`) and log to `copilot/errors` | REN (spiked) |
| P2 | Planner | `Planner` Python passes `pytest` (energy, block, infeasible, 92 and 100 slots); `PlanTask` turns `tasks/new` into `plans/<id>` via `CALL PYTHON` | price fixture |
| P3 | Clock + Dispatch | `SimClock` honours `start`/`pause`/`reset`; `Dispatch` publishes `command` (auto) or `advice` (advise) at the plan's slots and logs `audit/decisions` | plan + clock fixtures |
| P4 | Simulator | `device_sim.py` obeys `command`, publishes `telemetry` each slot; the cold room warms with the door open and cools when on | command fixture |
| P5a | Guard + email | Cold room > `temp_max_c` → `command on` now, one `alerts/guardrail` per episode, email in Mailpit | telemetry fixtures (`--edge`) |
| P5b | Meter + audit log | `kpi/savings` updates every slot; every decision lands in `broker/exports/decisions.json` | plan + telemetry fixtures |
| P6 | Intent | Free text → `tasks/proposed` (LLM connector if licensed, else `services/intent_parser.py`); invalid text → `assistant/errors` | request fixture |
| P7a | HUB Panel | Prices, plans, advice, mode toggles, € counter, confirm + preset buttons, door button | all fixtures |
| P7b | Web dashboard | Same as P7a with a real price chart and the plans shaded on it, over `ws://localhost:9001/mqtt` (opt-in, see `broker/docker-compose.ws.yml`) | all fixtures |
| P8 | Rules + reset | Rules as in README §5 (only if the licence allows Rules); one command resets the demo's starting state | everything |
| P9 | Pitch | Slides, demo script, backup video at H+4:30, Q&A answers, 3 timed rehearsals | demo script |

## Notebooks

| Notebook | Owner | Contents |
|----------|-------|----------|
| `00-setup.lotnb` | D | Retained config: devices, modes, clock; the reset Action |
| `10-prices.lotnb` | A | `RenPrices` Connector, `FetchPrices`, `ParsePrices`, `PriceTools` Python |
| `20-planner.lotnb` | B | `Device` and `Task` Models, `PlanTask`, `Planner` Python |
| `30-dispatch.lotnb` | A | `SimClock`, `Dispatch`, `Decision` Model |
| `40-guard.lotnb` | A | `Guard`, `Alert` Model, `Mailer` Connector |
| `50-meter.lotnb` | B | `Meter`, `DecisionLog` Connector |
| `60-intent.lotnb` | B | `ParseIntent`, LLM Connector (if licensed) |
| `70-rules.lotnb` | A | Rules (if licensed) |
| `80-panel.lotnb` | C | HUB Panel |

## Timeline

| When | Goal (verifiable) | Integration check on the presentation laptop |
|------|-------------------|----------------------------------------------|
| **H+0:00** | 15-min kickoff: read the topic map together, confirm owners, `replay.py` works on every laptop | — |
| **H+0:30** | Licence activated, tier read → decide LLM in broker vs plan B, Rules yes/no (see below) | `curl localhost:9100/license` |
| **H+1:00** | P1 real prices retained · P2 tests green · P4 publishes telemetry · P7a shows prices from fixtures | prices from REN on the panel |
| **H+2:00** | **MVP without the LLM:** preset button → plan → clock → Dispatch → appliance on in the valley. *From here there is always a demo.* | full demo path, presets only |
| **H+3:00** | P6 text → tasks · P5a Guard + email · P5b Meter + log · lunch · Victor assigns pitch blocks | demo path with text + door |
| **H+4:00** | P8 Rules · P7b web dashboard · polish | full demo path, timed |
| **H+4:30** | **Feature freeze.** Record the backup video. Only bug fixes from here. | backup video recorded |
| **H+4:30 → 6:00** | Pitch: 3 timed rehearsals on the presentation laptop, Q&A drill, reset the starting state | — |

## H+0:30 decision: what the licence unlocks

Put the code in `broker/.env` (`COREFLUX_ACTIVATION_CODE=CFLX-...`) **only on the integration laptop**, or activate
it from the HUB (each activation uses a seat). Then `curl -s localhost:9100/license` and read `tier` and `effectiveLimits`:

| If… | Then |
|-----|------|
| `TYPE LLM` deploys | P6 in the broker: `CALL LLM` in `ParseIntent` (best architecture story) |
| `TYPE LLM` is refused | P6 plan B: `services/intent_parser.py` with the `anthropic` SDK, same topics. Say so honestly in the pitch |
| `maxRules` > 0 | P8 Rules go in; they are a maturity/security slide |
| `maxRules` = 0 | Drop P8 Rules; "Rules" moves to "next steps" in the pitch |
| `maxRoutes` = 3 | Exactly enough for `RenPrices`, `Mailer`, `DecisionLog`; no room for an LLM connector anyway |

Developer laptops stay on Community: fine for everything except the LLM connector and Rules.

## Spike results (23/10, broker 2.22.0, Community)

| Risk | Result |
|------|--------|
| `CALL PYTHON` | ✅ ~0.2 ms to sort 96 prices, ~100–250 ms end to end. **Return `json.dumps(...)`**: dicts and ints break at runtime (see `AGENTS.md`) |
| REST connector with the date in the URL | ✅ `{payload.json.date}` works; REN answers in ~370 ms; 404 arrives as `{"success":false,...}` |
| REN data shape | ⚠️ **92 values today**, 96 on complete days, 100 on 25/10; tomorrow's prices appear ~13:00 |
| WebSocket for the dashboard | ✅ container port 5000, path `/mqtt`; opt-in `docker-compose.ws.yml` → `ws://localhost:9001/mqtt` (cross-site risk with the default password, see the file) |
| EMAIL to Mailpit | ✅ subject placeholders work |
| FILE_STORAGE audit log | ✅ after `chmod 777 broker/exports`; use JSON (CSV triple-quotes strings) |
| LLM connector | ❌ refused on Community; needs the event licence |
| Notebook per feature | ✅ the project loads by kind, so cross-notebook Models work |

## Entity budget (Community worst case)

Actions 24 (events and Python count): ~8 Actions (`FetchPrices`, `ParsePrices`, `SimClock`, `PlanTask`, `Dispatch`,
`Guard`, `Meter`, `ParseIntent`) + 3 connector events + 2 Python scripts ≈ **13/24**. Connectors **3/3**. Models
~5/24 (`Device`, `Task`, `Alert`, `Decision`, maybe `Plan`). Ask the team before adding a 4th connector.

## Tonight (23/10): prep only, no product code

- [x] Contract frozen, fixtures + `replay.py` (data and tooling, not product logic)
- [x] Spikes on the local broker (above)
- [x] Task board on GitHub Issues
- [ ] Everyone: `git pull`, `chmod 777 hackathon/broker/exports`, `docker compose up -d`,
      `scripts/mcp_token.py`, then `scripts/replay.py --list` works
- [ ] Assign tracks A, B, C (fill the table above)
- [ ] Anthropic API key with credit, tested with `curl` (needed by plan B and by the LLM connector); keep it out of git
- [ ] Victor: slide skeleton (hook, problem with the REN numbers, architecture), first draft of the demo script
- [ ] Track C: read the `lot-panels` skill; Track B: the `python-scripts` skill and the
      [Python integration](https://docs.coreflux.org/latest/lot-language/actions/python-integration.md) page
- [ ] Sleep
