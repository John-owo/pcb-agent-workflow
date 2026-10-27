# Getting started: your first PCB from scratch

For people making their first PCB. Follow this and you will go from installing KiCad all the way to ordering at JLCPCB. Each step covers three things: what you do, what you can ask the agent (Claude Code or Codex) to do, and how to confirm you got it right.

First, the scope of this guide:

- **It stops at ordering.** This workflow comes from a GNSS board that has been ordered but not yet tested as a real board (see [examples/](../examples/max-m10s-breakout-revc/README.md)). For power-up and testing after the board arrives, there is a [bench test procedure](../examples/max-m10s-breakout-revc-tests/README.md) for the example board, but it has not yet been run on a real board.
- **That example board is not a good model for a first board.** It is 4 layers with an RF antenna, which makes it an advanced design. Read it to see what a complete release package looks like, not to copy it.
- **The agent is an assistant, not the designer.** It can look things up, explain errors, check files, and draft documents; check its conclusions against the manufacturer's datasheet, and you are always the one who clicks pay or submit.
- Look up unfamiliar terms in the [glossary](glossary.md).

## 0. Keep the first board small

The goal of a first board is "go through the whole workflow once and get a working board", not to build the most impressive feature. Recommendations:

| Item | First-board recommendation | Why |
|---|---|---|
| Layer count | 2 layers | Cheap, KiCad defaults to 2 layers, simple rules |
| Size | Within a business card | Cheap; too small actually runs into assembly size limits |
| Components | 0805 or larger resistors and capacitors, or through-hole parts | Easy to hand-solder, easy to rework |
| Part numbers | Prefer JLC Basic parts | Each Extended part type carries an extra feeder loading fee (observed 2026-10) |
| Assembly | PCB only and solder it yourself, or single-side assembly only | Double-sided assembly requires Standard assembly, which costs more (observed 2026-09, see [jlc-ordering.md](workflow/jlc-ordering.md)) |
| Avoid | RF/antennas, high-speed signals, lithium battery charging, mains (AC 220 V/110 V) | These need experience, and mistakes can be dangerous |

Example projects: USB-C power + LED + button, a breakout board for a sensor module, an expansion board for Arduino/Pico.

**You can ask the agent:**

> I want to make a board that <function>. The first version uses only 2 layers, JLC Basic parts, and single-side assembly. List the functional blocks I need, and which manufacturer datasheet or reference design to consult for each. Don't start drawing, and don't change any files.

## 1. Set up your environment

