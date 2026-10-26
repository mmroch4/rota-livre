# AGENTS.md: LoT rules for AI assistants

Coreflux LoT project of team O(1/n). The product, architecture and the
**MQTT topic map** (the contract between every component) are in [`README.md`](README.md).
Setup of the AI tooling (MCP servers, skills, token) is in [`AI.md`](AI.md).

## Sources of truth

- **LoT code:** the `.lotnb` notebooks in `lot/`. Never leave logic only in the broker or the HUB.
- **Topics:** the topic map in `README.md`. Add a row there whenever you create a topic.
- **Syntax:** never from memory. In this order: the vendored skills in `.claude/skills/`
  (`lot-actions`, `lot-models`, `lot-routes`, `lot-rules`, `lot-panels`, `python-scripts`, …;
  pinned to broker 2.22.0), then the `coreflux-docs` MCP server.
  If they disagree, `validate_lot` on the live broker decides.

## Workflow

1. Load the skill for the kind you are writing; check what exists with `explore_topics` /
   `list_entities` (coreflux-broker MCP).
2. Write or edit the block in the notebook of its **feature** (one owner per notebook); a notebook holds that feature's Models, Actions, Connectors and Python.
   The broker loads by kind (Models before Actions), so a notebook may use a Model from another.
   Python for `CALL PYTHON` goes in a `python` cell with `# Script Name: <Name>`; keep it pure and add
   `pytest` tests in `services/tests/`.
3. Deploy with the `/lot-deploy` skill (validate → swap → diagnose). For quick experiments,
   `validate_lot` + `deploy_lot` a single block, then move it into the notebook.
4. Prove it works: `run_action <Name> {"topic":…,"payload":…}` or publish a test message, and
   show the published topics/payloads. Build and test **one** Action/Connector at a time.

## Naming and code standards

- Entities in PascalCase: Actions verb-first (`UpdateRoute`), Models nouns (`Sensor`), Rules by scope
  (`AllowAdminWrites`), Connectors by destination (`Mailer`). Variables and model fields in
  `snake_case`. Topics lowercase, `/`-separated, under the project prefix or `config/` (see the topic map).
- Indent 4 spaces per level. Code fences use `lot`. Write the language name as "LoT".
- Type-cast every numeric value before math or comparisons (`PAYLOAD AS DOUBLE`,
  `GET TOPIC "…" AS DOUBLE`). Booleans and integers are not quoted.
- Internal state uses `KEEP TOPIC`; `PUBLISH TOPIC` only for what other components read.
- Models trigger on the primary data field, never on a timestamp. Use `COLLAPSED` models when an
  Action controls publish timing.
- Small callable Actions with `INPUT`/`OUTPUT` instead of one big Action.
- LoT for publish/subscribe, conditionals and simple math; Python only for what LoT does badly
  (algorithms, folds over state). An LLM, if used, only turns free text/images into JSON and never decides.

## Broker 2.22.0 quirks (verified live on 23/10; these override the skills)

- **`CALL PYTHON` must return a `str`.** Return `json.dumps({...})`. A returned dict or int fails at
  runtime with `Self referencing loop detected with type 'Python.Runtime.PyObject'` and **aborts the
  rest of the Action** (an earlier attempt gave the opaque `{"h":...,"r":1}`). Arguments arrive as `str`.
- **`GET JSON` on a Python result:** `SET "x" WITH GET JSON "k" IN {r} AS DOUBLE` works when `{r}` is the
  `RETURN AS` variable itself (or `PAYLOAD`). Wrapping it in parentheses, or reading from a copy
  (`SET "c" WITH {r}`), fails at runtime with `SafeParseDouble ... instance reference`.
  `validate_lot` accepts all of these forms, so **run `diagnose` after every deploy and after the first message**.
- `GET JSON ... AS BOOL` publishes `True`/`False` (capitalized).
- **`PUBLISH MODEL` (verified 24/10):** a model header with `RETAIN` is rejected (LOT1001 "empty body") unless it
  also has `WITH TOPIC`; even then `PUBLISH MODEL ... TO` publishes **not retained**, and a field declared
  `WITH TIMESTAMP "ISO"` is missing from the payload. For retained state, use `PUBLISH TOPIC ... WITH RETAIN QOS1`.
- **An Action cannot clear a retained message (verified 24/10).** `PUBLISH TOPIC ... WITH "" WITH RETAIN` (literal or
  an empty variable) is dropped silently and the old retained payload stays; `WITH EMPTY` does not parse. To retire
  a barrier from the broker, republish it retained with `expires_at` in the past: the app hides expired barriers.
- **Never end a block with `UNTIL` (verified 24/10).** When the line after `UNTIL` dedents, the parser drops one
  dedent: everything after it is scoped one level deeper than written. An outer `ELSE`/`ELSE IF` binds to the inner
  `IF`, and later top-level lines run only inside that branch. `validate_lot` and `deploy_lot` accept it (a bare
  `UNTIL` directly followed by `ELSE` fails to parse). Keep a statement at the `REPEAT`'s own level after `UNTIL`.
  `REPEAT` is do-while (the body runs once even when the condition is already true).
