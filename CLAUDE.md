# CLAUDE.md

Repositório da equipa O(1/n) (Miguel, Victor, Ben, Pedro) no SciTeCh '26 (BEST Porto, FCUP,
24–25 out 2026). Duas modalidades, cada uma com 6 h de trabalho: `hackathon/` (Coreflux,
**sábado 24**) e `team-design/` (Arduino, **domingo 25**). Ver `README.md` e `regulamento.pdf`.

## Convenções (obrigatórias)

- **Código em inglês**: identificadores, nomes de ficheiros/pastas, mensagens Serial, tópicos MQTT,
  nomes de Actions/Models/Connectors LoT.
- **Documentação em PT-PT** (READMEs, este ficheiro). Os comentários no código podem ficar em PT-PT.
- Git trunk-based: commits pequenos diretamente em `main`; `git pull --rebase` antes de push.
- Nunca fazer commit de segredos (`.env` está no `.gitignore`).
- Hackathon: as soluções passam por deteção de plágio. Não copiar os labs da formação Coreflux
  (`CorefluxCommunity/weather-station-hackathon`); usá-los só como referência de sintaxe.

## team-design/ (PlatformIO, Arduino Uno)

```bash
cd team-design && source .venv/bin/activate
pio test -e native     # testes Unity da lógica pura no PC — correr depois de qualquer alteração
pio run -e uno         # compilar
pio run -e uno -t upload && pio device monitor   # placa real, Serial a 9600
wokwi-cli --scenario test/wokwi/mode_cycle.yaml --timeout 10000   # precisa de WOKWI_CLI_TOKEN
```

Arquitetura: **lógica pura** em `lib/Control/` (sem `Arduino.h`, testável com `-e native`) vs.
**camada de hardware** em `src/main.cpp` (pinos, Servo, Serial). A nova lógica vai para `lib/` com testes
em `test/test_control/`; o `main.cpp` deve ficar fino.

Invariantes que é fácil partir:
- `include/pins.h`, `diagram.json` (Wokwi) e a montagem real têm de coincidir.
- O Servo usa o Timer1 → **não há PWM nos pinos 9/10**; o PWM dos motores está em 5/6.
- A saída Serial `KEY=value` (ex.: `MODE=FORWARD A=200 B=200 SERVO=90`) é verificada à letra por
  `test/wokwi/mode_cycle.yaml`. Se mudar o formato, atualizar o cenário.
- O Wokwi não tem L298N/motores DC: no `diagram.json` os sinais da ponte H são LEDs.

## hackathon/ (Coreflux)

Broker MQTT Coreflux + HUB em Docker (`hackathon/broker/`). A lógica vive no broker em LoT
(Actions, Models, Connectors, Rules, Panels); a fonte de verdade são os ficheiros `.lotnb` em
`hackathon/lot/`. Sintaxe de referência: `hackathon/LOT_CHEATSHEET.md`. A organização dá uma licença do
evento (`CFLX-...`, em `hackathon/broker/.env`, fora do git); sem ela, a edição Community só permite
**3 Connectors** e nenhuma Rule personalizada.
O pitch (5 min + até 3 min de perguntas; problema → demo → arquitetura → maturidade) está em
`hackathon/PITCH.md`.
