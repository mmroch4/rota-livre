#pragma once

// Pure robot logic, with no Arduino dependencies, so it can be tested on the PC
// with `pio test -e native`.
//
// The robot is a scoop on a string: a DC-motor winch on the ground pulls a string over two
// pulleys at the top of a tower and down to a hanging servo with a cup. The servo turns the
// cup through the sand in A, the winch lifts it and the servo turns it over the mouth of the
// chute to B. Travel is timed (no sensors): put the scoop at the top before starting.

#include <stdint.h>

enum class Phase : uint8_t { Idle, Lower, Dig, Raise, Settle, Dump, Return };

// Everything to calibrate on the real build. Servo angles in degrees 0..180,
// times in ms, winch speed 0..255 (positive = up; swap the motor wires if it runs backwards).
struct CraneConfig {
  int16_t winchSpeed = 200;
  uint16_t lowerMs = 2500;   // from the top down into the sand
  uint16_t digMs = 800;      // cup turns rest -> full through the sand
  uint16_t raiseMs = 2800;   // back to the top (slower than going down: it carries the sand)
  uint16_t settleMs = 800;   // let the hanging scoop stop swinging before dumping
  uint16_t dumpMs = 1000;
  uint16_t returnMs = 600;   // cup turns back to rest, still at the top
  uint8_t scoopRest = 180;   // opening facing right, away from the chute
  uint8_t scoopFull = 100;   // opening up
  uint8_t scoopDump = 0;     // opening facing left, over the chute
};

struct CraneOutputs {
  int16_t winch;  // -255..255, positive = up
  uint8_t scoop;
};

class Crane {
 public:
  explicit Crane(const CraneConfig& config = CraneConfig());

  void start(uint32_t nowMs);  // from Idle, with the scoop at the top: cycle until stopped
  void stop();                 // winch off at once, the servo holds where it is

  // Advances the cycle. Returns true when the phase changed.
  bool update(uint32_t nowMs);

  // Manual calibration, only while Idle.
  void setScoop(uint8_t angle);

  Phase phase() const { return phase_; }
  const CraneOutputs& outputs() const { return out_; }
  uint16_t cycles() const { return cycles_; }

 private:
  void enter(Phase next, uint32_t nowMs);

  CraneConfig cfg_;
  Phase phase_ = Phase::Idle;
  uint32_t phaseStart_ = 0;
  CraneOutputs out_;
  uint16_t cycles_ = 0;
};

const char* phaseName(Phase phase);

// Angle `ms` into a linear move from `from` to `to` lasting `durationMs` (then stays at `to`).
uint8_t ramp(uint8_t from, uint8_t to, uint32_t ms, uint32_t durationMs);

// Signals of one H-bridge channel (IN1/IN2 set the direction, pwm the speed).
struct HBridgeChannel {
  bool in1;
  bool in2;
  uint8_t pwm;
};

// Converts a signed speed into H-bridge signals. Speed 0 coasts (free-wheel).
HBridgeChannel hBridgeChannel(int16_t speed);

// Serial commands, one per line:
//   g = start   x = stop   u / d = jog the winch up / down   s<deg> = scoop angle (e.g. "s100")
enum class CommandType : uint8_t { None, Start, Stop, JogUp, JogDown, Scoop };
struct Command {
  CommandType type;
  uint8_t angle;
};
Command parseCommand(const char* line);

// Debounce for an active-LOW button. update() returns true exactly once per
// press, when the reading stays stable for `intervalMs`.
class Debounce {
 public:
  explicit Debounce(uint32_t intervalMs = 30) : intervalMs_(intervalMs) {}
  bool update(bool pressedReading, uint32_t nowMs);

 private:
  uint32_t intervalMs_;
  bool lastReading_ = false;
  bool stableState_ = false;
  uint32_t changedAt_ = 0;
};
