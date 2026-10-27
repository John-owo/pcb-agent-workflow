# cam-diff: layer-by-layer diff of the factory production file against the original Gerbers

Align the factory CAM-modified production file (often with rails and panelization) back to the single-board Gerbers you submitted and find differences layer by layer. The review workflow and how to interpret results are in [procedure.md](procedure.md).

The scripts only analyze; they never modify input files and never go online.

## Requirements

| Script | Python | Packages |
|---|---|---|
| `render_compare.py` | 3.12 (the version used for pinned packages and CI) | `gerbonara`, `Pillow` |
| `pixel_compare.py` | 3.12 (the version used for pinned packages and CI) | `Pillow` |
| `check_inner_removals.py` | 3.12 (the version used for pinned packages and CI) | `Pillow` |

```
python -m pip install -r scripts/requirements-cam.txt
```

Installing in a venv is recommended. gerbonara pulls in click, rtree and quart (for its own CLI and viewer). Neither gerbv nor KiCad is required. KiCad's Gerber Viewer is good for visual rechecks; KiCad's bundled Python is needed only to produce a `holes.json` with net names (see below).

Run the install command from this skill's folder; dependency versions (including indirect packages) are pinned in `scripts/requirements-cam.txt`. When updating versions, rerun `python -m unittest discover -s tests -v`; CI runs the tests on Windows and Linux with Python 3.12.

## Results and stop conditions

The JSON from all three scripts has `schema_version`, `status`, `scope` and `issues`. Statuses and exit codes:

| status | exit code | Meaning |
|---|---|---|
| `PASS` | 0 | The scope the script declares is complete, with no pending items |
| `WARNING` | 1 | Analysis complete but there are differences, or the upload identity has not been checked; needs review |
| `INCOMPLETE` | 2 | Missing data, non-unique pairing, partial analysis or unsupported items; cannot claim a pass |
| `ERROR` | 2 | Input, parse or execution error; cannot claim a pass |

Other agents must check both the exit code and the JSON from that run; "there is a report / there are PNGs / there are no orange boxes" must not be read as PASS. Downstream steps do not accept an old report without a status, or a non-PASS upstream result, as complete verification; diagnostic images can still be produced, but the result will not be PASS. On CLI argument errors, failure to write output, or refusal to reuse an output directory, there may be no new JSON; exit code 2 still means failure, and an old report must not be used in its place.

A `render_compare` PASS only means input coverage and rendering are complete; the per-layer pixel diff still has to be done. `pixel_compare` reports WARNING for any pixel difference (tolerance and region size only control display and classification; they cannot hide differences). A `check_inner_removals` PASS applies only to the copper-removal heuristic on the selected layers; when there are no inner layers, an empty result must not be taken as a pass. None of these PASS results is a netlist check, manufacturing tolerance check, physical board verification or production approval.

Use a fresh or empty `--out` directory for every rendering, outside the source folder, so old and new PNG/JSON files never mix. Error reports keep only the exception type; detailed console messages and relative file names may still contain private information, so check them yourself before publishing.

## The three scripts

| Step | Script | Input | Output |
|---|---|---|---|
| 1 | `render_compare.py` | Original Gerbers + drill (folder or zip), factory production file (folder or zip) | `layer-summary.json`, `<layer>-orig.png`, `<layer>-cam.png`, `panel-<filename>.png` |
| 2 | `pixel_compare.py` | Folder from step 1 | `<layer>-diff.png`, `<layer>-comparison.png`, `pixel-summary.json` |
| 3 | `check_inner_removals.py` | Folder from step 1, optionally with `holes.json` | `<layer>-inner-check.png`, `inner-check.json` |

