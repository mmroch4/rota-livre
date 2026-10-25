# Alternative B — low-speed bucket wheel extraction study

Status: proposed, not built or simulated. Preserve `sand-extraction-animated.blend`
and its generator as Alternative A, the articulated-arm reference. No changes to
that geometry or animation are made by this study.

## Decision

Test a small rigid wheel with fixed cups and one rotary drive before committing to
another full machine. It removes coordinated shoulder/elbow/bucket control and
does not need a flexible endless belt. This is a simplicity argument, not proof
that the mechanism is more reliable under the supplied sand and motor conditions.

The current chute is NOT assumed compatible: its inlet is 235 mm above the arena,
while this wheel's highest tip is only about 195 mm in the example below. A separate
transfer solution or a different extractor will be needed if this concept passes.

## Proposed extraction cycle

Six shallow fixed cups rotate through the bottom region of A, enter the loose sand,
lift small batches on the ascending side and empty into a stationary receiving
funnel after passing the top. Cup opening angle and funnel position must be tested
with a single physical cup first; gravity discharge is not guaranteed by a circular
path alone. Run slowly, with shallow engagement. Never bury the whole wheel.

## Geometry envelope — millimetres

- A external dimensions: 190 x 190, height 95, fixed to arena.
- Trial wheel outside diameter INCLUDING cups: 160–170.
- Trial axial width: 70–90. Use the actual internal opening and rounded corners
  to determine final clearances, not the nominal 190 mm size.
- Example: radius 85, shaft centre 110 above floor. Lowest point = 25; highest = 195.
- Shaft is above the rim, supported by a freestanding frame on either side of A.
  The shaft crosses the bowl in the direction transverse to A-to-B transport.
- Do not support or clamp the mechanism to the fixed containers without permission.
- The 25 mm nominal bottom gap, plus actual bowl floor thickness, is a significant
  extraction limit. A fixed wheel also excavates a local trench; loose sand is not
  assumed to replenish that trench completely.

Therefore this is an initial partial-recovery concept, not a complete-emptying
solution. If residual mass is too large, reject it or deliberately add a separate
feed mechanism; do not quietly assume a rake, operator assistance or funnel-shaped
source. Moving the shaft downward would conflict with the rim unless the support
and drive architecture were redesigned.

## Shop mapping and practical gates

- 125 plywood: wheel cheeks and cup structure; 170 mm discs fit 300 mm sheets,
  but two 170 mm discs cannot fit on one 300 mm square. Plan two sheets or change
  the disc design. Account for cups, kerf and other uses before ordering.
- 120/121 wood: independent bearing stand; dimensions and cuts unconfirmed.
- 122 round stock or another confirmed shaft: diameter, straightness and material
  must match measured bearings. Do not assume furniture dowel 128 is a suitable axle.
- 136/137/140 bearings: select after shaft measurement; picture alone gives no fit.
- 160/162 motor: requires actual torque/speed and a feasible reduction/coupling.
  The wooden wheel must not hang from the motor shaft. Provide independent supports.
- 129 K-line: stationary funnel mockup, not an unreinforced digging edge.
- Fixed cups can be built from plywood offcuts; no hinges or servo per cup.
- Power, driver, wiring and guards remain unresolved; no final budget established.

## Alternatives considered

1. Bucket wheel: simple rigid transmission and one repeated path, but limited lift,
   retained bottom layer, local trench and cup discharge uncertainty.
2. Bucket belt elevator: compatible with higher discharge and near-bottom pickup,
   but handmade belt tracking, tension and cup fixation add substantial risks.
3. Screw conveyor: compact intake, but the shop has no confirmed manufactured screw;
   fabricating concentric flights and adequate casing clearance is a poor initial
   reliability bet for this team and timescale.
4. Existing arm: adaptable reach but three controlled joints, torque, sensing and
   trajectory coordination; its pickup remains unvalidated.

## First physical test, before new full CAD

1. One real cup, filled by moving through actual sand: check penetration, retention
   and emptying by slowly rotating through the intended orientations.
2. Two opposed cups on a temporary rigid wheel, operated through an allowed crank
   with the same supported shaft architecture. Record jamming and effort; do not
   infer motor capability from hand operation.
3. Add cups only if the first test works. Run repeated timed extraction tests into
   an independent weighed receiver; record transferred mass, spilled mass, stalls
   and residual source mass at high, medium and low fill levels.
4. Suggested engineering gate: five consecutive 90-second runs without intervention
   after starting, then compare delivered mass and remaining sand against the arm.
   This is a proposed test criterion, not evidence of achieved reliability.

No claim of fail-proof operation. The most useful early result may be rejecting
this architecture because it cannot recover enough of the remaining sand.

Background: KWS describes bucket-elevator loading/discharge systems and the importance
of tension and bearing protection in a free-flowing-material application:
https://www.kwsmfg.com/resources/problem-solvers/bucket-elevator-boot-section/
This supports identifying belt/chain maintenance concerns, not validating this
specific bucket-wheel design or extrapolating industrial performance to sand here.
