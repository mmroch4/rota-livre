#include <Arduino.h>
#include <Servo.h>

#include "Control.h"
#include "pins.h"

constexpr uint16_t JOG_MS = 200;

Servo scoopServo;
Crane crane;
Debounce button;

char line[16];
uint8_t lineLength = 0;
uint32_t jogUntil = 0;
int16_t jogSpeed = 0;
bool showState = true;  // print after the next crane.update(), so the line shows fresh outputs

// Both channels get the same direction; speed is full (ENA/ENB jumpers on).
void writeWinch(int16_t speed) {
  HBridgeChannel channel = hBridgeChannel(speed);
  digitalWrite(PIN_IN1, channel.in1 ? HIGH : LOW);
  digitalWrite(PIN_IN2, channel.in2 ? HIGH : LOW);
  digitalWrite(PIN_IN3, channel.in1 ? HIGH : LOW);
  digitalWrite(PIN_IN4, channel.in2 ? HIGH : LOW);
}

// Fixed KEY=value format: easy to read for humans, Wokwi tests and LLMs
void printState() {
  const CraneOutputs& out = crane.outputs();
  Serial.print(F("PHASE="));
  Serial.print(phaseName(crane.phase()));
  Serial.print(F(" WINCH="));
  Serial.print(out.winch);
  Serial.print(F(" SCOOP="));
  Serial.print(out.scoop);
  Serial.print(F(" CYCLES="));
  Serial.println(crane.cycles());
}

void handleCommand(const Command& cmd, uint32_t now) {
  const bool manual = crane.phase() == Phase::Idle;
  switch (cmd.type) {
    case CommandType::Start: crane.start(now); break;
    case CommandType::Stop: crane.stop(); break;
    case CommandType::JogUp:
    case CommandType::JogDown:
      if (manual) {
        jogSpeed = cmd.type == CommandType::JogUp ? CraneConfig().winchSpeed : -CraneConfig().winchSpeed;
        jogUntil = now + JOG_MS;
        Serial.println(jogSpeed > 0 ? F("JOG=UP") : F("JOG=DOWN"));
      }
      return;
    case CommandType::Scoop: crane.setScoop(cmd.angle); break;
    case CommandType::None:
      Serial.println(F("ERROR=unknown command (g x u d s<deg>)"));
      return;
  }
  showState = true;
}

void readSerial(uint32_t now) {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (lineLength == 0) continue;
      line[lineLength] = '\0';
      lineLength = 0;
      handleCommand(parseCommand(line), now);
    } else if (lineLength < sizeof(line) - 1) {
      line[lineLength++] = c;
    }
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(PIN_BUTTON, INPUT_PULLUP);
  const uint8_t outputPins[] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4};
  for (uint8_t pin : outputPins) {
    pinMode(pin, OUTPUT);
  }
  writeWinch(0);
  scoopServo.attach(PIN_SCOOP_SERVO);

  crane.update(millis());
  printState();
  showState = false;
  Serial.println(F("System ready"));
}

void loop() {
  const uint32_t now = millis();
  if (button.update(digitalRead(PIN_BUTTON) == LOW, now)) {
    if (crane.phase() == Phase::Idle) {
      crane.start(now);
    } else {
      crane.stop();
    }
    showState = true;
  }
  readSerial(now);

  if (crane.update(now) || showState) {
    printState();
    showState = false;
  }

  const CraneOutputs& out = crane.outputs();
  const bool jogging = static_cast<int32_t>(jogUntil - now) > 0;
  writeWinch(jogging ? jogSpeed : out.winch);
  scoopServo.write(out.scoop);
}
