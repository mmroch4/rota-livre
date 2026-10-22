# Cheatsheet LoT (Language of Things)

Referência rápida da sintaxe usada na formação Coreflux (Broker 2.22). Os exemplos são **genéricos**:
servem para lembrar a sintaxe, não para copiar (há deteção de plágio). Documentação completa:
<https://docs.coreflux.org/latest/lot-language/introduction>.

| Bloco | Para quê | Comando do broker |
|-------|----------|-------------------|
| `DEFINE ACTION` | Lógica: "quando X, faz Y" | `-addAction` |
| `DEFINE MODEL` | Esquema de um payload JSON estruturado | `-addModel` |
| `DEFINE CONNECTOR` | Ponte para fora (REST, ficheiro, email, BD, PLC) | `-addConnector` |
| `DEFINE RULE` | Controlo de acesso a tópicos (precisa de licença) | `-addRule` / `-removeRule` |
| `DEFINE PANEL` | Dashboard ao vivo no HUB | `-addPanel` |
| `DEFINE THING` | Agrupa tudo num template reutilizável | — |

Voltar a fazer deploy de um bloco com o mesmo nome **substitui-o**.

## Actions

```lot
DEFINE ACTION Tick
ON EVERY 10 SECONDS DO
    PUBLISH TOPIC "demo/status" WITH "alive"
```

Gatilhos: `ON EVERY <n> SECONDS|MINUTES DO`, `ON TOPIC "a/b" DO`.

```lot
DEFINE ACTION CheckLevel
ON TOPIC "demo/sensor/level" DO
    SET "level" WITH (GET JSON "value" IN PAYLOAD AS DOUBLE)
    SET "limit_raw" WITH GET TOPIC "config/level_limit"
    IF {limit_raw} == EMPTY THEN
        PUBLISH TOPIC "demo/errors" WITH "no limit configured"
    ELSE
        SET "limit" WITH (GET TOPIC "config/level_limit" AS DOUBLE)
        IF {level} > {limit} THEN
            PUBLISH TOPIC "demo/alerts/level" WITH PAYLOAD
        ELSE
            PUBLISH TOPIC "demo/alerts/level_ok" WITH "ok"
```

| Construção | Exemplo |
|------------|---------|
| Variável local | `SET "x" WITH 3` · usar com `{x}` |
| Aritmética | `SET "f" WITH (({c} * 9.0 / 5.0) + 32.0)` |
| Campo JSON do payload | `GET JSON "a.b.c" IN PAYLOAD AS DOUBLE` (ou `AS STRING`) |
| Payload inteiro | `PAYLOAD` |
| Último valor de um tópico | `GET TOPIC "config/x"` · `GET TOPIC "config/x" AS DOUBLE` |
| Vazio / nulo | `IF {x} == EMPTY OR {x} == "null" THEN` |
| Condições | `IF ... THEN` / `ELSE`, `==`, `!=`, `>`, `<`, `AND`, `OR`; os blocos são definidos **pela indentação (4 espaços)** |
| Timestamp | `TIMESTAMP "UTC"` |

**Padrão "alerta só uma vez por episódio":** guardar o estado num tópico (`.../active` = `on`/`off`),
lê-lo com `GET TOPIC` e só publicar o alerta na transição `off → on`.

## Models

```lot
DEFINE MODEL Reading COLLAPSED
    ADD DOUBLE "value"
    ADD STRING "unit"
    ADD STRING "timestamp"
```

`COLLAPSED` = só publica quando uma Action o envia explicitamente:

```lot
    PUBLISH MODEL Reading TO "demo/sensor/reading" WITH
        value = {v}
        unit = "cm"
        timestamp = TIMESTAMP "UTC"
```

## Connectors

⚠️ A **Community Edition só permite 3 Connectors.**

**REST API** (pedido disparado por uma mensagem num tópico, resposta publicada noutro):

```lot
DEFINE CONNECTOR SomeApi WITH TYPE REST_API
    ADD REST_API_CONFIG
        WITH BASE_ADDRESS "https://api.example.com"
        WITH ENABLE_CLIENT "true"
        WITH USE_SSL "true"
    ADD EVENT FetchData
        WITH SOURCE_TOPIC "demo/api/request"
        WITH DESTINATION_TOPIC "demo/api/raw"
        WITH METHOD "GET"
        WITH ENDPOINT "/v1/data?id={env.SOME_ID}"
```

**Ficheiro CSV** (pasta montada em `broker/exports/` → `/data/exports`):

```lot
DEFINE CONNECTOR History WITH TYPE FILE_STORAGE
    ADD FILE_STORAGE_CONFIG
        WITH STORAGE_DIR "/data/exports"
        WITH FORMAT "CSV"
        WITH FILE_PATTERN "history.csv"
        WITH APPEND "true"
    ADD EVENT Save
        WITH SOURCE_TOPIC "demo/sensor/reading"
        WITH QUERY "CLEAN:{table: history, data: {value.json}}"
```

**Email** (Mailpit local na porta 1025; template em `broker/templates/` → `/templates`):

```lot
DEFINE CONNECTOR Mailer WITH TYPE EMAIL
    ADD SMTP_CONFIG
        WITH HOST GET ENV "SMTP_HOST"
        WITH PORT 1025
        WITH USERNAME GET ENV "SMTP_USER"
        WITH PASSWORD GET SECRET "SMTP_PASSWORD"
        WITH USE_TLS false
    ADD EVENT SendAlert
        WITH SOURCE_TOPIC "demo/alerts/level"
        WITH RECIPIENT "team@example.com"
        WITH SUBJECT "Level alert"
        WITH TEMPLATE_PATH "/templates/alert.html"
```

Um Connector `FILE_STORAGE` com ponto vermelho no HUB é **normal** (não mantém um socket aberto).

## Panels (dashboard no HUB)

```lot
DEFINE PANEL Overview
    WITH VISIBILITY PUBLIC
    WITH STATE PUBLISHED
    WITH TITLE "Overview"
    WITH LAYOUT "grid" COLUMNS 2 ROWS 1

    ADD COMPONENT "LevelGauge" WITH TYPE "gauge"
        AT COLUMN 1 ROW 1
        SET LABEL "Level"
        SET RANGE FROM 0 TO 100
        SET UNIT "cm"
        BIND VALUE TO TOPIC "demo/sensor/reading" WITH JSON_PATH "value"

    ADD COMPONENT "State" WITH TYPE "text"
        AT COLUMN 2 ROW 1
        SET LABEL "Alert"
        BIND CONTENT TO TOPIC "demo/alerts/level_active"
```

Tipos vistos: `gauge`, `value` (`SET DECIMALS n`), `text` (`BIND CONTENT`).
Se todos os cartões mostram o mesmo número, falta o `WITH JSON_PATH`.

## Comandos do broker (HUB → `root` → Command Console)

```text
-setEnv NAME=value            # variável (sem espaços à volta do =)
-setSecret NAME=value         # segredo (não usar // no valor: inicia um comentário)
-listEnv  /  -listSecrets
-activateLicense CFLX-...
-removeConnector <Name>  /  -removeRule <Name>
```

Também se podem publicar como MQTT em `$SYS/Coreflux/Command` (resposta em `$SYS/Coreflux/Command/Output`).

## Publicar a partir de Python

```python
import json
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="o1n-simulator")
client.username_pw_set("root", "coreflux")
client.connect("localhost", 1883)
client.publish("demo/sensor/level", json.dumps({"value": 42.0}))
client.disconnect()
```

O broker rejeita dois clientes com o mesmo `client_id`: usar um id diferente por processo.