- **A broker boot can restore an older version of a redeployed Action (verified 24/10, three boots).** Each boot
  logs "Duplicate DEFINE ACTION block for 'ImportCityAlerts' in actions file. Keeping the first definition": the
  persisted actions file holds every version deployed over an entity that came from project `lot` (the broker's own
  copy, older than ac5ec1f), and the **first, oldest** one wins. Actions deployed only ad hoc (e.g. `SwitchCityAlerts`,
  the `OpsSummary*` ones) came back current. `remove_action` reports "2 duplicate definitions cleaned up", but after
  remove + `deploy_lot` the next boot still logged the duplicates and reverted. So **after every broker restart** run
  `docker restart o1n-broker && sleep 10 && python3 broker/redeploy_lot.py --fix` (login from
  `BROKER_USERNAME` / `BROKER_PASSWORD`). It compares every Action of Miguel's notebooks with its **retained**
  `$SYS/Coreflux/Actions/<Name>` (one exact subscription each: `$SYS/Coreflux/#` also gets non-retained traffic and
  gave a false mismatch), resends the notebook's Python cells and then the Actions that differ through
  `$SYS/Coreflux/Command`, and checks again; `--check` alone only reports. It never sends routes or panels and never
  removes anything. No project swap (`load_project` would bring back the copy's old `ImportCityAlerts`). Ben's
  `10-barriers-db.lotnb` **stays loaded**
  (`RouteBarrierMessage` + `BarriersDB`): reports and answers are saved in Supabase. Never remove them; if they are
  missing after a restart, add those two cells one at a time (it needs the env `SUPABASE_DB_HOST`/`SUPABASE_DB_USER`
  and the secret `SUPABASE_DB_PASSWORD` on the broker, see `db/README.md`), then check that
  `$SYS/Coreflux/Routes/BarriersDB/status` says `Connected`. `redeploy_lot.py` does not cover these two.
- **The command channel strips comments, Python included (verified 24/10).** A payload on `$SYS/Coreflux/Command`
  loses `//`, `/* */` and `-- ` outside string literals, so `-addPython` with `x // 2` in plain code fails
  (`'(' was never closed`); `//` inside a string or f-string (`f"{n // 1000:03d}"`) survives. Use `int(a / b)` or
  keep it inside an f-string in cells that `redeploy_lot.py` sends. The MCP `add_python` tool was not checked for this.
- **An Action's triggers run concurrently (verified 24/10).** Reading a retained topic, changing it and publishing it
  back loses updates on a burst: a summary updated by 24 back-to-back barrier messages counted 6, and a plain LoT
  counter on a single topic lost 5 of 40 once. There is no way to serialise an Action. A Python script's module
  globals persist between `CALL PYTHON` calls (same module object), so a `threading.Lock` around state kept in the
  module made 30 concurrent calls exact (`OpsSummary` in `lot/ops_panel.lotnb`). Seed that state from a retained
  topic, since it is empty after a restart or `add_python`. `StoreBarrierFeedback`'s `gone_count` is read-change-publish
  too: two distinct answers to the same barrier in the same instant could count once (not observed).
- **`KEEP TOPIC` is memory only; retained topics survive a restart (durability on, verified 24/10).** State that must
  outlive a restart goes in a retained `PUBLISH TOPIC`; `GET TOPIC` reads the retained value after a boot.
  Right after a restart (seconds after `/health` is healthy) one subscriber got no retained messages at all; 5 s
  later everything was there. Reload clients that connected during a restart.
- `GET TOPIC {var}` and `GET TOPIC {a} + "/x" AS INT` work with a computed topic; an unknown topic reads as `""`
  (`0` with `AS INT`), so it can be used to skip duplicates.
- **REST connector:** `WITH ENDPOINT "...?date={payload.json.date}"` works. A non-2xx answer is published to
  DESTINATION_TOPIC as `{"success":false,"statusCode":404,...}`; check for it.
- **Community limits** (`curl localhost:9100/license`): 3 Connectors, 24 Actions (Connector events and
  Python scripts count too), 24 Models, **0 Rules**, 5 Panels, and no `TYPE LLM`.

## Boundaries

- **Always:** validate before deploying; keep `lot/` and the broker in sync; update the topic map.
- **Ask first:** adding or changing Connectors (the Community edition allows only 3), changing
  Rules, removing any entity, `load_project`/`unload_project` of anything other than `lot`,
  installing Python packages in the broker.
- **Never:**
  - invent syntax;
  - put licence codes, MCP tokens, passwords or API keys in committed files (use `-setSecret` /
    `GET SECRET`, and `broker/.env`);
  - copy code from the Coreflux training labs (`CorefluxCommunity/weather-station-hackathon`):
    there is plagiarism detection;
  - use the broker's user-management tools;
  - expose ports beyond `127.0.0.1` (the one exception is the opt-in WebSocket tunnel for the web app,
    `broker/docker-compose.tunnel.yml`, used only with a changed root password and `lot/web_access.lotnb` deployed).
