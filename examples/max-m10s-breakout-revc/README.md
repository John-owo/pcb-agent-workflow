# MAX-M10S Passive-Antenna GNSS Breakout (Rev C, OSP, top-side assembly only)

A small GNSS breakout built around the u-blox MAX-M10S, taking a passive antenna, for use from a breadboard or host board over UART/I2C. Natively designed in KiCad 10; released 2026-09-21.

## Board specifications

- 25.0 × 36.5 mm, 4 layers, 1.6 mm thick, OSP finish, stackup set to JLC04161H-7628.
- U1: MAX-M10S-00B, using the default low-gain internal LNA.
- J1: I-PEX MHF I (20279-001E-03) for a passive 50 Ω antenna; no antenna power is supplied. D1 provides ESD protection at the antenna end.
- J2, J3: two 1×6, 2.54 mm pin headers inserted from the board bottom, rows 17.78 mm apart.
- 33 Ω series resistors on TX/RX/PPS, 4.7 kΩ pull-ups on I2C, a power LED, and a PPS LED buffered by a BSS138. There are also 5 test pads (TP1, TP2, TP4–TP6).
- No RTC backup supply: U1 pin 6 (V_BCKP) is intentionally left unconnected, and there is no battery or supercapacitor on the board.
- Schematic notes: UART 9600 8N1, I2C address 0x42.

## Wiring

- Connect only a regulated external 3.3 V supply and 3.3 V logic. Not 5 V tolerant.
- Module TX → host RX, module RX → host TX, with a common ground.
- Header pins, from the antenna end down:
  - J2: 3V3 / GND / TX / RX / PPS / EXTINT
  - J3: GND / SCL / SDA / RESET_N / SAFEBOOT_N / GND
- There is no backup supply; after a full power-down the host must reconfigure the GNSS.
- Disconnect host signals before removing GNSS power.
- A blinking PPS LED does not mean a fix has been obtained.

## Files

| Path | Contents |
|---|---|
| `MAX-M10S-Passive.kicad_pro` / `.kicad_sch` / `.kicad_pcb` / `.kicad_dru` | Native KiCad 10 project, schematic, PCB, custom design rules |
| `fp-lib-table`, `sym-lib-table` | Project library tables, pointing to the next two items via `${KIPRJMOD}` relative paths |
| `footprints/PassiveGNSS.pretty/` | Project footprint library |
| `symbols/PassiveGNSS.kicad_sym` | Project symbol library |
| `design.json` | Machine-readable summary of components, nets, part numbers and PCB coordinates (KiCad does not read this file) |
| `manufacturing/gerbers-board.zip` | Single-board Gerbers, drill files and Gerber job file |
| `manufacturing/BOM-JLCPCB-top-only.csv` | Fab assembly BOM: 11 line items, 17 components per board, with LCSC part numbers |
| `manufacturing/CPL-board-top-only.csv` | Fab placement coordinates, Top only, single-board coordinates |
| `manufacturing/assembly-orientation.pdf` / `.csv` / `-1.png` | Assembly orientation drawing and table (pin 1, polarity end, coordinates) |
| `manufacturing/BOM-customer-headers.csv` | Pin headers J2, J3, hand-soldered by you |
| `manufacturing/schematic.pdf` | Schematic PDF |
| `verification/erc.json`, `drc.json` | Native ERC/DRC results at release |
| `verification/release-checks.json` | Release diff check summary |
| `verification/independent-release-review.md` | Independent review record (scope described below) |

The `PassiveGNSS` library also contains items not used on the Rev C board: footprints `ADCM_S05R5SA`, `CPH3225A` (the removed backup supply), `Fiducial_1mm`, `ToolingHole_2mm`, and symbols `BAS116`, `C_Polarized`, `D`. Some footprints/symbols are derived from the official KiCad libraries; see the repo NOTICE for sources and licenses.

## Which files to use for manufacturing

The following four items are one set. Use them together and do not mix them with files from other versions:

1. `manufacturing/gerbers-board.zip`: board fabrication
2. `manufacturing/BOM-JLCPCB-top-only.csv`: assembly BOM
3. `manufacturing/CPL-board-top-only.csv`: placement coordinates
4. `manufacturing/assembly-orientation.pdf` (plus `.csv`, `.png`): assembly orientation, used to check the fab's placement preview

Notes:

- The Gerbers are a single board, without panel rails or fiducials. The arrangement at the original release was for the fab to add rails and fiducials and remove the rails before delivery; this service and approach must be confirmed with the fab.
- The factory assembles only the 17 top-side components. Headers J2 and J3 are not in the assembly BOM/CPL; per `BOM-customer-headers.csv`, insert them from the board bottom and solder them yourself (2 per board). The native design still keeps J2 and J3 as part of the finished product.
- Solder the headers on OSP boards as soon as possible after they arrive.

## Verified

