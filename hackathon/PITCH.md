# Pitch and demo

> The presentation **matters a lot**: it is how the jury judges the solution (Rules, Art. 1, 3).
> Set aside at least **1h30 of the 6h** to prepare and rehearse the pitch and the demo.

**Format:** a **5-minute** pitch, which can stretch to **8 minutes** if the jury asks questions
and wants to know more about the project. Event on **Saturday, 24/10**.

## Structure (mapped to the jury's criteria)

| # | Block | Jury criterion | Time (~5-min pitch) | Content |
|---|-------|----------------|:-----:|---------|
| 1 | Hook | — | 0:20 | One sentence/number that shows the pain. |
| 2 | **Problem** | problem statement | 0:50 | Who suffers, how much it costs, why it is not solved today. |
| 3 | Solution | — | 0:30 | The product in one sentence and what changes for the user. |
| 4 | **Demo** | demonstration | 1:40 | Live: a real event flows through the system end to end. |
| 5 | **Architecture** | architecture built | 0:50 | One diagram: sources → Coreflux (Actions/Models/Connectors) → outputs. Highlight what runs **inside the broker**. |
| 6 | **Maturity** | maturity | 0:40 | What is real vs. simulated, tests, security (Rules), scale, next steps. |
| 7 | Close | — | 0:10 | The product sentence + team name. |

## Script (Passo Livre, ~5 min)

| # | Block | Lines / screen |
|---|-------|----------------|
| 1 | Hook | *"The City Council of Porto has registered 26 586 times that a pavement was occupied. For most of us that is a detour. For someone in a wheelchair, it is the end of the trip, and they only find out when they get there."* (Source: City Council open data, unplanned restrictions, type "Ocupação do passeio".) |
| 2 | Problem | Porto is steep, paved with granite that slips in the rain, and full of steps. Normal maps give the shortest route, not one you can take. And accessibility changes during the day: works, a lift out of service, a van on the pavement. The information exists (the City Council, IPMA, citizens on ReportaPorto) but it never reaches the person on the way. |
| 3 | Solution | *"Passo Livre gives people with reduced mobility in Porto a route they can actually take, and changes it while they walk when the street changes."* |
| 4 | Demo | See the script below. |
| 5 | Architecture | One diagram (README §3). Message: **every source is an event in the broker**: City Council alerts and IPMA through REST Connectors, citizens and lifts over MQTT. Python inside the broker decides what each record means for a pedestrian and which trips it affects; the routing engine only computes the path we tell it to; the LLM only reads the citizen's text and photo. Only the screens and the simulator are outside. |
| 6 | Maturity | Real data (City Council, IPMA, Porto's road network) vs. simulated (lifts, the demo's reports and trips), a reason for every barrier and every route, honest "no accessible route", tests, audit log, Rules per role, works offline with a cache. |
| 7 | Close | *"Passo Livre: the city changes, your route too." Team O(1/n).* |

## Demo script (1:40)

Initial state: `ResetDemo` run; config retained; the city alerts and the weather already polled (real, or the
recorded snapshot); no active trip; Mailpit empty. Three windows: traveller (phone size), reporter (phone size),
operator map.

1. **(0:20) Plan.** On the traveller's phone, profile **wheelchair**, trip **São Bento → Praça da Ribeira**. The route
   appears with its reasons: *"Evita ruas com inclinação acima de 6%. Evita o passeio ocupado na Av. Gustavo Eiffel
   (Câmara Municipal do Porto)."* Tap **Start**: the dot starts moving along the route.
2. **(0:15) Live barrier map.** The operator map shows the **real** City Council alerts in the zone (coloured by
   source), the Aliados weather station and the active trip.
3. **(0:20) Report.** On the reporter's phone: photo of a pavement blocked by works, pin confirmed, *"Passeio bloqueado
   por obras, não dá para passar com cadeira de rodas."* The analysis appears (*sidewalk blocked*), a new barrier shows
   up on the operator map, and the ReportaPorto hand-off is ready (the email lands in the city inbox, Mailpit).
4. **(0:30) The key moment.** That barrier is on the active trip. Without anyone touching the traveller's phone:
   *"Nova rota: +4 min. O passeio na Rua … está bloqueado por obras (reportado há 1 min)."* The new route is drawn from
   where the dot is.
5. **(0:10) Rain.** Publish the rain message (or it is really raining): *"Está a chover: a rota passa a evitar
   inclinações acima de 3% e calçada irregular."* The route changes again.
6. **(0:05) Proof.** The HUB shows the Actions, Python scripts and Connectors running in the broker.

