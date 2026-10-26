---
name: lot-deploy
description: "Validate and deploy team O(1/n)'s .lotnb notebooks from lot/ to the local Coreflux broker via the coreflux-broker MCP server, so the broker always matches git. Use after editing any .lotnb, or when asked to deploy, sync, reload or reset the broker's LoT."
---

# Deploy lot/ to the local broker

The broker mounts `lot/` read-only at `/lot` (see `broker/docker-compose.yml`)
and loads it as the project **`lot`**. `-addProject` takes a *snapshot* of the folder, so after
any edit the project has to be removed and re-added. `-loadProject` replaces every entity of the
previous project (ad-hoc entities from `deploy_lot`/`add_action` survive).

All tools below are on the `coreflux-broker` MCP server; each takes `{"argument": "<text>"}`.
If that server is missing or answers 401, stop and tell the user to follow `AI.md`
(start the broker, run `scripts/mcp_token.py`, restart Claude Code).

## Steps

1. **Validate first, while the old version is still running.** For every notebook that changed
   (or all of them when unsure), call `validate_lotnb` with the file's JSON content as `argument`.
   Fix every `error` diagnostic (it has `cellIndex`, `line`, `column`) and re-validate until
   `"valid": true`. Info diagnostic `LOT2004` ("would replace the live …") is expected.
   Never continue with errors: a failed swap leaves the broker with no project loaded.
2. **Swap**, in this order:
   1. `unload_project` with `""` (ignore "no project loaded")
   2. `remove_project` with `lot` (ignore "not found")
   3. `add_project` with `/lot lot`
   4. `load_project` with `lot`: check `counts` and that `warnings` is absent or empty
3. **Check** with `diagnose` and `get_pending_status` (an Action may wait for a Model, a Python
   script or a Connector). For a new Action, prove it with
   `run_action` `<Name> {"topic":"<real topic>","payload":...}`, which really publishes
   (see the `broker-operations` skill, section 3).
4. Report: entities loaded per kind, warnings, and anything pending or failing.

## Notes

- Notebook format: a JSON array of cells; only `kind: 2` cells load (`lot` or `python` with a
  `# Script Name: <Name>` comment). Load order is by kind, not by file name.
- To try a single block quickly without touching git, use `validate_lot` then `deploy_lot`.
  Copy the final code into the right `.lotnb` before committing; the next `/lot-deploy` doesn't
  remove ad-hoc entities, so `remove_action` (etc.) the scratch copy if its name changed.
- Retained config (devices, modes) is published by `00-setup.lotnb`; reloading does not clear
  retained topics.
