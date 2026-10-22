#pragma once

// Lógica pura do robô, sem dependências do Arduino, para poder ser testada no PC
// com `pio test -e native`.

#include <stdint.h>

enum class Mode : uint8_t { Stopped, Forward, Backward, Rotate };

// Estado desejado das saídas para um modo.
// Velocidades de -255 (trás, máximo) a 255 (frente, máximo); servo em graus 0..180.
struct Outputs {
  int16_t motorA;
  int16_t motorB;
  uint8_t servoAngle;
};

// Sinais de um canal da ponte H (IN1/IN2 definem o sentido, pwm a velocidade).
struct HBridgeChannel {
  bool in1;
  bool in2;
  uint8_t pwm;
};

Mode nextMode(Mode mode);
Outputs outputsFor(Mode mode);
const char* modeName(Mode mode);

// Converte uma velocidade com sinal nos sinais da ponte H. Velocidade 0 trava em roda livre.
HBridgeChannel hBridgeChannel(int16_t speed);

// Debounce de um botão ativo em LOW. update() devolve true uma única vez por
// cada pressão, quando a leitura se mantém estável durante `intervalMs`.
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
