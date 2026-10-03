#!/usr/bin/env python3
"""check_inner_removals.py - is the copper the factory removed only unused (non-functional) pads?

Step 3 of the cam-diff toolkit (see README.md in this folder). Reads the folder written by
render_compare.py. Typical use: inner layers, where CAM often deletes the isolated copper ring
around a via or pin that has no connection on that layer ("non-functional pad removal").

Method, per layer and per hole (holes come from the original drill files, or from --holes):
  * In the ORIGINAL render, flood-fill the copper under the hole centre inside a box of
    +/- --max-pad-mm. If the fill never reaches the box edge, the copper is an isolated island
    (an unused pad on this layer). If it reaches the edge, the pad is connected to a trace,
    spoke or plane on this layer.
  * Copper removed by the factory (beyond --tolerance-px) is "expected" only inside isolated
    islands (grown by the tolerance). Anything removed elsewhere is listed as suspicious.
  * A connected pad whose centre copper disappeared in the factory render is suspicious.
  * With --holes carrying a "net" per hole, holes on --plane-nets that lost centre copper are
    listed too (useful to show the plane net, e.g. GND, kept every connection).

This is a raster heuristic at the render resolution. It is not a netlist comparison and does not
replace the factory's electrical test or their own netlist check; ask them for that.

Usage
  python check_inner_removals.py --renders cam-diff-out
  python check_inner_removals.py --renders cam-diff-out --layers In1_Cu In2_Cu \
      --holes holes.json --plane-nets GND

holes.json (optional), original single-board frame, mm, same origin as your Gerbers:
  [{"x": 6.34, "y": 5.90, "net": "PPS"}, {"x": 20.84, "y": 28.5, "net": "GND"}, ...]

Requires the pinned CAM runtime (Python 3.12; pip install -r requirements-cam.txt).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


def load_mask(path):
    from PIL import Image

    return Image.open(path).convert("L").point(lambda v: 255 if v < 128 else 0)


class Frames:
    def __init__(self, summary):
        (self.x0, self.y0), (self.x1, self.y1) = summary["window_mm"]
        self.ppmm = summary["ppmm"]
        if not all(math.isfinite(v) for v in (self.x0, self.y0, self.x1, self.y1, self.ppmm)) or self.ppmm <= 0 or self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("invalid render window or ppmm")
        t = summary.get("transform", {})
        self.dx, self.dy = t.get("offset_mm", [0.0, 0.0])
        if not all(math.isfinite(v) for v in (self.dx, self.dy, t.get("rotate_deg_ccw", 0.0))):
            raise ValueError("invalid transform")
        a = math.radians(t.get("rotate_deg_ccw", 0.0))
        self.c, self.s = math.cos(a), math.sin(a)

    def fwd(self, x, y):  # original -> factory frame
        return self.c * x - self.s * y + self.dx, self.s * x + self.c * y + self.dy

    def inv(self, X, Y):
        u, v = X - self.dx, Y - self.dy
        return self.c * u + self.s * v, -self.s * u + self.c * v

    def to_px(self, X, Y):
        return math.floor((X - self.x0) * self.ppmm), math.floor((self.y1 - Y) * self.ppmm)

    def to_mm(self, px, py):
        return self.x0 + (px + 0.5) / self.ppmm, self.y1 - (py + 0.5) / self.ppmm


def island(data, w, h, px, py, half):
    """Flood-fill copper from (px, py) inside a box of +/- half pixels.
    Returns (set_of_indices, touched_box_edge)."""
    x0, x1, y0, y1 = px - half, px + half, py - half, py + half
    start = py * w + px
    seen, stack = {start}, [start]
    edge = False
    while stack:
        i = stack.pop()
        x, y = i % w, i // w
        if x <= x0 or x >= x1 or y <= y0 or y >= y1 or x in (0, w - 1) or y in (0, h - 1):
            edge = True
            break
        for j in (i - 1, i + 1, i - w, i + w):
            if j not in seen and data[j]:
                seen.add(j)
                stack.append(j)
    return seen, edge


def components(indices, w):
    todo, out = set(indices), []
    while todo:
        s = todo.pop()
        stack, comp = [s], [s]
        while stack:
            i = stack.pop()
            x, y = i % w, i // w
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (dx == 0 and dy == 0) or not 0 <= x + dx < w:
                        continue
                    j = (y + dy) * w + x + dx
                    if j in todo:
                        todo.remove(j)
                        stack.append(j)
                        comp.append(j)
        out.append(comp)
    return out


def check_layer(label, info, renders, fr: Frames, holes, args):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    a = load_mask(renders / info["png_original"])
    b = load_mask(renders / info["png_factory"])
    if a.size != b.size:
        raise ValueError(f"{label}: original/factory image sizes differ")
    expected_size = (max(1, round((fr.x1 - fr.x0) * fr.ppmm)),
                     max(1, round((fr.y1 - fr.y0) * fr.ppmm)))
    if a.size != expected_size:
        raise ValueError(f"{label}: image size does not cover the declared render window")
    w, h = a.size
    ad, bd = a.tobytes(), b.tobytes()
    k = 2 * args.tolerance_px + 1
    removed = ImageChops.subtract(a, b.filter(ImageFilter.MaxFilter(k)) if k > 1 else b)

    allowed = Image.new("L", a.size, 0)
    allowed_px = allowed.load()
    half = max(2, round(args.max_pad_mm * fr.ppmm))
    centers = []
    for hole in holes:
        px, py = fr.to_px(hole["X"], hole["Y"])
        centers.append(py * w + px if (0 <= px < w and 0 <= py < h) else None)
    rows = []
    for hole, i in zip(holes, centers):
        row = {k2: hole[k2] for k2 in ("x", "y", "net", "d") if k2 in hole}
        if i is None:
            row["state"] = "outside_window"
            rows.append(row)
            continue
        px, py = i % w, i // w
        row["original_center_copper"] = bool(ad[i])
        row["factory_center_copper"] = bool(bd[i])
        if not ad[i]:
            row["state"] = "no_copper_in_original"
        else:
            pixels, touched = island(ad, w, h, px, py, half)
            joined = sum(1 for c in centers if c is not None and c in pixels)
            if touched:
                row["state"] = "connected"
            elif joined > 1:  # one copper island linking several holes is a connection, not an unused pad
                row["state"] = "connected"
                row["note"] = f"island joins {joined} holes"
            else:
                row["state"] = "isolated"
                row["island_mm2"] = round(len(pixels) / fr.ppmm ** 2, 4)
                for j in pixels:
                    allowed_px[j % w, j // w] = 255
        if row["state"] == "isolated":
            row["verdict"] = "unused pad removed (expected CAM edit)" if not bd[i] else "unused pad kept"
        elif row["state"] == "connected":
            row["verdict"] = "SUSPICIOUS: connected pad lost centre copper" if not bd[i] else "ok"
        else:
            row["verdict"] = "-"
        rows.append(row)

    grow = args.tolerance_px + 1
    allowed = allowed.filter(ImageFilter.MaxFilter(2 * grow + 1))
    outside = ImageChops.subtract(removed, allowed)
    od = outside.tobytes()
    out_idx = [i for i, v in enumerate(od) if v]
    regions = []
    for comp in components(out_idx, w):
        if len(comp) < args.min_region_px:
            continue
        xs, ys = [i % w for i in comp], [i // w for i in comp]
        cX, cY = fr.to_mm((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        oX, oY = fr.inv(cX, cY)
        regions.append({"center_factory_mm": [round(cX, 3), round(cY, 3)],
                        "center_original_mm": [round(oX, 3), round(oY, 3)],
                        "removed_mm2": round(len(comp) / fr.ppmm ** 2, 4)})
    regions.sort(key=lambda r: -r["removed_mm2"])

    # picture: removed copper (blue), suspicious removal (red), hole markers
    pic = Image.new("RGB", a.size, "white")
    pic.paste((200, 200, 200), mask=a)
    pic.paste((22, 131, 219), mask=removed)
    pic.paste((230, 30, 30), mask=outside)
    d = ImageDraw.Draw(pic)
    for row in rows:
        if "original_center_copper" not in row:
            continue
        X, Y = fr.fwd(row["x"], row["y"])
        px, py = fr.to_px(X, Y)
        color = (230, 30, 30) if row["verdict"].startswith("SUSPICIOUS") else (0, 150, 70)
        d.ellipse((px - 4, py - 4, px + 4, py + 4), outline=color, width=2)
    pic.save(renders / f"{label}-inner-check.png")

    plane_lost = []
    if args.plane_nets:
        nets = {n.upper() for n in args.plane_nets}
        plane_lost = [r for r in rows if str(r.get("net", "")).upper().lstrip("/") in nets
                      and r.get("original_center_copper") and not r.get("factory_center_copper")]

    removed_n = sum(removed.histogram()[1:])
    return {
        "removed_beyond_tol_mm2": round(removed_n / fr.ppmm ** 2, 4),
        "removed_outside_unused_pads_mm2": round(len(out_idx) / fr.ppmm ** 2, 4),
        "removed_outside_unused_pads_px": len(out_idx),
        "suspicious_regions": regions[: args.max_regions],
        "suspicious_regions_total": len(regions),
        "holes_total": len(rows),
        "holes_outside_window": sum(r.get("state") == "outside_window" for r in rows),
        "isolated_pads": sum(r.get("state") == "isolated" for r in rows),
        "isolated_pads_removed": sum(r.get("verdict", "").startswith("unused pad removed") for r in rows),
        "connected_pads": sum(r.get("state") == "connected" for r in rows),
        "connected_pads_lost_center": sum(r.get("verdict", "").startswith("SUSPICIOUS") for r in rows),
        "plane_net_holes_lost_center": plane_lost,
        "holes": rows,
        "picture": f"{label}-inner-check.png",
    }


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Check that copper removed by the factory on inner layers is only unused, isolated pads. "
                    "Step 3 of cam-diff.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python check_inner_removals.py --renders cam-diff-out --plane-nets GND --holes holes.json")
    ap.add_argument("--renders", required=True, help="folder written by render_compare.py")
    ap.add_argument("--layers", nargs="*", help="labels to check (default: every In<n>_Cu in layer-summary.json)")
    ap.add_argument("--holes", help="JSON list of {x, y[, net]} in the original frame (default: original drill hits)")
    ap.add_argument("--plane-nets", nargs="*", default=[], help="with --holes nets: nets that must keep every pad, e.g. GND")
    ap.add_argument("--tolerance-px", type=int, default=1, help="ignore edge differences up to this many pixels")
    ap.add_argument("--max-pad-mm", type=float, default=1.5,
                    help="half-size of the box used to decide whether a pad is an isolated island (mm)")
    ap.add_argument("--min-region-px", type=int, default=2, help="ignore suspicious specks smaller than this")
    ap.add_argument("--max-regions", type=int, default=100, help="suspicious regions listed per layer")
    ap.add_argument("--out", help="JSON result path (default: <renders>/inner-check.json)")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    renders = Path(args.renders)
    out = Path(args.out) if args.out else renders / "inner-check.json"
    result = {"schema_version": 1, "tool": "check_inner_removals.py", "status": "PASS", "issues": [],
              "scope": "Selected layers only; raster heuristic for isolated-pad removals, not netlist or manufacturing approval.",
              "tolerance_px": args.tolerance_px, "max_pad_mm": args.max_pad_mm, "layers": {}}

    def issue(status, message):
        result["issues"].append({"status": status, "message": message})
        priority = {"PASS": 0, "WARNING": 1, "INCOMPLETE": 2, "ERROR": 3}
        if priority[status] > priority[result["status"]]:
            result["status"] = status

    try:
        import PIL  # noqa: F401
        if args.tolerance_px < 0 or not math.isfinite(args.max_pad_mm) or args.max_pad_mm <= 0 or args.min_region_px < 1 or args.max_regions < 1:
            raise ValueError("tolerance must be nonnegative; pad size and region limits must be positive")
        summary = json.loads((renders / "layer-summary.json").read_text(encoding="utf-8"))
        upstream = summary.get("status")
        result["upstream_status"] = upstream
        if upstream != "PASS":
            issue("ERROR" if upstream == "ERROR" else "INCOMPLETE",
                  f"render verification did not PASS (status={upstream!r})")
        fr = Frames(summary)
        if args.holes:
            raw = json.loads(Path(args.holes).read_text(encoding="utf-8"))
            holes = []
            for hdef in raw:
                x, y = float(hdef["x"]), float(hdef["y"])
                if not all(math.isfinite(v) for v in (x, y)):
                    raise ValueError("hole coordinates must be finite")
                X, Y = fr.fwd(x, y)
                holes.append({**hdef, "x": x, "y": y, "X": X, "Y": Y})
            reference = summary.get("drills", {}).get("original_holes", [])
            matches = [[i for i, original in enumerate(reference)
                        if math.isclose(hole["x"], float(original["x"]), rel_tol=0, abs_tol=1e-6)
                        and math.isclose(hole["y"], float(original["y"]), rel_tol=0, abs_tol=1e-6)]
                       for hole in holes]
            verified = bool(reference) and len(holes) == len(reference) and all(len(m) == 1 for m in matches)
            verified = verified and len({m[0] for m in matches}) == len(reference)
            result["custom_holes_verified"] = verified
            if not verified:
                issue("INCOMPLETE", "custom holes must match every original drill hole uniquely within 0.000001 mm")
                # Keep diagnostic geometry from the drill reference; do not trust unverified net labels.
                holes = reference
        else:
            holes = summary.get("drills", {}).get("original_holes", [])
        if not holes:
            issue("INCOMPLETE", "no original holes available; provide --holes")
        for hole in holes:
            if not all(math.isfinite(float(hole[k])) for k in ("x", "y", "X", "Y")):
                raise ValueError("hole coordinates must be finite")
        if args.plane_nets and (not args.holes or any(not h.get("net") for h in holes)):
            issue("INCOMPLETE", "--plane-nets requires a net for every hole from --holes")
        labels = args.layers if args.layers is not None else [lb for lb in summary["layers"] if re.fullmatch(r"In\d+_Cu", lb)]
        result["requested_layers"] = labels
        if not labels:
            issue("INCOMPLETE", "no layers selected; provide --layers to check other layers")
        prerequisite_status = result["status"]
        for label in labels:
            info = summary["layers"].get(label)
            if not info:
                issue("INCOMPLETE", f"{label}: not in layer-summary.json")
                result["layers"][label] = {"status": "INCOMPLETE", "issues": ["not in layer-summary.json"]}
                continue
            try:
                r = check_layer(label, info, renders, fr, holes, args)
                r["status"] = prerequisite_status
                if r["holes_outside_window"]:
                    if r["status"] != "ERROR":
                        r["status"] = "INCOMPLETE"
                    issue("INCOMPLETE", f"{label}: {r['holes_outside_window']} holes outside render window")
                if r["removed_outside_unused_pads_px"] or r["connected_pads_lost_center"] or r["plane_net_holes_lost_center"]:
                    if r["status"] == "PASS":
                        r["status"] = "WARNING"
                    issue("WARNING", f"{label}: suspicious copper removal requires review")
                result["layers"][label] = r
                print(f"{label}: {r['status']}; outside unused pads {r['removed_outside_unused_pads_mm2']} mm2; connected pads lost {r['connected_pads_lost_center']}")
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
                print(f"{label}: ERROR: {exc}")
                message = f"{label}: invalid or unreadable render input ({type(exc).__name__})"
                issue("ERROR", message)
                result["layers"][label] = {"status": "ERROR", "issues": [message]}
    except (ImportError, OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        print(f"ERROR: {exc}")
        issue("ERROR", f"invalid or unreadable input ({type(exc).__name__})")
    try:
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write result: {exc}")
        return 2
    print(f"{result['status']}: wrote {out}")
    return {"PASS": 0, "WARNING": 1, "INCOMPLETE": 2, "ERROR": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