- **Native ERC/DRC** (KiCad 10.0.6, at release 2026-09-21): ERC 0 violations; DRC 0 violations, 0 unconnected items, 0 schematic/PCB parity issues. Reports include all three severities (error, warning, exclusion); see `verification/`.
- **Re-run on this copy** (2026-10-02, KiCad 10.0.6 `kicad-cli`, `--severity-all`, DRC with `--schematic-parity`): same results. Libraries loaded correctly via `${KIPRJMOD}`, with no missing symbol or footprint warnings. The output of this re-run is not included in the package, so as not to alter the release-time `verification/`; you can reproduce it with the commands in section 5 of [kicad-tools.md](../../docs/workflow/kicad-tools.md).
- **Release diff check** (`release-checks.json`): compared with the previous Rev C, PCB geometry, tracks, pads and nets are unchanged. This version only changed the D1 part number text, datasheet links, OSP manufacturing attributes and the assembly lists. The Gerber ZIP is bit-for-bit identical to the file uploaded to the fab at the time.
- **Independent review** (`independent-release-review.md`): a read-only review agent checked the release files (README, BOM, CPL, assembly table, ERC/DRC reports, etc.) for mutual consistency and found no fatal inconsistencies or omissions. The review covers only the consistency of these files; it reviewed the original release README, and this README, rewritten for the public example, is out of scope. The reviewer did not reopen or recompute the Gerber ZIP, nor check website status, stackup implementation, PDF rendering, electrical/RF/EMC/DFM behavior, or physical boards.

## Not verified

- Passing ERC/DRC does not mean the circuit is correct, that the fab will accept it, or that the physical board works.
- EMC: the earlier design review did only a heuristic EMC analysis, leaving untested risk notes, e.g. no dedicated GND stitching via within 1 mm of where interface signals change layers. These do not count as passing EMC, and no EMC testing has been done.
- SPICE: automatic simulation was skipped because the local simulator timed out; there is no SPICE pass result.
- This version only checked delivery differences; it is not a fresh full electrical/EMC verification.
- Fab DFM review and placement confirmation results are not in this package. The fab's final production file and component orientation must be confirmed separately.
- No physical board testing has been done yet, and M10S assisted-positioning firmware has not been verified. For the test procedure and results, see [max-m10s-breakout-revc-tests](../max-m10s-breakout-revc-tests/README.md). Earlier ALP/AOP tests on a NEO-6M cannot be taken as M10S results.

## Known caveats

- **D1 footprint name differs from the actual part number**: the footprint is named `PassiveGNSS:PESD3V3C1BSF`, but the actual part is Nexperia PESD3V3Z1BSFYL (LCSC C2908830). Both use the same land pattern (DSN0603-2/SOD962-2, 0.4 mm pitch), so the footprint name was not changed. Purchase according to the part number in the BOM.
- **D1 pad clearance**: following the Nexperia recommended land pattern, the actual gap between the two pads is about 0.144 mm, smaller than the project default clearance (0.2 mm net class). `.kicad_dru` sets local rules for D1 pad-to-pad (0.13 mm) and RF track to D1 pads (0.15 mm), and also requires 1.0 mm between RF and the GND pour.
- **Finish field in the Gerber job file**: in `gerbers-board.zip`, `MAX-M10S-Passive-job.gbrjob` has `Finish` set to `ENIG`, while the PCB settings and this version's manufacturing spec are OSP. The Gerbers were not regenerated after switching to OSP, so select OSP on the order.
- **J1 coordinates**: the CPL uses the connector's mechanical center (15.800, 33.700), which differs from the RF contact pad (15.800, 32.175). Confirm the orientation of the shell and the center contact.
- **Polarity**: top-side markings on a component do not necessarily indicate polarity. For D2, D3, Q1 and U1, compare the fab's placement preview against pin 1 and the polarity end in `assembly-orientation.pdf`.
- **Component count in design.json**: the note says 19 components; this count includes the hand-soldered J2 and J3. Fab assembly is 17.
- During design, the differences and trade-offs were compared item by item with SparkFun's public MAX-M10S breakout schematic. This design's circuit and files were redrawn; no SparkFun files were copied.
- The U1 and J1 footprints were built from manufacturer documents: MAX-M10S Integration Manual UBX-20053088 R05 (pads, stencil apertures) and I-PEX 20279 drawing rev.29. These manufacturer documents are not included in this package.

## Manufacturer datasheets

Manufacturer datasheets, integration manuals and drawings are copyrighted and not included in this package; download them from the manufacturers' websites. The table below is taken from the Datasheet fields of the schematic symbols:

| Designator | Part number | Manufacturer | Datasheet |
|---|---|---|---|
| U1 | MAX-M10S-00B | u-blox | https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf |
| D1 | PESD3V3Z1BSFYL | Nexperia | https://assets.nexperia.com/documents/data-sheet/PESD3V3Z1BSF.pdf |
| Q1 | BSS138 | onsemi | https://www.onsemi.com/pdf/datasheet/bss138-d.pdf |

The Datasheet fields of the other components (resistors, capacitors, LEDs, J1, headers) are empty; look them up on the manufacturers' websites by the manufacturer part numbers in the BOM.
