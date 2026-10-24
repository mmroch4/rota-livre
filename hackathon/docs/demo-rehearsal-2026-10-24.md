# Panel moment rehearsal (24 October 2026, 13:35–13:45 UTC)

One take of the 30-second operator-panel moment from [`broker-for-pitch.md`](broker-for-pitch.md), on Miguel's laptop:
locally served app (`127.0.0.1:8765`), local broker `o1n-broker`, local Valhalla, HUB panel `RotaLivreOps`, Chrome.
São Bento (41.1455, -8.6105) → Batalha (41.1459, -8.6064), wheelchair profile, 6 %.

**Result in one line:** the panel part works as claimed (city 24 → 0 and back, a report shows up as a new row in about
a second), but **the app part did not**. With the switch ON there was no 6 % route at all, not the expected 2.164 km. The cause is a real
app report, `bmvmf2lix8tqd`, which sits on the city detour. Fix that before the demo (see "Before the demo").

## Recordings

| File | What it shows |
|---|---|
| [`media/panel_moment.gif`](media/panel_moment.gif) | The take, 12 frames, both tabs in sequence (the recorder follows whichever tab is acted on): app with no route and panel at rest (city 24, On) → switch off → panel city 0 / Off → app still on the no-route message → replanned 1,3 km route with orange segments → report steps 1–3 → panel app 2 with the "ensaio — apagar" row |
| [`media/panel_moment_end_panel.png`](media/panel_moment_end_panel.png) | Panel end state of the take: app 2, city 0, demo 0, Off, 2 rows |
| [`media/panel_moment_end_app.png`](media/panel_moment_end_app.png) | App end state of the take: test report on Calçada de Vandoma, no 6 % route again |

The GIF is one file, not two: frames of both tabs alternate in it.

## What happened, step by step

| Step (UTC) | Broker / panel | App |
|---|---|---|
| Start, 13:35 | `--check` 8/8 IDENTICAL, summary FRESH; switch `off`, `last_ok` 13:04:41.587Z; active city 0, demo 0, app 1 (`bmvmf2lix8tqd`) | — |
| `on`, 13:36:10.240 | summary city 24 at 13:36:12.055 (1.8 s), `last_ok` 13:36:10.646Z | — |
| Route drawn, 13:40 | panel: app 1, city 24, demo 0, "On", 25 rows | "Não encontrámos um caminho até Praça da Batalha com subidas até 6%" + "Tentar com subidas até 8%", 25 obstacles |
| `off`, 13:41:06.794 | first summary 13:41:06.805 said **city 7** (out-of-order publishes in the burst); the 15 s refresh at 13:41:12.055 set **city 0** (5.3 s). Panel: city 0, grey "Off", trend 25 → 1, 1 row | obstacle count 25 → 1 at 13:41:06.996 (**0.2 s**), but **no reroute**: it stayed on the no-route message |
| Replan, 13:41:28.5 | — | `planRoute()` called by hand (same as searching the destination again): route screen 13:41:30.092 (1.6 s), **21 min, 1,3 km** (Valhalla: 1.302 km), warning "tem 7 partes mais inclinadas do que pediu" with orange segments |
| Report, 13:42:25 | summary `updated_at` 13:42:25.428 with **app 2** (event-driven, under 0.1 s); panel row `bmvmg7khcs08r`, parked_car, "ensaio — apagar" visible at the next screenshot (~13:42:30) | marker on the map at 13:42:25.481; the app replanned by itself and found **no 6 % route** again (the report is on Calçada de Vandoma, the only 6 % way through) |
| Cleanup, 13:43:2x | "Apagar o meu reporte" → summary app 1 at 13:43:27.857; `barriers.py list`: only `bmvmf2lix8tqd` as app barrier | 1 obstacle |
| `on`, 13:43:45.668 | summary city 24 at 13:43:45.994 (0.3 s); panel app 1, city 24, "On" | — |
| End, 13:44 | `--check` 8/8 IDENTICAL + FRESH, exit 0; `diagnose` 0 action errors, nothing pending | — |

End state: switch `on`, 24 city barriers active, 1 app barrier (`bmvmf2lix8tqd`), no test barrier left. São Bento →
Batalha at 6 % with every active barrier excluded: **no route (442)**, not 2.164 km.

## What looked wrong on screen

1. **No route with the switch ON (blocker).** `bmvmf2lix8tqd` (parked car, 41.1466, -8.6110, reported 13:10 UTC,
   expires 25/10 13:10 UTC) plus the 24 city works leave no 6 % route. Valhalla, same request as the app:

   | Excluded | 6 % | 8 % | 10 % |
   |---|---|---|---|
   | nothing | 1.302 km | 1.041 km | 0.971 km |
   | `bmvmf2lix8tqd` only | 1.302 km | 1.041 km | 0.971 km |
   | 24 city only | 2.164 km | 1.474 km | 1.980 km |
   | 24 city + `bmvmf2lix8tqd` | **442** | 1.477 km | 1.983 km |

   The 2.164 km of "City alerts switch verified" was measured at 12:30, before that report existed. It will still be
   active during the demo. I did not remove it: you asked me to leave it alone, and retiring it from the broker was
   refused by the session's permission check. Its original payload is saved in my scratchpad in case it is needed.
