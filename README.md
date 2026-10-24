# O(1/n) — SciTeCh '26

Code and development repository of team **O(1/n)** at
[SciTeCh '26](https://scitech.bestporto.org/index.html) (Science and Technology Challenge),
organized by BEST Porto at FCUP on **24 and 25 October 2026**.

| Team |
|------|
| Miguel |
| Victor |
| Ben    |
| Pedro  |

## The two challenges

SciTeCh has two events, one per day, each with **6 hours of work** followed by judging.
Each folder in this repo maps to one challenge:

| Day | Folder | Challenge | What it is | Status |
|-----|--------|-----------|------------|--------|
| **Sat 24/10** | [`hackathon/`](hackathon/) | **Hackathon** | An automation solution for a **real problem we choose**, built on the **Coreflux** platform (MQTT broker + LoT). Judged on a 5-min pitch with a demo (up to 8 min with jury questions). | New idea (24/10), not written up yet; broker setup ready. |
| **Sun 25/10** | [`team-design/`](team-design/) | **Team Design** | A working physical prototype made from simple, low-cost materials, answering the brief revealed on the day. | Practice skeleton (Arduino Uno + H-bridge + servo), ready to adapt. |

## Repository layout

```text
scitech-2026/
├── README.md           # this file
├── CLAUDE.md           # context and conventions for AI agents
├── regulamento.pdf     # official SciTeCh '26 rules (Portuguese)
├── team-design/        # PlatformIO firmware (Arduino Uno) + Wokwi simulation
└── hackathon/          # Coreflux solution: broker, LoT code, services, dashboard and pitch
```

## Getting started

Common prerequisites (Linux or macOS): `git`, `python3`, **Docker + Docker Compose v2** (hackathon)
and VS Code (recommended).

```bash
git clone git@github.com:mmroch4/scitech-2026.git
cd scitech-2026
```

Then follow the challenge's README:
- **Team Design:** [`team-design/README.md`](team-design/README.md)
- **Hackathon:** [`hackathon/README.md`](hackathon/README.md)

## How we work

- **Everything in English:** code, identifiers, file names, Serial/MQTT messages, topics, comments
  and documentation.
- **Trunk-based git:** everyone pushes straight to `main`, with small, frequent commits.
  Before every push: `git pull --rebase`. On competition day there are no PRs (no time).
- **Never commit secrets** (Wokwi token, Coreflux licence code, API keys).
  They live in `.env`, which is in `.gitignore`.

## Rules that affect the code

Summary of [`regulamento.pdf`](regulamento.pdf), only the points that affect the technical work:

- **Team Design (Art. 5):** only **the materials and tools provided by the organizers** may be used,
  except for computers. Tools may not be part of the prototype. Electronic components
  stay with the organizers at the end. The test criteria are only revealed in the brief, at the start of the event.
- **Hackathon (Art. 1, 6):** judging is based on a **presentation** that covers:
  1. the **problem** statement;
  2. a **demonstration** of the solution;
  3. the **architecture** built;
  4. the **maturity** of the solution.

  Solutions go through **plagiarism-detection software**: do not copy code from the Coreflux
  training labs; write our own.
- **Credits (Art. 13):** 1.5 ECTS requires taking part in **both** challenges with a grade ≥ 10.
