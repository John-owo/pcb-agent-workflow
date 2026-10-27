# First-board checklist

Tick each item before sending to the fab. It's for people to read, and you can also hand it to an agent for review: ask it to answer "pass/fail/can't tell" for each item with evidence (file location, command output, datasheet page number). A "pass" without evidence doesn't count.

This list catches common beginner mistakes; it is not a full design review. Ticking everything does not mean the circuit is correct or that the real board will work.

## Scope

- [ ] You can state what this board does, how it is powered, and what it connects to.
- [ ] It doesn't involve RF/antennas, high-speed signals, lithium battery charging, or mains; if it does, have someone experienced look at it first.

## Schematic

- [ ] Each IC's connections were checked against the typical application circuit in the manufacturer's datasheet, with the source page numbers noted.
- [ ] Every power pin of every IC has a decoupling capacitor, with values per the datasheet.
- [ ] Unused pins are handled per the datasheet (grounded, pulled up, or left floating), not by guesswork.
- [ ] Supply voltages match each part's voltage rating; 3.3 V parts are not connected directly to 5 V signals.
- [ ] LEDs have current-limiting resistors; buttons and switches are wired the way the firmware expects (pull-up or pull-down).
- [ ] The power input has reverse-polarity or overcurrent protection considered, or an explicit decision not to add it.
- [ ] ERC has no errors; you can state the reason for every ignored item.

## Parts and footprints

- [ ] Every assembled part has an LCSC part number, with stock checked and the lookup date recorded.
- [ ] You know which parts are Extended, and how much extra feeder loading fee you'll pay.
- [ ] Every footprint's dimensions and pins match the datasheet of **the exact part you are buying**.
- [ ] Pin 1 or polarity of polarized parts (diodes, LEDs, electrolytic capacitors, ICs) is consistent across symbol, footprint, and silkscreen.
- [ ] Connector pin order, gender, and orientation match what they connect to (ideally checked against the real part or the mating side's pinout).

## PCB

- [ ] Board setup uses the recommended values from [Getting started](getting-started.md#5-set-board-rules), or looser values.
- [ ] Decoupling capacitors are next to their corresponding power pins.
- [ ] Power track widths were calculated from current.
- [ ] GND is a continuous copper pour, not cut into islands.
- [ ] Connector, button, and mounting hole positions fit the enclosure or mating board.
- [ ] Silkscreen has the board name, version, date or revision, and pin names, and is not covered by pads.
- [ ] DRC has no errors and no unconnected items; you can state the reason for every ignored item.
- [ ] You've looked at it once in the 3D Viewer: no overlapping parts, sensible orientations.

## Manufacturing files

- [ ] Gerber, drill, BOM, and CPL were exported at the same time, from the same version.
- [ ] Every layer was checked in the Gerber Viewer: board outline complete, copper layers correct, no extra or missing layers.
- [ ] BOM and CPL use JLC column names, and pcb-agent-workflow's `skills/jlc-production-review/scripts/check_bom_cpl.py` reports PASS, or every WARNING has a reason.
- [ ] DNP parts, test points, and mounting holes are not mixed into the BOM and CPL.
- [ ] The files handed over are frozen as one set and recorded in the project's README or WORKLOG.

## Before ordering

- [ ] Pin 1, polarity, and rotation of each part were checked in JLC's preview.
- [ ] Confirm Production file is set to Yes; with JLC assembly, Confirm Parts Placement is also set to Yes.
- [ ] You've reviewed the items in the quote that are not included in the total.
- [ ] Uploading, accepting terms, submitting, paying, downloading factory files, confirming the production file or parts placement, and sending messages are all decided and clicked by you; the agent only goes as far as checking and drafting. Full rules are in "Who decides" in jlc-ordering.md.
