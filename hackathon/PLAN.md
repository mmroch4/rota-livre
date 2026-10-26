# Development plan: Rota Livre

> **Historical.** This was the plan for the 6 hours of 24/10/2026; Rota Livre won 1st place. The current state
> and the open items for the next phase are in [README.md](README.md).

Updated 24 October 2026 for the Valhalla implementation and the agreed team tracks.
Rota Livre provides accessible routes in Porto that react to reported barriers.
This plan supersedes the earlier OpenRouteService plan and its deleted fixtures.

## Tracks and initial owners

| Track | Owner | Responsibilities |
|-------|-------|------------------|
| Web interfaces | **Ben** | `app/`: route planning, accessibility controls, barrier reports, route explanations and reroute feedback. Add an operator view only after the core flow works. |
| Data, broker and routing | **Miguel** | Valhalla setup and slope validation; Coreflux connectivity, barrier contract and automation; source intake; integration and repeatable demo setup. |
| Presentation, pitch and demo preparation | **Victor** | Demo script, slides, speaker notes, backup recording, timed rehearsals and Q&A. Start at kickoff; Ben and Miguel support the technical demo and reset. |

**Pedro is unavailable and has no assigned tasks.** Existing references to Pedro's server describe prior work,
not an ongoing dependency: Miguel owns verifying access or arranging a usable routing service.

These are initial owners. After finishing a task, coordinate with the other owners and help the highest-priority
remaining work across tracks. Keep one active task per person and one writer per notebook/file at a time.
If blocked for 15 minutes, raise it and pair. Use small commits to `main`, pulling with rebase before pushing.

## Current baseline and contract

- Ben's static interface is in `app/` (HTML, JavaScript, Leaflet and mqtt.js); see [app/README.md](app/README.md).
  It calls Valhalla `/route` directly and `/trace_attributes` for additional slope details.
- Accessibility controls supply pedestrian costing options, including `max_grade`, and barrier exclusion polygons.
  The code does not automatically relax the user's slope limit when no route is found.
- Coreflux shares one retained JSON message per barrier at `access/barriers/<id>` by default. Payload fields are
  `id`, `kind`, `description`, `lat`, `lon`, `reported_at`, `expires_at`; an empty retained message removes it.
  The UI filters expired barriers and recalculates on barrier messages when avoidance is enabled.
- `app/config.js` has empty routing and broker endpoints. Their deployment configuration and an end-to-end run
  remain to be verified. Credentials belong in ignored local configuration, never committed files.
- Valhalla and OpenStreetMap source trees exist under `projects/`. The
  [routing handoff](../accessibility_routing_project_handoff.md) records unresolved slope-unit, downhill and
  missing-elevation questions. Its historical upload warnings are not the current repository status.
- Current rerouting uses the selected origin/destination. Rerouting from a moving traveller's position and
  explaining the change are follow-up work, not demonstrated capabilities yet.

Keep the existing `access` prefix and payload while integrating. Document any agreed topic additions in
[README.md](README.md) before using them. Do not restore the old `passolivre/` topic contract, ORS gateway,
`report-site/`, or deleted fixtures as dependencies. Earlier issue numbers and milestone claims need review
against this plan before reuse; this document does not change GitHub assignments.

## Delivery order and acceptance checks

| Priority | Work | Owner | Done when |
|----------|------|-------|-----------|
| Core 1 | Working services and contract | Miguel, with Ben | App reaches the intended Valhalla and Coreflux endpoints; a retained barrier appears in two browser sessions and survives a reload. Record the actual deployment setup. |
| Core 2 | Accessible route validation | Miguel, with Ben | Known gentle, steep uphill and steep downhill cases verify the cap; missing elevation has an explicit policy. No-route UI is clear and the cap is never silently raised. |
| Core 3 | Report → barrier → reroute | Ben + Miguel | A report from one session reaches another and causes a route avoiding its polygon; clearing it is reflected live. The UI explains why the route changed. |
| Core 4 | Current-position rerouting and repeatable demo | Ben + Miguel | A real or explicitly simulated position becomes the new origin while the destination stays fixed; the changed route is explained. Demo barriers can be reset and the sequence repeated. |
| Follow-up | Live city data and barrier lifecycle | Miguel | Map city alerts into the current barrier contract with stable IDs and expiry; demonstrate broker-side automation and document its inputs/outputs. Label snapshots honestly. |
| Follow-up | Operator view and polish | Ben | Show active barriers and relevant status clearly; improve failure messages and demonstrate the core flow on a phone-sized screen. |
| Follow-up | Rain, hand-off, audit and access rules | Miguel, with Ben | Take separately after the core works; validate each integration and update the contract. Do not claim undelivered features in the pitch. |
| Stretch | LLM analysis and lift simulator | Miguel, with help as available | Only start if the core is stable and presentation preparation is on schedule. Neither blocks the demo. |
| Required throughout | Presentation and demo preparation | Victor | Script and slides match demonstrated behavior; backup recording, three timed rehearsals and Q&A preparation complete. |

The existing manual barrier-kind selection is sufficient for the core demo; LLM classification is optional.
Coreflux currently distributes barriers while the browser requests routes. Miguel should make any added
broker automation demonstrable; Victor must describe the architecture as implemented.

## Six-hour checkpoints

Times are relative to kickoff; if work has already started, assess the current checkpoint before taking more scope.

| When | Target |
|------|--------|
| H+0:00 | Confirm owners, endpoints, barrier contract and demo route. Victor starts the pitch outline and script. |
| H+0:30 | Resolve routing-service access, broker connectivity and any required licence limits. Establish how slope enforcement will be tested. |
| H+1:00 | Route shown in the app; retained barriers exchanged between sessions; slope validation underway. |
| H+2:00 | MVP: verified accessibility behavior and report → barrier → reroute working end to end. |
| H+3:00 | Rerouting from current/simulated position with clear feedback; repeatable demo. Victor aligns slides with verified behavior. |
| H+4:00 | Stabilize; add follow-ups only if the core is reliable. Run the actual demo with Victor and cut unfinished claims. |
| H+4:30 | Feature freeze. Record the backup video; only bug fixes after this point. |
| H+4:30–6:00 | All three: three timed rehearsals, reset between runs, Q&A drill. |

## Risks and fallback decisions

- **Slope enforcement:** do not treat the public Valhalla fallback as proof of the custom cap; the app's config
  explicitly warns that it ignores that customization. Validate the actual service before claiming accessible routing.
  If validation fails, narrow the demo claims and explain the limitation.
- **Unavailable previous server:** Miguel verifies or rebuilds a usable service from the checked-in work; do not
  wait for Pedro. Time-box setup and expose any blocker early.
- **Network/service failure:** record the working demo before feature freeze. Prepared routes or snapshots must
  be labelled as recorded data; offline replay is planned only if implemented and checked.
- **Time pressure:** protect the core and Victor's preparation; defer live sources and other follow-ups before
  spending time on LLM analysis, lifts or a separate operator interface.
- **Scope and status:** code presence is not runtime verification. Record the tested route cases, endpoints and
  remaining limitations with the demo notes before rehearsals.
