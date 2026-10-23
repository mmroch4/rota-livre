# Hackathon — solução Coreflux

> **Estado:** ideia escolhida (23/10): **Copiloto energético com LLM para PMEs**. A estrutura segue os
> 4 pontos em que o júri avalia (Regulamento, Art. 1.º, 3): **problema → demo → arquitetura → maturidade**.
> O que está marcado com ⚠️ **verificar** tem de ser confirmado na primeira hora da prova.

**Nome do produto:** **Vale**: encontra os *vales* da curva de preço da eletricidade e põe lá o consumo.
**Uma frase:** Para pequenos negócios com tarifa indexada, que pagam a eletricidade a um preço que muda
de 15 em 15 minutos, o **Vale** percebe o que cada equipamento tem de fazer (a partir de uma frase em português),
planeia-o para os quartos de hora mais baratos e liga-o sozinho, sem nunca pôr em causa a operação.

---

## 1. O problema

- **Quem:** pequenos negócios (restaurantes, minimercados, padarias) com **tarifa indexada ao OMIE**, com
  equipamentos cujo consumo pode mudar de hora sem prejudicar a operação: câmaras frigoríficas (inércia
  térmica), máquinas de lavar loiça industriais, termoacumuladores e carrinhas elétricas de entregas.
- **A dor, em números reais** (REN DataHub, preço do mercado diário em Portugal):
  - **22/10/2026:** entre **0,28 €/MWh** e **286,76 €/MWh** no mesmo dia, cerca de **1000×**. A média
    horária foi de cerca de 1 €/MWh às 12h–15h e de cerca de 245 €/MWh às 18h–19h.
  - **A hora mais barata muda todos os dias:** de 15 a 23/10 foi às 12h, 13h, 11h, 11h, **1h**, 14h, 14h, 14h.
    A intuição das tarifas bi-horárias ("o vazio é de noite") já não corresponde ao mercado: com o solar,
    o vale é muitas vezes ao meio-dia, e a noite pode ser das horas mais caras.
- **Como se resolve hoje:** não se resolve, ou com temporizadores fixos. O dono não vai consultar o OMIE
  todos os dias às 13h (quando sai o preço de amanhã) para reprogramar 4 equipamentos.
- **Porque é automação:** é preciso **integrar** os preços com os equipamentos, **otimizar** a agenda
  e **agir** a cada 15 minutos, respeitando restrições como a temperatura dos alimentos ou a hora de saída da carrinha.
- **Honestidade:** o Vale só mexe na componente de **energia** da fatura. As redes, a potência e os impostos não mudam.
  Os números de poupança apresentados referem-se sempre a essa componente.

## 2. A solução

1. **Diz o que precisa, em português:** *"A carrinha chega às 9h e tem de sair às 17h com 30 kWh; a câmara 1
   tem de ficar entre 0 e 5 °C."* Um LLM converte isto numa **tarefa estruturada**, que é validada
   (Model `Task`) e mostrada ao dono para confirmar.
2. **O Vale vai buscar os preços** de hoje e de amanhã à REN (todos os dias depois das 13h) e **planeia** cada tarefa
   nos quartos de hora mais baratos dentro das restrições.
3. **Aconselha ou age:** cada equipamento está em modo `advise` ("ligue a máquina às 14h15, poupa 1,80 €")
   ou `auto` (o Vale liga e desliga o equipamento sozinho).
4. **Nunca põe a operação em risco:** os *guardrails* no broker sobrepõem-se ao plano (ex.: a câmara
   acima de 5 °C liga **já**, custe o que custar) e avisam o dono por email.
5. **Mostra o que poupou:** contador de € poupados face a "ligar logo", e um registo de auditoria (CSV) com cada decisão e a sua razão.

## 3. Arquitetura

```text
 [fontes]                         [Coreflux Broker: a lógica vive aqui]                [saídas]

 REN DataHub ◄──REST_API──── Connector RenPrices ──► Action ParsePrices ──────┐
 (preços 15 min)                                     (CALL PYTHON PriceTools) │
                                                                              ▼
 dashboard ──"texto livre"──► Action ParseIntent ──► Model Task ──► Action PlanTask ──► copilot/plans/<id>
                              (CALL LLM Assistant)    (validação)   (CALL PYTHON Planner)        │
                                                                                                 ▼
 Action SimClock ──copilot/clock/slot──► Action Dispatch ─────► modo auto:   .../command ──► equipamentos
 (1 s = 15 min na demo)                 (plano + modo)  └─────► modo advise: copilot/advice ──► dashboard
                                                                                 │
 equipamentos ──telemetria──► Action Guard (guardrails, alerta 1×/episódio) ─────┼──► Connector Mailer (email)
 (simulador Python)           Action Meter (custo real vs. ingénuo)              └──► Connector DecisionLog (CSV)
                                                                                      dashboard web + Panel HUB
                              Rules: só as Actions do broker podem publicar comandos para os equipamentos
```

