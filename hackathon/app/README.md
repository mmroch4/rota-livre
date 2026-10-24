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
  to avoid rough surfaces, a maximum `step_penalty` to avoid steps, and every active barrier sent as an
  `exclude_polygons` square. If there is no route under the slope limit, the page retries 2 % higher each time
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

## MQTT topics

| Topic | Retained | Payload |
|-------|:--------:|---------|
| `access/barriers/<id>` | yes | `{"id","kind","description","lat","lon","reported_at","expires_at"}`; an empty message removes it |
| `access/barriers/<barrier id>/feedback` | no | `{"id","barrier_id","answer":"gone","answered_at","lat"?,"lon"?}`: someone says it is gone; stored by the backend for review, removes nothing |

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
