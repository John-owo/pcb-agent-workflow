# PCB layout: the debug-friendly parts

Electrical and manufacturing rules (RF, impedance, decoupling distance, DFM) follow each project's design documents and the fab's specifications; this page lists only debugging and hand-soldering habits. These practices come from the actual layout of a 95 × 50 mm 4-layer board (MCU + LoRa module + GNSS); adjust for other boards by layer count and density.

## Blocks and designators
- Layout blocks mirror the schematic blocks and follow the same current flow; keep the components of one functional block together.
- Number designators in ranges per sub-sheet (e.g. 1xx power, 2xx MCU, 3xx wireless, 4xx GNSS); silkscreen designators are legible and do not sit on pads/vias, with only two reading directions per side.
- Designators that do not fit in dense areas go only on F.Fab/B.Fab, with a list in the layout notes; when debugging, use the reference drawing (see below).

## Layer roles (4-layer board)
- **F.Cu**: short connections between parts, RF lines, high-current paths such as battery and boost; pour GND everywhere else.
- **In1.Cu**: solid GND, no routing, as the return plane for the RF line and all signals.
- **In2.Cu**: long east-west runs; **B.Cu**: long north-south runs. Both layers pour GND in empty areas.
- To change direction, change layers with a via; no crossings within one layer. When tracing a line, one layer tells you the direction.
- The layout notes list which nets are on each layer, to help find traces when reviewing and debugging.

## Test points and debug reference drawings
- Place test points where a probe can reach (not under components, not covered by the enclosure or a module); every power rail, enable signal and key IO gets at least one test point or measurable pad; ground points should be easy to clip an alligator clip to.
- Test point silkscreen shows only the short net name (e.g. `VBAT`, `3V3G`, `TX`); TP designators go on the Fab layer to avoid crowding text in dense areas.
- Also output front and back debug reference drawing PDFs that use Fab-layer pad outlines and pin numbers to map designators:
  `kicad-cli pcb export pdf --sp --cdnp --ev --scale 2.6 -l <copper layer,silkscreen,Fab,Edge.Cuts> -o <output>.pdf <board>.kicad_pcb`
  `--sp` draws pad outlines and pin numbers on the Fab layer, `--cdnp` crosses out DNP components, `--ev` hides values and keeps only designators; adjust `--scale` to the board size (2.6 for a 95 × 50 mm board).
- Attach a test point table to the layout notes: TP designator, net, silkscreen, location, expected value.
- Mark polarity on the silkscreen for polarized parts (diodes, electrolytic capacitors, battery holders, LEDs); mark pin 1 and signal names on connectors; mark ON/OFF direction on switches. If the manufacturer drawing does not state the switch direction, do not guess; mark it "to be confirmed on the physical part".
- Keep pads and silkscreen for DNP/optional parts, and note DNP on the Fab layer or silkscreen.
- At segmented debug points, place components that can be opened (0 Ω, solder jumper pads) so each power rail's current can be measured separately.
- Put the revision, date and project name on the board; the back can carry manufacturing information such as stackup and surface finish.

## Hand-soldering friendliness
- Choose **lead-free HASL** surface finish (KiCad board setup `HAL lead-free`), and select the same option when ordering. OSP pads do not wet well, making hand soldering difficult.
- Use thermal relief connections for front and back GND pours (e.g. 0.3 mm gap, 0.4 mm spokes) so the large ground pads of modules and battery holders can be heated by a soldering iron; use solid connections on In1/In2.
- Do not place parts around the soldering side of hand-soldered components.

## Verification
1. DRC: `kicad-cli pcb drc --all-track-errors --schematic-parity --severity-all -o drc.rpt <project name>.kicad_pcb` → 0 errors, 0 unconnected, 0 schematic parity issues; explain the source of every warning.
2. `--schematic-parity` must run on the project's official file name (same name as `.kicad_pro`/`.kicad_sch`). When a scratch copy has a different file name, kicad-cli does not do the parity check, and the copy's DRC result cannot serve as parity evidence.
3. When a script changes only silkscreen, fields or surface finish, compare traces and vias, pads, copper pours and component positions before and after; counts and coordinates must all be identical.
4. Visually inspect each layer's PDF and the debug reference drawings. Passing DRC does not mean electrically correct, correct RF impedance, accepted by the fab, or that the physical board will work.

Tool limitations are in [konnect-limits.md](konnect-limits.md).
