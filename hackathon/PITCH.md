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

## Script (Rua Viva, ~5 min)

| # | Block | Lines / screen |
|---|-------|----------------|
| 1 | Hook | *"Five neighbours report the same broken bench. Today that is five tickets, five e-mails, and a crew that still doesn't know if it has the wood to fix it."* `[TODO #17: add one verified number with its source]` |
| 2 | Problem | The manager gets reports, not jobs: where exactly, what, whose, how urgent, how long, with what material? The daily crew plan is built by memory and rebuilt by phone when a part is missing. And the citizen never hears back. |
| 3 | Solution | *"Rua Viva turns reports about public space into maintenance plans. It organizes reports, finds likely duplicates and helps the municipality decide what each crew can fix today, with the resources it has."* |
| 4 | Demo | See the script below. |
| 5 | Architecture | One diagram (README §3). Message: **every report, from a citizen or a device, is an event in the broker**; matching, triage and planning are Python inside the broker, the LLM only reads the text and the photo, and the manager approves. Only the screens and the simulator are outside. |
| 6 | Maturity | Real vs. fictional data (labelled), human in the loop, a reason for every decision, replan that never touches started work, tests, audit log, Rules per role. |
| 7 | Close | *"Rua Viva: from reports to repairs." Team O(1/n).* |

## Demo script (1:40)

Initial state: `ResetDemo` run; config, assets and the day's resources retained; 8 seed reports already turned into
6 issues; no plan yet; Mailpit empty. Three windows: citizen (phone size), manager, technician (phone size).

1. **(0:20) Report.** On the citizen view, pick the bench photo, confirm the pin, type *"O banco junto ao parque
   infantil tem uma tábua partida e um parafuso exposto."* The analysis appears: *street furniture · bench repair ·
   hazard: exposed screw*, and the manager's card shows **high priority** with the reason *"sharp element next to a
   children's play area"*. The outcome on the phone: *"Joined 4 other reports of this problem."*
2. **(0:15) Many reports, few issues.** The streetlight controller reports lamp 07 dead: it joins a citizen's "the
   street is dark" report. One ambiguous report waits in *Possible duplicates*; the manager attaches it with one click.
3. **(0:20) Today's plan.** The manager approves the issues and clicks **Plan today**: two crews, numbered routes on
   the map, durations and materials, and *pending: paving repair, not enough paving stones in stock*.
4. **(0:30) The key moment.** On the technician view, the electrician marks the first lamp job **blocked: wrong lamp
   model, need another LED lamp**. Rua Viva recomputes: *"Lamp 11 waits: the last LED lamp in stock goes to lamp 07, at the
   pedestrian crossing (higher priority). Lamp 07 now starts at 08:42."* The manager approves the new version.
5. **(0:10) Close the loop.** The technician finishes the bench (after photo + note), the manager closes it, and
   Mailpit shows **one email per citizen who reported it**.
6. **(0:05) Proof.** The HUB shows the Actions, Python scripts and Connectors running in the broker.

**Plan B (in order):**
- **the LLM fails or is slow:** the keyword classifier answers with `source: "keywords"`, same flow;
- **no internet:** keyword classifier + map without tiles; everything else is local;
- **a web view fails:** `replay.py` publishes the same messages, MQTT Explorer shows the result;
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
| Why Coreflux and not a normal web app with a database? | Reports come from people **and** from devices (lighting controllers, sensors). The broker is where both arrive as events; the same pipeline handles any channel, with no extra integration server. Every step is an event, so state, audit and notifications fall out of one stream. |
| What is real and what is fictional? | Real: the pipeline, the LLM analysis, matching, triage, planning, replanning, approvals, emails, audit. Fictional and labelled: the neighbourhood's assets, reports, crews and stock, and the streetlight controller. |
| What if the AI gets it wrong? | It only *suggests* the category and the summary. Matching, triage and planning are deterministic rules with written reasons, and the manager approves priorities, plans and closures. Safety decisions are never automatic. |
| Doesn't the number of reports bias priority toward loud neighbourhoods? | The count is one small, capped signal. Risk, sensitive area, impact on use and waiting time weigh more, and every score shows its reasons. |
| How do you know two reports are the same problem? | Distance, category, the asset, text similarity and the state of the existing issue. Above a threshold it attaches; in a grey zone it asks the manager; if the issue was closed recently, it opens a *recurrence*. |
| How good is the plan? | It is a greedy planner with visible assumptions (durations per job type, straight-line travel). Its value is that it is **feasible and explained**, and it can be recomputed in a second when the day changes. A real road network and learned durations come next. |
| How would it scale? | Categories, job types, assets and crews are configuration. One broker per municipality; parishes add crews and assets. The Python functions are pure and stateless. |
| What about privacy and security? | Citizens' contacts never reach the crews' view. Rules give each role (citizen, technician, manager) only its own topics, and only broker Actions write state. |
| Who pays? | The municipality, as a subscription priced by population. It complements existing reporting apps instead of replacing them. |
| What next? | Integrations with existing reporting apps and asset inventories, failure prediction from asset history, camera detection, photo comparison at closure. |

## Roles and timeline

No fixed roles: the pitch is built through issues like everything else, **#17** (demo script + deck) and **#18**
(backup video + rehearsals). Who presents: `TODO` (decide at kickoff; Victor was the plan before tasks became
free-for-all). The 6-hour plan, checkpoints and how we take tasks are in [`PLAN.md`](PLAN.md).

## Slides

The Vale deck (<https://claude.ai/artifact/3QRZ8JXuDBSsBftHCqjaCK>) is **obsolete**. New deck: `TODO` (#17).
Suggested 11 slides: cover, hook, problem, the path of one report, demo, architecture, explainability (one plan with
its reasons), maturity, what it is worth, close, and backup slides (why Coreflux, what if the AI is wrong).

Backup video: `TODO` (record at H+4:30).