2. **The app does not reroute from the no-route message.** `barriersChanged()` (`app/app.js:1211`) replans only when
   `state.screen === "route"`. On the no-route message the screen is `"plan"`, so switching `off` updated the obstacle
   count but left the message up until a new search. When a route is drawn, a barrier change does replan by itself
   (seen when the test report landed). Not fixed (Ben's file); worth a look if the demo depends on it.
3. **Panel showed a wrong intermediate count.** Right after `off`, the summary briefly said city 7 before the
   refresh corrected it to 0 within ~5 s. The baseline already notes that publishes can arrive out of order. If the
   presenter watches the gauge, it may stop at 7 for a few seconds before reaching 0.
4. **Orange "steeper than asked" segments on the 1,3 km route** (7 parts flagged), although every edge is within 6 %:
   the known `degreesToPercent` bug. A fix, `5f33747` ("read trace_attributes grades as percent, not degrees"), was
   committed locally at 13:41:09 UTC, during the take and after the page had loaded, so it was not seen here. At
   13:45 it was still unpushed and conflicts with Ben's pushed app commits (see "Not committed" below).
5. **The report form starts at the laptop's own position** (FCUP, Campo Alegre), not on the route: the pin has to be
   moved to the street before "Seguinte". For the take, the mini-map was moved to a point on the drawn route with
   `reportMap.setView(...)`, the same as a drag.

## How the take was driven (so the timings can be trusted)

- Start/destination were set through the page's own `state.from`/`state.to` and `planRoute()`, not by typing in the
  search box (that path, which uses Nominatim, was not exercised). The replan after `off` was the same call.
- Report: real UI clicks (orange button → Seguinte → "Carro no passeio" → Seguinte → description → Enviar), apart
  from the mini-map move above. Delete: real click on the marker and "Apagar o meu reporte".
- Switch: the documented one-liner. Timings: a 0.5 s poll of `access/ops/summary` and a 0.2 s in-page log of the
  obstacle count and screen. The panel's own redraw was not timed: it showed the new values at the next screenshot,
  ≤ 8 s after each event.
- The app was served by an already running `http.server` on 8765 (pid 3592781), not one started by me.

## Before the demo

The parked-car report has to go, or the script has to change:

- **Best:** whoever reported `bmvmf2lix8tqd` deletes it from that browser ("Apagar o meu reporte"; only that device
  sees the button). Then the planned script holds: 2.164 km with city on, 1.302 km off.
- **Or** retire it from the broker the way the broker retires barriers (republish its payload retained with
  `expires_at` = now). Supabase keeps the row either way.
- **Fallback without touching it:** use 8 % (the "Andarilho ou canadianas" profile). City on: 1.477 km; off: 1.041 km.
  A route is drawn in both states, so the app reroutes by itself. Measured in Valhalla only, not rehearsed in the browser.

## What to click (for Victor), assuming the parked-car report is gone

Setup (Miguel, before): `demo-day-broker-checklist.md` steps 1–9, switch **on**, panel maximized in one window and the
app in another, side by side.

1. **App:** "Para onde quer ir?" → Praça da Batalha; "Mudar" → Estação de São Bento; keep "Cadeira de rodas".
   Say: "with today's Câmara works, the step-free route is 2,2 km". The panel shows city 24, "On".
2. **Terminal:** run the switch one-liner with `off`. Say: "the operator turns the city feed off".
3. **Panel:** city gauge drops to 0 (it can stop at a wrong value for up to ~5 s), indicator grey "Off".
   **App:** the route redraws by itself, 1,3 km. Mention that the orange "steeper" warning is a known display bug.
4. **App:** orange button → move the pin onto the street → Seguinte → "Carro no passeio" → Seguinte → Enviar.
   **Panel:** "app" gauge +1 and a new row within a second or two.
5. **App:** tap the new marker → "Apagar o meu reporte" (panel app gauge −1). Then switch **on** again for the next run.

If step 1 shows "Não encontrámos um caminho", the parked-car report is still there: switch to the 8 % profile (see above).

## Not committed at first (git)

At 13:45 local `main` held two unpushed app commits (`5f33747`, `8bf5bc5`) while `origin/main` had three new app
commits by Ben (`077ccc1`, `d3a2749`, `f49d148`). `git pull --rebase` stopped with conflicts in `CLAUDE.md` and
`hackathon/app/app.js`; the rebase was aborted (tree back to `8bf5bc5`, clean) and these docs waited until the app
commits are reconciled by their owner.

## Blocker removed (13:51 UTC)

On Miguel's go-ahead, `bmvmf2lix8tqd` was retired the way the broker retires barriers: its original payload
republished retained with `expires_at` = 2026-10-24T13:50:59.994Z (the app hides it; Supabase keeps the row). Right
after: summary app 0, city 24; São Bento → Batalha at 6 % with every active barrier excluded = 2.164 km, and a freshly
loaded app tab drew "35 min 2,2 km". The original payload (expiry 2026-10-25T13:10:33.849Z) can be republished to
undo it. The click script above now applies as written; the 8 % fallback is no longer needed.