**Plan B (in order):**
- **ORS fails or no internet:** cached routes for the demo trips (`source: "cache"`), same flow and same reroute;
- **FIWARE fails:** the recorded snapshot of city alerts and weather;
- **the LLM fails or is slow:** the keyword classifier answers with `source: "keywords"`;
- **a web view fails:** `replay.py` publishes the same messages, MQTT Explorer shows the result;
- **everything fails:** the demo video recorded at H+4:30.

## Demo checklist

- [ ] A **written script** of the demo: every click and every published message.
- [ ] A single "happy" path, rehearsed **at least 3 times**, ideally on the presentation machine.
- [ ] A reproducible initial state (`ResetDemo` in `00-setup.lotnb`).
- [ ] Data that triggers the interesting event **on demand** (the report, the rain message, a lift key press),
      instead of waiting for a timer.
- [ ] Demo trips that show a **visible** detour on the map (checked with ORS tonight / H+1).
- [ ] **Plan B:** screen-recorded demo video + cached routes + recorded source snapshot.
- [ ] No internet? Know what stops working (the REST Connectors: city, weather, ORS) and switch to the cache.
- [ ] Large font in the HUB/terminal; notifications off; tabs ready.

## Jury questions (up to 3 min)

The extra 3 minutes are an opportunity: questions show interest. Prepare short answers
(≤ 30 s) and, where it makes sense, a **backup slide** for each one:

| Likely question | Answer / backup slide |
|-----------------|-----------------------|
| Why not Google Maps, or OpenRouteService directly? | They compute a path on a map that does not know that this pavement is blocked *now*. We use ORS as the engine; what Passo Livre adds is the live barrier map from the City Council, IPMA, citizens and lifts, what each barrier means for each profile, and the reaction during the trip. |
| Why Coreflux and not a normal web app with a database? | The value is in reacting to events from many sources: polled APIs, citizens, devices. The broker is where they all arrive; Connectors bring the external ones in, Actions and Python react, and state, audit and notifications fall out of one stream, with no extra integration server. |
| What is real and what is simulated? | Real: City Council alerts and IPMA weather (live, from Porto's urban platform), Porto's road network and routing, the whole pipeline, the reroute, the hand-off email, the audit log. Simulated and labelled: the lift controller and the demo's reports and trips. |
| How do you know what a City Council alert means for a wheelchair? | A rule table, per alert type and detail: "pavement occupied" blocks, "parking" is ignored, "hole" blocks a wheelchair and is a penalty for a walker. It is configuration, every barrier shows its reason, and we would review it with associations of people with disabilities. |
| What if the AI gets it wrong? | It only *suggests* the kind of obstacle from the citizen's text and photo. The impact table and the router decide; an ambiguous report goes to review. |
| What if there is no accessible route? | Passo Livre says so and says why, instead of drawing a route that cannot be taken. |
| What about ReportaPorto? | We do not replace it: we prepare the report (category, place, description, photo) so the citizen sends it in one step. It has no public API today; an official integration is the next step. |
| Privacy? | A traveller's position only exists inside their own trip topics; Rules stop other roles from reading them. Reports carry no identity unless the citizen adds a contact for the hand-off. |
| How would it scale? | Sources, profiles, kinds and rules are configuration. Porto publishes its alerts in FIWARE NGSI, an open European standard: another city that uses it changes a URL and the rule table. The Python functions are pure and stateless. |
| Who pays? | Free for people. The city or the metro operator pays for the operator map, the live barrier data and the qualified reports it receives. |
| What next? | Real lift status from the metro operator, official ReportaPorto integration, our own slope model from elevation data, crowd confirmation of barriers, more profiles (visual impairment), voice guidance. |

## Roles and timeline

No fixed roles: the pitch is built through issues like everything else, **#17** (demo script + deck) and **#18**
(backup video + rehearsals). Who presents: `TODO` (decide at kickoff). The 6-hour plan, checkpoints and how we take
tasks are in [`PLAN.md`](PLAN.md).

## Slides

The Vale deck (<https://claude.ai/artifact/3QRZ8JXuDBSsBftHCqjaCK>) is **obsolete**, and there was never a Rua Viva
deck. New deck: `TODO` (#17).
Suggested 11 slides: cover, hook (the 26 586), problem (a photo of a steep Porto street with steps), the path of one
trip, demo, architecture, explainability (one route with its reasons and one reroute), maturity (real vs. simulated),
what it is worth, close, and backup slides (why not Google Maps, why Coreflux, the impact table).

Backup video: `TODO` (record at H+4:30).
