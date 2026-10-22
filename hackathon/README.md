# Hackathon — solução Coreflux

> **Estado:** tema aberto, ideia em **brainstorming**. As secções marcadas com `TODO` são o template
> da solução, a preencher assim que a ideia estiver escolhida. A estrutura segue os 4 pontos em que
> o júri avalia (Regulamento, Art. 1.º, 3): **problema → demo → arquitetura → maturidade**.

**Nome do produto:** `TODO`
**Uma frase:** `TODO` — "Para <quem>, que <sofre com X>, o <produto> <faz Y> automaticamente com Coreflux."

---

## 1. O problema

`TODO`
- Quem tem o problema? (pessoa/organização concreta, idealmente da UP/FEUP/FCUP)
- Qual é a dor, e com que frequência acontece? Um número vale mais do que um adjetivo.
- Como se resolve hoje, e porque é que isso não chega?
- Porque é um problema de **automação** (processos, integração de sistemas, otimização de tarefas)?

## 2. A solução

`TODO`: o que o sistema faz, do ponto de vista do utilizador, em 3–5 passos.

## 3. Arquitetura

`TODO`: diagrama e descrição. Ponto de partida:

```text
 [fontes de dados]            [Coreflux Broker]                        [saídas]
 sensores / Arduino ──MQTT──►  Actions  (lógica, eventos, timers)  ──►  Panel (dashboard HUB)
 APIs externas ◄──Connector──  Models   (dados estruturados)       ──►  dashboard web própria
 serviços Python ──MQTT──►     Connectors (REST, CSV, email, BD)   ──►  email / CSV / API
                               Rules    (quem pode publicar o quê)
```

### Mapa de tópicos MQTT

O contrato entre todas as partes do sistema. **Atualizar sempre que se cria um tópico.**

| Tópico | Publicado por | Lido por | Payload | Retained |
|--------|---------------|----------|---------|:--------:|
| `TODO/...` | | | | |

Convenções: tópicos em inglês, minúsculas, `snake_case`, hierarquia `<domínio>/<entidade>/<medida>`;
configuração em `config/...` (retained); erros em `.../errors`.

### Componentes

| Componente | Onde | Tecnologia |
|------------|------|------------|
| Lógica de automação | `lot/` | LoT (Actions, Models, Connectors, Rules) |
| Serviços externos / simuladores | `services/` | Python + `paho-mqtt` |
| Dashboard | `dashboard/` ou Panel LoT | `TODO` (Panel no HUB **ou** web app própria) |
| Infraestrutura | `broker/` | Docker Compose: Coreflux Broker 2.22, HUB 2.12, Mailpit |

## 4. Demo

`TODO`: guião passo a passo da demo ao vivo (ver [`PITCH.md`](PITCH.md)), com o **plano B** se algo falhar
(vídeo gravado, dados simulados em vez de um sensor real, etc.).

## 5. Maturidade e próximos passos

`TODO`: o que já funciona de ponta a ponta, o que é simulado, como escala, custo, segurança (Rules),
e o que faríamos com mais tempo.

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