**render_compare.py**
- Pairs layers by file name. The original side recognizes KiCad naming (`*-F_Cu.*`, `*.gtl`, etc.); the factory side recognizes JLCPCB's extensionless files (`tl bl l2 l3 ts bs to bo ko drl`) and common extensions. Candidates for all aliases are checked together, and a pairing is used only if it is unique; it no longer takes the first match. `--pair label=original_pattern,factory_pattern` overrides this; patterns containing `/` match the full relative path, otherwise the basename.
- Top copper, bottom copper and outline are required; any other layer needs a pairing as soon as either side has a file. Unpaired files on the original CAM side also count as INCOMPLETE. All drill patterns are merged (including PTH/NPTH); multiple drill files with the same basename are never chosen between automatically. Non-standard boards can use `--only-pairs` for diagnosis, but cannot get a complete PASS.
- When the production file lacks a paste layer or similar, record the reason with `--omit-layer F_Paste=stencil reviewed separately`; an excluded layer still makes the result INCOMPLETE and needs separate review evidence; success on the remaining layers cannot stand in for it.
- Finds the original→factory coordinate transform: `--rotate` (degrees counterclockwise, about the origin, applied first) plus translation. You can give the translation yourself (`--offset 23 17`) or have `--offset auto` estimate it from drill positions.
- Transforms the original board outline (Edge_Cuts centerline) into factory coordinates as the comparison window, and rasterizes both sides in the same window at the same resolution (default 40 px/mm).
- Pairs drill holes one to one and lists holes moved more than `--moved-tol` (default 0.005 mm), holes missing at the factory, extra holes inside the board, holes outside the board (usually rail tooling holes), and an original-diameter→factory-diameter mapping (which reveals compensation).
- Also outputs a preview of the whole process frame for each factory Gerber, for recognizing rails, V-cuts and hole treatment markings.
- `--check-upload` takes the factory's retained "copy of the original submission" and compares the SHA-256 of every member file by full relative path. Same-named files in different directories do not overwrite each other; missing files, extra files and differing content are all reported as INCOMPLETE. If the factory repackaged the directories, first verify and arrange the corresponding root directory in a new working copy; basenames are never guessed automatically. When not provided, `upload_check.status=NOT_RUN` and the overall result is at least WARNING.
- Slots are currently only counted, not compared geometrically, so the result is INCOMPLETE when slots are present. Parser warnings, empty artwork, missing/empty drill, missing outline, or a manually narrowed window cannot get a complete PASS. Hole position and diameter differences are reported as WARNING; equidistant drill candidates are not paired and are reported as INCOMPLETE.

**pixel_compare.py**
- Gray = present on both sides, red = only in the factory file (added), blue = only in the original (removed). Changes beyond tolerance are marked with orange boxes.
- `pixel-summary.json` lists the added/removed area per layer (both total and beyond tolerance) and the center of each changed region, in both factory coordinates and original single-board coordinates. Use original single-board coordinates when writing to the factory.
- "What is drawn" means copper on copper layers, openings on solder mask layers and ink on silkscreen layers.

**check_inner_removals.py**
- For each hole, flood-fills the connected copper outward from the hole center on the original image. If the fill stays within a `--max-pad-mm` box and contains only one hole, it is treated as an unused isolated pad on that layer; otherwise it is treated as connected.
- Copper removed by the factory counts as expected processing (removal of non-functional pads on inner layers) only if it falls within an isolated pad. Removal anywhere else, or missing center copper on a connected pad, is listed as suspicious.
- When net names are supplied with `--holes`, add `--plane-nets GND` to list holes on plane nets that lost their center copper.
- A custom `--holes` file must map uniquely, one to one and completely onto the original drill coordinates from step 1 within 0.000001 mm. Missing, extra, duplicate or mismatched holes are reported as INCOMPLETE, and the original hole positions are used for diagnosis; unverified net labels are not trusted. `custom_holes_verified` records the check result.
- Besides matching each other in size, the two PNGs must fully cover the declared `window_mm × ppmm` extent; two images cropped the same way cannot pass.

## Usage

```
python scripts/render_compare.py --original release/gerbers.zip --factory factory/production.zip --offset auto --out out
python scripts/pixel_compare.py --renders out
python scripts/check_inner_removals.py --renders out
```

