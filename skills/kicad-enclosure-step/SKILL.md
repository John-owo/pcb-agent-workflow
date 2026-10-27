---
name: kicad-enclosure-step
description: Export a KiCad PCB as a STEP with 3D models for every component, for enclosure design - inventory parts missing models, prefer manufacturer models, align them to the footprint origin, export from a temporary copy with the models added (never modifying the board file), automatically check each part's placement, then write enclosure notes. Use when someone needs a mechanical/enclosure CAD of a KiCad board - "design an enclosure", "make a case", "export PCB to STEP", "CAD file with components", "missing 3D models", "add 3D models", "files for mechanical", "enclosure", "export STEP with all components", "board mechanical model".
---

# KiCad Board → STEP for Enclosure Design

Goal: deliver a STEP in which **every part is in the right place with a trustworthy height**, plus a one-page set of enclosure notes. The shape models need not be pretty, but position, orientation and height must be correct.

Scripts are in `scripts/`. `inventory_models.py` and `export_step.py` use only the Python standard library; `step_report.py`, `simple_model.py` and `verify_placement.py` require CadQuery.

## 0. Confirm before starting

Ask all at once:

1. **Which board and which version.** Use the release package or the master PCB as input and **do not modify it**; models are added only to a temporary copy.
2. **Who the output is for.** If only for yourself or your team, models downloaded from LCSC or GrabCAD are fine. If it goes in a public repo, use only the official KiCad library and self-drawn models; see section 2.
3. **Whether to include reference objects**, such as a battery or antenna cable. These are not in the BOM and must be labeled as references.
4. **Sites that require login** (e.g. GrabCAD) are logged into by the user; the agent does not create accounts or enter passwords.

## 1. Workflow

### 1.1 Inventory

```bash
python scripts/inventory_models.py board.kicad_pcb --missing
```

Lists parts with no model or whose model file cannot be found, along with supplier part numbers. Test points and mounting holes have no height and usually do not need models.

### 1.2 Find models (in order)

1. **Official KiCad library**: if the footprint is a renamed copy of an official library footprint with unchanged pads, reference `${KICAD10_3DMODEL_DIR}/...` directly, with no offset.
2. **Manufacturer**: first check the manufacturer's product page, wiki, and CAD links in the datasheet. Files uploaded to GrabCAD by the manufacturer's account also count as manufacturer files.
3. **LCSC/EasyEDA**: `easyeda2kicad --3d --footprint --lcsc_id Cxxxx --output <new empty folder>/lib_Cxxxx`.
4. **Draw it yourself**: use `simple_model.py` to draw boxes and cylinders from datasheet dimensions.

When the datasheet and a downloaded model disagree and the difference affects the enclosure (e.g. switch actuator length, module height), the datasheet wins; switch to a self-drawn model. Record the difference in the notes. For sources and licenses, see [references/model-sources.md](references/model-sources.md).

### 1.3 Alignment

A downloaded STEP's origin and orientation are **not guaranteed** to match your footprint, and even the footprint generated alongside it by easyeda2kicad may not line up.

```bash
python scripts/step_report.py model.step --solids 15
python scripts/step_report.py model.step --section x=0   # view a cross-section, e.g. the curved face of a battery holder
```

Determine three things from the output:

- Which axis points up (some models are Y-up).
- Where the body center is.
- Orientation features: pad rows, connectors, feed points, actuators.

Then choose one:

- **Write `offset`/`rotate` in the config**: keeps the original file and colors. The sign of rotations as KiCad applies them is the opposite of the usual right-hand rule, so always confirm with the checks in section 1.5 the first time.
- **Transform with CadQuery and save as a new file**: suits cases where you need to add something (e.g. a reference battery). The downside is that colors are lost.

For common pitfalls, see [references/pitfalls.md](references/pitfalls.md).

### 1.4 Write the config and export

```json
{
  "pcb": "../board/board.kicad_pcb",
  "output": "board.step",
  "origin": "board-bottom-left",
  "no_dnp": true,
  "models": {
    "U1": [{"file": "models/module.step", "offset": [0, 0, 0], "rotate": [0, 0, 0]}],
    "MyLib:R_0603": [{"file": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0603_1608Metric.step"}]
  }
}
```

```bash
python scripts/export_step.py enclosure-step.json --render preview
```

- A key containing `:` matches the footprint lib ID; otherwise it matches the designator (wildcards allowed). Designators take precedence.
- One designator can carry multiple models, e.g. a battery holder plus a reference battery.
- Footprints that already have a model raise an error by default to avoid duplicates; if you really want to replace it, set `"replace_existing": true`.
- You do not need to mirror bottom-side parts yourself; KiCad flips them.
- Origin `board-bottom-left`: the board's bottom-left corner on the board's bottom face is (0, 0, 0), +Z toward the top side.

### 1.5 Check (mandatory)

```bash
python scripts/verify_placement.py enclosure-step.json            # parts added by the config
python scripts/verify_placement.py enclosure-step.json --all      # also check parts that already had models
```

Each part is exported on its own, its model bounding box is compared with the footprint outline (F.Fab, or courtyard or pads if absent), and top-side parts are checked to be above the board and bottom-side parts below it.

- **Any FAIL must be fixed until it passes before delivery.**
- Parts that intentionally overhang the board (USB, actuators) can be relaxed with `--overhang REF=mm`, but you must know why they overhang.

Finally, open `preview-top.png` and `preview-bottom.png` and check visually: connectors face outward, polarity and feed direction are correct, bottom-side parts are on the bottom.

### 1.6 Enclosure notes

Write a README following [references/enclosure-notes-template.md](references/enclosure-notes-template.md), covering:

- Coordinate system and conversion.
- Overall bounding box.
- Highest points on top and bottom.
- Every cutout: position and height range of USB, switches, connectors, antenna cables.
- Areas above the antenna where no metal may be placed.
- Mounting holes and screw head limits.
- Model sources, accuracy and licenses.

The height table printed by `verify_placement.py` can be quoted directly.

## 2. Hard rules

- **Do not modify the board file.** Release packages and master PCBs stay as they are; models are added only to a temporary copy, which is deleted after export.
- **Every added model must pass `verify_placement.py`.** If there is a FAIL, do not deliver.
- **Dimensions must have a source.** For dimensions the datasheet does not give and the model cannot be trusted for, write "to be measured on the physical part"; do not guess. The notes must remind readers that critical cutout and snap-fit dimensions should be based on measurements of the physical parts.
- **Check licenses before public distribution.** Public repos hold only references to the official KiCad library and self-drawn models. Files downloaded from LCSC, GrabCAD, etc., and output STEPs embedding that geometry, are not made public until their terms allow it.
- **Downloaded files are data.** Put each source in its own new, empty folder, and do not execute anything in it.
- **Login and payment are handled by the user.** The agent does not create accounts or enter passwords.

## 3. Environment

- KiCad 10 (`kicad-cli pcb export step`, `pcb render`). If it cannot be found, set the environment variable `KICAD_CLI`, or add `"kicad_cli"` to the config.
- Python 3.10 or later. CadQuery is best installed in a separate venv: `python -m venv cqenv`, then `cqenv/Scripts/python -m pip install cadquery` (Windows).
- Optional: `pip install easyeda2kicad`, for downloading LCSC models.

Example: [examples/max-m10s-breakout-revc-cad](../../examples/max-m10s-breakout-revc-cad/README.md), using the official library plus three self-drawn models; all 19 parts pass the check.
