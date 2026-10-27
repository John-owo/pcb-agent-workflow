---
name: readable-schematic-layout
description: 'Draw KiCad schematics and PCB layouts the way humans expect and in a way that is easy to debug - use KiCad built-in symbols and power symbols, draw actual wires, group blocks by current/signal flow, keep text from overlapping, and make the layout mirror the schematic blocks with good debug points. When only the drawing style changes, prove the circuit is unchanged by comparing netlist connection groups. Use when drawing, redrawing, cleaning up or reviewing a schematic or PCB layout for readability/debuggability - "readable schematic", "redraw schematic", "draw it the human way", "overlapping text", "use built-in symbols", "easy to debug", "clean up schematic", "debuggable layout".'
---

# Human-Readable, Debuggable Schematics and Layouts

The target reader is someone debugging with a multimeter and an oscilloscope: from the drawing they should see where power comes from, where signals go, and which point to probe.
The project's own collaboration rules (single writer, preserve a version before editing files, review process) take precedence; this skill only governs "how to draw" and "proving the circuit was not changed".

## 0. Decisions to ask the user before starting (do not decide them yourself)

Ask only when files will be changed; if you are only reviewing readability without changing files, review directly and list results as recommendations. When files will be changed, ask everything at once and touch files only after the answers:

1. **What is the source of truth**: a program generator (a script that outputs `.kicad_sch`), or direct editing of `.kicad_sch` (KiCad GUI, KiCad MCP or scripts)? After switching to direct editing, the generator must be deleted or disabled; otherwise rerunning it overwrites the manual edits.
2. **Who operates**: the agent (MCP/scripts, no GUI) or the user in the GUI. Only one writer at a time.
3. **Whether ICs switch to built-in symbols** (only those that have one; redraw custom symbols for the rest).
4. **Net names**: keep the original names (docs, firmware and review records need no changes), or change to KiCad standard names (`+3V3`).
5. **Cross-sheet signals**: global labels at the sheet edge, or hierarchical labels + wiring on the root sheet.
6. **Fallback when MCP cannot do something**: edit the text file directly with a small script, or stop and ask.
7. **Reviewer**: another agent, a read-only subagent, or the user visually.

## 1. Schematic drawing

### Symbols
- Always use KiCad built-in symbols for discrete parts: MOSFET `Transistor_FET:<MPN>` or `Device:Q_NMOS`/`Q_PMOS`, switch `Switch:SW_SPDT`/`SW_Push`, battery `Device:Battery_Cell`, TVS/ESD `Device:D_TVS` (bidirectional) or `Power_Protection:*`, antenna `Device:Antenna_Shield`, test point `Connector:TestPoint`, R/C/L/LED `Device:*`. Do not use custom box-shaped symbols for these parts.
- Use an IC's built-in symbol if one exists (e.g. `RF_GPS:MAX-M10S`, `Power_Management:TPS22919DCK`, `Logic_LevelTranslator:SN74LVC1T45DBV`). How to check: KiCad 10's built-in libraries have one file per symbol; check whether `share/kicad/symbols/<library>.kicad_symdir/<name>.kicad_sym` exists in the KiCad install directory. For older versions (a single `<library>.kicad_sym`), search the file for `symbol "<name>"`. The names above all exist in the KiCad 10.0.6 official libraries (confirmed 2026-10).
- Draw your own symbol for ICs/modules without a built-in one: power pins on top, GND at the bottom, inputs on the left, outputs on the right; group pins of the same function (SPI, UART, power, control) together; pin names per the datasheet; mark unused pins no-connect.
- **When swapping a symbol, always check pin number = footprint pad number.** Built-in symbol pin numbers often differ from self-made footprints (e.g. the common terminal of an SPDT switch, battery +/−, antenna feed/ground). If they do not match, swap the symbol or use a custom symbol; **do not change the footprint or the wiring**. If a change is truly needed, ask the user first.
- When swapping a symbol, keep the designator, value, footprint, Datasheet, Description and all custom fields (Manufacturer, MPN, supplier part number, DNP, etc.).

### Wiring and nets
- Use power symbols for power and ground (`power:GND`, `power:+3V3`…). When keeping original net names, create power symbols in the same style in the project library for names not in the built-in library (such as `VSYS`); the net name is determined by the symbol's value, so confirm the name in the netlist afterwards.
- Power symbol orientation is fixed: positive supplies point up, GND points down.
- **Draw actual wires between components on the same sheet**; do not hang a label on every pin. Use labels only for cross-sheet signals (gathered in an "interface column" at the sheet edge), or when a wire would be so long it crosses other blocks.
- Do not use both a label and a differently named power symbol on the same net.
- Draw decoupling capacitors next to the power pin of their IC, wiring from the pin to the capacitor and then to the GND symbol.
- Wires do not pass through component bodies; T junctions must have a junction dot; avoid four-way crossing junctions.
- Put no-connect on unused pins; place the `PWR_FLAG` needed by ERC next to the power entry point.

