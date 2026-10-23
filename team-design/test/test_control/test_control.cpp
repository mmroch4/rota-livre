#include <unity.h>

#include "Control.h"

void setUp() {}
void tearDown() {}

void test_mode_cycle_wraps_around() {
  Mode m = Mode::Stopped;
  m = nextMode(m);
  TEST_ASSERT_EQUAL(Mode::Forward, m);
  m = nextMode(m);
  TEST_ASSERT_EQUAL(Mode::Backward, m);
  m = nextMode(m);
  TEST_ASSERT_EQUAL(Mode::Rotate, m);
  m = nextMode(m);
  TEST_ASSERT_EQUAL(Mode::Stopped, m);
}

void test_stopped_turns_motors_off() {
  Outputs out = outputsFor(Mode::Stopped);
  TEST_ASSERT_EQUAL(0, out.motorA);
  TEST_ASSERT_EQUAL(0, out.motorB);
}

void test_rotate_drives_motors_in_opposite_directions() {
  Outputs out = outputsFor(Mode::Rotate);
  TEST_ASSERT_TRUE(out.motorA > 0);
  TEST_ASSERT_TRUE(out.motorB < 0);
}

void test_servo_within_0_to_180() {
  const Mode modes[] = {Mode::Stopped, Mode::Forward, Mode::Backward, Mode::Rotate};
  for (Mode m : modes) {
    TEST_ASSERT_LESS_OR_EQUAL(180, outputsFor(m).servoAngle);
  }
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
  RUN_TEST(test_mode_cycle_wraps_around);
  RUN_TEST(test_stopped_turns_motors_off);
  RUN_TEST(test_rotate_drives_motors_in_opposite_directions);
  RUN_TEST(test_servo_within_0_to_180);
  RUN_TEST(test_h_bridge_forward);
  RUN_TEST(test_h_bridge_backward);
  RUN_TEST(test_h_bridge_stopped_never_sets_in1_and_in2);
  RUN_TEST(test_h_bridge_clamps_speed);
  RUN_TEST(test_debounce_ignores_noise);
  RUN_TEST(test_debounce_counts_each_press_once);
  return UNITY_END();
}
