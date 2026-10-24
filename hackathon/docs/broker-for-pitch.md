# What the broker does in Rota Livre (for the pitch)

For Victor's architecture and maturity slides. Plain language, and only what was built and checked on 24/10.
Every number comes from [`runtime-baseline.md`](runtime-baseline.md); the section is named in brackets.

## The one-sentence version

Coreflux is the shared, live memory of Rota Livre: every obstacle anyone reports, or that the city has registered,
sits in the broker, reaches every open map without a reload, makes the route planner go around it, and survives
a broker restart.

## What it does, as verified

**1. Shares obstacle reports between people, live.** The web app talks to the broker over MQTT on a WebSocket. Each
obstacle is one "retained" message: the broker keeps the latest copy and hands it to anyone who opens the app later.
In two browser tabs, a report made in one appeared in the other and the route was recalculated around it with no
reload; a freshly opened tab got the obstacles back at once ["Core 1 verified", "Demo barriers verified"].
São Bento → Batalha with the wheelchair profile (slopes up to 6 %): 1.302 km with no obstacles, 1.856 km with the
two demo obstacles ["Demo barriers verified"].

**2. Imports the city's registered road works.** The broker itself polls the Porto Urban Platform (the Câmara's
FIWARE open data) every 10 minutes and turns road-works alerts near the demo route into obstacles in the same format
as user reports: 24 kept out of 48 alerts still valid that day ["City alerts verified"]. An on/off switch, also in
the broker, removes or restores them all at once. Same route, same profile: **2.164 km with the city's road works,
1.302 km without** ["City alerts switch verified"]. Say "registered road works", not "confirmed obstacles": these are
works the Câmara has on file, each one placed as a small square at the middle of the works area, so a long street
is only partly covered ["City alerts verified", caveats].

**3. Records "Já não está" ("it's gone") answers.** When someone says an obstacle is gone, the broker stores the
answer and keeps a live count per obstacle; a repeated answer counts once ["Broker durability verified"]. It does not
remove the obstacle: the team reviews the counts. The long-term database is Supabase (Postgres), written by the
broker through a database connector. Be precise about this one: it is **not connected to the broker we demo**.
Ben reports it working on a separate Coreflux cloud broker (`db/README.md`, step 5); that was not re-checked here.

**4. Survives restarts.** Durability is switched on: after a broker restart every report, answer, count and the
switch came back byte for byte (31 messages on the first test) ["Broker durability verified"]; the latest restart
recovered 60 stored messages ["Post-restart repair scripted"].

**5. Gives operators a live panel.** `RotaLivreOps`, a dashboard inside the Coreflux HUB, shows how many obstacles
are active per source (app, city, demo), whether the city import is on, a trend line, the list of active obstacles
and the "gone" counts. In the HUB it showed city 24, then city 0 and demo 2 after switching the city off and adding
the demo obstacles, without a reload ["Operator panel verified"]. It is read-only.

## A 30-second panel moment for the demo

Have the app (route drawn, city works on) and the panel side by side. Switch the city import **off**: the city gauge
drops from 24 to 0 and the app's route shortens from 2.164 km to 1.302 km. Then make a report in the app: the "app"
gauge goes up and the report joins the table. Checked separately, never in one take: the gauge and the table were
watched in the HUB with seeded demo obstacles, a test report was counted (app 1 → 0) through the panel's data, and
the route lengths come from the switch test ["Operator panel verified", "City alerts switch verified"]. Rehearse it once. Two practical notes: with the city works on, the two demo obstacles no
longer change the route, since the city detour already avoids them ["City alerts verified", caveats]; and the switch
is currently **off**, so turn it on before the demo.

## Honest limits (say these if asked)

- **Free (Community) tier.** It allows no custom access rules, so there are no per-user permissions: the local demo
  uses the broker's default login, reachable only from the demo laptop ["Core 1 verified", caveats].
- **One manual step after a restart.** Each broker boot brings back an older version of one city-import Action (a
  broker quirk). A single command repairs it, and that command was checked across a real restart
  ["Post-restart repair scripted"].
- **Supabase is not connected to the demo broker** (see point 3). Today the "gone" counts live in the broker only.
- **Which broker the demo uses.** The hosted page (`config.js`) now points at a tunnel to a different broker than the
  laptop's. The city import and the panel run on the laptop broker, so demo from the locally served app, as decided
  under "Core 1 verified".
- **City data.** Road works on file at the Câmara, not checked on the street. The Câmara's open data is polled every
  10 minutes, not pushed.
- **Not built:** the LLM that turns free text or photos into a report, rain/weather effects, and lift status.
- The panel's trend line is kept only while the HUB page is open.
