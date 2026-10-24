# Read-only live barrier route check

Owned by Codex: `check_live_routes.py`, `test_check_live_routes.py`, this file.
Standard-library Python, Linux/POSIX (uses SIGALRM for a hard overall deadline).
No package installation required. Run from the repository root with the existing
broker credentials already exported as `BROKER_USERNAME` and `BROKER_PASSWORD`:

```bash
python3 hackathon/runtime/demo/check_live_routes.py --json
```

Omit `--json` for labelled diagnostic lines. Credentials are environment-only,
never command-line options or output. Use the same authorized login as the ignored
`hackathon/app/config.local.js`, per the demo README. Do not paste that file or
`.env` into logs. The CLI does not automatically load either file. For the recorded
test, a local Python wrapper extracted only `brokerUsername`/`brokerPassword`
string literals into the child process environment, without printing their values
or executing JavaScript. No credentials were written to any new file.

| Input | Environment | Default |
|---|---|---|
| `--broker-host` | `BROKER_HOST` | `127.0.0.1` |
| `--broker-port` | `BROKER_PORT` | `1883` (plain MQTT TCP) |
| `--topic-prefix` | `TOPIC_PREFIX` | `access` |
| `--valhalla-url` | `VALHALLA_URL` | `http://127.0.0.1:8003` |
| `--connect-timeout` | — | 5 seconds |
| `--read-timeout` | — | 1.5 seconds, quiet window / complete packet budget |
| `--snapshot-timeout` | — | 8 seconds, including busy traffic |
| `--http-timeout` | — | 20 seconds per socket operation |
| `--overall-timeout` | — | 55 seconds for the complete check |

Explicit options override environment values. Keep this setup on loopback. The
overall deadline also bounds DNS, slow HTTP bodies and connection handshakes.
No automatic reconnect/retry or cap relaxation occurs.

## Read-only behavior and snapshot semantics

The checker reuses `barriers.Mqtt` string/packet encoding and disconnect handling,
but replaces connection, packet reads and collection. The original collector
has only an idle timeout, does not validate SUBACK or distinguish retained replay
from live traffic, and can run indefinitely on a busy broker. Its packet reads
also have no aggregate deadline or size limit. `barriers.py` was not edited.

The checker allows only CONNECT (clean session, no will), SUBSCRIBE at QoS 0 and
DISCONNECT outbound. It cannot PUBLISH, delete, seed, clear or operate the city
switch. It subscribes to `<prefix>/barriers/+` and `<prefix>/city/alerts/enabled`,
verifies both SUBACK results, and accepts only
retained direct children. No feedback descendants are collected. Packets are
limited to 1 MiB; snapshots to 10,000 unique topics; HTTP bodies to 4 MiB.

MQTT 3.1.1 has no end-of-retained-snapshot marker. Success means a quiet interval
after acknowledged subscription, not an atomic or provably complete snapshot.
Updates during collection are counted and cause failure/retry advice, rather
than mixing non-retained delivery into the retained set. A continuous stream or
partial packet causes nonzero timeout failure. Changes after collection, delayed
replay beyond the quiet interval and expiry during HTTP requests remain possible.
Expiry is evaluated once at `snapshot_at`, immediately after collection.

## Filtering and output

`city_switch` reports `retained`, `state` (`on`, `off`, `missing`, `invalid`), and
`effective`. A missing retained flag means the documented default `on`; an invalid
payload fails the check with `invalid_switch` and an unknown effective state.
Live switch updates invalidate the snapshot just like live barrier updates.
This records the switch, not proof that the import Action has finished executing:
inspect the active city count as well. The checker never changes the switch.
An off switch with active city barriers fails with `city_switch_mismatch` after
recording the route and grades. A brief mismatch can occur while retirement runs;
retry once after completion. Persistent mismatch requires the LoT owner's review.

The current app (`onBarrierMessage`, `activeBarriers`, `squareAround` in `app.js`)
uses the topic's final component as the ID, numeric coordinates, and no kind or
description filtering. The checker follows that behavior; `city-` topic IDs count
as city barriers. Unknown kinds and absent descriptions do not change routing.
One closed five-vertex `[lon, lat]` square of ±15 m is sent for each active record.

- `retained_records`: unique retained direct-child topics observed, including
  retired/expired records. City retirement republishes a past `expires_at`; it
  does not necessarily remove the retained record.
- `active_barriers`, `active_city_barriers`: valid, unexpired routing exclusions.
- `expired_records`: valid coordinates and a parsed expiry at or before the
  snapshot timestamp. These are excluded without failing the check.
- `invalid_records`: malformed JSON/object/coordinates or invalid expiry. These
  are excluded, with aggregate `invalid_reasons`; the final check fails even if
  routing with the remaining records succeeds. No payloads/descriptions are dumped.
- `missing_expiry_active`: missing/null/false/zero/empty-string expiry is active,
  matching JavaScript's falsy-expiry behavior. This is a diagnostic count, not a
  validation failure. Truthy invalid expiry is inactive in the app and invalid here.

