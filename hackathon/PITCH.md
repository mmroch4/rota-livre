# Pitch and demo

> The presentation **matters a lot**: it is how the jury judges the solution (Rules, Art. 1, 3).
> Set aside at least **1h30 of the 6h** to prepare and rehearse the pitch and the demo.

**Format:** a **5-minute** pitch, which can stretch to **8 minutes** if the jury asks questions
and wants to know more about the project. Event on **Saturday, 24/10**.

## Structure (mapped to the jury's criteria)

| # | Block | Jury criterion | Time (~5-min pitch) | Content |
|---|-------|----------------|:-----:|---------|
| 1 | Hook | — | 0:20 | One sentence/number that shows the pain. |
| 2 | **Problem** | problem statement | 0:50 | Who suffers, how much it costs, why it is not solved today. |
| 3 | Solution | — | 0:30 | The product in one sentence and what changes for the user. |
| 4 | **Demo** | demonstration | 1:40 | Live: a real event flows through the system end to end. |
| 5 | **Architecture** | architecture built | 0:50 | One diagram: sources → Coreflux (Actions/Models/Connectors) → outputs. Highlight what runs **inside the broker**. |
| 6 | **Maturity** | maturity | 0:40 | What is real vs. simulated, tests, security (Rules), scale, next steps. |
| 7 | Close | — | 0:10 | The product sentence + team name. |

## Script (Vale, ~5 min)

| # | Block | Lines / screen |
|---|-------|----------------|
| 1 | Hook | *"Yesterday, in Portugal, the same kWh cost 1000 times more at 19:00 than at midday."* Real REN chart for 22/10. |
| 2 | Problem | A restaurant on an indexed tariff: cold room, dishwasher, electric van. This week's cheapest hour was at 12:00, 13:00, 11:00, 11:00, **01:00**, 14:00, 14:00... A timer can't keep up with that, and nobody checks OMIE every day at 13:00. |
| 3 | Solution | *"Vale understands what each appliance needs from a single sentence, moves consumption into the price valleys and switches the appliances on by itself, without ever putting the food at risk."* |
| 4 | Demo | See the script below. |
| 5 | Architecture | One diagram (README §3). Message: **everything that decides lives in the broker**: REST and LLM Connectors, Python inside the broker, Actions, Rules. Only the appliance simulator and the screen are outside it. |
| 6 | Maturity | Real vs. simulated, *guardrails* above the plan, the LLM never acts, safe mode without internet, Rules, tests (including the 100-quarter-hour day on 25/10), CSV audit log. |
| 7 | Close | *"Vale: the cheapest energy is the energy used at the right time." Team O(1/n).* |

## Demo script (1:40)

Initial state: `00-setup.lotnb` run, today's prices already on `copilot/market/prices`, all appliances in `advise`,
clock stopped at slot 32 (08:00), Mailpit empty, CSV clean.

1. **(0:15) Real prices.** The dashboard shows today's curve from REN, with the midday valley clearly visible.
2. **(0:25) Sentence → tasks.** Type: *"The van arrives at 9:00 and must leave at 17:00 with 30 kWh. The lunch dishes
   must be washed before 19:00."* The JSON for the 2 tasks appears, and the plans are shaded over the curve:
   "expected savings: X €".
3. **(0:10) Advise → act.** A piece of advice appears in `advise` mode. Switch the van and the dishwasher to `auto`.
4. **(0:25) ▶ Simulate the day** (1 s = 15 min). The appliances switch on by themselves in the valleys, the cold room pre-cools before the
   18:00 peak and the € saved counter goes up.
5. **(0:20) Surprise.** Click "door open" on the cold room: the temperature goes above 5 °C and `Guard` turns the cold room on **even at a high price**.
   The email arrives in Mailpit ("Cold room 1 out of range") and a line with reason `guardrail` appears in the CSV.
6. **(0:05) Proof.** The HUB shows the Actions and Connectors running in the broker.

**Plan B (in order):**
- **the LLM fails or is slow:** buttons with preset tasks that publish the same `copilot/tasks/new`;
- **no internet:** 22/10 prices cached (file + retained) and the LLM replaced by the presets;
- **the dashboard fails:** the HUB Panel and MQTT Explorer;
- **everything fails:** the demo video recorded at H+4:30.

## Demo checklist

- [ ] A **written script** of the demo: every click and every published message.
- [ ] A single "happy" path, rehearsed **at least 3 times**, ideally on the presentation machine.
- [ ] A reproducible initial state (a script or `00-setup.lotnb` that resets the retained config).
- [ ] Data that triggers the interesting event **on demand** (button, Python script, publish from the HUB),
      instead of waiting for a timer.
