#include <unity.h>

#include "Control.h"

void setUp() {}
void tearDown() {}

namespace {
const CraneConfig cfg;
}  // namespace

void test_crane_starts_idle_with_winch_off() {
  Crane c(cfg);
  c.update(0);
  TEST_ASSERT_EQUAL(Phase::Idle, c.phase());
  TEST_ASSERT_EQUAL(0, c.outputs().winch);
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopRest, c.outputs().scoop);
}

void test_start_lowers_with_scoop_at_rest() {
  Crane c(cfg);
  c.start(0);
  c.update(10);
  TEST_ASSERT_EQUAL(Phase::Lower, c.phase());
  TEST_ASSERT_TRUE(c.outputs().winch < 0);
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopRest, c.outputs().scoop);
}

void test_full_cycle_order_and_count() {
  Crane c(cfg);
  c.start(0);
  uint32_t t = cfg.lowerMs;
  c.update(t);
  TEST_ASSERT_EQUAL(Phase::Dig, c.phase());
  TEST_ASSERT_EQUAL(0, c.outputs().winch);

  t += cfg.digMs;
  c.update(t);
  TEST_ASSERT_EQUAL(Phase::Raise, c.phase());
  TEST_ASSERT_TRUE(c.outputs().winch > 0);
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopFull, c.outputs().scoop);

  t += cfg.raiseMs;
  c.update(t);
  TEST_ASSERT_EQUAL(Phase::Settle, c.phase());
  TEST_ASSERT_EQUAL(0, c.outputs().winch);

  t += cfg.settleMs;
  c.update(t);
  TEST_ASSERT_EQUAL(Phase::Dump, c.phase());
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopDump, c.outputs().scoop);

  t += cfg.dumpMs;
  c.update(t);
  TEST_ASSERT_EQUAL(Phase::Return, c.phase());
  TEST_ASSERT_EQUAL(0, c.cycles());

  t += cfg.returnMs;
  c.update(t);
  TEST_ASSERT_EQUAL(Phase::Lower, c.phase());
  TEST_ASSERT_EQUAL(1, c.cycles());
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopRest, c.outputs().scoop);
}

void test_winch_off_whenever_the_scoop_turns() {
  Crane c(cfg);
  c.start(0);
  uint32_t t = 0;
  for (int i = 0; i < 2000; i++, t += 10) {
    c.update(t);
    Phase p = c.phase();
    if (p == Phase::Dig || p == Phase::Dump || p == Phase::Return) TEST_ASSERT_EQUAL(0, c.outputs().winch);
  }
}

void test_dig_sweeps_scoop_from_rest_to_full() {
  Crane c(cfg);
  c.start(0);
  c.update(cfg.lowerMs);
  c.update(cfg.lowerMs + cfg.digMs / 2);
  uint8_t mid = c.outputs().scoop;
  TEST_ASSERT_TRUE(mid < cfg.scoopRest && mid > cfg.scoopFull);
}

void test_stop_turns_winch_off_and_keeps_servo() {
  Crane c(cfg);
  c.start(0);
  c.update(100);
  c.stop();
  c.update(200);
  TEST_ASSERT_EQUAL(Phase::Idle, c.phase());
  TEST_ASSERT_EQUAL(0, c.outputs().winch);
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopRest, c.outputs().scoop);
}

void test_manual_angle_only_when_idle() {
  Crane c(cfg);
  c.setScoop(42);
  TEST_ASSERT_EQUAL_UINT8(42, c.outputs().scoop);
  c.setScoop(250);
  TEST_ASSERT_EQUAL_UINT8(180, c.outputs().scoop);
  c.start(0);
  c.setScoop(10);
  c.update(1);
  TEST_ASSERT_EQUAL_UINT8(cfg.scoopRest, c.outputs().scoop);
}

void test_ramp_endpoints_and_direction() {
  TEST_ASSERT_EQUAL_UINT8(119, ramp(119, 61, 0, 1500));
  TEST_ASSERT_EQUAL_UINT8(90, ramp(119, 61, 750, 1500));
  TEST_ASSERT_EQUAL_UINT8(61, ramp(119, 61, 1500, 1500));
  TEST_ASSERT_EQUAL_UINT8(61, ramp(119, 61, 9000, 1500));
  TEST_ASSERT_EQUAL_UINT8(100, ramp(0, 100, 5, 0));
}

