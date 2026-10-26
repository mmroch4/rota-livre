# Rota Livre web app

Static page (HTML + JS, no build step) for accessible walking routes in Porto. UI in European Portuguese.
Map-first layout inspired by Waze: a full-screen map with floating cards (a bottom sheet on phones), round
buttons and Lucide icons.

Flow: **welcome** (first visit only: "how do you get around?", five profiles from wheelchair to *no mobility
difficulties*, remembered in `localStorage`; the chip at the top changes it, with the slope/steps/surface/barrier
options under *Opções avançadas*) → **plan** ("Para onde quer ir?" opens a full-screen search; tapping the map also
picks a destination) → **route** (shown as soon as a destination is chosen: time, arrival time, a one-line
verdict, the streets you pass; when a barrier appears or goes away and the route changes, a short message says why and how much longer or shorter it is) → **guide** (turn arrow and distance on top, arrival/time/distance at the bottom,
the map follows you, recalculates when you leave the route or a new barrier appears ahead). The orange button
reports a barrier with one tap on its type.

Open with `?demo` (e.g. `http://localhost:8765/?demo`) for the pitch: the position starts at the map centre and
walks along the route by itself.

All routing calls are in `routeService` in `app.js`, so the routing backend can change without touching the screens.

- **Routes:** Valhalla `/route` with `costing: pedestrian`: `max_grade` from the slope slider, `type: wheelchair`
  to avoid rough surfaces, a maximum `step_penalty` to avoid steps, and barriers sent as `exclude_polygons`
  squares. On a Valhalla that ignores `max_grade` (the public one), the page also re-routes around the parts steeper
  than the limit, up to 3 requests (`saferRoute`). If there is no route under the slope limit, the page retries 2 % higher each time
  and finally without a limit, and says clearly that the route is steeper than asked (steep parts in orange). Steps,
  surface and barriers are never relaxed.
- **Details:** Valhalla `/trace_attributes` for the steepest climb and descent, and the sections near the limit
  (orange on the map).
- **Barriers:** the report dialog shows one step at a time ("Passo N de 3" with a progress bar, Voltar/Seguinte;
  "Seguinte" stays disabled until a type is picked) and asks *where* first: a small map with a fixed pin that the person moves the map
  under, with the address filled in automatically (Nominatim reverse, once the map stops), or typed and searched,
  or "my location". Then the type (one of six tiles), then an optional photo and description; anyone can remove one ("Já não está lá");
  reports expire after 24 h. With `brokerUrl` set they are shared live through the Coreflux broker over
  MQTT/WebSocket. **Until then (no `brokerUrl`) they are kept on the device** (`localStorage`, key
  `access.barriers`): they show on the map and that device's routes avoid them, but nobody else sees them.
  Photos (shrunk to 800 px JPEG) and the address text stay on the reporting device; they are not part of the
  MQTT payload.
- **Search:** Nominatim, limited to Porto, only when the user presses Enter.

Kerb height cannot be filtered: Valhalla's pedestrian costing has no option for it.

## Settings

`config.js` (committed, no secrets): `valhallaUrl`, `brokerUrl` (`wss://…`), `topicPrefix`, map centre.
Local overrides go in `config.local.js` (gitignored):

```js
Object.assign(window.APP_CONFIG, {
    valhallaUrl: "https://valhalla1.openstreetmap.de", // public instance: no custom slope cap
    brokerUsername: "…",
    brokerPassword: "…",
});
```

The hosted page needs the broker login in the browser, so use a broker user that can only read and write
`access/barriers/#`.

## Backend contract

The backend plugs in through `config.js` only: `valhallaUrl`, `brokerUrl`, `topicPrefix` (`access`). The page is
served over HTTPS: **both endpoints must be HTTPS/WSS and send CORS headers** (`Access-Control-Allow-Origin: *`),
or the browser blocks them. If this contract changes, update `routeService` in `app.js`, this section and the topic
map in the root `README.md` in the same commit.

