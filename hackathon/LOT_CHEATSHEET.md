# LoT (Language of Things) cheatsheet

Quick reference for the syntax used in the Coreflux training (Broker 2.22). The examples are **generic**:
they are here to remind us of the syntax, not to be copied (there is plagiarism detection). Full documentation:
<https://docs.coreflux.org/latest/lot-language/introduction>.

| Block | What for | Broker command |
|-------|----------|----------------|
| `DEFINE ACTION` | Logic: "when X, do Y" | `-addAction` |
| `DEFINE MODEL` | Schema of a structured JSON payload | `-addModel` |
| `DEFINE CONNECTOR` | Bridge to the outside (REST, file, email, DB, PLC) | `-addConnector` |
| `DEFINE RULE` | Topic access control (needs a licence) | `-addRule` / `-removeRule` |
| `DEFINE PANEL` | Live dashboard in the HUB | `-addPanel` |
| `DEFINE THING` | Groups everything into a reusable template | — |

Re-deploying a block with the same name **replaces it**.

## Actions

```lot
DEFINE ACTION Tick
ON EVERY 10 SECONDS DO
    PUBLISH TOPIC "demo/status" WITH "alive"
```

Triggers: `ON EVERY <n> SECONDS|MINUTES DO`, `ON TOPIC "a/b" DO`.

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

| Construct | Example |
|-----------|---------|
| Local variable | `SET "x" WITH 3` · use as `{x}` |
| Arithmetic | `SET "f" WITH (({c} * 9.0 / 5.0) + 32.0)` |
| JSON field of the payload | `GET JSON "a.b.c" IN PAYLOAD AS DOUBLE` (or `AS STRING`) |
| Whole payload | `PAYLOAD` |
| Last value of a topic | `GET TOPIC "config/x"` · `GET TOPIC "config/x" AS DOUBLE` |
| Empty / null | `IF {x} == EMPTY OR {x} == "null" THEN` |
| Conditions | `IF ... THEN` / `ELSE`, `==`, `!=`, `>`, `<`, `AND`, `OR`; blocks are defined **by indentation (4 spaces)** |
| Timestamp | `TIMESTAMP "UTC"` |

**"Alert only once per episode" pattern:** keep the state in a topic (`.../active` = `on`/`off`),
read it with `GET TOPIC` and only publish the alert on the `off → on` transition.

## Models

```lot
DEFINE MODEL Reading COLLAPSED
    ADD DOUBLE "value"
    ADD STRING "unit"
    ADD STRING "timestamp"
```

`COLLAPSED` = only published when an Action sends it explicitly:

```lot
    PUBLISH MODEL Reading TO "demo/sensor/reading" WITH
        value = {v}
        unit = "cm"
        timestamp = TIMESTAMP "UTC"
```

## Connectors

⚠️ **Community Edition only allows 3 Connectors.**

**REST API** (request triggered by a message on one topic, response published on another):

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

**CSV file** (folder mounted at `broker/exports/` → `/data/exports`):

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

**Email** (local Mailpit on port 1025; template in `broker/templates/` → `/templates`):

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

A `FILE_STORAGE` Connector with a red dot in the HUB is **normal** (it does not keep a socket open).

## Panels (dashboard in the HUB)

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

Types seen: `gauge`, `value` (`SET DECIMALS n`), `text` (`BIND CONTENT`).
If every card shows the same number, the `WITH JSON_PATH` is missing.

## Broker commands (HUB → `root` → Command Console)

```text
-setEnv NAME=value            # variable (no spaces around the =)
-setSecret NAME=value         # secret (do not use // in the value: it starts a comment)
-listEnv  /  -listSecrets
-activateLicense CFLX-...
-removeConnector <Name>  /  -removeRule <Name>
```

They can also be published over MQTT to `$SYS/Coreflux/Command` (response on `$SYS/Coreflux/Command/Output`).

## Publishing from Python

```python
import json
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="o1n-simulator")
client.username_pw_set("root", "coreflux")
client.connect("localhost", 1883)
client.publish("demo/sensor/level", json.dumps({"value": 42.0}))
client.disconnect()
```

The broker rejects two clients with the same `client_id`: use a different id per process.