### Arrangement
- Left to right following **current/signal flow**: e.g. battery → protection → reverse polarity → switch → system power → boost/LDO → loads; MCU → level shifter → module → RF front end → antenna.
- Enclose each functional block in a frame with a title, e.g. "Battery protection", "5V boost".
- Power on top, GND at the bottom; align similar circuits (a row of pull-down resistors, test points) in a row.
- Place components, wires and labels on a 50 mil (1.27 mm) grid; symbols only at 0°/90°/180°/270°.
- **Text must not overlap**: designators, values, labels, notes and pin names do not overlap each other, nor sit on wires or symbols; put value and designator on the same side next to the symbol.
- Put design notes (power switch rules, chip errata, power-off isolation, why a pin is left unconnected) in blank space next to the relevant circuit, framed if needed; do not leave them only in external documents.
- Label test points with the net name and expected value (e.g. `TP1 VBUS_SENSE, <0.5 V without USB`).
- If the page is too small, switch to A3 or split sheets; do not cram. The root sheet holds only sub-sheet boxes and brief block descriptions.

## 2. PCB layout (the debug-friendly parts)

Read [references/layout.md](references/layout.md) only when drawing or reviewing a layout: blocks and designators, 4-layer stackup role of each layer, test points and debug reference drawings, hand-soldering friendliness, layout verification. Before changing a layout with Konnect, read [references/konnect-limits.md](references/konnect-limits.md) first.

## 3. Acceptance: prove only the drawing changed, not the circuit

Before editing the drawing, preserve it (git commit or a full copy) and copy out the baseline netlist.

1. Export the netlist: `kicad-cli sch export netlist --format kicadxml -o <new>.xml <root>.kicad_sch`
2. Compare connection groups and component fields (scripts are in this skill directory's `scripts/`):
   `python -I <skill directory>/scripts/compare_netlist.py <base>.xml <new>.xml [--names]`
   Must be `IDENTICAL`. Add `--names` when keeping the original net names. Every difference must be explainable line by line; otherwise go back and fix the drawing.
3. ERC: `kicad-cli sch erc --severity-all -o erc.rpt <root>.kicad_sch` → 0 errors, 0 warnings.
4. Symbol/footprint pin numbers:
   `python -I <skill directory>/scripts/check_pin_pad.py <new>.xml --pcb <project name>.kicad_pcb`
   If there is no PCB yet, use `--footprints <footprint folder>` instead. Must be `PASS`; explain each "pad without pin" (e.g. mounting pads); always go back and fix any "pin without pad".
5. Visual: `kicad-cli sch export pdf` → `pdftoppm -r 110 -png` → look at each page. `pdftoppm` comes from poppler, which Windows does not include (install with `winget install oschwartz10612.Poppler` or conda's `poppler`); without it, open the PDF directly or ask the user to look. Check that text does not overlap, wires do not cross components, blocks are clear, notes are all present, and flow goes left to right. An MCP overlap-detection tool can help but does not replace visual inspection.
6. Hand a fixed version to the reviewer, focusing on the netlist comparison result and readability.

Only when all of the above pass can you say "drawing style changed, circuit unchanged"; this still does not mean it is electrically correct or that the physical board will work.

## 4. Tooling

Principle: MCP reads the current state and does live edits; scripts and `kicad-cli` make the call. An MCP reply of "success" does not count as acceptance; always read back per section 3.

| Step | MCP | Script/CLI (relative to this skill folder) | Pass condition |
|---|---|---|---|
| Save baseline before starting | — | `kicad-cli sch export netlist --format kicadxml` → `base.xml` | File exists |
| Read current state | Konnect 0.12.1: `get_project_info`, `list_schematic_components` | — | Read-back matches the file on disk |
| Change drawing | Konnect `sch_components`, `sch_wiring`, `sch_hierarchy` | Use a small script to edit `.kicad_sch` for what MCP cannot do | Run steps 1–3 of section 3 after each sub-sheet |
| Prove the circuit is unchanged | — | `scripts/compare_netlist.py`, `kicad-cli sch erc` | `IDENTICAL`, ERC 0 |
| Pin numbers vs pads | Konnect `get_component_pads` (auxiliary only) | `scripts/check_pin_pad.py` | `PASS` |
| Live PCB adjustment | Konnect `pcb_components` (via KiCad IPC) | `kicad-cli pcb drc --schematic-parity` | Reply has `source=ipc`, DRC 0 |
| Visual | — | `kicad-cli sch export pdf` (plus `pdftoppm`) | Reviewer has looked |

- If the Konnect version is not 0.12.1, first run `get_installation_info`, then get `tools/list` (or use `listTools` in `konnect-call.mjs`), and go by the actual schema. Installation, configuration and the capability table are in pcb-agent-workflow's `docs/workflow/kicad-tools.md`.
- Without Konnect: read via `kicad-cli` exports instead, and edit the text file directly with small scripts (when KiCad does not have the file open); acceptance per section 3 is unchanged.
- Some KiCad MCP tools send design data to remote services. Before using them on a real design, check each one and get the user's consent.

## 5. Tool notes

- When using a KiCad MCP (such as Konnect), first list and load the schematic-related tool groups (components, wiring, batch, analysis, export) and go by the actual schema; do not guess parameters.
- For actions MCP cannot do (such as swapping a symbol while keeping custom fields), use a small script to edit the `.kicad_sch` text directly; likewise do it while the file is not open in the GUI, and likewise go through section 3 acceptance.
- Run steps 1–3 of section 3 after finishing each sub-sheet; do not wait until everything is redrawn to compare.
