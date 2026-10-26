#include "Control.h"

Crane::Crane(const CraneConfig& config) : cfg_(config), out_{0, config.scoopRest} {}

void Crane::start(uint32_t nowMs) {
  if (phase_ == Phase::Idle) enter(Phase::Lower, nowMs);
}

void Crane::stop() {
  phase_ = Phase::Idle;
  out_.winch = 0;
}

void Crane::setScoop(uint8_t angle) {
  if (phase_ == Phase::Idle) out_.scoop = angle > 180 ? 180 : angle;
}

void Crane::enter(Phase next, uint32_t nowMs) {
  phase_ = next;
  phaseStart_ = nowMs;
}

bool Crane::update(uint32_t nowMs) {
  const Phase before = phase_;
  const uint32_t t = nowMs - phaseStart_;

  switch (phase_) {
    case Phase::Idle:   break;
    case Phase::Lower:  if (t >= cfg_.lowerMs) enter(Phase::Dig, nowMs); break;
    case Phase::Dig:    if (t >= cfg_.digMs) enter(Phase::Raise, nowMs); break;
    case Phase::Raise:  if (t >= cfg_.raiseMs) enter(Phase::Settle, nowMs); break;
    case Phase::Settle: if (t >= cfg_.settleMs) enter(Phase::Dump, nowMs); break;
    case Phase::Dump:   if (t >= cfg_.dumpMs) enter(Phase::Return, nowMs); break;
    case Phase::Return:
      if (t >= cfg_.returnMs) {
        cycles_++;
        enter(Phase::Lower, nowMs);
      }
      break;
  }

  // Outputs of the (possibly new) phase.
  const uint32_t e = nowMs - phaseStart_;
  const int16_t up = cfg_.winchSpeed;
  switch (phase_) {
    case Phase::Idle:   out_.winch = 0; break;
    case Phase::Lower:  out_ = {static_cast<int16_t>(-up), cfg_.scoopRest}; break;
    case Phase::Dig:    out_ = {0, ramp(cfg_.scoopRest, cfg_.scoopFull, e, cfg_.digMs)}; break;
    case Phase::Raise:  out_ = {up, cfg_.scoopFull}; break;
    case Phase::Settle: out_ = {0, cfg_.scoopFull}; break;
    case Phase::Dump:   out_ = {0, cfg_.scoopDump}; break;
    case Phase::Return: out_ = {0, ramp(cfg_.scoopDump, cfg_.scoopRest, e, cfg_.returnMs)}; break;
  }
  return phase_ != before;
}

const char* phaseName(Phase phase) {
  switch (phase) {
    case Phase::Idle:   return "IDLE";
    case Phase::Lower:  return "LOWER";
    case Phase::Dig:    return "DIG";
    case Phase::Raise:  return "RAISE";
    case Phase::Settle: return "SETTLE";
    case Phase::Dump:   return "DUMP";
    case Phase::Return: return "RETURN";
  }
  return "?";
}

uint8_t ramp(uint8_t from, uint8_t to, uint32_t ms, uint32_t durationMs) {
  if (durationMs == 0 || ms >= durationMs) return to;
  const int32_t delta = static_cast<int32_t>(to) - from;
  return static_cast<uint8_t>(from + delta * static_cast<int32_t>(ms) / static_cast<int32_t>(durationMs));
}

HBridgeChannel hBridgeChannel(int16_t speed) {
  if (speed > 255) speed = 255;
  if (speed < -255) speed = -255;

  if (speed > 0) return {true, false, static_cast<uint8_t>(speed)};
  if (speed < 0) return {false, true, static_cast<uint8_t>(-speed)};
  return {false, false, 0};
}

namespace {
bool isBlank(const char* p) {
  for (; *p; ++p) {
    if (*p != ' ' && *p != '\r' && *p != '\n' && *p != '\t') return false;
  }
  return true;
}
}  // namespace

Command parseCommand(const char* line) {
  while (*line == ' ' || *line == '\t') ++line;
  const char c = *line++;
  switch (c) {
    case 'g': return {isBlank(line) ? CommandType::Start : CommandType::None, 0};
    case 'x': return {isBlank(line) ? CommandType::Stop : CommandType::None, 0};
    case 'u': return {isBlank(line) ? CommandType::JogUp : CommandType::None, 0};
    case 'd': return {isBlank(line) ? CommandType::JogDown : CommandType::None, 0};
    case 's': {
      uint16_t value = 0;
      uint8_t digits = 0;
      for (; *line >= '0' && *line <= '9' && digits < 4; ++line, ++digits) value = value * 10 + (*line - '0');
      if (digits == 0 || value > 180 || !isBlank(line)) return {CommandType::None, 0};
      return {CommandType::Scoop, static_cast<uint8_t>(value)};
    }
  }
  return {CommandType::None, 0};
}

bool Debounce::update(bool pressedReading, uint32_t nowMs) {
  if (pressedReading != lastReading_) {
    lastReading_ = pressedReading;
    changedAt_ = nowMs;
  }

  if (nowMs - changedAt_ >= intervalMs_ && stableState_ != lastReading_) {
    stableState_ = lastReading_;
    return stableState_;  // only the transition to "pressed" counts
  }
  return false;
}