- [ ] **Plan B:** screen-recorded demo video + simulated data if a sensor or external API fails.
- [ ] No internet? Know what stops working (REST Connectors) and have an alternative.
- [ ] Large font in the HUB/terminal; notifications off; tabs ready.

## Jury questions (up to 3 min)

The extra 3 minutes are an opportunity: questions show interest. Prepare short answers
(≤ 30 s) and, where it makes sense, a **backup slide** for each one:

| Likely question | Answer / backup slide |
|-----------------|-----------------------|
| Why Coreflux and not a normal script/server? | The broker is already where the appliance data flows. Putting the decision there (Actions, `CALL PYTHON`, `CALL LLM`) removes an intermediate server, a point of failure and latency, and the decision keeps working close to the appliance, even with the cloud down. |
| What is real and what is simulated? | Real: REN prices, the LLM, scheduling, dispatch, *guardrails*, emails and auditing. Simulated: the appliances and the accelerated clock. Going live only needs a relay/PLC subscribing to the same `.../command`. |
| How would it scale to N users/devices? | Appliances are configuration (`config/devices/<id>`), not code. One broker per shop, linked to a central broker, for chains. The planner is pure and stateless. |
| What about security (who can publish/change config)? | Rules: only Actions publish commands to the appliances, the dashboard only sends requests and changes the mode, and each appliance only publishes its own telemetry. The LLM never acts: the task is validated by a Model before it is scheduled. |
| What if the LLM gets it wrong? | The LLM only produces a task *proposal*. The Model validates it, the owner sees and confirms it, and the *guardrail* always protects operations. In the worst case the schedule is suboptimal, but never dangerous. |
| How much does it really save? | Only the energy component changes (not grid fees, contracted power or taxes). In the demo we show € saved on that component, with real prices. The honest claim is: "shifts X kWh/day from the peak to the valley". |
| How much does it cost to deploy? Who would pay? | The business owner pays a subscription per establishment, plus cheap relays or integration with the existing controller. The sales pitch is the bill simulator (how much they would save on the indexed tariff). |
| What would you do next with more time? | Modbus integration with the refrigeration controllers, forecasting tomorrow's price before 13:00, optimizing contracted power and solar self-consumption, and the residential profile (electric car). |

## Roles on the day

No fixed roles in the team. Decide **by lunchtime** who presents each block and who
"drives" the demo while someone else talks.

Suggested split of work (4 parallel tracks, with the README topic map as the contract):
**A**: broker/LoT (Connectors, `ParsePrices`, `SimClock`, `Dispatch`, `Guard`, Rules) ·
**B**: planner Python + tests · **C**: web dashboard · **D**: LLM (`ParseIntent`), appliance simulator
and, from H+3, the slides.

## 6-hour plan

| Milestone | Goal (verifiable) |
|-----------|-------------------|
| **H+0:30** | Broker and licence active. ⚠️ Verified: licence tier (LLM Connector?), `CALL PYTHON`, REST Connector with the date in the endpoint, WebSocket port. Plan B decisions made **here**, not later. |
| **H+1** | Real prices reach `copilot/market/prices` (retained). The planner passes its tests. The dashboard draws the curve. The simulator publishes telemetry. |
| **H+2** | **End-to-end MVP without the LLM:** a task from a form → plan → `SimClock` → `Dispatch` → the appliance switches on in the valley. From here on there is always a demo. |
| **H+3** | The LLM turns text into a `Task` (or plan B in Python). `Guard` + email + CSV working. Lunch; decide who presents what. |
| **H+4** | Rules, `Meter` (€ counter), HUB Panel, dashboard polish. **H+4:30: feature freeze and record the backup video.** |
| **H+4:30 → H+6** | **1h30 for the pitch only:** slides, 3 timed rehearsals on the presentation machine, jury questions, reset the initial state. Bug fixes only. |

## Day-before prep (no product code)

The rules don't explicitly forbid prior work, but the event brief is only handed out on the day, and there is plagiarism detection.
So the day before we only do **environment, research and decisions**:
- `docker compose pull` and a test `up`. Have the licence at hand. Install the LoT Notebooks extension.
- Create an Anthropic API key (with credit) and test it with `curl`. It stays outside git.
- Read the docs: [LLM Connector](https://docs.coreflux.org/latest/lot-language/routes/ai-routes.md),
  [Python integration](https://docs.coreflux.org/latest/lot-language/actions/python-integration.md), Rules, Panels and the
  REST Connector (how to put the payload's date into the endpoint).
- Save last week's REN prices as JSON (data, for the no-internet plan B and for the slide charts).
- Slide skeleton: hook, problem with the numbers, architecture diagram.
- Agree who takes each track (A–D) and get some sleep.

## Slides

`TODO`: link to the slides (Google Slides/Canva) and to the backup video.
