#pragma once

// Mapa de pinos do Arduino Uno. Tem de bater certo com diagram.json e com a montagem real.
//
// Nota: a biblioteca Servo usa o Timer1 e desativa o analogWrite nos pinos 9 e 10,
// por isso o PWM dos motores (ENA/ENB) fica nos pinos 5 e 6 (Timer0).

// Botão: liga ao GND, usa o pull-up interno (premido = LOW)
constexpr uint8_t PIN_BUTTON = 2;

// Servo 180º (sinal)
constexpr uint8_t PIN_SERVO = 9;

// Ponte H (L298N) — motor A (esquerdo)
constexpr uint8_t PIN_ENA = 5;  // PWM
constexpr uint8_t PIN_IN1 = 7;
constexpr uint8_t PIN_IN2 = 8;

// Ponte H (L298N) — motor B (direito)
constexpr uint8_t PIN_ENB = 6;  // PWM
constexpr uint8_t PIN_IN3 = 10;
constexpr uint8_t PIN_IN4 = 11;