Common options:

| Option | Purpose |
|---|---|
| `--offset auto` / `--offset DX DY` | Translation (mm). If auto finds several candidate positions it stops and reports ERROR; specify each one with `--offset` |
| `--rotate 90` | Use when the factory rotated the board; degrees counterclockwise |
| `--pair In1_Cu=*-In1_Cu.*,l2` | Add or override a layer pairing; also used to compare the paste layer when a stencil file is provided separately |
| `--margin 0.5` | Extend the window outward by 0.5 mm, for changes near the board edge |
| `--ppmm 80` | Increase resolution (memory and time grow roughly with the square) |
| `--check-upload original_submission_copy.zip` | Compare the factory's retained original submission with your fixed package |

First self-compare the same Gerbers to confirm the environment works (expected: offset (0, 0), all holes paired with zero error, zero difference on every layer):

```
python scripts/render_compare.py --original gerbers.zip --factory gerbers.zip --check-upload gerbers.zip --out selftest
python scripts/pixel_compare.py --renders selftest
```

### Generating holes.json with net names from KiCad

Run with KiCad's bundled Python (Windows example: `"C:\Program Files\KiCad\10.0\bin\python.exe"`). Coordinates are converted to Gerber coordinates: relative to the drill/place origin, Y axis up. If the Gerbers were exported without using that origin, change `o` to (0, 0).

```python
import json, sys, pcbnew
board = pcbnew.LoadBoard(sys.argv[1])
o = board.GetDesignSettings().GetAuxOrigin()
ox, oy = pcbnew.ToMM(o.x), pcbnew.ToMM(o.y)
def xy(p): return round(pcbnew.ToMM(p.x) - ox, 4), round(oy - pcbnew.ToMM(p.y), 4)
holes = []
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA":
        x, y = xy(t.GetPosition()); holes.append({"x": x, "y": y, "net": t.GetNetname()})
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.HasHole():
            x, y = xy(pad.GetPosition())
            holes.append({"x": x, "y": y, "net": pad.GetNetname(), "ref": fp.GetReference() + "-" + pad.GetNumber()})
json.dump(holes, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
```

## Limitations

- Resolution: at 40 px/mm one pixel is 0.025 mm, and the default tolerance is 1 pixel. Shape changes smaller than about 0.03 mm (such as copper compensation) are not listed as beyond tolerance. Hole position comparison is numeric and not subject to this limit; for small hole moves, see `drills.moved` in `layer-summary.json`.
- Looks only at graphics and does not understand nets. It cannot prove connectivity, nor replace the factory's netlist comparison or electrical test; `check_inner_removals.py` is a heuristic on rasters.
- No DRC: does not check whether clearance, annular ring or solder mask dams meet process capability.
- The transform supports only rotation plus translation, not mirroring or scaling. Bottom-layer Gerbers are already in top-view coordinates and need no mirroring.
- Layer pairing relies on file names. Unmatched layers are recorded in `issues` in `layer-summary.json` and reported as INCOMPLETE; they must be supplied and rerun. Only non-required layers that are empty on both sides (such as an unused bottom paste layer) can complete pairing; the required copper layers and outline cannot be empty.
- Parsing depends on gerbonara; the number of parse warnings is recorded in `layer-summary.json`. Format issues such as arcs with omitted parameters may cause small silkscreen differences; rule out parsing problems before treating them as factory changes.
- Outline layer line widths often differ from the original (factory drawing lines are thicker); interpret outline differences by board size and V-cut annotations, not pixel area.
- Does not interpret ODB++, V-cut semantics, hole treatment markings (such as `sk`) or panelization process steps. For these, read the drawing annotations and ask engineering.
- Does not check PCBA placement; placement coordinates and polarity are checked manually per the workflow document.

## Privacy

The output JSON records the factory files' member names and hashes, and file names may contain the order number; the PNGs are the factory's production data. Keep the output in a private directory and do not commit it to a public repository.
