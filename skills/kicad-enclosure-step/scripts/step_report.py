#!/usr/bin/env python3
"""Describe a STEP file so it can be aligned to a footprint (needs CadQuery).

Prints the overall bounding box and the largest solids. Use it on a downloaded
model to find which axis is "up", where the body centre is and where pins or
connectors sit, before writing offset/rotate values.

Usage:
  python step_report.py model.step [--solids 12] [--section x=0]
"""
import argparse


def fmt(b):
    return f"x[{b.xmin:8.3f},{b.xmax:8.3f}] y[{b.ymin:8.3f},{b.ymax:8.3f}] z[{b.zmin:8.3f},{b.zmax:8.3f}]"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step")
    ap.add_argument("--solids", type=int, default=12, help="how many of the largest solids to list")
    ap.add_argument("--section", help="axis=value, e.g. x=0: list solid pieces cut by a 0.5 mm slab there")
    args = ap.parse_args(argv)

    import cadquery as cq
    shape = cq.importers.importStep(args.step)
    whole = shape.val().BoundingBox()
    print("overall ", fmt(whole), f" size {whole.xlen:.3f} x {whole.ylen:.3f} x {whole.zlen:.3f}")
    solids = sorted(shape.solids().vals(), key=lambda s: -s.Volume())
    print(f"{len(solids)} solid(s); largest:")
    for s in solids[:args.solids]:
        print(f"  V={s.Volume():10.2f}  {fmt(s.BoundingBox())}")
    if args.section:
        axis, value = args.section.split("=")
        value = float(value)
        big = 1e4
        lo = {"x": (value - 0.25, -big, -big), "y": (-big, value - 0.25, -big), "z": (-big, -big, value - 0.25)}[axis]
        size = {"x": (0.5, 2 * big, 2 * big), "y": (2 * big, 0.5, 2 * big), "z": (2 * big, 2 * big, 0.5)}[axis]
        slab = cq.Solid.makeBox(*size, pnt=cq.Vector(*lo))
        print(f"section {axis}={value:g}:")
        for s in solids:
            for piece in s.intersect(slab).Solids():
                print("  ", fmt(piece.BoundingBox()))


if __name__ == "__main__":
    main()
