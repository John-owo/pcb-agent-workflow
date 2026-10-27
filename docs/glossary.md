# Glossary

Terms that come up often in this repo, in workflow order: design, manufacturing files, fab and ordering. English abbreviations are kept as is, because both the KiCad and JLC interfaces use English.

## Design

| Term | Meaning |
|---|---|
| Schematic | The drawing of "which parts and how they connect", regardless of physical position. KiCad file `.kicad_sch` |
| PCB layout | Placing parts on the board and drawing copper traces. KiCad file `.kicad_pcb` |
| symbol | A part's symbol on the schematic |
| footprint | A part's pad pattern on the PCB. Its dimensions must match the part you actually buy |
| net | A group of pins electrically connected together, e.g. `GND`, `3V3` |
| netlist | The list of all nets; comparing it before and after a change shows whether connections were altered |
| ERC | Electrical Rules Check, checks the schematic's connection rules (e.g. output tied to output, unconnected pins) |
| DRC | Design Rules Check, checks PCB rules such as trace width, clearance, and unrouted connections |
| Decoupling capacitor | A small capacitor placed next to an IC's power pin to stabilize the supply |
| via | A small hole connecting different copper layers |
| Annular ring | The width of the copper ring around a hole |
| Copper pour (zone) | A large copper area, usually tied to GND |
| Board outline (Edge.Cuts) | The layer defining the board's shape |
| Stackup | The material and thickness of each layer in a multilayer board |
| DNP | Do Not Populate, a part drawn in the design but not assembled |
| Test point | A pad left for measurement |

## Manufacturing files

| Term | Meaning |
|---|---|
| Gerber | The manufacturing file format fabs use, one file per layer, usually packed into a zip |
| Drill file (Excellon) | Records the position and diameter of every hole |
| PTH/NPTH | Hole walls plated with copper (conductive) / not plated (e.g. mounting holes) |
| Solder mask | The green (or other color) coating on the board surface that keeps solder from flowing where it shouldn't |
| Silkscreen | Text and markings printed on the board |
| Paste layer / stencil | The opening pattern used to print solder paste during assembly |
| BOM | Bill of Materials, the parts list: value, designator, package, part number |
| CPL | Component Placement List, each part's coordinates, rotation, and side. Also called pick-and-place or position file |
| Designator (reference) | A part's identifier, e.g. R1, C3, U1 |
| pin 1 | A part's first pin, used to determine orientation |

## Fab and ordering

| Term | Meaning |
|---|---|
| PCB/PCBA | Bare board / board with parts assembled (Assembly) |
| SMT/THT | Surface-mount parts / through-hole parts |
| LCSC part number, C-code | Part number shared by JLC and LCSC, e.g. `C14663` |
| MPN | Manufacturer Part Number, the original manufacturer's part number |
| Basic/Extended parts | Basic parts stay loaded on the pick-and-place machines; Extended parts require a feeder change, with a fee per part type. Preferred Extended parts avoid the feeder change fee with Economic assembly (observed 2026-10; the JLC website takes precedence) |
| Economic/Standard assembly | JLC's two assembly service levels, differing in which sides can be assembled, minimum component size, and size limits; see [jlc-ordering.md](workflow/jlc-ordering.md) |
| DFM | Design for Manufacturing, the fab's check of whether the design can be made |
| Confirmation items | Umbrella term for what the factory asks you to confirm after payment, split into the two kinds below |
| Production file | PCB only: the version the factory prepares for production after CAM processing of your Gerbers; you need to confirm it |
| Parts placement confirmation | PCBA only: each component's position, rotation, and polarity; you need to confirm it, and JLC puts it into production automatically when overdue |
| Rails | Strips added around the board edge for machine clamping, removable after assembly |
| Panel | Multiple boards arranged together for production |
| V-cut | V-shaped grooves between panel boards so they can be snapped apart |
| Fiducial | Round copper marks the pick-and-place machine uses for alignment |
| Surface finish | How the pad surfaces are treated: HASL (hot-air solder leveling, cheap but uneven), ENIG (immersion gold, flat, more expensive), OSP (organic protective coating, cheap, solder soon after opening the package) |

## Terms specific to this repo

The authoritative definitions for this section are in [CONTEXT.md](../CONTEXT.md) at the repo root; where the two disagree, CONTEXT.md wins.

| Term | Meaning |
|---|---|
| Release package | The set of files handed to the factory, not modified afterward; see [release-package.md](workflow/release-package.md) |
| Bench test record | Power-on and functional test results after the boards arrive, kept outside the release package |
| WORKLOG | A chronological work log of who did what and where things stopped |
| Writer | The only person or agent allowed to modify the design files at a given time |
| PASS/WARNING/INCOMPLETE/ERROR | Result states of this repo's scripts. Only PASS means everything in that script's check scope passed; the others all need handling or review |
