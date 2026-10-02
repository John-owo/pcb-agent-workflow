#!/usr/bin/env python3
"""pixel_compare.py - per-layer raster diff of original vs factory renders.

Step 2 of the cam-diff toolkit (see README.md in this folder). Reads the folder written by
render_compare.py (layer-summary.json + <LABEL>-orig.png / <LABEL>-cam.png).

For every layer pair it writes
  <LABEL>-diff.png        grey = both, red = only in factory (added), blue = only in original
                          (removed); orange boxes mark changes larger than --tolerance-px
  <LABEL>-comparison.png  original (left) and factory (right) side by side
  pixel-summary.json      added/removed area in mm2, total and beyond tolerance, plus a list of
                          changed regions with centres in the factory frame AND the original
                          single-board frame (use the latter when you write to the factory)

"Drawn" means copper for copper layers, an opening for solder mask, paste for paste and ink for
silkscreen. A pixel diff only shows where the artwork differs; it does not tell you whether a
change is acceptable and it is not a netlist comparison.

Usage
  python pixel_compare.py --renders cam-diff-out
  python pixel_compare.py --renders cam-diff-out --layers F_Cu B_Cu --tolerance-px 1

Requires the pinned CAM runtime (Python 3.12; pip install -r requirements-cam.txt).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load_mask(path):
    from PIL import Image

    return Image.open(path).convert("L").point(lambda v: 255 if v < 128 else 0)


def count(img):
    return sum(img.histogram()[1:])


def dilate(img, px):
    from PIL import ImageFilter

    return img if px <= 0 else img.filter(ImageFilter.MaxFilter(2 * px + 1))


def label_regions(mask, w):
    """8-connected components of a binary 'L' image; returns lists of flat pixel indices."""
    data = mask.tobytes()
    todo = {i for i, v in enumerate(data) if v}
    regions = []
    while todo:
        seed = todo.pop()
        stack, comp = [seed], [seed]
        while stack:
            i = stack.pop()
            x, y = i % w, i // w
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx = x + dx
                    if nx < 0 or nx >= w:
                        continue
                    j = (y + dy) * w + nx
                    if j in todo:
                        todo.remove(j)
                        stack.append(j)
                        comp.append(j)
        regions.append(comp)
    return regions


class Frames:
    """pixel <-> factory mm <-> original mm, from layer-summary.json."""

    def __init__(self, summary):
        (self.x0, self.y0), (self.x1, self.y1) = summary["window_mm"]
        self.ppmm = summary["ppmm"]
        t = summary.get("transform", {})
        self.dx, self.dy = t.get("offset_mm", [0.0, 0.0])
        a = math.radians(t.get("rotate_deg_ccw", 0.0))
        self.c, self.s = math.cos(a), math.sin(a)

    def factory_mm(self, px, py):
        return self.x0 + (px + 0.5) / self.ppmm, self.y1 - (py + 0.5) / self.ppmm

    def original_mm(self, X, Y):
        u, v = X - self.dx, Y - self.dy
        return self.c * u + self.s * v, -self.s * u + self.c * v


def compare_layer(label, info, renders, out, fr: Frames, args):
    from PIL import Image, ImageChops, ImageDraw

    a = load_mask(renders / info["png_original"])
    b = load_mask(renders / info["png_factory"])
    if a.size != b.size:
        raise SystemExit(f"error: {label}: image sizes differ {a.size} vs {b.size}")
    expected = (max(1, round((fr.x1 - fr.x0) * fr.ppmm)), max(1, round((fr.y1 - fr.y0) * fr.ppmm)))
    if a.size != expected:
        raise ValueError(f"{label}: render dimensions do not cover the declared frame")
    w, h = a.size
    px_area = 1.0 / (fr.ppmm ** 2)
    added, removed = ImageChops.subtract(b, a), ImageChops.subtract(a, b)
    big_add = ImageChops.subtract(b, dilate(a, args.tolerance_px))
    big_rem = ImageChops.subtract(a, dilate(b, args.tolerance_px))
    changed = ImageChops.lighter(big_add, big_rem)

    regions = []
    add_bytes, rem_bytes = big_add.tobytes(), big_rem.tobytes()
    if count(changed):
        for comp in label_regions(dilate(changed, args.group_px), w):
            n_add = sum(1 for i in comp if add_bytes[i])
            n_rem = sum(1 for i in comp if rem_bytes[i])
            if n_add + n_rem < args.min_region_px:
                continue
            real = [i for i in comp if add_bytes[i] or rem_bytes[i]]
            xs, ys = [i % w for i in real], [i // w for i in real]
            bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            fX, fY = fr.factory_mm(cx, cy)
            oX, oY = fr.original_mm(fX, fY)
            (fx0, fy1), (fx1, fy0) = fr.factory_mm(bx0, by0), fr.factory_mm(bx1, by1)
            regions.append({
                "center_factory_mm": [round(fX, 3), round(fY, 3)],
                "center_original_mm": [round(oX, 3), round(oY, 3)],
                "bbox_factory_mm": [round(fx0, 3), round(fy0, 3), round(fx1, 3), round(fy1, 3)],
                "added_mm2": round(n_add * px_area, 4),
                "removed_mm2": round(n_rem * px_area, 4),
                "_box_px": (bx0, by0, bx1, by1),
            })
    regions.sort(key=lambda r: -(r["added_mm2"] + r["removed_mm2"]))

    # images
    both = ImageChops.darker(a, b)
    overlay = Image.new("RGB", a.size, "white")
    overlay.paste((54, 54, 54), mask=both)
    overlay.paste((239, 59, 56), mask=added)
    overlay.paste((22, 131, 219), mask=removed)
    d = ImageDraw.Draw(overlay)
    pad = max(4, args.group_px)
    for r in regions:
        x0, y0, x1, y1 = r["_box_px"]
        d.rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad), outline=(255, 140, 0), width=2)
    overlay.save(out / f"{label}-diff.png")

    sheet = Image.new("RGB", (w * 2 + 10, h + 40), "white")
    sd = ImageDraw.Draw(sheet)
    sd.text((10, 12), f"{label}: original (left) / factory CAM (right), same window", fill="black")
    sheet.paste(Image.open(renders / info["png_original"]).convert("RGB"), (0, 40))
    sheet.paste(Image.open(renders / info["png_factory"]).convert("RGB"), (w + 10, 40))
    sheet.save(out / f"{label}-comparison.png")

    for r in regions:
        r.pop("_box_px")
    return {
        "changed_pixels": count(added) + count(removed),
        "size_px": [w, h],
        "added_mm2": round(count(added) * px_area, 4),
        "removed_mm2": round(count(removed) * px_area, 4),
        "added_beyond_tol_mm2": round(count(big_add) * px_area, 4),
        "removed_beyond_tol_mm2": round(count(big_rem) * px_area, 4),
        "regions_total": len(regions),
        "regions": regions[: args.max_regions],
        "diff_png": f"{label}-diff.png",
        "comparison_png": f"{label}-comparison.png",
    }


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Raster diff of the PNG pairs written by render_compare.py. Step 2 of cam-diff.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python pixel_compare.py --renders cam-diff-out")
    ap.add_argument("--renders", required=True, help="folder written by render_compare.py")
    ap.add_argument("--out", help="output folder (default: the --renders folder)")
    ap.add_argument("--layers", nargs="*", help="labels to compare (default: all in layer-summary.json)")
    ap.add_argument("--tolerance-px", type=int, default=1,
                    help="ignore edge differences up to this many pixels (default 1 = 0.025 mm at 40 px/mm)")
    ap.add_argument("--group-px", type=int, default=3, help="merge changed pixels closer than this into one region")
    ap.add_argument("--min-region-px", type=int, default=2, help="drop regions with fewer changed pixels")
    ap.add_argument("--max-regions", type=int, default=200, help="regions listed per layer in the JSON")
    return ap.parse_args(argv)


def run(args, result):
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit("error: Pillow is missing; run: python -m pip install -r requirements-cam.txt")
    renders = Path(args.renders)
    summary = json.loads((renders / "layer-summary.json").read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else renders
    out.mkdir(parents=True, exist_ok=True)
    fr = Frames(summary)
    if not math.isfinite(fr.ppmm) or fr.ppmm <= 0 or not all(math.isfinite(v) for v in
            (fr.x0, fr.x1, fr.y0, fr.y1, fr.dx, fr.dy, fr.c, fr.s)) or fr.x1 <= fr.x0 or fr.y1 <= fr.y0:
        raise ValueError("invalid render frame")
    if args.tolerance_px < 0 or args.group_px < 0 or args.min_region_px < 1 or args.max_regions < 1:
        raise ValueError("invalid pixel or region limits")
    labels = args.layers if args.layers is not None else list(summary["layers"])
    result.update(ppmm=fr.ppmm, tolerance_mm=round(args.tolerance_px / fr.ppmm, 4),
                  upstream_status=summary.get("status"), requested_layers=labels)
    if summary.get("status") != "PASS":
        result["issues"].append({"status": "INCOMPLETE", "message": "render verification did not PASS"})
    if not labels:
        result["issues"].append({"status": "INCOMPLETE", "message": "no layers selected"})
    if set(labels) != set(summary["layers"]):
        result["issues"].append({"status": "INCOMPLETE", "message": "partial layer selection"})
    print(f"{'layer':10} {'added':>9} {'removed':>9} {'add>tol':>9} {'rem>tol':>9} {'regions':>8}   (mm2)")
    for label in labels:
        info = summary["layers"].get(label)
        if not info:
            result["issues"].append({"status": "INCOMPLETE", "message": f"{label}: missing requested layer"})
            continue
        r = compare_layer(label, info, renders, out, fr, args)
        result["layers"][label] = r
        if r["changed_pixels"]:
            result["issues"].append({"status": "WARNING", "message": f"{label}: raster differences require review"})
        print(f"{label:10} {r['added_mm2']:9.3f} {r['removed_mm2']:9.3f} {r['added_beyond_tol_mm2']:9.3f} "
              f"{r['removed_beyond_tol_mm2']:9.3f} {r['regions_total']:8d}")
    print(f"\nwrote {out / 'pixel-summary.json'}; open the *-diff.png files and classify each orange box")


def main(argv=None):
    args = parse_args(argv)
    out = Path(args.out or args.renders)
    out.mkdir(parents=True, exist_ok=True)
    result = {"tool": "pixel_compare.py", "schema_version": 1,
              "scope": "raster difference detection; not netlist or production approval",
              "tolerance_px": args.tolerance_px, "layers": {}, "issues": []}
    try:
        run(args, result)
    except (Exception, SystemExit) as e:
        result["issues"].append({"status": "ERROR", "message": f"analysis failed ({type(e).__name__})"})
        print(f"error: {e}")
    priority = {"PASS": 0, "WARNING": 1, "INCOMPLETE": 2, "ERROR": 3}
    result["status"] = max((i["status"] for i in result["issues"]), key=priority.get, default="PASS")
    (out / "pixel-summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1 if result["status"] == "WARNING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
