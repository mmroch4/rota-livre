# report-site (Passo Livre)

The phone app of [Passo Livre](../README.md). Today it is the **obstacle report form**, built by Ben on 23/10 as the
report form of the previous idea (Rua Viva); it grows into the full phone app (plan a trip, travel, report).
Plain HTML/CSS/JS, no build step.
The interface is in European Portuguese (pt-PT); code, comments and JSON keys stay in English.

- Upload a photo; its GPS location is read from the photo's EXIF data when present.
- Otherwise use the browser's location or click the map.
- Pick a category, add an optional description, send.

**Status:** frontend only. Reports are stored in the browser's `localStorage`, and the categories are still the
general public-space ones (pothole, streetlight, garbage…).

**Next steps** (contract: [topic map](../README.md#mqtt-topic-map)):
- **#14 Report an obstacle:** replace the categories with the barrier kinds from `config/barrier_kinds`
  (`sidewalk_blocked`, `works`, `broken_pavement`, `lift_out`, `missing_ramp`, other); make `sendReport()` in `app.js`
  publish the photo on `passolivre/photos/<photo_id>` and the Model `Report` on `passolivre/reports/new` (MQTT over
  WebSocket); show the `analysis`, the `match` and the ReportaPorto `handoff`.
- **#13 Plan + travel:** a second screen: profile, destination (demo trips one tap away), route with reasons,
  *Start* (simulated walk publishing `passolivre/trips/<trip_id>/status`), reroute alert.

## Run

```bash
python -m http.server 8090 --directory hackathon/report-site
```

Then open http://localhost:8090.