Deliberately stricter validation: coordinates must be finite JSON numbers (not
booleans or numeric strings), and the entire square must lie within geographic
bounds. Truthy expiry must be an ISO timestamp with timezone accepted by Python
`datetime.fromisoformat`; JavaScript accepts some additional date formats and
timezone-less dates that this checker rejects. No attempt is made to reproduce
browser-specific `Date.parse` heuristics. Invalid records are reported separately
from expired records; validation of coordinates precedes expiry classification.

The fixed request uses exact coordinates `(41.1455,-8.6105)` →
`(41.1459,-8.6064)`, pedestrian wheelchair, `max_grade: 6`,
`step_penalty: 43200`, kilometers, `language: pt-PT`, and all valid active
exclusions. Both HTTP requests use `Content-Type: text/plain` with JSON bodies,
matching the app's browser-compatible request construction.

Route output is length in km and time in seconds. The trace uses `edge_walk` and
the app's edge attribute filter. Grades are **already percent** on this custom
backend; no `tan()` conversion is used. First/last trace edges are conservatively
classified as endpoint candidates (possibly partial), reported separately and
not included in the interior cap assertion. Their full-edge grades do not prove
the grade of just the traversed portion. Missing fields, nonnumeric/nonfinite
grades or ±32768 count as missing elevation. Missing interior elevation, no
interior edges or an interior grade outside +6%/−6% fails the check. Endpoint
missing/excess grades remain explicit diagnostics and do not fail the interior
check. Known zero-grade short-edge and DEM smoothing limitations remain; zero
is not proof of measured flatness. This is not accessibility certification.

Exit 0 means snapshot, route and interior checks passed with no invalid records.
Exit 1 reports a categorized failure, including authentication, subscription,
transport, snapshot timeout/change, invalid response, no route (442/443), other
Valhalla error (including 176), grade check or invalid barriers. CLI usage errors
exit 2. Server error text is not echoed. Already-completed snapshot/route results
remain in output if a later check fails. No exact live distance or monotonic
distance assertion is made.

## Actual verification — 24 October 2026

Authenticated local run at **12:27:35 UTC**, MQTT `127.0.0.1:1883` and Valhalla
`127.0.0.1:8003`:

| Measurement | Observed |
|---|---|
| Retained / active / active city | 24 / 24 / 24 |
| Expired / invalid / missing expiry | 0 / 0 / 0 |
| Concurrent updates | 0 |
| Polygons / vertices | 24 / 120 |
| Route | 2.164 km, 2072.82 s (34.547 min) |
| Interior trace | 87 edges; max uphill +6%, downhill −6%; zero missing or outside-cap edges |
| Endpoint candidates | 2 edges; max uphill +1%, downhill −3%; zero missing or outside-cap edges |
| Result | PASS, including the active >20-barrier case; no error 176 |

The separate independent fixture command also passed:

```bash
python3 hackathon/runtime/demo/check_routes.py
```

Baseline/control/reset 1.302 km; roadworks 1.721 km; parked car 1.437 km;
both 1.856 km. All interior caps, changed detours and unchanged control/reset
geometry passed. **That script never reads MQTT**: city barriers do not need to
be off, and its expectations must not be changed to the live city baseline.

Offline tests: **15 passed** (mock sockets/HTTP only), including the hard overall
deadline and malformed route response. `git diff --check` also passed.

```bash
python3 -m unittest discover -s hackathon/runtime/demo -p 'test_check_live_routes.py' -v
```

Coverage includes expiry equality/retirement/timezones, missing/invalid expiry,
malformed coordinates/JSON, polygons, retained direct-child filtering, live
updates, subscription/auth failures, busy/partial/slow packets, read-only send
guard, HTTP invalid JSON/transport/errors 176 and 442/443, percent grades,
endpoint separation and missing elevation.

## Original acceptance plan (superseded)

1. The supported switch and mutation sequence have now been supplied by Miguel.
   Follow `README.md` and the latest integration-check document for current evidence.
2. Record the current read-only snapshot. Operate the authorized city-off switch;
   rerun the checker. Confirm active city count is zero; retained city records
   may remain and count as expired. Preserve all non-city reports.
3. With the authorized demo setup, observe both local app sessions, create only
   the agreed demo reports, verify propagation/reload and actual changed route
   geometry, and remove only those demo reports. Other active reports can affect
   the baseline; do not require fixture distances from live state.
4. Miguel selected city-off for the demo. Restore city-on only if he requests it;
   record actual restored counts and route rather than assuming 24.
5. Check cleanup and restoration in the UI and record the actual sequence.

Claude owns the switch, retained durability investigation and feedback-storage
overlap; no work on those was duplicated. Ben owns the app: its
`degreesToPercent` conversion still needs correction for this backend's percent
grades, preserving missing-data handling and endpoint warnings. This CLI run
does not establish browser MQTT/WSS, hosted HTTPS integration, separate-device
behavior or retention across broker restart. Services were not restarted or
reconfigured, and no MQTT application messages were published.