### Routing (Valhalla HTTP API)

Today `valhallaUrl` is the slope-aware instance through its tunnel (it changes when
the tunnel container is recreated). With the public FOSSGIS instance, which ignores the slope cap, the page steers
around steep parts itself (`saferRoute`, below). The slope-aware instance is
`runtime/valhalla/` (local on `http://127.0.0.1:8003`, public through its opt-in `compose.tunnel.yml`).
- `POST {valhallaUrl}/route` with `locations` (start, destination), `costing: "pedestrian"`,
  `costing_options.pedestrian` = `type` (`"wheelchair"` when avoiding rough surfaces, else `"foot"`), `max_grade`
  (percent, 2–14; **omitted** for "no limit"), `step_penalty: 43200` when avoiding steps; `exclude_polygons`
  (one closed `[lon, lat]` square of ±15 m around each active barrier); `units: "kilometers"`, `language: "pt-PT"`.
- Read from the response: `trip.summary.{length,time}`, `trip.legs[0].shape` (polyline, 6 decimals),
  `legs[0].maneuvers[].{type, instruction, street_names, length, begin_shape_index, end_shape_index}`
  (types 4–6 = arrival). Errors: `error_code` 442/443 = no route under the limits: the page retries with
  `max_grade` +2 % each time and finally without it (`gentlestRoute`), and **always tells the person** when the route
  is above their limit; steps, surface and barriers are never relaxed. 170/171 = point too far from a path, anything
  else = "try again". The Valhalla server itself must not relax anything (the page could not tell).
- `POST {valhallaUrl}/trace_attributes` with `encoded_polyline`, `shape_match: "edge_walk"`, the same costing and
  `filters.attributes` = `edge.length`, `edge.use`, `edge.max_upward_grade`, `edge.max_downward_grade`,
  `edge.begin_shape_index`, `edge.end_shape_index`. Grades are **percent** (Valhalla stores rise/run × 100
  despite its "degrees" comments);
  32768 = no elevation. Used for the "steeper than you asked" warning; if it fails, the route still shows.

### Barriers (Coreflux MQTT over secure WebSocket)

Today `brokerUrl` is the team's broker through its quick tunnel
(it changes when the tunnel container is recreated). With `brokerUrl` empty, reports stay on the device
(`localStorage` key `access.barriers`) and nobody else sees them. The broker is the team's local Docker one,
  reached through the opt-in Cloudflare tunnel (`broker/docker-compose.tunnel.yml`, steps in the root `README.md`)
  as user `web`, which `lot/web_access.lotnb` limits to `access/barriers/#`.
- Topic `access/barriers/<id>`, one **retained** message per barrier, QoS 1. The page subscribes to
  `access/barriers/+` and publishes new reports itself. Only the device that made a report may delete it
  ("Apagar o meu reporte"), by publishing an **empty retained** payload on its topic.
