# Route planner (web app)

Static page (HTML + JS, no build step) for accessible walking routes in Porto. UI in European Portuguese.

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

## Deploy (Cloudflare Pages)

Upload the `hackathon/app/` folder as a Pages project (no build command). Pedro's Valhalla must be reachable
over HTTPS, e.g. with `cloudflared tunnel --url http://localhost:8003`, and its URL set as `valhallaUrl`.
