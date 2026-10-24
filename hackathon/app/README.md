# Route planner (web app)

Static page (HTML + JS, no build step) for accessible walking routes in Porto. UI in European Portuguese.

Screens: **welcome** (first visit only: "how do you get around?", remembered in `localStorage`) → **plan**
("where do you want to go?", start = your location unless changed; everything else under *Opções avançadas*)
→ **route** (time, one-line verdict, the streets you pass) → **guide** (live position, next-step banner, map
follows you, recalculates when you leave the route or a new barrier appears ahead).

Open with `?demo` (e.g. `http://localhost:8765/?demo`) for the pitch: the position starts at the map centre and
walks along the route by itself.

All routing calls are in `routeService` in `app.js`, so the routing backend can change without touching the screens.

- **Routes:** Valhalla `/route` with `costing: pedestrian`: `max_grade` from the slope slider, `type: wheelchair`
  to avoid rough surfaces, a maximum `step_penalty` to avoid steps, and every active barrier sent as an
  `exclude_polygons` square. If there is no route, the page says so and offers a higher slope; it never relaxes
  the limits by itself.
- **Details:** Valhalla `/trace_attributes` for the steepest climb and descent, and the sections near the limit
  (orange on the map).
- **Barriers:** reported and shown live through the Coreflux broker over MQTT/WebSocket.
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

## MQTT topics

| Topic | Retained | Payload |
|-------|:--------:|---------|
| `access/barriers/<id>` | yes | `{"id","kind","description","lat","lon","reported_at","expires_at"}`; an empty message removes it |

`kind`: `works`, `blocked_sidewalk`, `parked_car`, `broken_lift`, `damaged_pavement`, `other`.

## Run locally

```bash
python -m http.server 8765 --directory hackathon/app
```

## Deploy (Cloudflare)

Live at <https://accessible-routes.benlubetzky.workers.dev> (add `?demo` for the pitch). It is a Cloudflare Worker
that only serves this folder's static files (`wrangler.jsonc`; `.assetsignore` keeps the README and local config out).

**Automatic:** Cloudflare's Git integration redeploys on every push to `main` that touches `hackathon/app/`.
One-time setup in the dashboard: Workers & Pages → `accessible-routes` → Settings → Build → Connect →
`mmroch4/scitech-2026`, branch `main`, root directory `hackathon/app`, deploy command `npx wrangler deploy`,
build watch paths `hackathon/app/*`.

**By hand** (from `hackathon/app/`, logged in with `npx wrangler login`):

```bash
npx wrangler deploy
```

Pedro's Valhalla must be reachable over HTTPS, e.g. with `cloudflared tunnel --url http://localhost:8003`, and its
URL set as `valhallaUrl` in `config.js`.
