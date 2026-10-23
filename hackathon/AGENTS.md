# AGENTS.md: LoT rules for AI assistants (hackathon/)

Coreflux LoT project for **Vale** (energy copilot for SMEs). The product, architecture and the
**MQTT topic map** (the contract between every component) are in [`README.md`](README.md).
Setup of the AI tooling (MCP servers, skills, token) is in [`AI.md`](AI.md).

## Sources of truth

- **LoT code:** the `.lotnb` notebooks in `lot/`. Never leave logic only in the broker or the HUB.
- **Topics:** the topic map in `README.md`. Add a row there whenever you create a topic.
- **Syntax:** never from memory. In this order: the vendored skills in `.claude/skills/`
  (`lot-actions`, `lot-models`, `lot-routes`, `lot-rules`, `lot-panels`, `python-scripts`, …;
  pinned to broker 2.22.0), then the `coreflux-docs` MCP server, then `LOT_CHEATSHEET.md`.
  If they disagree, `validate_lot` on the live broker decides.

## Workflow

1. Load the skill for the kind you are writing; check what exists with `explore_topics` /
   `list_entities` (coreflux-broker MCP).
2. Write or edit the block in the right notebook (`00-setup`, `10-models`, `20-actions`,
   `30-connectors`, `40-rules`, `50-panel`). Python for `CALL PYTHON` goes in a `python` cell with
   `# Script Name: <Name>`; keep it pure and add `pytest` tests in `services/tests/`.
3. Deploy with the `/lot-deploy` skill (validate → swap → diagnose). For quick experiments,
   `validate_lot` + `deploy_lot` a single block, then move it into the notebook.
4. Prove it works: `run_action <Name> {"topic":…,"payload":…}` or publish a test message, and
   show the published topics/payloads. Build and test **one** Action/Connector at a time.

## Naming and code standards

- Entities in PascalCase: Actions verb-first (`ParsePrices`), Models nouns (`Task`), Rules by scope
  (`AllowDispatchCommands`), Connectors by destination (`RenPrices`). Variables and model fields in
  `snake_case`. Topics lowercase, `/`-separated, under `copilot/` or `config/` (see the topic map).
- Indent 4 spaces per level. Code fences use `lot`. Write the language name as "LoT".
- Type-cast every numeric value before math or comparisons (`PAYLOAD AS DOUBLE`,
  `GET TOPIC "…" AS DOUBLE`). Booleans and integers are not quoted.
- Internal state uses `KEEP TOPIC`; `PUBLISH TOPIC` only for what other components read.
- Models trigger on the primary data field, never on a timestamp. Use `COLLAPSED` models when an
  Action controls publish timing.
- Small callable Actions with `INPUT`/`OUTPUT` instead of one big Action.
- LoT for publish/subscribe, conditionals and simple math; Python only for what LoT does badly
  (sorting 96 prices, the planner). The LLM only translates text to JSON and never decides.

## Boundaries

- **Always:** validate before deploying; keep `lot/` and the broker in sync; update the topic map.
- **Ask first:** adding or changing Connectors (the Community edition allows only 3), changing
  Rules, removing any entity, `load_project`/`unload_project` of anything other than `lot`,
  installing Python packages in the broker.
- **Never:**
  - invent syntax;
  - put licence codes, MCP tokens, passwords or API keys in committed files (use `-setSecret` /
    `GET SECRET`, and `hackathon/broker/.env`);
  - copy code from the Coreflux training labs (`CorefluxCommunity/weather-station-hackathon`):
    there is plagiarism detection;
  - use the broker's user-management tools;
  - expose ports beyond `127.0.0.1`.
