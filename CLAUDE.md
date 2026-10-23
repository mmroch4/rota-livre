# CLAUDE.md

Repository of team O(1/n) (Miguel, Victor, Ben, Pedro) at SciTeCh '26 (BEST Porto, FCUP,
24–25 Oct 2026). Two challenges, each with 6 h of work: `hackathon/` (Coreflux,
**Saturday 24**) and `team-design/` (Arduino, **Sunday 25**). See `README.md` and `regulamento.pdf`.

## Conventions (mandatory)

- **Everything in English**: code (identifiers, file/folder names, Serial messages, MQTT topics,
  names of LoT Actions/Models/Connectors), code comments and documentation (READMEs, this file).
- Trunk-based git: small commits straight to `main`; `git pull --rebase` before pushing.
- Never commit secrets (`.env` is in `.gitignore`).
- Hackathon: solutions go through plagiarism detection. Do not copy the Coreflux training labs
  (`CorefluxCommunity/weather-station-hackathon`); use them only as a syntax reference.

## team-design/ (PlatformIO, Arduino Uno)

```bash
cd team-design && source .venv/bin/activate
pio test -e native     # Unity tests of the pure logic on the PC — run after any change
pio run -e uno         # build
pio run -e uno -t upload && pio device monitor   # real board, Serial at 9600
wokwi-cli --scenario test/wokwi/mode_cycle.yaml --timeout 10000   # needs WOKWI_CLI_TOKEN
```

Architecture: **pure logic** in `lib/Control/` (no `Arduino.h`, testable with `-e native`) vs.
**hardware layer** in `src/main.cpp` (pins, Servo, Serial). New logic goes into `lib/` with tests
in `test/test_control/`; `main.cpp` should stay thin.

Invariants that are easy to break:
- `include/pins.h`, `diagram.json` (Wokwi) and the real wiring must match.
- Servo uses Timer1 → **no PWM on pins 9/10**; motor PWM is on 5/6.
- The `KEY=value` Serial output (e.g. `MODE=FORWARD A=200 B=200 SERVO=90`) is checked verbatim by
  `test/wokwi/mode_cycle.yaml`. If you change the format, update the scenario.
- Wokwi has no L298N/DC motors: in `diagram.json` the H-bridge signals are LEDs.

## hackathon/ (Coreflux)

Coreflux MQTT broker + HUB in Docker (`hackathon/broker/`). The logic lives in the broker as LoT
(Actions, Models, Connectors, Rules, Panels); the source of truth is the `.lotnb` files in
`hackathon/lot/`. Syntax reference: `hackathon/LOT_CHEATSHEET.md`. The organizers provide an event
licence (`CFLX-...`, in `hackathon/broker/.env`, outside git); without it, the Community edition only allows
**3 Connectors** and no custom Rules.
The pitch (5 min + up to 3 min of questions; problem → demo → architecture → maturity) is in
`hackathon/PITCH.md`.