**Divisão de responsabilidades:**
- **Broker (LoT):** ingestão de preços, relógio, estado, despacho, *guardrails*, contabilidade, alertas,
  auditoria e segurança.
- **Python dentro do broker (`CALL PYTHON`):** o que o LoT não faz bem, como ordenar 96 preços e escolher os
  N quartos de hora mais baratos antes de um prazo. As funções são **puras e sem estado** (objetivo: abaixo de 100 ms) e testáveis com `pytest` fora do broker.
- **LLM dentro do broker (`CALL LLM`, `PROVIDER "anthropic"`):** só traduz texto em JSON. **Nunca decide**
  nada sozinho: a tarefa é validada pelo Model e o plano é determinístico.
- **Fora do broker:** só o **simulador de equipamentos** (no mundo real seriam relés/PLC) e o **dashboard**.

⚠️ **Verificar:** o Connector `TYPE LLM` precisa de licença **Growth/Enterprise** segundo a documentação. Se a
licença do evento não o incluir, o plano B é `services/intent_parser.py` (Claude API via `anthropic` SDK), que lê
`copilot/assistant/request` e publica em `copilot/tasks/new`, com o mesmo contrato de tópicos.

### Mapa de tópicos MQTT

O contrato entre todas as partes do sistema. **Atualizar sempre que se cria um tópico.**
`<id>` ∈ `cold_room_1`, `dishwasher_1`, `van_1` (os equipamentos da demo).

| Tópico | Publicado por | Lido por | Payload | Retained |
|--------|---------------|----------|---------|:--------:|
| `copilot/market/request` | Action `FetchPrices` (diária às 13:30 e no arranque) | Connector `RenPrices` | `{"date":"2026-10-24"}` | |
| `copilot/market/raw` | Connector `RenPrices` | Action `ParsePrices` | JSON da REN (`series[].data`) | |
| `copilot/market/prices` | Action `ParsePrices` | `PlanTask`, `Dispatch`, `Meter`, dashboard | `{"date","unit":"EUR/MWh","step_min":15,"prices":[96 valores]}` | ✅ |
| `config/clock/mode` | setup / dashboard | `SimClock` | `sim` \| `real` | ✅ |
| `copilot/clock/slot` | Action `SimClock` | `Dispatch`, `Meter`, dashboard | `0`–`95` (quarto de hora atual) | ✅ |
| `config/devices/<id>` | `00-setup` | `PlanTask`, dashboard | Model `Device`: `type` (`thermal`\|`block`\|`energy`), `power_kw`, limites | ✅ |
| `config/devices/<id>/mode` | dashboard (dono) | `Dispatch` | `advise` \| `auto` | ✅ |
| `copilot/assistant/request` | dashboard | Action `ParseIntent` | `{"text":"..."}` | |
| `copilot/tasks/new` | `ParseIntent` ou formulário (plano B) | Action `PlanTask` | Model `Task`: `device_id`, `kind`, `energy_kwh`, `duration_slots`, `earliest_slot`, `deadline_slot` | |
| `copilot/assistant/errors` | `ParseIntent` | dashboard | texto do erro de validação | |
| `copilot/plans/<id>` | Action `PlanTask` | `Dispatch`, dashboard | `{"slots":[...],"cost_eur","naive_cost_eur","savings_eur","reason"}` | ✅ |
| `copilot/devices/<id>/command` | `Dispatch` (modo `auto`), `Guard` | simulador / relé | `on` \| `off` | ✅ |
| `copilot/advice/<id>` | `Dispatch` (modo `advise`) | dashboard | `"Ligue às 14:15 (poupa 1,80 €)"` | |
| `copilot/devices/<id>/telemetry` | simulador (`services/device_sim.py`) | `Guard`, `Meter`, dashboard | `{"on":true,"power_kw":3.0,"temp_c":3.4}` | |
| `copilot/alerts/guardrail` | Action `Guard` (só na transição) | Connector `Mailer`, dashboard | Model `Alert` | |
| `copilot/alerts/guardrail/<id>/active` | Action `Guard` | Action `Guard` | `on` \| `off` | ✅ |
| `copilot/audit/decisions` | `Dispatch`, `Guard` | Connector `DecisionLog` (CSV) | Model `Decision`: `slot`, `device_id`, `action`, `price`, `reason` | |
| `copilot/kpi/savings` | Action `Meter` | dashboard, Panel | `{"cost_eur","naive_cost_eur","saved_eur"}` | ✅ |
| `copilot/errors` | qualquer Action | dashboard | texto | |

