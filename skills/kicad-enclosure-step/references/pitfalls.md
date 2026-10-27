# Common Pitfalls

Problems encountered while doing an actual main board (95 × 50 mm, with an MCU module, LoRa module, GNSS patch, and an 18650 battery holder on the bottom). Values were observed 2026-10 on that job; reconfirm if parts change.

## Origin and orientation

- **A downloaded STEP's origin is not necessarily at the footprint origin.** The footprint and STEP generated together by easyeda2kicad may also not match each other: for one LoRa module, the footprint pads were offset 2.7 mm from the model, while the model itself matched the project footprint outline exactly. Align using the model geometry, e.g. outline, small pad solids, connector position, not the downloaded footprint.
- **Some models are Y-up.** For example, in one XIAO model the PCB thickness direction is Y. `step_report.py` shows the ranges of all three axes, which tells you which axis is the thickness.
- **KiCad's `rotate` sign is the opposite of the right-hand rule.** Measured in KiCad 10: writing `rotate [90, 0, 0]` in the config is equivalent to rotating −90° about the X axis; to turn "Y-up" into "Z-up", you have to write `-90`. Getting it wrong flips the model below the board, and `verify_placement.py` reports FAIL.
- **Modules rotated by 90°.** Some models have length and width swapped relative to the footprint, e.g. 9.7 × 10.1 vs 10.1 × 9.7. Comparing the long and short sides of the bbox reveals this.
- **Feed point and actuator direction.** An antenna's feed electrode, a switch actuator, and a connector opening must be checked against the footprint's F.Fab markings, not just the outline, because the outline still matches after a 180° rotation.

## Height and dimensions

- **Model heights from the fab's library may be inaccurate.** Examples:
  - LoRa module model 5.0 mm tall, datasheet 3.87 mm.
  - GNSS module model 2.2 mm tall, datasheet typical 2.5 mm, max 2.7 mm.
  - Switch actuator model protrudes 1.5 mm, part spec is 2.0 mm.

  For dimensions that affect the enclosure, the datasheet wins; record the differences in the notes.
- **Board thickness in a manufacturer's KiCad files may not be the real value.** One dev board's official KiCad stackup adds up to 1.6 mm, but the official solid model's board thickness is 1.25 mm. Go by the solid model or the physical part.
- **Models may float above the board.** For example, one patch antenna's bottom face is at z = 0.72 and needs to be moved down.
- **Models with the origin at the body's mid-height.** For example, a z range of −0.53…0.48 means z = 0 is not the bottom face; it needs to be moved up.

## Bottom-side parts and through-board features

- Write bottom-side parts in the config as if they were on the top; KiCad automatically flips them to the bottom.
- Battery holder locating posts and header pins go through the board and protrude about 2 mm on the other side. The enclosure must leave room, and the notes must say so.
- If you do not know the battery's height in the holder, use `step_report.py --section x=0` to view the cradle's curved face and back out the battery axis. For example, three section points giving a radius of 9.58 mm means a Ø18.6 battery fits.

## Export

- `--no-dnp` excludes DNP parts; enclosure models usually want this.
- Use `${KICAD10_3DMODEL_DIR}` or absolute paths for model files. The temporary copy is not in the original project folder, so `${KIPRJMOD}` points to the temporary folder.
- `kicad-cli` only prints a warning for missing models and does not fail. `export_step.py` exits with code 2 on `Could not add 3D model`.
- Re-saving a STEP with CadQuery loses colors. To keep the manufacturer's colors, leave the original file alone and write `offset`/`rotate` in the config.

## Downloads

- GrabCAD requires login. The browser the agent uses may have a different login state; ask the user to log in in that browser, or to download to a designated folder themselves.
- GrabCAD's "Download files" first shows a "preparing" message, and the zip downloads a few seconds later; single-file links do not always respond.
- Put each source in its own new, empty folder, and after extracting, read only the STEP.
