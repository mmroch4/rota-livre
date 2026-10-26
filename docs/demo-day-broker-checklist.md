# Demo-day checklist, broker side

The hour before the demo, on Miguel's laptop. The demo runs on localhost: the locally served app, the local broker
`o1n-broker` and the local Valhalla ([`broker-for-pitch.md`](broker-for-pitch.md)). Run every command from the repo
root, with the broker login exported first (default login, loopback only; never print it):

```bash
export BROKER_USERNAME=... BROKER_PASSWORD=...
```

## Before the demo, in order

1. **Containers up and healthy.** `docker ps` lists `o1n-broker`, `o1n-hub` and `passolivre-valhalla`;
   `curl -s localhost:9100/health` says `"healthy"`. If they are down, start the broker with WebSocket:
   `cd broker && docker compose -f docker-compose.yml -f docker-compose.ws.yml up -d broker && cd -`.
2. **If the broker restarted (or you are not sure), repair its LoT.** Wait ~10 s after `/health` is healthy, then
   `python3 broker/redeploy_lot.py --fix`. Next, `python3 broker/redeploy_lot.py --check` must
   print IDENTICAL on every line and exit 0. Every boot brings back an older `ImportCityAlerts`, which ignores the
   switch (`AGENTS.md`, boot-revert quirk).
3. **Valhalla.** `bash runtime/valhalla/setup.sh smoke` passes (start it with `setup.sh start` if needed).
4. **Serve the app locally.** `python3 -m http.server 8765 --bind 127.0.0.1 --directory app`, then open
   <http://127.0.0.1:8765/>. `app/config.local.js` must point `valhallaUrl` at `http://127.0.0.1:8003` and
   `brokerUrl` at `ws://127.0.0.1:9001/mqtt` (check the URLs only; the file also holds the login). Not the hosted page.
5. **City switch ON.**
   `python3 -c "import sys; sys.path.insert(0,'runtime/demo'); from barriers import connect; c=connect(); c.publish('access/city/alerts/enabled', sys.argv[1].encode()); c.close()" on`.
   Wait until the panel's city gauge (or `active.city` in `access/ops/summary`) shows the import: 24 on 24/10
   ("City alerts switch verified"). São Bento → Batalha, wheelchair 6 %, should then be 2.164 km.
6. **Demo barriers only if the script uses them.** `python3 runtime/demo/barriers.py seed`
   (`list` / `clear` likewise). They expire 24 h after seeding, so seed on the day. With the city works on they do
   **not** change the route, because the city detour already avoids them ("City alerts verified", caveats).
7. **Reload every app and HUB tab** opened before a restart: right after one, retained messages can be missing for
   ~5 s after `/health` ("Broker durability verified").
8. **Open the panel.** <http://localhost:3000> → Dashboards → "Rota Livre: barrier operations" (`RotaLivreOps`).
   City gauge as in step 5, indicator "On".
9. **Final check.** `redeploy_lot.py --check` exits 0, and the coreflux-broker MCP `diagnose` shows 0 action errors
   and nothing pending.

## If something breaks live

- **Switch stuck** (`off` does not drop the city gauge or shorten the route): run
  `python3 broker/redeploy_lot.py --check`. If `ImportCityAlerts` DIFFERS, run `--fix`, then send `off` again.
- **Panel frozen:** `access/ops/summary` has an `updated_at`, refreshed every 15 s by `OpsSummaryRefresh`. If it is
  older than that, run `redeploy_lot.py --check` (the `OpsSummary*` Actions), then reload the HUB tab.
- **App shows no barriers:** reload the tab (retained messages are sent again on connect). If it still says
  offline, check `config.local.js` URLs and that the broker was started with `docker-compose.ws.yml` (port 9001).
- **Route fails with every barrier active:** Valhalla allows 1000 polygon vertices only on the local instance
  ("City alerts verified"); make sure the app uses `127.0.0.1:8003`, not the public fallback.
