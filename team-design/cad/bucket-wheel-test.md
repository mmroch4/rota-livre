# Alternative B — bucket wheel extraction test

Separate from Alternative A: the arm model and its simulation are unchanged.
Open `bucket-wheel-test.blend`; Space starts/pauses the baked timeline.
Generator: `build_bucket_wheel.py`; numerical results: `bucket-wheel-report.json`.

## Test setup

- Fixed source A: nominal 190 x 190 x 95 mm, rectangular assumed internal walls.
- Six open cups on a rigid rotor, outside swept diameter approximately 168 mm.
- Shaft centre 110 mm above the arena; approximately 26 mm lowest swept point.
- Cup width approximately 82 mm including side walls; supported shaft on both sides.
- One revolution at 6 rpm after a 2-second settling phase; final settling to 15 s.
- Independent blue receiver is test equipment, NOT B and NOT the competition layout.
  Its placement does not claim a solution to the 500 mm A-to-B transfer.

## Simulation scope

All particle motion, including pickup, is computed by rigid-body contact from the
start. There are no particle transport keyframes and no scripted attachment to cups.
The rotor's movement alone is prescribed. Passive animated cup panels collide with
active spherical proxies. 64 substeps per frame and 40 solver iterations are used.

Particles are 10 mm spheres of assigned mass 0.8 g, friction 0.4 and restitution
0.01. These are coarse numerical proxies, NOT calibrated representations of the
actual sand. Their size changes filling, jamming and flow behaviour. Grain count
is not a measured mass throughput or a predicted competition score.

The imposed rotor can deliver unlimited torque and cannot stall. Bearings, motor
gearing, shaft fit, flexure, structural stability, electrical power and wear are
not physically validated. Actual stock dimensions, sheet nesting, required joints
and the complete budget remain to be reconciled with the store.

## Reading the result

- `unique_particles_lifted_above_105mm`: particles whose centres ever exceed this
  level, not necessarily retained and discharged correctly.
- `in_test_receiver`: final or sampled particles inside the separate test tray.
- `in_A`: particles still below the source rim within its assumed internal footprint.
- `outside_A_xy`: includes particles airborne or spilled, not just successful output.

A low receiver count is evidence of a weakness in THIS geometry/simulation, not a
reason to prescribe particle motion to make the demonstration look successful.
Test a real cup with the supplied sand before adopting or rejecting the mechanism.

## Result of the first bake (25 Oct, 11:02)

346 grain proxies, one revolution at 6 rpm (`bucket-wheel-report.json`,
frames `wheel-frame-*.png`):

- 0 grains reached the test receiver; 0 left A's footprint.
- 15 grains (4 %) were ever lifted above 105 mm; all fell back into A.

Why the receiver count says nothing yet: this geometry has NO discharge path. The
wheel's top is directly above A and there is no funnel or chute towards the
receiver, so anything the cups release at the top drops back into A. The test only
measures pickup. Pickup itself is pessimistic: 10 mm spheres against cups about
33 x 26 mm means each cup holds only a few proxies, unlike real loose sand.

Next steps, if this alternative is kept: add a stationary funnel under the top of
the wheel leading out of A, use smaller proxies (or fewer, larger cups), and
measure pickup with a real cup in the supplied sand before trusting any count.