| Tool | Required? | Purpose |
|---|---|---|
| [KiCad](https://www.kicad.org/download/) 10 | Required | Draw the schematic and PCB, export manufacturing files. This repo verified its commands on 10.0.6 |
| Git | Strongly recommended | Commit after each step so you can go back if something breaks |
| Claude Code or Codex | Recommended | This repo's workflow is written for collaborating with an agent |
| Python 3.12 | Required for JLC assembly | Runs the BOM/CPL check script (step 7). Not needed if you only order PCBs and solder yourself |
| [kicad-happy](https://github.com/aklofas/kicad-happy) skills | Optional | Lets the agent analyze schematics, BOMs, DRC |
| Konnect MCP | **Not needed for beginners** | Lets the agent operate KiCad directly; currently beta, see [kicad-tools.md](workflow/kicad-tools.md) |

Then download this repo to your computer, **outside your PCB project folder**, for example side by side:

```bash
git clone https://github.com/John-owo/pcb-agent-workflow.git
```

Without Git, you can also use Code → Download ZIP on the GitHub page and unzip it. Wherever `<pcb-agent-workflow>` appears below, it means the path to this folder.

**Confirm it's right:** running `kicad-cli version` in a terminal prints a version number. If Windows can't find the command, KiCad's `bin` folder may not be on PATH; you can ask the agent to help find the install location.

## 2. Start a new project

1. KiCad: File → New Project, and pick a folder that holds **only this project**.
2. Copy `AGENTS.md`, `CLAUDE.md`, `WORKLOG.md`, `README.md` from `<pcb-agent-workflow>/templates/` into it and replace the `<...>` placeholders with your own content; copy `templates/kicad-project.gitignore` into it and rename it to `.gitignore`.
3. Run `git init` in the folder and make your first commit.

From then on, each new agent conversation starts by reading `README.md` and `WORKLOG.md`, so it knows where you left off.

## 3. Draw the schematic

1. **Start every circuit block from the manufacturer's documentation.** An IC datasheet usually has a "Typical Application" circuit listing the external components and values needed. Follow it, not your memory.
2. Place symbols, draw wires, label nets. Use power symbols for power and GND.
3. For each part to be assembled, add a field named `LCSC` to the symbol and fill in the LCSC part number (for example `C25804`). Step 7 uses this field name when exporting the BOM.
4. Set parts that won't be populated (for example test points) to DNP (Do Not Populate).
5. Run ERC (Inspect → Electrical Rules Checker), and understand every error before dealing with it.

**You can ask the agent:**

> What external components does the typical application circuit in the <MPN> datasheet need? List the values, their purpose, and the datasheet page numbers.

> Run `kicad-cli sch erc`, explain each error in plain language, and describe possible fixes. Don't change any files yet.

**Confirm it's right:** ERC has no errors; every IC power pin has a decoupling capacitor; you can say which document each part value came from.

## 4. Choose parts and footprints

1. Search [LCSC](https://www.lcsc.com/) or JLC's parts library and note the part number starting with C (the C-code). Check three things: package size, stock, and whether it is Basic or Extended.
2. Each part's footprint must match the dimensions in the datasheet of **the exact part you are buying**. Two parts both called SOT-23 may have different pinouts from different manufacturers; headers and connectors must also face the right way.
3. Footprints not in KiCad's built-in libraries can be obtained from the manufacturer or the LCSC page. Put them in the **project's own** library (with a `${KIPRJMOD}` path), not only in a global library on your machine.

**You can ask the agent:**

> Find 0805, 10 kΩ, 1% Basic parts on LCSC and list the C-code, stock, and lookup date.

> Compare U1's footprint pins with the pinout in the <MPN> datasheet, list pin by pin whether they match, and include the datasheet page numbers.

**Confirm it's right:** every assembled part has a C-code; you have personally checked pin 1 and the orientation of polarized parts (diodes, LEDs, electrolytic capacitors) against the datasheet.

## 5. Set board rules

In the PCB Editor, open File → Board Setup, and fill in the table below under Design Rules → Constraints and Net Classes. Menu names may differ in the version you installed.

| Item | Beginner value | JLC 2-layer capabilities page (observed 2026-10) |
|---|---|---|
| Signal track width | 0.25 mm | Min 0.10 mm |
| Clearance | 0.2 mm | Min 0.10 mm |
| Power track width | Calculate from current with Track Width in KiCad's built-in Calculator Tools, at least 0.5 mm | — |
| Via drill/diameter | 0.3 mm/0.6 mm | Drill 0.2–0.25 mm with diameter under 0.45 mm, or drill 0.15 mm or less, costs extra |
| Copper to board edge | 0.5 mm | Min 0.2 mm |
| Silkscreen text height/line width | 1.0 mm/0.15 mm | Text height 1.0 mm, line width 0.15 mm or more |

The recommended values are deliberately looser than the capabilities page: a first board should be easy to make and easy to rework, not push the limits. Capabilities change; before ordering, go by the [JLC PCB capabilities page](https://jlcpcb.com/capabilities/pcb-capabilities).

## 6. Placement and routing

1. Draw the board outline (Edge.Cuts) first, then place things with fixed positions: connectors, buttons, mounting holes.
2. Then place ICs, with decoupling capacitors close to the IC power pins.
3. Route by hand: power first, then signals. A common approach on 2-layer boards is a large GND pour on the bottom layer.
4. Put the board name, version, pin names, and pin 1 on the silkscreen.
5. Run DRC (Inspect → Design Rules Checker): no errors, no unconnected items.

Auto-placement and autorouting have **no verified** solution in this workflow; route your first board yourself.

**You can ask the agent:**

> Review the current schematic and PCB against <pcb-agent-workflow>/docs/first-board-checklist.md. For each item write "pass/fail/can't tell" with evidence. Don't change any files.

> Run `kicad-cli pcb drc` and explain each violation. Don't change any files yet.

**Confirm it's right:** you have gone through every item in the [first-board checklist](first-board-checklist.md); ERC and DRC have no errors. Remember that passing ERC/DRC does not mean the circuit is correct, only that it breaks no rules.

## 7. Export manufacturing files

For the Gerber, drill, and CPL export commands, see [kicad-tools.md section 5](workflow/kicad-tools.md#5-kicad-cli-commands); for a 2-layer board, remove `In1.Cu` and `In2.Cu` from the Gerber layer list. Put output in a folder such as `out/` inside the project, and don't overwrite design files. After exporting, zip the folder containing the Gerber and drill files; that is the Gerber zip you upload.

For JLC assembly you also need a BOM and CPL, with column names in JLC's format:

| File | JLC column names | Source in KiCad |
|---|---|---|
| BOM | `Comment`, `Designator`, `Footprint`, `LCSC Part #` | Value, Reference, Footprint, the `LCSC` field added in step 3 |
| CPL | `Designator`, `Mid X`, `Mid Y`, `Layer`, `Rotation` | Ref, PosX, PosY, Side, Rot from the position file (pos) |

The BOM can be exported directly with JLC column names, with the part number included in the grouping so parts with the same value but different part numbers are not merged:

```bash
kicad-cli sch export bom --fields "Value,Reference,Footprint,LCSC" --labels "Comment,Designator,Footprint,LCSC Part #" --group-by "Value,Footprint,LCSC" --ref-range-delimiter "" --exclude-dnp -o out/bom-jlc.csv <project>.kicad_sch
```

This command has not yet been tested on KiCad 10; first run `kicad-cli sch export bom --help` to confirm all these flags exist. `--ref-range-delimiter ""` turns off range abbreviation: by default KiCad writes `R1,R2,R3` as `R1-R3`, but JLC needs each one listed, and the check script also rejects abbreviations. Windows PowerShell 5.1 does not pass the empty string `""` to programs, so run it in Git Bash or PowerShell 7.3 or later.

After exporting the CPL from the position file, rename the columns to JLC's format and add units to the coordinates, for example `12.5mm`. You can ask the agent to do the conversion.

Then run the check script:

```bash
python <pcb-agent-workflow>/skills/jlc-production-review/scripts/check_bom_cpl.py --bom out/bom-jlc.csv --cpl out/cpl-jlc.csv
```

It checks that the BOM and CPL designators match exactly, for duplicates, part number format, coordinates, and side. The result is `PASS` (exit code 0), `WARNING` (1, needs a human to look), or `INCOMPLETE` or `ERROR` (2, do not order). It does **not** check rotation, polarity, stock, or whether footprints are correct; confirm those in JLC's preview.

**You can ask the agent:**

> Convert the position file KiCad exported in out/ to JLC's CPL column names and format, save it as cpl-jlc.csv without overwriting the original, then run <pcb-agent-workflow>/skills/jlc-production-review/scripts/check_bom_cpl.py and explain the result.

**Confirm it's right:** open the exported Gerbers in KiCad's Gerber Viewer and look at every layer once; the check script reports `PASS`, or you can explain the reason for each `WARNING`.

## 8. Order

There are two routes for a first board:

| Route | How | Suits |
|---|---|---|
| A. PCB only | Upload the Gerber zip, receive bare boards, solder them yourself | All parts are through-hole or 0805 and larger, and you can use a soldering iron |
| B. Economic PCBA | Also upload the BOM and CPL; JLC assembles one side | You have small SMD parts or want to save soldering time |

For ordering details (service level, parts matching, submission settings, post-payment process), see [jlc-ordering.md](workflow/jlc-ordering.md). Common beginner pitfalls:

- After uploading, check pin 1 and polarity of each part in the preview.
- Set **Confirm Production file** to Yes so the factory asks you before changing your files. On route B, also set **Confirm Parts Placement** to Yes.
- Uploading, accepting terms, submitting, paying, downloading factory files, confirming the production file or parts placement, and sending messages are each decided and clicked by you (full rules in "Who decides" at the top of [jlc-ordering.md](workflow/jlc-ordering.md)). The agent can help you check things and draft messages to customer service, stopping before any button is pressed.

Before ordering, freeze the set of files you hand to the factory (see [release-package.md](workflow/release-package.md)) so later questions can be traced to a version.

## 9. Waiting for boards and after they arrive

- When the factory sends the production file, you download it, then ask the agent to help compare it following the [jlc-production-review skill](../skills/jlc-production-review/SKILL.md). Confirming the production file is still your decision.
- For power-up and testing after the boards arrive, follow the example board's [bench test procedure](../examples/max-m10s-breakout-revc-tests/README.md). If your board differs, keep at least its first three steps: visually inspect for shorts or solder bridges, measure that power is not shorted to ground before powering up, and use a current-limited supply for the first power-up.

## What to read next

| To learn about | Read |
|---|---|
| What terms mean | [glossary.md](glossary.md) |
| What to check before sending to the fab | [first-board-checklist.md](first-board-checklist.md) |
| Collaborating with and handing off to agents | [collaboration.md](workflow/collaboration.md) |
| JLC ordering details | [jlc-ordering.md](workflow/jlc-ordering.md) |
| Communicating with JLC customer service | [jlc-support skill](../skills/jlc-support/SKILL.md) |
| Drawing readable, debuggable schematics | [readable-schematic-layout skill](../skills/readable-schematic-layout/SKILL.md) |
| Letting the agent operate KiCad directly (advanced) | [kicad-tools.md](workflow/kicad-tools.md) |