Convenções: tópicos em inglês, minúsculas, `snake_case`, hierarquia `<domínio>/<entidade>/<medida>`;
configuração em `config/...` (retained); erros em `.../errors`.

### Componentes

| Componente | Onde | Tecnologia |
|------------|------|------------|
| Lógica de automação | `lot/` | LoT: Actions, Models, Connectors (`REST_API`, `LLM`, `EMAIL`, `FILE_STORAGE`), Rules, Panel |
| Otimizador e parsing de preços | `lot/` (scripts `CALL PYTHON`) + testes em `services/tests/` | Python (só biblioteca padrão) |
| Simulador de equipamentos | `services/device_sim.py` | Python + `paho-mqtt` (modelo térmico simples da câmara frigorífica) |
| Dashboard | `dashboard/` | Web app própria (HTML + MQTT por WebSocket + gráfico de preços com o plano sobreposto); Panel no HUB como vista técnica e plano B |
| Infraestrutura | `broker/` | Docker Compose: Coreflux Broker 2.22, HUB 2.12, Mailpit |

⚠️ **Verificar:** a porta WebSocket do broker para o dashboard. Se não existir, a alternativa é uma *bridge* mínima MQTT → SSE em Python.

## 4. Demo

Guião completo e plano B em [`PITCH.md`](PITCH.md#guião-da-demo-140). Resumo:
1. O gráfico dos **preços reais de hoje** (REN) mostra o vale ao meio-dia.
2. O dono escreve uma frase, o LLM transforma-a em tarefas (o JSON aparece no ecrã) e os planos aparecem sobre o gráfico, com a poupança prevista.
3. **▶ Simular o dia** (1 s = 15 min): os equipamentos ligam-se sozinhos nos vales e o contador de € sobe.
4. **Abre-se a porta da câmara:** a temperatura passa os 5 °C, o *guardrail* liga a câmara mesmo com preço alto, chega um
   email ao Mailpit e aparece uma linha no CSV de auditoria.

## 5. Maturidade e próximos passos

- **De ponta a ponta e real:** os preços (API pública da REN, sem chave), o LLM, o planeamento, o despacho, os *guardrails*, os emails
  e a auditoria correm no broker.
- **Simulado:** os equipamentos (simulador Python com modelo térmico) e o relógio acelerado. Ligar a hardware
  real é trocar o simulador por um relé/PLC a subscrever o **mesmo** tópico `.../command`.
- **Fiabilidade:**
  - os preços ficam retained e em cache: sem internet, o Vale usa o último plano conhecido;
  - sem preços nenhuns, cai para um modo seguro (comportamento normal do equipamento);
  - o LLM nunca atua diretamente;
  - os *guardrails* têm prioridade sobre o plano;
  - o alerta é enviado só uma vez por episódio.
- **Segurança (Rules):**
  - só as Actions do broker publicam em `copilot/devices/+/command`;
  - o utilizador do dashboard só pode publicar pedidos e mudar o modo;
  - cada equipamento só publica a sua própria telemetria.
- **Testes:** o otimizador tem testes `pytest`, incluindo casos-limite: o prazo impossível, os preços em falta e o dia de **100** quartos de hora
  na mudança de hora (25/10!).
- **Escala:** os equipamentos são configuração (`config/devices/<id>`), e um novo tipo é uma nova estratégia no planner.
  Para várias lojas, um broker por loja, ligados a um broker central.
- **Modelo de negócio:** subscrição por estabelecimento. O Vale começa com um **simulador de fatura** ("na indexada,
  com os seus equipamentos, pouparia X €/mês"), que é também a ferramenta comercial.
- **Com mais tempo:**
  - perfil residencial (o mesmo motor para a família com carro elétrico);
  - previsão do preço antes das 13h;
  - otimizar a **potência contratada** e o autoconsumo solar;
  - integração Modbus com os controladores de frio.

---

## Setup do ambiente (Linux / macOS)

Pré-requisitos: **Docker** e **Docker Compose v2** (`docker --version`, `docker compose version`).

```bash
cd hackathon/broker
cp .env.example .env          # opcional: código de licença do evento
docker compose up -d
```

| Serviço | Endereço | Credenciais |
|---------|----------|-------------|
| Coreflux HUB | <http://localhost:3000> | ligação pré-preenchida: host `broker`, porta `1883`, `root` / `coreflux` |
| Broker MQTT (de fora do Docker) | `localhost:1883` | `root` / `coreflux` |
| Mailpit (caixa de email de teste) | <http://localhost:8025> | — |
| Saúde do broker | <http://localhost:9100/health> | — |

- `docker compose down` pára e mantém os dados; `docker compose down -v` **apaga tudo, incluindo a licença**.
- O HUB liga-se a `broker` (nome do serviço Docker), não a `localhost`.
- Porta ocupada? Mudar o número da porta do host em `docker-compose.yml` (ex.: `"127.0.0.1:3001:3000"`).

### Segurança na rede do evento

Na FCUP estamos na mesma rede que as outras equipas, e a password por omissão (`root` / `coreflux`)
é igual para todas. Por isso **todas as portas ficam só em `127.0.0.1`** (apenas a própria máquina).
Para um Arduino/ESP32 ou o portátil de um colega publicar no nosso broker:

1. **Primeiro** mudar a password de `root` (ou criar um utilizador próprio para os dispositivos)
   no HUB: ver a [documentação do broker](https://docs.coreflux.org/latest/mqtt-broker/overview).
2. Depois pôr `MQTT_BIND=0.0.0.0` em `broker/.env` e fazer `docker compose up -d`.

O HUB, o Mailpit e o endpoint de saúde ficam sempre só em localhost.

### Licença do evento

A organização dá-nos um **código de licença** (`CFLX-...`). Sem ele, o broker corre em
**Community Edition**, que só permite **3 Connectors** e **nenhuma `DEFINE RULE` personalizada**.
Com a licença, temos mais Connectors e podemos usar Rules, que contam como argumento de
**maturidade/segurança** no pitch.

Ativar de uma de duas formas:
- pôr `COREFLUX_ACTIVATION_CODE=CFLX-...` em `broker/.env` (fora do git) **antes** do primeiro `docker compose up`;
- HUB → `root` → Broker Settings → License, ou `-activateLicense CFLX-...` no Command Console.

Cada ativação gasta um *seat*, por isso evitar `docker compose down -v` depois de ativar.
Confirmar o tier no badge ao lado de `root` ou em <http://localhost:9100/license>.

### Fluxo de trabalho com código LoT

A **fonte de verdade é o git**: os ficheiros `.lotnb` em `lot/`.

1. Instalar a extensão VS Code **LoT Notebooks**
   ([VSCodeLotNotebook](https://github.com/CorefluxCommunity/VSCodeLotNotebook/releases/tag/v1.0.0), ficheiro `.vsix`):
   `code --install-extension vscode-lot-notebooks-1.0.0.vsix`
2. Abrir um `.lotnb` de `lot/` e ligar a `localhost:1883` (`root` / `coreflux`).
3. Correr as células (▷) para fazer deploy para o broker local; commit dos `.lotnb`.

Se alguém editar diretamente no HUB, deve copiar o código final para o `.lotnb` correspondente antes do commit.
Organização sugerida, um notebook por responsabilidade:
`lot/00-setup.lotnb` (variáveis, segredos, config retained), `lot/10-models.lotnb`, `lot/20-actions.lotnb`,
`lot/30-connectors.lotnb`, `lot/40-rules.lotnb`, `lot/50-panel.lotnb`.

### Ferramentas úteis

- **MQTT Explorer** ou `mosquitto_sub -h localhost -u root -P coreflux -t '#' -v` para ver todos os tópicos.
- **Python:** `pip install paho-mqtt` para serviços e simuladores em `services/`.
- Variáveis e segredos no broker: `-setEnv NOME=valor`, `-setSecret NOME=valor` (sem espaços à volta do `=`),
  e depois `{env.NOME}` ou `GET ENV "NOME"` / `GET SECRET "NOME"` no LoT.

## Documentos desta pasta

- [`LOT_CHEATSHEET.md`](LOT_CHEATSHEET.md): sintaxe LoT de referência (Actions, Models, Connectors, Rules, Panels).
- [`PITCH.md`](PITCH.md): estrutura da apresentação e checklist da demo.

## Referências

- Documentação Coreflux: <https://docs.coreflux.org>
- Repo da formação (só como referência, **não copiar**: há deteção de plágio):
  <https://github.com/CorefluxCommunity/weather-station-hackathon>
