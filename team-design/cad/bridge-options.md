# Bridge options — bucket wheel in A to B (500 mm gap)

Open `bridge-tilt.blend` or `bridge-belt.blend`; Space starts/pauses (25 s at 24 fps).
Generator: `build_bridge_options.py -- tilt|belt`; results: `bridge-*-report.json`,
frames `bridge-*-frame-*.png`.

## Why a powered bridge

A fixed gravity chute needs its inlet at 190–430 mm for 10–30 degrees over the
~600 mm run (outlet 80 mm, 20 mm above B's 60 mm rim). The wheel must fit inside A
(diameter <= ~170 mm), so its top is 195 mm and the catch point ~150 mm: about
7 degrees, below the slide angle of dry sand (typically 20–30 degrees, NOT measured).

The cups must also empty sideways (+y, a low lip on that side): straight over the top
the sand falls inside the swept circle of the descending cups, where no bridge fits.

## Options modelled

- **Tilt**: K-line tray (670 x 70 mm, 30 mm walls) hinged at x=300 mm, outside B, with
  a 50 mm lip over B. Rests at ~4 degrees while filling; a cord over a pulley on a
  580 mm tower lifts the A end to 35 degrees in 2 s, holds 2 s, returns in 1.5 s.
  Cycle 11.25 s. One DC motor as winch.
- **Belt**: tarp loop over two 30 mm rollers (x=900 and x=260 mm), 4.5 degrees down,
  0.1 m/s, full-length skirts, back plate behind the tail roller. Second DC motor.
- Both: same hood/baffle over B, supported outside B; same prescribed feed.

## Result (120 grains fed, 8 every 1.67 s, i.e. one cup passage)

| | Tilt | Belt |
|---|---:|---:|
| In B at 25 s | 59 | 88 |
| Still on the bridge | 11 | 32 (belt load in transit) |
| Back in A (recirculated, not lost) | 50 | 0 |
| Spilled on arena / thrown by solver | 0 / 0 | 0 / 0 |
| Steady-state share of the feed delivered | ~55 % | ~100 % after a ~7 s first transit |

Over 90 s with the same feed, the belt delivers roughly 1.7x what the tilting tray
delivers. The tray loses whatever the cups pour while it is raised or moving (it falls
back into A: no penalty, but wasted lift). Stopping the wheel during the tip gives the
same throughput; only a buffer hopper with a gate would recover it.

## Practicality (not simulated)

| | Tilt | Belt |
|---|---|---|
| Moving parts | 1 hinge, 1 cord, 1 winch | 2 rollers, 4 bearings, belt |
| Hard parts to make | Tower stiffness (580 mm), cord winding | 1.39 m loop from a 60 x 100 cm tarp needs a seam; tracking and tension; coupling the motor to a roller (store couplers are for steppers, 100 coins) |
| Sensitivity to sand friction | Low: tilt further if it does not slide | Low at 4.5 degrees, but sand can fall onto the return run and jam a roller |
| Control | Timed cycle (optional microswitch at the top) | Run continuously |
| Height | 580 mm tower | < 200 mm |
| Typical failure | Cord slips or winch stalls; sand does not slide | Belt walks off, seam catches, belt slips on the roller |

## Scope and limits

Simulated: grain contact with the tray, belt slats, skirts, hood and containers after
release (Bullet, 64 substeps, 30 iterations). Grains are 7 mm faceted proxies, 0.3 g,
angular damping 0.9 (so they slide rather than roll); pair friction 0.49 (~26 degrees),
uncalibrated. The belt is a chain of rigid slats with 2 mm gaps.

Not simulated: wheel pickup (the feed is prescribed and identical in both options;
`bucket-wheel-test.md` shows pickup is the open problem), motor torque or stall, cord
stretch, belt slip, seam or tracking, structural stiffness, real sand.

Two solver artefacts were fixed before these numbers: overlapping spawn points, and
waiting grains sweeping through the bridge (Blender interpolates animated bodies
between frames). Earlier runs mixed artefacts into the "lost" counts.

## Next physical tests

1. Slide angle of the real sand on K-line and on tarp (decides the tilt angle, or
   whether a fixed chute is possible after all).
2. One cup with a side lip: does it empty sideways onto a bridge at ~150 mm?
3. If the belt is chosen: a tarp loop on two rollers, run by hand for 5 minutes, before
   building anything else.
