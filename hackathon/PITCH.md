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
| Why Coreflux and not a normal web app with a database? | TODO |
| What is real and what is simulated? | TODO |

## Owner and slides

**Victor owns the pitch** (demo script, slides, rehearsals, presents). Deck: `TODO`. Backup video: `TODO`.
