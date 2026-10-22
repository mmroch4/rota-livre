#include <Arduino.h>
#include <Servo.h>

#include "Control.h"
#include "pins.h"

Servo servo;
Debounce button;
Mode mode = Mode::Stopped;

void writeMotor(uint8_t pinEn, uint8_t pinInA, uint8_t pinInB, int16_t speed) {
  HBridgeChannel channel = hBridgeChannel(speed);
  digitalWrite(pinInA, channel.in1 ? HIGH : LOW);
  digitalWrite(pinInB, channel.in2 ? HIGH : LOW);
  analogWrite(pinEn, channel.pwm);
}

void applyMode(Mode next) {
  Outputs out = outputsFor(next);
  writeMotor(PIN_ENA, PIN_IN1, PIN_IN2, out.motorA);
  writeMotor(PIN_ENB, PIN_IN3, PIN_IN4, out.motorB);
  servo.write(out.servoAngle);

  // Formato fixo KEY=value: fácil de ler por humanos, testes Wokwi e LLMs
  Serial.print(F("MODE="));
  Serial.print(modeName(next));
  Serial.print(F(" A="));
  Serial.print(out.motorA);
  Serial.print(F(" B="));
  Serial.print(out.motorB);
  Serial.print(F(" SERVO="));
  Serial.println(out.servoAngle);
}

void setup() {
  Serial.begin(9600);

  pinMode(PIN_BUTTON, INPUT_PULLUP);
  const uint8_t outputPins[] = {PIN_ENA, PIN_IN1, PIN_IN2, PIN_ENB, PIN_IN3, PIN_IN4};
  for (uint8_t pin : outputPins) {
    pinMode(pin, OUTPUT);
  }
  servo.attach(PIN_SERVO);

  applyMode(mode);
  Serial.println(F("System ready"));
}

void loop() {
  bool pressed = digitalRead(PIN_BUTTON) == LOW;
  if (button.update(pressed, millis())) {
    mode = nextMode(mode);
    applyMode(mode);
  }
}
