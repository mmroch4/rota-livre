#include "Control.h"

namespace {
constexpr int16_t SPEED = 200;
constexpr uint8_t SERVO_CENTER = 90;
constexpr uint8_t SERVO_ROTATE = 180;
constexpr uint8_t SERVO_REST = 0;
}  // namespace

Mode nextMode(Mode mode) {
  switch (mode) {
    case Mode::Stopped:  return Mode::Forward;
    case Mode::Forward:  return Mode::Backward;
    case Mode::Backward: return Mode::Rotate;
    case Mode::Rotate:   return Mode::Stopped;
  }
  return Mode::Stopped;
}

Outputs outputsFor(Mode mode) {
  switch (mode) {
    case Mode::Stopped:  return {0, 0, SERVO_REST};
    case Mode::Forward:  return {SPEED, SPEED, SERVO_CENTER};
    case Mode::Backward: return {-SPEED, -SPEED, SERVO_CENTER};
    case Mode::Rotate:   return {SPEED, -SPEED, SERVO_ROTATE};
  }
  return {0, 0, SERVO_REST};
}

const char* modeName(Mode mode) {
  switch (mode) {
    case Mode::Stopped:  return "STOPPED";
    case Mode::Forward:  return "FORWARD";
    case Mode::Backward: return "BACKWARD";
    case Mode::Rotate:   return "ROTATE";
  }
  return "?";
}

HBridgeChannel hBridgeChannel(int16_t speed) {
  if (speed > 255) speed = 255;
  if (speed < -255) speed = -255;

  if (speed > 0) return {true, false, static_cast<uint8_t>(speed)};
  if (speed < 0) return {false, true, static_cast<uint8_t>(-speed)};
  return {false, false, 0};
}

bool Debounce::update(bool pressedReading, uint32_t nowMs) {
  if (pressedReading != lastReading_) {
    lastReading_ = pressedReading;
    changedAt_ = nowMs;
  }

  if (nowMs - changedAt_ >= intervalMs_ && stableState_ != lastReading_) {
    stableState_ = lastReading_;
    return stableState_;  // só conta a transição para "premido"
  }
  return false;
}
