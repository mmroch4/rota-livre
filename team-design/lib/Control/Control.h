#pragma once

// Pure robot logic, with no Arduino dependencies, so it can be tested on the PC
// with `pio test -e native`.

#include <stdint.h>

enum class Mode : uint8_t { Stopped, Forward, Backward, Rotate };

// Desired output state for a mode.
// Speeds from -255 (full backward) to 255 (full forward); servo in degrees 0..180.
struct Outputs {
  int16_t motorA;
  int16_t motorB;
  uint8_t servoAngle;
};

// Signals of one H-bridge channel (IN1/IN2 set the direction, pwm the speed).
struct HBridgeChannel {
  bool in1;
  bool in2;
  uint8_t pwm;
};

Mode nextMode(Mode mode);
Outputs outputsFor(Mode mode);
const char* modeName(Mode mode);

// Converts a signed speed into H-bridge signals. Speed 0 coasts (free-wheel).
HBridgeChannel hBridgeChannel(int16_t speed);

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
