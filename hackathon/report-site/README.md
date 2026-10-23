# report-site (Rua Viva)

Citizen-facing website for reporting problems in Porto (potholes, broken streetlights, garbage…).
Plain HTML/CSS/JS, no build step.
The interface is in European Portuguese (pt-PT); code, comments and JSON keys stay in English.

- Upload a photo; its GPS location is read from the photo's EXIF data when present.
- Otherwise use the browser's location or click the map.
- Pick a category, add an optional description, send.

**Status:** frontend only. Reports are stored in the browser's `localStorage`.
Next step: make `sendReport()` in `app.js` publish the report JSON to the Coreflux broker
on `porto/reports/new` (MQTT over WebSockets).

## Run

```bash
python -m http.server 8090 --directory hackathon/report-site
```

Then open http://localhost:8090.
