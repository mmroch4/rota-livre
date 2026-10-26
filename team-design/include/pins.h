#pragma once

// Arduino Uno pin map of the competition kit, read from its wiring. Must match diagram.json.
//
// The L298N keeps its ENA/ENB jumpers on: no PWM pin, the motor always runs at full speed.
// The winch drives both channels the same way, so it works on whichever L298N output the
// motor is connected to (the second DC motor is not used).

// L298N inputs
constexpr uint8_t PIN_IN1 = 4;  // channel A
constexpr uint8_t PIN_IN2 = 5;
constexpr uint8_t PIN_IN3 = 2;  // channel B
constexpr uint8_t PIN_IN4 = 3;

// 180° servo (signal): the kit servo hanging on the string, cup on its horn
constexpr uint8_t PIN_SCOOP_SERVO = 6;

// Optional start/stop button: wired to GND, uses the internal pull-up (pressed = LOW)
constexpr uint8_t PIN_BUTTON = 12;
