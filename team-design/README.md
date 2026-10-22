# Team Design — robô Arduino Uno

Protótipo para a modalidade **Team Design** do SciTeCh '26. Neste momento é um **esqueleto de treino**:
o guião real só é revelado no início da prova, e este projeto serve para chegarmos lá com o toolchain,
os testes e a simulação já a funcionar.

**Comportamento atual:** cada pressão do botão avança o modo, num ciclo
`STOPPED → FORWARD → BACKWARD → ROTATE → STOPPED`.

| Modo | Motor A | Motor B | Servo |
|------|--------:|--------:|------:|
| `STOPPED`  | 0    | 0    | 0°   |
| `FORWARD`  | 200  | 200  | 90°  |
| `BACKWARD` | -200 | -200 | 90°  |
| `ROTATE`   | 200  | -200 | 180° |

> ⚠️ **Material:** pelo regulamento (Art. 5.º, 7.a), no dia só podemos usar os **materiais fornecidos pela
> organização**. O hardware abaixo é o do treino; adaptar `pins.h` e `diagram.json` ao kit que recebermos.

## Setup (Linux / macOS)

```bash
cd team-design
python3 -m venv .venv
source .venv/bin/activate
pip install platformio
```

- **Linux:** para fazer upload sem `sudo`, instalar as
  [udev rules do PlatformIO](https://docs.platformio.org/en/latest/core/installation/udev-rules.html)
  e adicionar o utilizador ao grupo `dialout` (`sudo usermod -aG dialout $USER`, depois reiniciar a sessão).
- **macOS:** os clones do Uno com chip CH340 podem precisar do driver do fabricante (WCH).
- **Wokwi:** instalar o [Wokwi CLI](https://docs.wokwi.com/wokwi-ci/getting-started)
  e/ou a extensão Wokwi para VS Code. Cada membro cria o **seu** token (grátis) em
  <https://wokwi.com/dashboard/ci> e põe-no num `.env` (nunca em commit):
  ```bash
  export WOKWI_CLI_TOKEN=...
  ```

## Comandos

```bash
source .venv/bin/activate
pio test -e native            # testes da lógica no PC (rápido, sem placa)
pio run -e uno                # compilar
pio run -e uno -t upload      # enviar para a placa
pio device monitor            # ver a saída Serial (9600 baud)
wokwi-cli --scenario test/wokwi/mode_cycle.yaml --timeout 10000   # teste de simulação
```

## Arquitetura

O código está dividido em duas camadas, para que a maior parte possa ser testada sem hardware:

```text
src/main.cpp            camada de hardware: lê o botão, escreve nos pinos, Servo, Serial
   │  usa
   ▼
lib/Control/            lógica pura (sem Arduino.h): modos, saídas, ponte H, debounce
   ▲  testada por
   │
test/test_control/      testes Unity, correm no PC com `pio test -e native`
```

| Ficheiro | Responsabilidade |
|----------|------------------|
| `src/main.cpp` | `setup()`/`loop()`. `applyMode()` aplica as saídas de um modo e imprime-as na Serial; `writeMotor()` traduz uma velocidade para os pinos de um canal da ponte H. |
| `lib/Control/Control.h/.cpp` | `Mode` e `nextMode()` (máquina de estados), `outputsFor()` (modo → velocidades e ângulo), `hBridgeChannel()` (velocidade com sinal → IN1/IN2/PWM, com saturação a ±255), `Debounce` (uma pressão = um evento). |
| `include/pins.h` | Mapa de pinos. **Fonte única** que tem de coincidir com `diagram.json` e com a montagem. |
| `test/test_control/` | 10 testes unitários (ciclo de modos, ponte H, debounce com ressaltos). |
| `test/wokwi/mode_cycle.yaml` | Teste de integração em simulação: carrega no botão e verifica a Serial e os pinos. |
| `diagram.json`, `wokwi.toml` | Circuito e configuração do simulador Wokwi. |
| `platformio.ini` | Ambientes `uno` (firmware) e `native` (testes no PC). |

### Para adaptar ao guião do dia

1. Nova lógica (sensores, estados, temporizações) → funções puras em `lib/Control/` **com testes**.
2. `main.cpp` só liga essa lógica aos pinos.
3. Pinos novos → `include/pins.h` **e** `diagram.json`.
4. `pio test -e native` → `pio run -e uno` → simulação → placa real.

### Decisões de design

- **PWM nos pinos 5/6, não 9/10:** a biblioteca `Servo` usa o Timer1 e desativa o `analogWrite` nos pinos 9 e 10.
- **Saída Serial `KEY=value`** (ex.: `MODE=FORWARD A=200 B=200 SERVO=90`): legível por humanos,
  verificável pelo Wokwi (`wait-serial`) e fácil de interpretar por um LLM ao depurar. Mudar o formato obriga
  a atualizar `test/wokwi/mode_cycle.yaml`.
- **Debounce em software (30 ms)** com o pull-up interno: não é preciso resistência no botão.
- **Velocidade 0 = roda livre** (IN1=IN2=LOW), nunca IN1=IN2=HIGH.

## Ligações reais

| Arduino Uno | Ligar a                         | Nota                                  |
|-------------|---------------------------------|---------------------------------------|
| D2          | Botão (outro lado ao GND)       | pull-up interno, sem resistência      |
| D9          | Servo — sinal (laranja)         |                                       |
| D5 (PWM)    | L298N ENA                       | retirar o jumper do ENA               |
| D7 / D8     | L298N IN1 / IN2                 | motor A (esquerdo)                    |
| D6 (PWM)    | L298N ENB                       | retirar o jumper do ENB               |
| D10 / D11   | L298N IN3 / IN4                 | motor B (direito)                     |
| GND         | L298N GND + GND da bateria      | **massa comum obrigatória**           |
| —           | L298N OUT1/OUT2 → motor A; OUT3/OUT4 → motor B |                        |
| —           | L298N 12V ← bateria dos motores (7–12 V)       |                        |

**Alimentação:** não alimentar os motores DC pelo 5V do Arduino. O servo pode ir ao 5V do Arduino
para testes, mas com carga deve ter uma fonte de 5V própria (com GND comum).

## Simulação (Wokwi)

O Wokwi não tem L298N nem motor DC, por isso em `diagram.json` os sinais ENA/IN1..IN4/ENB
aparecem como LEDs (ENA/ENB variam de brilho com o PWM). O servo e o botão são reais.
Abrir no VS Code com a extensão Wokwi depois de `pio run -e uno`.
