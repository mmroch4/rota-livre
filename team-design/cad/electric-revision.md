# Electric revision — conceptual assembly

The user authorized electronics and said hydraulic items will be returned.
No return, purchase or firmware upload was performed. Returns do not refund credits
under the competition rules; last observed balance was 905 credits.

Files: `sand-transfer-electric.blend`, `sand-transfer-electric.obj`, and
`sand-transfer-electric-preview.png`. The original non-electric assembly is retained.

## Proposed sequence

1. M1 lowers a guided carriage into fixed source A.
2. M2 translates the open scoop through a short stroke in the loose sand.
3. M1 raises the scoop to the chute inlet.
4. A servo tips the scoop about its front hinge; sand falls into the fixed chute to B.

This is a static discharge pose, not a simulation of a complete working cycle.
The guide shoes, translation transmission, cable routing, shaft couplings and
retention during lifting still require detailed design and physical testing.

## Corrections based on shop photos

- Scoop base and sides are now plywood, not foam board.
- Tipping uses the actual hinge category 147, not rigid L brackets 146/148.
- Chute is represented as supported K-line; woven sack 193 is not assumed to be a
  low-friction liner. Test the actual surface and angle.
- Electronics sit in proposed removable cradles/restraints, without adhesive or
  screws into the returned components.
- Two DC motors, a servo, Arduino and driver are allocation envelopes for kit 160.
  Exact hardware models, dimensions, gearbox availability, motor torque, servo
  torque and driver current rating are NOT confirmed.
- The power block is a reserved volume, not an identified available power supply.
  A usable supply must be established before buying or building the electric drive.

## Unresolved feasibility and budget

Kit snapshot price is 250 credits, leaving 655 of the last observed 905, before
mechanical parts, wiring and power. This is not a full priced bill of materials.
Guide and support stock lengths, sheet nesting, fasteners and total quantities
must be reconciled with store limits. No load rating is established.

No hardware test, motor sizing, stability validation, collision sweep or functional
firmware implementation has been completed. No hydraulic part is included.