void test_parse_commands() {
  TEST_ASSERT_EQUAL(CommandType::Start, parseCommand("g").type);
  TEST_ASSERT_EQUAL(CommandType::Stop, parseCommand(" x\r").type);
  TEST_ASSERT_EQUAL(CommandType::JogUp, parseCommand("u").type);
  TEST_ASSERT_EQUAL(CommandType::JogDown, parseCommand("d").type);
  Command s = parseCommand("s100");
  TEST_ASSERT_EQUAL(CommandType::Scoop, s.type);
  TEST_ASSERT_EQUAL_UINT8(100, s.angle);
}

void test_parse_rejects_bad_input() {
  TEST_ASSERT_EQUAL(CommandType::None, parseCommand("").type);
  TEST_ASSERT_EQUAL(CommandType::None, parseCommand("s").type);
  TEST_ASSERT_EQUAL(CommandType::None, parseCommand("s181").type);
  TEST_ASSERT_EQUAL(CommandType::None, parseCommand("s9x").type);
  TEST_ASSERT_EQUAL(CommandType::None, parseCommand("a61").type);
  TEST_ASSERT_EQUAL(CommandType::None, parseCommand("go").type);
}

void test_h_bridge_forward() {
  HBridgeChannel c = hBridgeChannel(200);
  TEST_ASSERT_TRUE(c.in1);
  TEST_ASSERT_FALSE(c.in2);
  TEST_ASSERT_EQUAL_UINT8(200, c.pwm);
}

void test_h_bridge_backward() {
  HBridgeChannel c = hBridgeChannel(-120);
  TEST_ASSERT_FALSE(c.in1);
  TEST_ASSERT_TRUE(c.in2);
  TEST_ASSERT_EQUAL_UINT8(120, c.pwm);
}

void test_h_bridge_stopped_never_sets_in1_and_in2() {
  HBridgeChannel c = hBridgeChannel(0);
  TEST_ASSERT_FALSE(c.in1 && c.in2);
  TEST_ASSERT_EQUAL_UINT8(0, c.pwm);
}

void test_h_bridge_clamps_speed() {
  TEST_ASSERT_EQUAL_UINT8(255, hBridgeChannel(1000).pwm);
  TEST_ASSERT_EQUAL_UINT8(255, hBridgeChannel(-1000).pwm);
}

void test_debounce_ignores_noise() {
  Debounce d(30);
  TEST_ASSERT_FALSE(d.update(true, 0));
  TEST_ASSERT_FALSE(d.update(false, 5));   // bounce
  TEST_ASSERT_FALSE(d.update(true, 10));
  TEST_ASSERT_FALSE(d.update(true, 30));   // only 20 ms stable
  TEST_ASSERT_TRUE(d.update(true, 40));    // 30 ms stable -> press
  TEST_ASSERT_FALSE(d.update(true, 100));  // holding it down does not repeat
}

void test_debounce_counts_each_press_once() {
  Debounce d(30);
  int presses = 0;
  // two 100 ms presses separated by 100 ms released
  for (uint32_t t = 0; t < 400; t += 5) {
    bool pressed = (t < 100) || (t >= 200 && t < 300);
    if (d.update(pressed, t)) presses++;
  }
  TEST_ASSERT_EQUAL(2, presses);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_crane_starts_idle_with_winch_off);
  RUN_TEST(test_start_lowers_with_scoop_at_rest);
  RUN_TEST(test_full_cycle_order_and_count);
  RUN_TEST(test_winch_off_whenever_the_scoop_turns);
  RUN_TEST(test_dig_sweeps_scoop_from_rest_to_full);
  RUN_TEST(test_stop_turns_winch_off_and_keeps_servo);
  RUN_TEST(test_manual_angle_only_when_idle);
  RUN_TEST(test_ramp_endpoints_and_direction);
  RUN_TEST(test_parse_commands);
  RUN_TEST(test_parse_rejects_bad_input);
  RUN_TEST(test_h_bridge_forward);
  RUN_TEST(test_h_bridge_backward);
  RUN_TEST(test_h_bridge_stopped_never_sets_in1_and_in2);
  RUN_TEST(test_h_bridge_clamps_speed);
  RUN_TEST(test_debounce_ignores_noise);
  RUN_TEST(test_debounce_counts_each_press_once);
  return UNITY_END();
}
