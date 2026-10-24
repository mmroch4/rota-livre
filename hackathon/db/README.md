# Database (Supabase Postgres)

```
web app ──MQTT──▶ Coreflux cloud broker ──PostgreSQL connector──▶ Supabase
                  RouteBarrierMessage (Action)   BarriersDB (lot/10-barriers-db.lotnb)
```

Coreflux is the backend: it receives what the web app publishes (contract in the root `CLAUDE.md`), sorts it
and writes it to Supabase. Nothing else runs in between.

| Table / view | What is in it |
|--------------|---------------|
| `barriers` | One row per reported barrier; `deleted_at` is set when its reporter deletes it |
| `barrier_feedback` | One row per "Já não está" answer; never removes a barrier |
| `barrier_review` (view) | End-of-day review: each listed barrier with its "gone" answers, today and in total |

`schema.sql` was tested on Postgres 15 (the version family Supabase runs) with the connector's queries filled in
the way Coreflux does: reports with apostrophes, a repeated (retained) message, a SQL injection attempt (stored
as plain text), an invalid kind (rejected), the reporter's delete, answers with and without a location, and the
review view. The `coreflux_writer` role cannot delete rows.

## Setup (one time)

### 1. Create the Supabase project
1. <https://supabase.com> → sign in → **New project**.
2. Name `rota-livre`, region **Central EU (Frankfurt)** or **West EU (Paris)**, any database password (keep it
   in a password manager; it is the admin password, not the one Coreflux uses).

### 2. Create the tables
1. Open `schema.sql`, replace `CHANGE-ME-BEFORE-RUNNING` with a new strong password: this is the password
   Coreflux will use. **Do not commit the file with the real password.**
2. Supabase → **SQL Editor** → **New query** → paste the whole file → **Run**. "Success. No rows returned".
3. **Table Editor** now lists `barriers` and `barrier_feedback`.

### 3. Get the connection details
Supabase → **Connect** (top of the project page) → **Session pooler** (works over IPv4; the "Direct
connection" host is IPv6 only and the cloud broker may not reach it). Note:
- **Host**, e.g. `aws-0-eu-central-1.pooler.supabase.com`; **port** `5432`; **database** `postgres`
- **User** for Coreflux: `coreflux_writer.<project-ref>` (the pooler adds the project reference shown in
  its own user name, `postgres.<project-ref>`).

### 4. Give them to the Coreflux cloud broker (never in git)
In the HUB (<https://hub.eu1.coreflux.cloud/>) Command Console, no spaces around `=`:
```
-setEnv SUPABASE_DB_HOST=aws-0-eu-central-1.pooler.supabase.com
-setEnv SUPABASE_DB_USER=coreflux_writer.<project-ref>
-setSecret SUPABASE_DB_PASSWORD=<the password from step 2>
```

### 5. Load the notebook
HUB → **LoT Editor** (dock) → `…` → **Import .lotnb file** → `hackathon/lot/10-barriers-db.lotnb`, then
**Run cell** on the `BarriersDB` connector (Connectors app: green dot = logged in to Supabase) and on the
`RouteBarrierMessage` action. **Done on the cloud broker on 24/10:** a test report (Action Console → Run once on
`access/barriers/btest00001`) and a test answer (Data Viewer → Publish on `.../feedback`) both reached Supabase.
The env/secret values were set in HUB → account menu → **Broker Settings** → **Variables & Secrets**.

### 6. Check
- `$SYS/Coreflux/Routes/BarriersDB/status` should report the connection as healthy.
- Publish a test report on `access/barriers/btest00001` (the payload format is in `CLAUDE.md`) and look for the
  row in Supabase → Table Editor → `barriers`; then a "gone" answer on `access/barriers/btest00001/feedback`
  and check `barrier_review`.
- Then set `brokerUrl` (the cloud broker's `wss://` address from Coreflux Fleet) in `hackathon/app/config.js`
  and the page's broker login in `config.local.js`: real reports start flowing.

## Still to do
- **A broker rule** so the web page's user may publish only on `access/barriers/#` and never on
  `access/db/#` (the internal topics the connector writes from). Until then, anyone with the page's login could
  publish there directly.
- Still to confirm on the live broker: an empty retained message (the reporter's delete) triggers
  `RouteBarrierMessage` and sets `deleted_at`. (An answer without a location was stored with empty `lat`/`lon`.)
