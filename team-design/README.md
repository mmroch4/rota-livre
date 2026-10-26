# Team Design — Arduino Uno robot

Prototype for the SciTeCh '26 **Team Design** challenge. Right now it is a **practice skeleton**:
the real brief is only revealed at the start of the event, and this project is here so we arrive with the toolchain,
tests and simulation already working.

**Current behaviour:** a hanging scoop moves sand from A to B (build guide and CAD:
`cad/scoop-tower-guide.html`, `cad/build_scoop_tower.py`). A DC-motor winch on the ground pulls a string up a
tower, over two pulleys and down to the kit servo, which hangs over A with a cup on its horn. The servo turns the
cup through the sand like a hand, the winch lifts it, and the servo turns it over the mouth of the chute to B.
There are no sensors: every move is timed, so **put the scoop at the top before pressing START**. START starts
the cycle, or stops it at once.

| Phase | Winch | Scoop | Lasts |
|-------|------:|------:|------:|
| `LOWER`  | down | rest 180° (opening right)  | `lowerMs` 2.5 s |
| `DIG`    | off  | 180° → 100° ramp            | `digMs` 0.8 s |
| `RAISE`  | up   | full 100° (opening up)      | `raiseMs` 2.8 s |
| `SETTLE` | off  | 100°                        | `settleMs` 0.8 s (stops the swing) |
| `DUMP`   | off  | dump 0° (opening left)      | `dumpMs` 1 s |
| `RETURN` | off  | 0° → 180° ramp              | `returnMs` 0.6 s, then `LOWER` again |

All angles and times are starting values in `CraneConfig` (`lib/Control/Control.h`): calibrate them on the real
build. `raiseMs` is longer than `lowerMs` because the winch lifts the sand going up and gravity helps going down.

**Calibration over Serial** (9600, one command per line, only while `IDLE`): `s<deg>` scoop angle,
`u`/`d` jog the winch up/down for 200 ms, `g` start, `x` stop. Count the `d` presses from the top to the
sand (× 200 ms = `lowerMs`), find the angles with `s`, write them into `CraneConfig`, then flash again.
If the scoop ends a cycle lower or higher than it started, adjust `raiseMs`.

> ⚠️ **Materials:** under the rules (Art. 5, 7.a), on the day we may only use the **materials provided by the
> organizers**. The hardware below is the practice kit; adapt `pins.h` and `diagram.json` to the kit we receive.

## Setup (Linux / macOS)

```bash
cd team-design
python3 -m venv .venv
source .venv/bin/activate
pip install platformio
```

