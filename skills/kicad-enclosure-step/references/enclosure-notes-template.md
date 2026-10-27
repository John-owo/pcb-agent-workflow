# <board name> 3D Files for Enclosure Design

Source design: <board file path>, <version or commit>. These files are for enclosure design only, not for manufacturing; the board file was not modified.

## Files

| File | Contents |
|---|---|
| `<board name>.step` | Full board plus all parts (DNP excluded)<; also includes reference objects: …> |
| `preview-top.png`, `preview-bottom.png` | Top and bottom renders |
| `enclosure-step.json` | Export config: which model each part uses |
| `models/` | Added or self-drawn models |

To re-export: `python <skill>/scripts/export_step.py enclosure-step.json --render preview`

## Coordinates

- Units are mm. Origin at the board's bottom-left corner, on the board's bottom face; +X right, +Y up, +Z toward the component side.
- Board occupies x 0–<width>, y 0–<height>, z 0–<thickness>.
- Converting from board coordinates (origin at top-left, Y down): STEP (x, y) = (board x, <height> − board y).
- Overall bounding box: x <…>, y <…>, z <…>.

## Enclosure considerations

| Item | STEP position | Notes |
|---|---|---|
| Highest point on top | <designator>, (<x>, <y>) | Top at z <…>, <…> mm above the board surface |
| Lowest point on bottom | <designator> | Bottom down to z <…> |
| <connector/USB> cutout | x <…>, z <…>, overhangs <which edge> to <…> | The plug overmold is larger than the receptacle; leave space around the cutout |
| <switch actuator> | <…> | Width <…>, travel <…> |
| <antenna> | <…> | Only plastic above it, no metal |
| <through-board pins, locating posts> | <…> | Protrude <…> mm on the other side |
| Mounting holes | <position, diameter> | Max screw head/standoff diameter <…> |

## Model sources and accuracy

| Designator | Part | Source | Notes (correction method, differences from datasheet) |
|---|---|---|---|
| … | … | … | … |

`verify_placement.py`: all <n> parts pass (<date>). The shape models are not manufacturer mechanical drawings; **for critical enclosure cutout and snap-fit dimensions, rely on measurements of the physical parts**.

## License

<distribution terms for each source; clearly state which models are for internal use only>
