# Articulated extraction animation and discharge experiment

Open `sand-extraction-animated.blend`. Space starts/pauses playback. Timeline:
1 approach; 35 lower; 65 dig; 85 curl; 120 lift; 150 position over chute;
176 release; 235 return; 360 final settling. Duration: 15 seconds at 24 fps.
This timing is an animation choice, not a measured throughput estimate.

## Mechanism

Two paired 200 mm links rotate about a shoulder and elbow. A third rotary joint
tips an 80 x 110 mm scoop made from 5 mm plywood. M1/M2 drive the two arm joints;
the servo controls scoop pitch. The source remains fixed. The chute inlet stops
80 mm before the nearest source wall, leaving the collection opening clear.
A discharge hood directs particles into B and is attached to the chute, not B.

The arm path is solved using planar two-link inverse kinematics. Every programmed
wrist position is checked for reachability. Rotary joints are drawn explicitly,
but reductions, couplers, bearings, encoders/limit switches and motor mounts still
need measured hardware and detailed design. Motor envelopes do not imply adequate
torque, and the illustrated shafts are not confirmed shop stock.

## What is physically simulated

- Gravity, contact and discharge for 96 spheres after frame 176.
- Sphere diameter 5 mm, nominal mass 0.2 g, friction 0.35, restitution 0.02.
- Containers, bucket panels, chute and discharge hood are rigid colliders.
- 64 substeps per frame and 40 solver iterations; cache baked for frames 1–360.

## What is NOT physically simulated

- Excavation: grains move by prescribed keyframes from A into the scoop.
- Resistance of the sand bed, grain packing, cohesion, realistic grain shapes,
  scoop filling efficiency, soil forces or continuous removal of the visible bed.
- Motor dynamics, gearbox forces, holding torque, current, stability or flexure.
- The static sand bed is visual reference geometry only.

The report counts coarse proxies inside B at the final frame. It is not a mass
prediction, competition score or experimentally verified transfer efficiency.
The initial unhooded trial delivered 57/96 proxies and showed overshoot; the revised
hood trial is recorded in `extraction-simulation-report.json`.

The hood trial at 8 substeps still delivered 57/96. Increasing to 64 substeps
and 40 iterations delivered 96/96, demonstrating numerical sensitivity of the
small-particle collision test. This is not a convergence study or real sand validation.

Before construction: test a physical scoop in the supplied sand, measure force,
identify actual motors/gearing and power, inspect complete swept clearances, and
reconcile all parts and cuts with shop inventory and budget. No hardware validation
or complete collision-clearance certification has been performed.
