# Sand transfer concepts — A to B

Concepts studied on 25/10/2026 for the Team Design brief (move loose sand from A to B). None of them was
built to completion: the challenge ended without a finished prototype (see [`../README.md`](../README.md)).
Every file here is an editable spatial concept or a Blender physics study, NOT fabrication-ready CAD or a
validated mechanism. Generators run with `blender --background --python cad/<script>.py`.

In the order they were made:

| Concept | Generator | Files | Notes |
|---------|-----------|-------|-------|
| Fixed chute + scoop (original) | `build_concept.py` (now builds the electric revision) | `sand-transfer-concept.*`, `model-view.html`, `sand-transfer-preview.png` | Below, from "Confirmed geometry" |
| Electric revision: motorised carriage + tipping scoop | `build_concept.py` | `sand-transfer-electric.*` | `electric-revision.md` |
| Animated extraction | `build_extraction_animation.py`, `play_extraction.py`, `check_extraction_cache.py` | `sand-extraction-animated.blend`, `extraction-frame-*.png` | `extraction-animation.md`, `extraction-alternative-wheel.md` |
| Bucket wheel in A | `build_bucket_wheel.py` | `bucket-wheel-test.blend`, `wheel-frame-*.png` | `bucket-wheel-test.md` |
| Bridge from the wheel to B: tilting tray vs belt | `build_bridge_options.py -- tilt\|belt` | `bridge-*.blend`, `bridge-*-frame-*.png` | `bridge-options.md` (the belt delivered ~1.7× the tray) |
| Archimedes screw + fixed chute | `build_archimedes_screw.py` | `archimedes-screw.blend`, `archimedes-screw-frame-*.png` | `archimedes-screw-report.json`: 46 of 420 grains lifted above 120 mm in 12.5 s |
| Claw on a swinging arm + hopper + chute | `build_claw_chute.py` | `claw-chute.blend`, `claw-chute.png`, `claw-detail.png` | Build guide `claw-build-guide.html` (Portuguese) |
| **Hanging-scoop tower** (the one the firmware drives) | `build_scoop_tower.py` | `scoop-tower.blend`, `scoop-tower.png`, `scoop-tower-mouth.png` | Build guide `scoop-tower-guide.html` (Portuguese); firmware in [`../README.md`](../README.md) |

Shop data: `photo-review.md` (what the shop photos do and do not show) and `store-photos/`; the catalogue with
prices is [`../store.json`](../store.json).

## Original concept: fixed chute + scoop

Open `sand-transfer-concept.blend` in Blender or import the OBJ into a 3D viewer.
The OBJ uses metres and contains geometry only; the Blender file retains colours.
Rebuild with `blender --background --python cad/build_concept.py`.
The script uses millimetres; the Blender scene has metric scale 0.001.

## Confirmed geometry

- Arena: 1200 x 600 mm, 30 mm rim (competition rules).
- A, source at right: 190 x 190 x 95 mm (user measurements).
- B, destination at left: 160 x 240 x 60 mm (user measurements).
- Gap between nearest edges: 500 mm (competition diagram).
- Both containers remain fixed. Sand is loose.

Containers are rectangular reference envelopes. Wall thickness, rounded corners,
internal opening and exact arena placement are not measured.

## Proposed geometry and materials

- Fixed chute: 550 mm horizontal reach, 200 mm rise, approximately 20 degrees.
- Chute floor: 130 mm wide, outlet at 80 mm; inlet at 280 mm.
- Shop 129 K-line and 193 tarpaulin: chute/scoop mockup surfaces.
  The liner is represented by the same blue surface, not a separate mesh.
- Shop 120 rectangular laths: chute rails and crossbars. Cross-section and blank
  lengths are assumptions, not verified shop dimensions.
- Shop 121 square laths: supports and tower. Four 400 mm blanks could supply
  two tower uprights and two pairs of short supports if stock dimensions match.
- Shop 125 5 mm plywood: separate feet outside the container footprints.
- Shop 141 pulleys, 150 wire, 151 cord: schematic lifting arrangement.
- Hinges, cable routing, crank, scoop digging linkage, locking and tipping
  mechanism are not detailed. No motor or electronics are assumed.
- Orange lines are motion/flow guides, not physical components.

## Checks before committing to this architecture

1. Test actual sand on the selected liner at 20 degrees.
2. Demonstrate scoop filling, retention and controlled tipping independently.
3. Measure shop stock, pulleys and fasteners; prepare a cutting plan and full BOM.
4. Resolve actuator transmission and confirm manual controls comply with rules.
5. Check tipping stability, lift forces, joints, cable travel and full swept volume.
6. Verify clearances against actual container interiors and arena mounting blocks.

The raised scoop illustrates discharge location only. Its current level floor
does not demonstrate a working tipping cycle. Tower bracing is schematic.
Do not buy materials or cut parts solely from this concept. Prices are dynamic;
no complete cost or load capacity has been validated.
