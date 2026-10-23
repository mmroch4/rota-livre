# Team Design — Arduino Uno robot

Prototype for the SciTeCh '26 **Team Design** challenge. Right now it is a **practice skeleton**:
the real brief is only revealed at the start of the event, and this project is here so we arrive with the toolchain,
tests and simulation already working.

**Current behaviour:** each button press advances the mode, in a cycle
`STOPPED → FORWARD → BACKWARD → ROTATE → STOPPED`.

| Mode | Motor A | Motor B | Servo |
|------|--------:|--------:|------:|
| `STOPPED`  | 0    | 0    | 0°   |
| `FORWARD`  | 200  | 200  | 90°  |
| `BACKWARD` | -200 | -200 | 90°  |
| `ROTATE`   | 200  | -200 | 180° |

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
wokwi-cli --scenario test/wokwi/mode_cycle.yaml --timeout 10000   # simulation test
```

## Architecture

The code is split into two layers, so that most of it can be tested without hardware:

```text
src/main.cpp            hardware layer: reads the button, writes the pins, Servo, Serial
   │  uses
   ▼
lib/Control/            pure logic (no Arduino.h): modes, outputs, H-bridge, debounce
   ▲  tested by
   │
test/test_control/      Unity tests, run on the PC with `pio test -e native`
```

| File | Responsibility |
|------|----------------|
| `src/main.cpp` | `setup()`/`loop()`. `applyMode()` applies a mode's outputs and prints them to Serial; `writeMotor()` turns a speed into the pins of one H-bridge channel. |
| `lib/Control/Control.h/.cpp` | `Mode` and `nextMode()` (state machine), `outputsFor()` (mode → speeds and angle), `hBridgeChannel()` (signed speed → IN1/IN2/PWM, clamped to ±255), `Debounce` (one press = one event). |
| `include/pins.h` | Pin map. **Single source** that must match `diagram.json` and the wiring. |
| `test/test_control/` | 10 unit tests (mode cycle, H-bridge, debounce with bounces). |
| `test/wokwi/mode_cycle.yaml` | Simulation integration test: presses the button and checks Serial and the pins. |
| `diagram.json`, `wokwi.toml` | Circuit and configuration for the Wokwi simulator. |
| `platformio.ini` | `uno` (firmware) and `native` (PC tests) environments. |

### Adapting to the day's brief

1. New logic (sensors, states, timings) → pure functions in `lib/Control/` **with tests**.
2. `main.cpp` only wires that logic to the pins.
3. New pins → `include/pins.h` **and** `diagram.json`.
4. `pio test -e native` → `pio run -e uno` → simulation → real board.

### Design decisions

- **PWM on pins 5/6, not 9/10:** the `Servo` library uses Timer1 and disables `analogWrite` on pins 9 and 10.
- **`KEY=value` Serial output** (e.g. `MODE=FORWARD A=200 B=200 SERVO=90`): human-readable,
  checkable by Wokwi (`wait-serial`) and easy for an LLM to interpret while debugging. Changing the format means
  updating `test/wokwi/mode_cycle.yaml`.
- **Software debounce (30 ms)** with the internal pull-up: no resistor needed on the button.
- **Speed 0 = coast** (IN1=IN2=LOW), never IN1=IN2=HIGH.

## Real wiring

| Arduino Uno | Connect to                      | Note                                  |
|-------------|---------------------------------|---------------------------------------|
| D2          | Button (other side to GND)      | internal pull-up, no resistor         |
| D9          | Servo — signal (orange)         |                                       |
| D5 (PWM)    | L298N ENA                       | remove the ENA jumper                 |
| D7 / D8     | L298N IN1 / IN2                 | motor A (left)                        |
| D6 (PWM)    | L298N ENB                       | remove the ENB jumper                 |
| D10 / D11   | L298N IN3 / IN4                 | motor B (right)                       |
| GND         | L298N GND + battery GND         | **common ground required**            |
| —           | L298N OUT1/OUT2 → motor A; OUT3/OUT4 → motor B |                        |
| —           | L298N 12V ← motor battery (7–12 V)             |                        |

**Power:** do not power the DC motors from the Arduino's 5V. The servo can use the Arduino's 5V
for testing, but under load it should have its own 5V supply (with common GND).

## Simulation (Wokwi)

Wokwi has no L298N or DC motor, so in `diagram.json` the ENA/IN1..IN4/ENB signals
show up as LEDs (ENA/ENB change brightness with the PWM). The servo and the button are real.
Open it in VS Code with the Wokwi extension after `pio run -e uno`.