- **Linux:** to upload without `sudo`, install the
  [PlatformIO udev rules](https://docs.platformio.org/en/latest/core/installation/udev-rules.html)
  and add your user to the `dialout` group (`sudo usermod -aG dialout $USER`, then log out and back in).
- **macOS:** Uno clones with a CH340 chip may need the manufacturer's (WCH) driver.
- **Wokwi:** install the [Wokwi CLI](https://docs.wokwi.com/wokwi-ci/getting-started)
  and/or the Wokwi extension for VS Code. Each member creates **their own** (free) token at
  <https://wokwi.com/dashboard/ci> and puts it in a `.env` (never committed):
  ```bash
  export WOKWI_CLI_TOKEN=...
  ```

## Commands

```bash
source .venv/bin/activate
pio test -e native            # logic tests on the PC (fast, no board)
pio run -e uno                # build
pio run -e uno -t upload      # flash the board
pio device monitor            # watch the Serial output (9600 baud)
wokwi-cli --scenario test/wokwi/crane_cycle.yaml --timeout 20000  # simulation test
```

## Architecture

The code is split into two layers, so that most of it can be tested without hardware:

```text
src/main.cpp            hardware layer: button, Serial commands, writes the winch pins and the servo
   │  uses
   ▼
lib/Control/            pure logic (no Arduino.h): crane cycle, ramps, commands, H-bridge, debounce
   ▲  tested by
   │
test/test_control/      Unity tests, run on the PC with `pio test -e native`
```

| File | Responsibility |
|------|----------------|
| `src/main.cpp` | `setup()`/`loop()`. Feeds the button and Serial commands to `Crane`, writes its outputs (winch, servo) and prints each phase change; `writeWinch()` turns a speed into the H-bridge pins. |
| `lib/Control/Control.h/.cpp` | `Crane` (cycle state machine, `CraneConfig` = every value to calibrate), `ramp()` (gradual servo moves), `parseCommand()` (Serial commands), `hBridgeChannel()` (signed speed → IN1/IN2/PWM, clamped to ±255), `Debounce` (one press = one event). |
| `include/pins.h` | Pin map. **Single source** that must match `diagram.json` and the wiring. |
| `test/test_control/` | 16 unit tests (crane cycle, winch off while the scoop turns, ramps, commands, H-bridge, debounce). |
| `test/wokwi/crane_cycle.yaml` | Simulation integration test: one full timed cycle, then stop; checks Serial and the pins. |
| `diagram.json`, `wokwi.toml` | Circuit and configuration for the Wokwi simulator. |
| `platformio.ini` | `uno` (firmware) and `native` (PC tests) environments. |

### Adapting to the day's brief

1. New logic (sensors, states, timings) → pure functions in `lib/Control/` **with tests**.
2. `main.cpp` only wires that logic to the pins.
3. New pins → `include/pins.h` **and** `diagram.json`.
4. `pio test -e native` → `pio run -e uno` → simulation → real board.

### Design decisions

- **No PWM on the winch:** the kit's L298N keeps its ENA/ENB jumpers on, so the motor runs at full speed and
  only IN1..IN4 switch it. Both channels are driven alike, so the winch works on either output.
- **`KEY=value` Serial output** (e.g. `PHASE=LOWER WINCH=-200 SCOOP=180 CYCLES=0`): human-readable,
  checkable by Wokwi (`wait-serial`) and easy for an LLM to interpret while debugging. Changing the format means
  updating `test/wokwi/crane_cycle.yaml`.
- **Timed winch, no sensors** (team decision, fewest parts): the winch can drift a little every cycle
  (load, battery). Watch the first cycles and correct `raiseMs`; `u`/`d` re-place the scoop between runs.
- **Winch off while the servo turns:** the scoop hangs on the string, so it only turns when it is still.
- **Software debounce (30 ms)** with the internal pull-up: no resistor needed on the button.
- **Speed 0 = coast** (IN1=IN2=LOW), never IN1=IN2=HIGH.

## Real wiring

Competition kit (160), as wired on its board:

| Arduino Uno | Connect to                      | Note                                  |
|-------------|---------------------------------|---------------------------------------|
| D4 / D5     | L298N IN1 / IN2 (channel A)     | ENA jumper on: no PWM, full speed     |
| D2 / D3     | L298N IN3 / IN4 (channel B)     | ENB jumper on                         |
| D6          | Scoop servo — signal            | cable runs up the string              |
| D12         | START button (other side to GND) | optional; Serial `g`/`x` do the same |
| GND         | L298N GND + servo GND           | **common ground required**            |
| —           | Winch motor (silver drum) on OUT1/OUT2 or OUT3/OUT4 | the firmware drives both channels the same way |

**Power:** do not power the DC motor or the servo from the Arduino's 5V: a stalled servo resets the board.
The L298N's on-board regulator gives 5V when its 5V jumper is on and its input is ≤ 12 V.

## Simulation (Wokwi)

Wokwi has no L298N or DC motor, so in `diagram.json` the winch signals IN1..IN4
show up as LEDs (IN1/IN3 = up, IN2/IN4 = down). The servo and the START
button are real.
Open it in VS Code with the Wokwi extension after `pio run -e uno`.
