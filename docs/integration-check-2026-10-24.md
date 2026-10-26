# Browser integration check — 24 October 2026

Verified by Codex at approximately 12:10–12:14 UTC on Miguel's laptop.
Scope: connectivity, UI report submission, propagation, retained delivery, rerouting and cleanup.
No frontend, broker automation, account, deployment or service configuration was changed.

## Result

**Local demo passes; hosted shared-report demo is blocked by missing configuration.**

| Surface | Configuration / observation | Result |
|---|---|---|
| Hosted app | `https://accessible-routes.benlubetzky.workers.dev` | Loads; displays that reports stay on this device |
| Hosted routing | Public `config.js` uses `https://valhalla1.openstreetmap.de` | POST `/route` with `Content-Type: text/plain` and hosted Origin returns HTTP 200 and `Access-Control-Allow-Origin: *`; this is not the custom slope-aware service |
| Hosted broker | Public `brokerUrl` is empty | No WSS endpoint configured; cross-device reports cannot work in this deployment |
| Local app | `http://127.0.0.1:8765/`, existing ignored `config.local.js` | Loads and reports real-time barriers |
| Local routing | `http://127.0.0.1:8003` | Browser routes successfully with wheelchair profile |
| Local broker | `ws://127.0.0.1:9001/mqtt` | UI reports propagate and retained messages arrive after reload |

Two Chrome tabs used the same browser profile and origin. This proves separate live app/MQTT
connections, not separate devices, separate browser storage or cross-device deletion permissions.
No geolocation permission was granted; all test locations were entered manually.

## Observed browser sequence

1. Select the **Cadeira de rodas** profile. Search for origin `41.1455, -8.6105`
   and choose **Praça de Almeida Garrett**. Search destination `41.1459, -8.6064`
   and choose **Cervejaria Artesanal Levare**. These searches resolve to named OSM
   places, so they need not use the exact coordinates of the API regression fixture.
2. Initially the local route showed **1.3 km / 21 min**.
3. During the session, **24 other barriers arrived through the shared broker**.
   The existing route automatically changed to **2.2 km / 35 min**. These barriers
   were preserved. The same route was planned in the second tab.
4. In tab A, use the orange report button. Search **Rua da Firmeza 300, Porto**,
   select **Passeio bloqueado**, and use description
   `TESTE DE INTEGRAÇÃO CODEX — temporário, remover após verificação.`
   Submit. The marker appeared in both tabs. This placement did not visibly change the route.
5. Reload tab B: the report returned, with **25 obstacles** shown. Tab A's popup
   showed the test description. Choose **Apagar o meu reporte** in A: it disappeared
   from both tabs and B returned to **24 obstacles**.
6. Restore B's origin/destination after reload (routes themselves are not retained).
   In A, create another labelled **Passeio bloqueado** report at
   **Rua do Doutor Alves da Veiga 100, Porto**.
7. Both tabs changed their itinerary without reload:
   - Before: **Rua do Doutor Alves da Veiga 420 m → Rua Formosa 40 m**.
   - With report: **Rua do Doutor Alves da Veiga 200 m → Rua de Fernandes Tomás 95 m
     → Rua de Dom João IV 205 m**.
   - The rounded headline remained **2.2 km / 35 min**; use the street list and map
     to show the actual detour, not rounded distance alone.
8. Delete that report through A's **Apagar o meu reporte**. Both tabs restored
   **Rua do Doutor Alves da Veiga 420 m → Rua Formosa 40 m**.

