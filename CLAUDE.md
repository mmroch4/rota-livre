# CLAUDE.md

Rota Livre, accessible walking routes in Porto on Coreflux: the Hackathon entry of team O(1/n) (Miguel, Victor,
Ben, Pedro) at SciTeCh '26 (BEST Porto, FCUP, 6 h of work on 24 Oct 2026). The whole repo is this one project, at
the root. See `README.md` (product, architecture, MQTT topic map, setup) and `regulamento.pdf`.

**Status (26 Oct 2026): the event is over.** Rota Livre won **1st place** and goes on to a further stage of the
competition, mentored by Coreflux, competing for a place at **Hannover Messe** (open items: "Next phase" in
`README.md`). The Team Design entry was removed from the tree; its last state is the git tag
`team-design-final`. Until 26/10 everything below lived in `hackathon/`: older commits and notes use that prefix.

## Conventions (mandatory)

- **Everything in English**: code (identifiers, file/folder names, MQTT topics,
  names of LoT Actions/Models/Connectors), code comments and documentation (READMEs, this file).
- Trunk-based git: small commits straight to `main`; `git pull --rebase` before pushing.
- Never commit secrets (`.env` is in `.gitignore`).
- Hackathon: solutions go through plagiarism detection. Do not copy the Coreflux training labs
  (`CorefluxCommunity/weather-station-hackathon`); use them only as a syntax reference.

## Coreflux broker and LoT

Coreflux MQTT broker + HUB in Docker (`broker/`). The logic lives in the broker as LoT
(Actions, Models, Connectors, Rules, Panels); the source of truth is the `.lotnb` files in
`lot/` (mounted read-only in the broker at `/lot`). LoT rules for the AI are in `AGENTS.md`
(imported at the end of this file). **Never write LoT from memory**: use the Coreflux skills in
`.claude/skills/` (pinned to broker 2.22.0) and the `coreflux-docs` MCP server, check against the live broker with
the `coreflux-broker` MCP server (`validate_lot`/`validate_lotnb`), and deploy with `/lot-deploy`.
Setup: `AI.md`. The team has an unlimited
licence (`CFLX-...`, in `broker/.env`, outside git); without it, the Community edition only allows
**3 Connectors**, no custom Rules and no `TYPE LLM`.

## Web app ↔ backend contract

The full contract (Valhalla requests and error handling, barrier and feedback payloads, storage) is in
`app/README.md`, "Backend contract"; the MQTT topic map is in `README.md`. Read them before touching `app/app.js`,
a notebook in `lot/` or `db/schema.sql`. Invariants that are easy to break:

- The backend plugs in through `app/config.js` only (`valhallaUrl`, `brokerUrl`, `topicPrefix` = `access`). The page is
  served over HTTPS, so both endpoints must be HTTPS/WSS and send CORS headers (`Access-Control-Allow-Origin: *`).
- All routing calls are in `routeService` in `app.js`. Steps, surface and barriers are never relaxed; a route above the
  slope limit is always flagged to the person; the Valhalla server must not relax anything either (the page could not tell).
- One **retained** message per barrier on `access/barriers/<id>` (QoS 1). "Já não está" is a **non-retained** message on
  `access/barriers/<id>/feedback` and never removes the barrier. A LoT Action cannot send an empty retained message
  (broker 2.22.0), so the broker retires a barrier by republishing it with `expires_at` = now.
- Changing a payload means changing, in the same commit: `app.js`, `app/README.md`, the topic map in `README.md`, the
  column in `db/schema.sql` and the connector's QUERY in `lot/10-barriers-db.lotnb`.
- The `web` broker user's password in `app/config.js` is public by design; `lot/web_access.lotnb` limits that user to
  `access/barriers/#`.

@AGENTS.md
