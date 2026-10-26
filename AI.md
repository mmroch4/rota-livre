# Developing with AI (Claude Code + Coreflux)

Based on the official guide: <https://docs.coreflux.org/latest/quick-start/using-ai>.
The repo comes ready to use. Each teammate only does the **one-time setup** below.

## What is already configured

| Piece | Where | What it gives the AI |
|-------|-------|----------------------|
| **Docs MCP** `coreflux-docs` | `.mcp.json` | Searches the official LoT docs, so the AI stops inventing syntax |
| **Broker MCP** `coreflux-broker` | `.mcp.json` + `broker/docker-compose.yml` (port 6278, localhost only) | 98 tools on our live broker: `validate_lot(nb)`, `deploy_lot`, `explore_topics`, `diagnose`, `run_action`, projects, … |
| **Coreflux agent skills** (MIT) | `.claude/skills/lot-*`, `broker-*`, `python-scripts` | The full LoT references, pinned to broker **2.22.0** and loaded on demand |
| **`/lot-deploy`** (ours) | `.claude/skills/lot-deploy/` | Validate the `.lotnb` files → reload the `lot` project from git → diagnose |
| **Project rules** | `AGENTS.md` (imported by `CLAUDE.md`) | Naming, standards, boundaries, workflow |
| **Permissions** | `.claude/settings.json` | Read-only tools run without asking; deploys ask first; `remove_all_*` and user management are blocked |

`lot/` is mounted read-only in the broker at `/lot`, so the broker loads exactly what
is in git.

## One-time setup (per laptop)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
(cd broker && cp -n .env.example .env && docker compose up -d)
.venv/bin/python scripts/mcp_token.py      # mints a token and saves it to .claude/settings.local.json (gitignored)
```

Then **restart Claude Code** in the repo root, accept the trust dialog and approve the
two `coreflux-*` MCP servers. Check with `/mcp` (both should show *connected*) or:

```bash
claude mcp list | grep coreflux
```

- **Token:** it acts as the broker user `root` and has no expiry. It is valid only on your broker
  and only on localhost. Revoke it with `scripts/mcp_token.py --revoke`. If you wipe the broker
  (`docker compose down -v`), mint a new one.
- **Different port or URL:** set `COREFLUX_MCP_URL` (default `http://127.0.0.1:6278/mcp`).
- **Cursor / VS Code users:** `AGENTS.md` works as is. Add the same two servers to `.cursor/mcp.json`
  or `.vscode/mcp.json` (both are gitignored, because they hold the token), using `"type": "http"`
  for the broker. Install the skills with the **Install Agent Skills...** button in the LoT Notebooks extension.
- **Upgrading the broker image:** run `scripts/sync_skills.sh <new-version>` and commit, so the
  skills keep matching the broker.

## Daily loop

1. *"Read the topic map and write Action `UpdateRoute` in `lot/20-routing.lotnb`..."*. Be specific:
   name the topics, the payload format and the thresholds (copy them from the topic map).
2. The AI loads the `lot-actions` skill, checks the live state (`explore_topics`), writes the block and
   runs `/lot-deploy`. Validation returns errors with line and column, and nothing is deployed until it is valid.
3. It proves the result with `run_action` and shows what was published. Review the diff, then commit.

Tips from the Coreflux guide:
- **one Action/Connector at a time**;
- check `/mcp` at the start of each session, because without the MCP connection the AI makes up syntax;
- when the AI gets something wrong twice, add a rule to `AGENTS.md`.
