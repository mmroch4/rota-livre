# Demo barriers (seed / list / clear)

`barriers.py` puts the demo barriers on the local Coreflux broker and takes them off again, so the
demo can be repeated. Retained barriers are lost when the broker restarts: seed again before each run.

## Victor's repeatable sequence (city import off)

Miguel selected the city-off demo on 24 October. From the repository root, with
the credentials below exported, first pause city import and retire its barriers:

```bash
python3 -c "import sys; sys.path.insert(0,'hackathon/runtime/demo'); from barriers import connect; c=connect(); c.publish('access/city/alerts/enabled', sys.argv[1].encode()); c.close()" off
python3 hackathon/runtime/demo/barriers.py clear
python3 hackathon/runtime/demo/check_live_routes.py --json
```

Confirm `city_switch.state` is `off`, active city barriers are zero, and the exact
API fixture is 1.302 km. Expired retained city records are expected. If another
person's active report changes the route, coordinate with them; do not delete it.

1. Open two local app tabs at `http://127.0.0.1:8765/`. Select **Cadeira de rodas**,
   origin `41.1455, -8.6105` (Praça de Almeida Garrett), destination
   `41.1459, -8.6064` (Cervejaria Artesanal Levare). Baseline UI: **1.3 km / 21 min**.
2. Run `python3 hackathon/runtime/demo/barriers.py seed`. Both existing routes
   should change without reload to **1.9 km / 29 min**; live API fixture: **1.856 km**.
3. Reload the observer tab. Both markers should return from retained MQTT.
   Re-enter origin/destination (the route itself is not retained); verify the detour.
4. Run `python3 hackathon/runtime/demo/barriers.py clear`. Both routes should
   return without reload to **1.3 km / 21 min**; live API fixture: **1.302 km**.
5. Run the live checker again and leave the switch **off** for the next rehearsal.

Only if Miguel requests city barriers at the end, repeat the switch command with
`on` and check the refreshed count/route. The previously observed city baseline is
24 barriers and 2.164 km; the current two demo barriers do not lengthen that route.
Do not promise a city-on demo detour with these positions.

Browser distances are rounded; exact distances above come from Valhalla requests.
Named search results can differ slightly from the exact fixture coordinates.
Until restart durability is verified, repeat `off` and seed after any broker restart.

```bash
export BROKER_USERNAME=...   # the broker login (same one as app/config.local.js); never committed or printed
export BROKER_PASSWORD=...
python3 hackathon/runtime/demo/barriers.py seed [--with-control]
python3 hackathon/runtime/demo/barriers.py list
python3 hackathon/runtime/demo/barriers.py clear
```

No install needed: it speaks MQTT 3.1.1 over TCP with the Python standard library (no `paho-mqtt`,
no `mosquitto_pub`). It connects to `127.0.0.1:1883`; override with `BROKER_HOST` / `BROKER_PORT`
(and `TOPIC_PREFIX`, default `access`).

- `seed` publishes one **retained, QoS 1** message per barrier on `access/barriers/<id>`, payload
  `{"id","kind","description","lat","lon","reported_at","expires_at"}` as in the contract in `CLAUDE.md`.
  `expires_at` = now + 24 h. Ids start with `demo-`, so seeding again replaces the same barriers.
- `list` prints every retained barrier on `access/barriers/+` (not only demo ones).
- `clear` publishes an empty retained payload **only** on `demo-*` topics (the known ids plus any other
  retained `demo-` id). Other reports are left alone. The `/feedback` topics are not touched.

## The barriers

Route: São Bento (41.1455, -8.6105) → Batalha (41.1459, -8.6064), wheelchair profile
(`type: wheelchair`, `max_grade: 6`, `step_penalty: 43200`), exclusion squares of ±15 m as in `app.js`.

| Id | Kind | Position | Route with it alone |
|---|---|---|---|
| (none) | | | 1.302 km, 21.4 min |
| `demo-roadworks` | `works` | 41.14384, -8.60766 | 1.721 km, 27.4 min |
| `demo-parked-car` | `parked_car` | 41.14494, -8.61080 | 1.437 km, 23.4 min |
| both | | | 1.856 km, 29.4 min |
| `demo-control` (`--with-control`) | `damaged_pavement` | 41.1468, -8.6085 | 1.302 km (off the route, changes nothing) |

The 6 % route always exists with these barriers; it only gets longer and different. Most other points on
the baseline route force a 2.16 km detour, which is why these two were picked.