Both Codex test reports were removed. No other reports were cleared. Retention
was tested across a page reload, not a broker restart. The test did not exercise
moving-position guidance, feedback processing or expiry (Claude's automation scope).

## Repeatable demo

- Open two tabs of the local app, select the wheelchair profile and set the route
  above in each tab. Confirm the existing obstacle set before choosing the test street.
- With the 24-barrier background seen during this check, use the Alves da Veiga
  report sequence above. Verify the changed street list in both tabs, then delete
  only the report just created and verify restoration.
- For a reload check, reload the observer while the report is present, confirm its
  marker, then re-enter the route before testing cleanup/rerouting.
- Do not clear other people's barriers to force fixture distances. City intake
  changes the baseline. Coordinate a stable obstacle set before recording the pitch.
- For an independent routing regression that does not touch the broker, run:

  ```bash
  python3 runtime/demo/check_routes.py
  ```

  That script sends only its explicit fixture exclusions to Valhalla. Expected
  fixture lengths: 1.302 km baseline, 1.721 km roadworks, 1.437 km parked car,
  1.856 km both. It checks unchanged control/reset geometry and interior grades
  within 6%. These are API-fixture results, not guaranteed UI distances with live city barriers.

## Handoff and remaining blockers

**Ben — slope display:** the existing `degreesToPercent` conversion in `app.js`
still applies `tan()` to values the custom backend stores as percent. The initial
1.3 km route displayed seven overly steep sections even though the API check passes
the interior 6% cap. Existing runtime-baseline notes already diagnose this. Coordinate
the display fix with the contract documentation. Endpoint partial edges remain a
separate, real routing limitation; do not suppress all warnings.

**Hosted integration:** supply a reachable HTTPS endpoint for the custom Valhalla
and a WSS endpoint with an appropriate browser account, then coordinate deployment
configuration with Ben. The current checked-in policy keeps services on loopback;
this verification did not establish public tunnels or expose the broker. The hosted
app is currently suitable for a public-routing/device-only demonstration, not a
claim that the custom cap and shared reports are connected.

**Demo coordination:** confirm which city barriers Claude's intake will keep active
before rehearsing. The working local demo does not require changing that automation.

## Repeatable city-off verification — follow-up starting 12:39 UTC

Miguel selected **keep city import off for the demo**. No city-on repositioning is
required for this sequence; the existing demo coordinates remain unchanged.
The supported switch command and presenter sequence are now in `runtime/demo/README.md`.

Baseline work committed as `c7e40f5`, after 15 offline unit tests and all independent
`check_routes.py` fixtures passed. Switch-state reporting adds a sixteenth test:
retained on/off, missing default-on, invalid values, and concurrent switch updates.
All 16 tests pass. The checker subscribes read-only to both barriers and the switch.

| UTC | Operation | Switch | Retained / active / city active | Exact API route |
|---|---|---|---|---|
| 12:39:55 | Publish retained `off`, run live checker | retained off | 24 / 0 / 0 (24 expired) | 1.302 km, 1281.263 s |
| 12:41:17 | Seed the existing two demo barriers, run live checker | **missing**, default on | 2 / 2 / 0 | 1.856 km, 1763.952 s |

Both API runs passed interior grade checks with no missing elevation or violations:
baseline 62 interior edges (+6% / −5%); detour 75 (+6% / −6%). Endpoint candidates
were separately reported at +1% / −3% in both cases.

The off flag and 24 expired city records disappeared between checks. Tab A briefly
showed disconnected/reconnecting, then reconnected. This is evidence of state loss
or external mutation, **not proof of a restart or of durability**. Broker commands
were paused and Miguel was asked to confirm stability before further mutations.
The demo barriers were seeded at 12:41:16 UTC, expiring 25 October at 12:41:16 UTC.

Browser observations so far in this follow-up: two fresh Chrome tabs of the local
app, same profile/origin, each routed the named São Bento → Batalha search results
with Cadeira de rodas and displayed **1.3 km / 21 min** before seeding. The existing
seven-section slope-display warning remained. Exact distances in the table are
API checks, not measurements extracted from browser requests. Subsequent detour,
reload and clearing observations will be recorded separately after broker stability
is confirmed. No services were restarted or reconfigured by this session.

### Stable-broker retry — 12:43 UTC: city-off regression

Miguel confirmed the broker was stable and authorized resuming checks. Published
retained `off` again, cleared only `demo-*`, then checked again after nine seconds:

| UTC | Operation | Switch | Active city / total | Exact API route |
|---|---|---|---|---|
| 12:43:26 | Publish off, snapshot | retained off | 24 / 26 | 2.164 km |
| 12:43:29 | Clear demo barriers, snapshot | retained off | 24 / 24 | 2.164 km |
| 12:43:35 | Read-only retry | retained off | 24 / 24 | 2.164 km |

All 24 city records were unexpired. Both existing browser tabs changed without
reload from **1.3 km / 21 min** to **2.2 km / 35 min**, with 24 works markers and
the city itinerary through Alves da Veiga. This confirms live updates, but **does
not pass the requested city-off demo sequence**. Its seed/reload/clear acceptance
remains incomplete. Miguel was asked to have Claude investigate `SwitchCityAlerts`;
no LoT changes or manual city-barrier retirement were performed here.

The checker initially returned PASS for these snapshots because routing and grade
checks succeeded. It now also fails `city_switch_mismatch` when off coexists with
active city barriers, retaining route/grade diagnostics. An offline regression test
covers that case. Current broker intent: retained off; demo barriers cleared.
Restart durability remains unverified: there is no controlled before/after snapshot
of identical barrier payloads and switch across a confirmed restart in this session.

## Repaired switch and completed browser sequence — 12:47–12:48 UTC

Miguel relayed Claude's diagnosis: the durability restart at 12:43 retained city
barriers but lost the memory-only `access/state/city_alerts` import snapshot, leaving
`off` with no known barriers to retire. Claude changed that snapshot to retained
storage and verified on → off at 12:45 (24 imported, then 24 retired). Claude also
reported that retained messages now survive broker restarts. This is owner-reported
restart evidence; this session did not restart the broker or deploy any LoT.

The following checks were then performed directly by this session, with both
existing Chrome tabs, local app :8765, broker WebSocket :9001/mqtt and Valhalla :8003:

| UTC / step | Live checker | Browser observation |
|---|---|---|
| 12:47:36 baseline | retained off; 24 expired records; 0 active; 1.302 km / 1281.263 s | Both tabs at 1.3 km / 21 min, no barrier markers |
| 12:47:48 after `barriers.py seed` | retained off; 26 retained, 2 active, 0 active city; 1.856 km / 1763.952 s | Both existing tabs changed without reload to 1.9 km / 29 min and two markers |
| Observer reload | Same seeded broker state; no mutation | Two retained markers returned, “2 obstáculos no mapa”; after re-entering the route, 1.9 km / 29 min and the same detour itinerary |
| 12:48:35 after `barriers.py clear` | retained off; 24 expired records, 0 active; 1.302 km / 1281.263 s | Both tabs changed without reload to 1.3 km / 21 min, no barrier markers, original itinerary restored |

The visible detour included Rua do Corpo da Guarda (175 m) and Rua do Sol (215 m).
Clearing restored Caminho pedonal (410 m) and Rua de Augusto Rosa (400 m).
Exact km/seconds are from the live checker with exact fixture coordinates; browser
headlines are rounded and endpoints are named search results. Routes themselves
are not retained across page reload; barrier messages are. The two tabs share a
Chrome profile/origin, so this does not establish independent devices/storage.
This run used CLI-seeded reports; browser-created report propagation was tested in
the earlier 12:10–12:14 sequence, not repeated here.

All live checks passed: no concurrent updates, invalid records, missing interior
elevation or interior grade violations. Baseline/reset: 62 interior edges, +6%/−5%;
detour: 75, +6%/−6%; endpoint candidates separately +1%/−3%. The app still showed
the known slope-display warning (7 baseline sections, 11 detour sections); this
remains Ben's issue and is not evidence that the interior API cap failed.

Final regression commands: 17 offline tests passed; `check_routes.py` passed all
fixtures (baseline/control/reset 1.302, roadworks 1.721, car 1.437, both 1.856 km),
including interior grades and unchanged control/reset geometry.

**Demo acceptance passes after the repair.** Final state: city switch retained off,
demo barriers cleared, zero active city barriers; no city-on step requested by Miguel.
No demo barrier positions were changed. Durability is attributed to Claude's report:
this session has not independently captured an unchanged switch plus identical demo
payloads immediately before and after a controlled restart. Post-restart functionality,
fresh retained replay, route changes and cleanup have all been checked directly.
