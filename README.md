# O(1/n) — SciTeCh '26

Code and development repository of team **O(1/n)** at
[SciTeCh '26](https://scitech.bestporto.org/index.html) (Science and Technology Challenge),
organized by BEST Porto at FCUP on **24 and 25 October 2026**.

> **The event is over.** We won **1st place in the Hackathon** with **Rota Livre**, accessible walking routes in
> Porto built on Coreflux.
> Rota Livre now goes on to a **further stage of the competition, mentored by Coreflux**, competing for a place at
> **Hannover Messe** (see [What's next](#whats-next-rota-livre-towards-hannover-messe)).

| Team |
|------|
| Miguel |
| Victor |
| Ben    |
| Pedro  |

## Results

SciTeCh had two events, one per day, each with **6 hours of work** followed by judging. This repo keeps only our
Hackathon entry; the Team Design entry was removed and its last state is the git tag `team-design-final`.

| Day | Folder | Challenge | What we built | Result |
|-----|--------|-----------|---------------|--------|
| **Sat 24/10** | [`hackathon/`](hackathon/) | **Hackathon**: an automation solution for a real problem we chose, on the **Coreflux** platform (MQTT broker + LoT), judged on a 5-min pitch with a live demo. | **Rota Livre**: a web app that plans walking routes in Porto under a person's limits (slope, steps, surface) and goes around barriers that anyone reports or that the Câmara has registered, shared live through the Coreflux broker. | **1st place** |

## What's next: Rota Livre towards Hannover Messe

The Hackathon win takes Rota Livre to a further stage of the competition, with **mentoring from Coreflux**, where
it competes for a place at **Hannover Messe**, the industrial trade fair in Hannover, Germany. Dates, format and
deliverables will be added here when we receive them.

Work for this phase continues in [`hackathon/`](hackathon/). Its README records the system as demonstrated
on 24/10 and the [open items](hackathon/README.md#next-phase-coreflux-mentoring-and-hannover-messe) we start from.

## Repository layout

```text
scitech-2026/
├── README.md           # this file
├── CLAUDE.md           # context and conventions for AI agents
├── regulamento.pdf     # official SciTeCh '26 rules (Portuguese)
├── hackathon/          # Rota Livre: web app, Coreflux broker + LoT, Valhalla runtime, database, docs and pitch
├── projects/           # source trees used by Rota Livre's routing: Valhalla (slope-cap fix) and the OSM website
└── accessibility_routing_project_handoff.md   # 24/10 handoff of the Valhalla slope-cap work (historical)
```

## Getting started

Common prerequisites (Linux or macOS): `git`, `python3`, **Docker + Docker Compose v2** (hackathon)
and VS Code (recommended).

```bash
git clone git@github.com:mmroch4/scitech-2026.git
cd scitech-2026
```

Then follow [`hackathon/README.md`](hackathon/README.md).

## How we work

- **Everything in English:** code, identifiers, file names, MQTT messages, topics, comments
  and documentation.
- **Trunk-based git:** everyone pushes straight to `main`, with small, frequent commits.
  Before every push: `git pull --rebase`. Every push that touches `hackathon/app/` redeploys the public page.
- **Never commit secrets** (Coreflux licence code, API keys, passwords).
  They live in `.env`, which is in `.gitignore`.

## Rules that affected the code

Summary of [`regulamento.pdf`](regulamento.pdf), only the points that affected the technical work at SciTeCh '26:

- **Hackathon (Art. 1, 6):** judging is based on a **presentation** that covers:
  1. the **problem** statement;
  2. a **demonstration** of the solution;
  3. the **architecture** built;
  4. the **maturity** of the solution.

  Solutions go through **plagiarism-detection software**: do not copy code from the Coreflux
  training labs; write our own.