- **"Is it still there?" answers:** while guiding, passing within 30 m of a barrier asks "Ainda está aí?" (once per
  barrier per trip; gone after 10 s without an answer). "Ainda está" sends nothing. "Já não está" (from that card
  or from a barrier's popup) **does not remove the barrier**: it publishes a **non-retained**, QoS 1 message on
  `access/barriers/<barrier id>/feedback` = `{"id", "barrier_id", "answer": "gone", "answered_at", "lat"?, "lon"?}`
  (`lat`/`lon` = where the person was, when known). **The backend must store these** (the page does not keep them
  once sent); the team reviews the counts per barrier at the end of the day and decides. The broker Action
  `StoreBarrierFeedback` (`lot/barrier_feedback.lotnb`) stores them under `access/feedback/<barrier id>/`
  (see the topic map in the root `README.md`). Until a broker is
  connected, answers wait in the device outbox (`localStorage` key `access.feedbackOutbox`) and are sent on connect.
- Payload: `{"id", "kind", "description", "lat", "lon", "reported_at", "expires_at"}` (ISO 8601 times; `id` like
  `b<base36 time><random>`; `description` may be `""`; expiry = report + 24 h). `kind` is one of `works`,
  `blocked_sidewalk`, `parked_car`, `broken_lift`, `damaged_pavement`, `other`. Unknown kinds show as `other`;
  messages without numeric `lat`/`lon` are ignored, extra fields are ignored.
- The page hides barriers past `expires_at` itself. A LoT Action cannot send an empty retained message (broker
  2.22.0), so the broker retires a barrier by republishing it with `expires_at` = now.
  Barriers published by the backend appear and are avoided like any report: `ImportCityAlerts`
  (`lot/city_alerts.lotnb`) imports the Câmara's active road works near the demo route as `city-<id>`
  barriers (`kind: "works"`, `expires_at` = the alert's end, extra field `source: "cm-porto"`).
  Retained `access/city/alerts/enabled` = `off` retires all of them the same way and pauses the import; `on` resumes it
  and republishes them at once (no flag counts as `on`). What was imported is kept in the internal retained topic
  `access/state/city_alerts` (broker only). Broker durability is on: every retained message above survives a restart.
- **Operator panel.** The broker keeps a retained `access/ops/summary` (active barriers per source, active list,
  "gone" counts; `lot/ops_panel.lotnb`) for the read-only HUB panel `RotaLivreOps`. The app does not read it.
- Valhalla rejects more than `max_exclude_polygons_vertices` (default 100 = 20 squares, error 176). So
  `saferRoute` in `app.js` starts with the barriers within 100 m of the start–destination line and, for up to 3
  requests, adds what each route runs into: barriers it goes through, then (with a slope limit) its parts steeper
  than the limit, read with `trace_attributes`; it keeps the route with the fewest barriers, then the fewest metres
  over the limit. The custom instance allows 1000 (`runtime/valhalla/setup.sh`); the public one does not.
- Not sent to the broker (device-only for now): the report's photo (≤ 800 px JPEG data URL) and the address text.
  Sharing them means adding optional `photo`/`address` fields to this contract first.

### Storage (Supabase Postgres, written by Coreflux)

Coreflux is the backend: `lot/10-barriers-db.lotnb`
(Action `RouteBarrierMessage` + PostgreSQL connector `BarriersDB`) stores reports in `barriers` (a reporter's
delete sets `deleted_at`, rows are never removed) and answers in `barrier_feedback`; the view `barrier_review`
is the end-of-day count. Schema, tests and setup: `db/` (`schema.sql`, `README.md`). Internal topics
`access/db/barriers/upsert` and `access/db/barriers/deleted` are for the broker only. The connector's
credentials are broker env/secrets (`SUPABASE_DB_HOST`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`), never git.
If you add a field to a payload above, add the column in `schema.sql` and the value in the connector's QUERY.

## Run locally

```bash
python -m http.server 8765 --directory app
```

## Deploy (Cloudflare)

Live at <https://accessible-routes.benlubetzky.workers.dev> (add `?demo` for the pitch). It is a Cloudflare Worker
that only serves this folder's static files (`wrangler.jsonc`; `.assetsignore` keeps the README and local config out).

**Automatic:** the GitHub Action [`deploy-app.yml`](../.github/workflows/deploy-app.yml) redeploys on every push
to `main` that touches `app/` (or by hand: Actions tab → *Deploy web app* → *Run workflow*).
It needs the repository secret `CLOUDFLARE_API_TOKEN`: a token from Cloudflare (My Profile → API Tokens →
Create Token → template *Edit Cloudflare Workers*), added by the repo owner under Settings → Secrets and
variables → Actions.

**By hand** (from `app/`, logged in with `npx wrangler login`):

```bash
npx wrangler deploy
```

The hosted page needs our Valhalla over HTTPS: its opt-in tunnel (`runtime/valhalla/compose.tunnel.yml`) prints a
`https://<random>.trycloudflare.com` address to set as `valhallaUrl` in `config.js`.
