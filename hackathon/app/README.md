# Rota Livre web app

Static page (HTML + JS, no build step) for accessible walking routes in Porto. UI in European Portuguese.
Map-first layout inspired by Waze: a full-screen map with floating cards (a bottom sheet on phones), round
buttons and Lucide icons.

Flow: **welcome** (first visit only: "how do you get around?", five profiles from wheelchair to *no mobility
difficulties*, remembered in `localStorage`; the chip at the top changes it, with the slope/steps/surface/barrier
options under *Opções avançadas*) → **plan** ("Para onde quer ir?" opens a full-screen search; tapping the map also
picks a destination) → **route** (shown as soon as a destination is chosen: time, arrival time, a one-line
verdict, the streets you pass) → **guide** (turn arrow and distance on top, arrival/time/distance at the bottom,
the map follows you, recalculates when you leave the route or a new barrier appears ahead). The orange button
reports a barrier with one tap on its type.

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

**Automatic:** the GitHub Action [`deploy-app.yml`](../../.github/workflows/deploy-app.yml) redeploys on every push
to `main` that touches `hackathon/app/` (or by hand: Actions tab → *Deploy web app* → *Run workflow*).
It needs the repository secret `CLOUDFLARE_API_TOKEN`: a token from Cloudflare (My Profile → API Tokens →
Create Token → template *Edit Cloudflare Workers*), added by the repo owner under Settings → Secrets and
variables → Actions.

**By hand** (from `hackathon/app/`, logged in with `npx wrangler login`):

```bash
npx wrangler deploy
```

Pedro's Valhalla must be reachable over HTTPS, e.g. with `cloudflared tunnel --url http://localhost:8003`, and its
URL set as `valhallaUrl` in `config.js`.
