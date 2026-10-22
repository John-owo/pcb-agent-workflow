#!/usr/bin/env python3
"""Build a simple STEP model from boxes and cylinders (needs CadQuery).

For parts with no usable vendor model. Dimensions come from the datasheet; the
spec uses footprint coordinates as in the .kicad_mod (origin = footprint origin,
+X right, +Y DOWN, Z up from the board surface), so numbers can be copied from
the footprint's F.Fab outline. The script converts to KiCad's model frame (+Y up).

Spec (JSON):
{
  "output": "MAX-M10S.step",
  "name": "MAX-M10S",
  "source": "u-blox UBX-20035208 R08 Table 21: 9.7 x 10.1 x 2.5 mm (typ)",
  "parts": [
    {"box": [-4.85, 4.85, -5.05, 5.05, 0, 2.5], "color": [0.75, 0.75, 0.78]},
    {"cylinder": {"axis": "z", "center": [0, 0], "radius": 1.0, "range": [0, 1.25]}},
    {"cylinder": {"axis": "x", "center": [0, 9.97], "radius": 9.3, "range": [-32.6, 32.6]}}
  ]
}
box = [x0, x1, y0, y1, z0, z1]. A cylinder's "center" is the two coordinates
perpendicular to its axis, in (x, y, z) order without the axis one.

Usage:
  python simple_model.py spec.json [more.json ...]
"""
import argparse
import glob
import json
import os


def build(spec, base):
    import cadquery as cq
    assy = cq.Assembly(name=spec.get("name", "model"))
    default_color = spec.get("color", [0.7, 0.7, 0.7])
    for i, part in enumerate(spec["parts"]):
        if "box" in part:
            x0, x1, y0, y1, z0, z1 = part["box"]
            shape = cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, pnt=cq.Vector(x0, -y1, z0))
        elif "cylinder" in part:
            c = part["cylinder"]
            r, (a0, a1) = c["radius"], c["range"]
            u, v = c["center"]
            axis = c.get("axis", "z")
            if axis == "z":
                pnt, d = cq.Vector(u, -v, a0), cq.Vector(0, 0, 1)
            elif axis == "x":
                pnt, d = cq.Vector(a0, -u, v), cq.Vector(1, 0, 0)
            else:  # footprint +Y is model -Y
                pnt, d = cq.Vector(u, -a0, v), cq.Vector(0, -1, 0)
            shape = cq.Solid.makeCylinder(r, a1 - a0, pnt, d)
        else:
            raise SystemExit(f"part {i}: need 'box' or 'cylinder'")
        assy.add(shape, name=f"{spec.get('name', 'part')}_{i}",
                 color=cq.Color(*part.get("color", default_color)))
    out = os.path.join(base, spec["output"])
    assy.export(out) if hasattr(assy, "export") else assy.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("specs", nargs="+")
    args = ap.parse_args(argv)
    # PowerShell does not expand wildcards for native commands, so expand them here.
    paths = [p for spec in args.specs for p in (sorted(glob.glob(spec)) or [spec])]
    for path in paths:
        with open(path, encoding="utf-8") as f:
            spec = json.load(f)
        print("wrote", build(spec, os.path.dirname(os.path.abspath(path))))


if __name__ == "__main__":
    main()
