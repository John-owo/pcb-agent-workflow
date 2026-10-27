# 3D Model Sources and Licenses

In order of priority. Licenses observed 2026-10; check each site's current terms before use.

| Source | How to get it | Good for | Distribution |
|---|---|---|---|
| Official KiCad 3D library | Comes with KiCad: `${KICAD10_3DMODEL_DIR}/<library>.3dshapes/<name>.step` | Passives, common IC packages, pin headers, connectors; when a footprint is a renamed official one with unchanged pads, offsets are all 0 | CC-BY-SA 4.0 plus the KiCad exception: designs and output using these models are not bound by CC-BY-SA, but the model files themselves are. In a public repo, reference them via `${KICAD10_3DMODEL_DIR}`; do not copy the model files |
| Manufacturer | Product page, wiki, datasheet CAD links; files uploaded by the manufacturer's account on GrabCAD and similar platforms | Modules, dev boards, special connectors | Per the manufacturer's terms. Without explicit permission to distribute, use internally only |
| LCSC/EasyEDA | `easyeda2kicad --3d --footprint --lcsc_id Cxxxx --output <dir>/lib_Cxxxx` | Parts in the fab's parts library | Terms do not explicitly allow distribution; use internally only |
| SnapEDA, Ultra Librarian, etc. | Account required; some take until the next day to generate | Filling gaps none of the above cover | Per each platform's terms |
| Draw it yourself (`simple_model.py`) | Draw boxes and cylinders from datasheet dimensions | No model available, downloaded model conflicts with the datasheet, public examples | Your own work, can be published. State the dimension source in the spec's `source` field |

## Finding manufacturer models

- Search "<part number> STEP" or "<part number> 3D model", preferring the manufacturer's domain.
- Dev board wikis often have a "Resources/Mechanical" section with 3D models, DXF dimension drawings and KiCad files.
- A manufacturer's KiCad project can be exported with `kicad-cli pcb export step`, but the models it references often point to the manufacturer's internal paths, such as `Y:/...`, so parts will be missing; the board thickness may also not be the real value.

## Accuracy of self-drawn models

- An enclosure needs only the outer envelope: body length, width and height, plus anything that sticks out (connectors, actuators, antenna connectors, through-board pins).
- Draw with the datasheet's **typical** values and state the maximum values in the notes, so the enclosure designer can decide how much clearance to leave.
- No need to draw internal structure, text or pin details.
