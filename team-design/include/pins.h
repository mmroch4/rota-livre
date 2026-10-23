#pragma once

// Arduino Uno pin map. Must match diagram.json and the real wiring.
//
// Note: the Servo library uses Timer1 and disables analogWrite on pins 9 and 10,
// so the motor PWM (ENA/ENB) lives on pins 5 and 6 (Timer0).

// Button: wired to GND, uses the internal pull-up (pressed = LOW)
constexpr uint8_t PIN_BUTTON = 2;

// 180° servo (signal)
constexpr uint8_t PIN_SERVO = 9;

// H-bridge (L298N) — motor A (left)
constexpr uint8_t PIN_ENA = 5;  // PWM
constexpr uint8_t PIN_IN1 = 7;
constexpr uint8_t PIN_IN2 = 8;

// H-bridge (L298N) — motor B (right)
constexpr uint8_t PIN_ENB = 6;  // PWM
constexpr uint8_t PIN_IN3 = 10;
constexpr uint8_t PIN_IN4 = 11;
