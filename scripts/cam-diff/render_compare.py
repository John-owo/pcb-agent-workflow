#!/usr/bin/env python3
"""render_compare.py - align a factory CAM Gerber set to your release Gerbers and rasterize both.

Step 1 of the cam-diff toolkit (see README.md in this folder).

What it does
  * Loads your original release Gerbers/drill files and the factory's CAM production file
    (a folder or a .zip each; sub-folders inside the zip/folder are searched).
  * Works out the transform original -> factory frame: an optional rotation you give, plus a
    translation you give (--offset DX DY) or that is estimated from drill hits (--offset auto).
  * Rasterizes each matching layer pair into the same window (the original board outline moved
    into the factory frame) at --ppmm pixels per mm, writing <LABEL>-orig.png / <LABEL>-cam.png.
  * Matches drill holes one-to-one after the transform and lists moved, missing and extra holes.
  * Writes layer-summary.json (file hashes, transform, window, per-layer info, drill matching).

Usage
  python render_compare.py --original release/gerbers.zip --factory factory_cam.zip \
      --offset auto --out cam-diff-out
  python render_compare.py --original gerbers/ --factory factory/ok --offset 23 17 --out out \
      --pair In1_Cu=*-In1_Cu.*,l2 --check-upload factory/YG/original_upload.zip

Next steps
  python pixel_compare.py --renders cam-diff-out
  python check_inner_removals.py --renders cam-diff-out

Requires Python >= 3.12 (gerbonara's minimum), gerbonara and Pillow:
  python -m pip install gerbonara pillow
Coordinates are in mm. Gerber Y points up; the PNGs are drawn with Y up as seen from the top.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import math
import warnings
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

# label, patterns for the original release, patterns for the factory file.
# Patterns match file basenames, case-insensitive, first pattern with a hit wins.
# The factory names (tl, bl, l2 ...) are what one JLCPCB production file used; check yours.
DEFAULT_LAYERS = [
    ("F_Cu", ["*-F_Cu.*", "*.gtl"], ["tl", "*.gtl", "*-F_Cu.*"]),
    ("B_Cu", ["*-B_Cu.*", "*.gbl"], ["bl", "*.gbl", "*-B_Cu.*"]),
    ("In1_Cu", ["*-In1_Cu.*", "*.g1"], ["l2", "*.g1", "*-In1_Cu.*"]),
    ("In2_Cu", ["*-In2_Cu.*", "*.g2"], ["l3", "*.g2", "*-In2_Cu.*"]),
    ("In3_Cu", ["*-In3_Cu.*", "*.g3"], ["l4", "*.g3", "*-In3_Cu.*"]),
    ("In4_Cu", ["*-In4_Cu.*", "*.g4"], ["l5", "*.g4", "*-In4_Cu.*"]),
    ("F_Mask", ["*-F_Mask.*", "*.gts"], ["ts", "*.gts", "*-F_Mask.*"]),
    ("B_Mask", ["*-B_Mask.*", "*.gbs"], ["bs", "*.gbs", "*-B_Mask.*"]),
    ("F_Paste", ["*-F_Paste.*", "*.gtp"], ["*.gtp", "*-F_Paste.*"]),
    ("B_Paste", ["*-B_Paste.*", "*.gbp"], ["*.gbp", "*-B_Paste.*"]),
    ("F_Silk", ["*-F_Silkscreen.*", "*-F_SilkS.*", "*.gto"], ["to", "*.gto", "*-F_Silkscreen.*"]),
    ("B_Silk", ["*-B_Silkscreen.*", "*-B_SilkS.*", "*.gbo"], ["bo", "*.gbo", "*-B_Silkscreen.*"]),
    ("Outline", ["*-Edge_Cuts.*", "*.gm1", "*.gko"], ["ko", "*.gko", "*.gm1", "*-Edge_Cuts.*"]),
]
DRILL_ORIGINAL = ["*.drl", "*.xln", "*.exc", "*-PTH*.gbr", "*-NPTH*.gbr", "*drl*.gbr"]
DRILL_FACTORY = ["drl", "*.drl", "*.xln", "*.exc"]


# ----------------------------------------------------------------------------- sources
class Source:
    """A folder or zip of fabrication files, read into memory (relative posix path -> bytes)."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.files: dict[str, bytes] = {}
        if self.path.is_dir():
            for p in sorted(self.path.rglob("*")):
                if p.is_file():
                    self.files[p.relative_to(self.path).as_posix()] = p.read_bytes()
            self.sha256 = None
        elif self.path.is_file() and zipfile.is_zipfile(self.path):
            with zipfile.ZipFile(self.path) as z:
                for name in sorted(z.namelist()):
                    if not name.endswith("/"):
                        self.files[name] = z.read(name)
            self.sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        else:
            raise SystemExit(f"error: {path} is neither a folder nor a zip file")

    def find(self, patterns, exclude=()):
        for pat in patterns:
            hits = [rel for rel in self.files
                    if rel not in exclude and fnmatch.fnmatch(PurePosixPath(rel).name.lower(), pat.lower())]
            if hits:
                return hits
        return []

    def describe(self):
        return {
            "path_name": self.path.name,  # basename only, keep local paths out of shared reports
            "zip_sha256": self.sha256,
            "members": {rel: hashlib.sha256(b).hexdigest() for rel, b in self.files.items()},
        }


def kind_of(data: bytes) -> str | None:
    head = data[:4096].decode("latin-1", errors="replace")
    if "\x00" in head:
        return None
    if "M48" in head or ("METRIC" in head and "%" in head and "T1" in head):
        return "excellon"
    if "%FS" in head or "%MO" in head or "G04" in head:
        return "gerber"
    return None


def load_cam(rel: str, data: bytes):
    """Parse one file with gerbonara. Returns (CamFile, kind, warning_count)."""
    from gerbonara.excellon import ExcellonFile
    from gerbonara.rs274x import GerberFile

    kind = kind_of(data)
    if kind is None:
        raise ValueError(f"{rel}: not a Gerber/Excellon text file")
    text = data.decode("utf-8", errors="replace")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if kind == "excellon":
            cam = ExcellonFile.from_string(text, filename=rel)
        else:
            cam = GerberFile.from_string(text, filename=rel)
    return cam, kind, len(caught)


# ----------------------------------------------------------------------------- transform
class Transform:
    """original (x, y) -> factory (X, Y): rotate CCW by rot_deg about the origin, then translate."""

    def __init__(self, rot_deg=0.0, dx=0.0, dy=0.0):
        self.rot_deg, self.dx, self.dy = rot_deg, dx, dy
        t = math.radians(rot_deg)
        self.c, self.s = math.cos(t), math.sin(t)

    def rot(self, x, y):
        return self.c * x - self.s * y, self.s * x + self.c * y

    def fwd(self, x, y):
        rx, ry = self.rot(x, y)
        return rx + self.dx, ry + self.dy

    def inv(self, X, Y):
        u, v = X - self.dx, Y - self.dy
        return self.c * u + self.s * v, -self.s * u + self.c * v


# ----------------------------------------------------------------------------- shapes
def object_shapes(obj, max_err):
    """Yield (exposed, shape) for one gerbonara graphic object, in mm.

    shape is ('circle', (x, y), r) | ('poly', [pts]) | ('thick', [pts], width).
    exposed is True where this primitive adds the object's polarity, False for holes
    inside an aperture (macro exposure off / aperture holes).
    """
    from gerbonara import graphic_primitives as gp
    from gerbonara.utils import MM, approximate_arc

    for p in obj.to_primitives(unit=MM):
        exposed = bool(p.polarity_dark) == bool(obj.polarity_dark)
        if isinstance(p, gp.Circle):
            yield exposed, ("circle", (p.x, p.y), p.r)
        elif isinstance(p, gp.Line):
            yield exposed, ("thick", [(p.x1, p.y1), (p.x2, p.y2)], p.width)
        elif isinstance(p, gp.Arc):
            pts = list(approximate_arc(p.cx, p.cy, p.x1, p.y1, p.x2, p.y2, p.clockwise, max_error=max_err))
            yield exposed, ("thick", pts, p.width)
        elif isinstance(p, gp.Rectangle):
            c, s = math.cos(p.rotation), math.sin(p.rotation)
            pts = [(p.x + c * u - s * v, p.y + s * u + c * v)
                   for u, v in ((-p.w / 2, -p.h / 2), (p.w / 2, -p.h / 2), (p.w / 2, p.h / 2), (-p.w / 2, p.h / 2))]
            yield exposed, ("poly", pts)
        else:  # ArcPoly and anything else that can become one
            ap = p if isinstance(p, gp.ArcPoly) else p.to_arc_poly()
            if len(ap.outline) >= 2:
                yield exposed, ("poly", list(ap.approximate_arcs(max_error=max_err).outline))


def transform_shape(shape, tf: Transform):
    if shape[0] == "circle":
        return ("circle", tf.fwd(*shape[1]), shape[2])
    if shape[0] == "poly":
        return ("poly", [tf.fwd(*q) for q in shape[1]])
    return ("thick", [tf.fwd(*q) for q in shape[1]], shape[2])


def shape_points(shape):
    """Centre-line points, used for outline extents."""
    if shape[0] == "circle":
        (x, y), r = shape[1], shape[2]
        return [(x - r, y - r), (x + r, y + r)]
    return shape[1]


class Raster:
    """Supersampled binary canvas for a window [x0, x1] x [y0, y1] (mm, Y up)."""

    def __init__(self, window, ppmm, supersample):
        from PIL import Image, ImageDraw

        (self.x0, self.y0), (self.x1, self.y1) = window
        self.ppmm, self.ss = ppmm, supersample
        self.scale = ppmm * supersample
        self.w = max(1, round((self.x1 - self.x0) * ppmm))
        self.h = max(1, round((self.y1 - self.y0) * ppmm))
        self.img = Image.new("L", (self.w * supersample, self.h * supersample), 0)
        self.draw = ImageDraw.Draw(self.img)
        self._Image, self._ImageDraw = Image, ImageDraw

    def px(self, x, y):
        return ((x - self.x0) * self.scale, (self.y1 - y) * self.scale)

    def _draw_shape(self, draw, shape, fill, origin=(0.0, 0.0)):
        ox, oy = origin

        def P(q):
            a, b = self.px(*q)
            return (a - ox, b - oy)

        if shape[0] == "circle":
            (cx, cy), r = P(shape[1]), shape[2] * self.scale
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
        elif shape[0] == "poly":
            pts = [P(q) for q in shape[1]]
            if len(pts) >= 3:
                draw.polygon(pts, fill=fill)
        else:
            pts, hw = [P(q) for q in shape[1]], shape[2] * self.scale / 2
            if hw < 0.5:
                draw.line(pts, fill=fill, width=1)
                return
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                L = math.hypot(bx - ax, by - ay)
                if L > 1e-9:
                    nx, ny = -(by - ay) / L * hw, (bx - ax) / L * hw
                    draw.polygon([(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)], fill=fill)
            for cx, cy in pts:
                draw.ellipse((cx - hw, cy - hw, cx + hw, cy + hw), fill=fill)

    def draw_object(self, shapes, dark):
        fill = 255 if dark else 0
        if all(exposed for exposed, _ in shapes):
            for _, sh in shapes:
                self._draw_shape(self.draw, sh, fill)
            return
        # Aperture with holes / macro with exposure-off parts: build the aperture image first,
        # so the holes do not erase copper drawn earlier by other objects.
        xs, ys = [], []
        for _, sh in shapes:
            for q in shape_points(sh):
                a, b = self.px(*q)
                xs.append(a)
                ys.append(b)
        pad = 2 + max((sh[2] * self.scale for _, sh in shapes if sh[0] == "thick"), default=0)
        left, top = math.floor(min(xs) - pad), math.floor(min(ys) - pad)
        right, bottom = math.ceil(max(xs) + pad), math.ceil(max(ys) + pad)
        if right - left > 20000 or bottom - top > 20000:
            raise ValueError("aperture image too large")
        mask = self._Image.new("L", (right - left, bottom - top), 0)
        md = self._ImageDraw.Draw(mask)
        for exposed, sh in shapes:
            self._draw_shape(md, sh, 255 if exposed else 0, origin=(left, top))
        self.img.paste(fill, (left, top), mask)

    def finish(self):
        """Downsample and threshold; return a black-on-white image (black = drawn)."""
        from PIL import Image

        small = self.img.resize((self.w, self.h), Image.Resampling.BOX) if self.ss > 1 else self.img
        return small.point(lambda v: 0 if v >= 128 else 255)


def rasterize(cam, tf: Transform | None, window, ppmm, supersample):
    r = Raster(window, ppmm, supersample)
    max_err = 0.25 / (ppmm * supersample)
    for obj in cam.objects:
        shapes = [(e, transform_shape(sh, tf) if tf else sh) for e, sh in object_shapes(obj, max_err)]
        if shapes:
            r.draw_object(shapes, obj.polarity_dark)
    return r.finish()


def centerline_bounds(cam, tf: Transform | None):
    xs, ys = [], []
    for obj in cam.objects:
        for _, sh in object_shapes(obj, 0.005):
            for q in shape_points(transform_shape(sh, tf) if tf else sh):
                xs.append(q[0])
                ys.append(q[1])
    if not xs:
        return None
    return [[min(xs), min(ys)], [max(xs), max(ys)]]


def bounds_of(cam):
    from gerbonara.utils import MM

    b = cam.bounding_box(MM, default=None)
    return None if b is None else [[b[0][0], b[0][1]], [b[1][0], b[1][1]]]


# ----------------------------------------------------------------------------- drills
def drill_hits(cam, kind, rel):
    """Return [{x, y, d, file, plated}] in mm for flashes (round holes). Slots are counted separately."""
    from gerbonara.graphic_objects import Flash
    from gerbonara.utils import MM

    hits, slots = [], 0
    for obj in cam.objects:
        if isinstance(obj, Flash):
            c = obj.converted(MM)
            ap = obj.aperture
            d = ap.equivalent_width(MM) if ap is not None else 0.0
            hits.append({"x": c.x, "y": c.y, "d": round(d, 4), "file": rel,
                         "plated": getattr(ap, "plated", None) if kind == "excellon" else None})
        else:
            slots += 1
    return hits, slots


class Grid:
    def __init__(self, pts, cell=0.1):
        self.cell, self.cells = cell, defaultdict(list)
        for i, (x, y) in enumerate(pts):
            self.cells[(math.floor(x / cell), math.floor(y / cell))].append((i, x, y))

    def near(self, x, y, radius):
        cx, cy, n = math.floor(x / self.cell), math.floor(y / self.cell), math.ceil(radius / self.cell)
        for i in range(cx - n, cx + n + 1):
            for j in range(cy - n, cy + n + 1):
                for k, px, py in self.cells.get((i, j), ()):
                    d = math.hypot(px - x, py - y)
                    if d <= radius:
                        yield d, k


def estimate_offset(orig_pts, fact_pts, tol):
    """Translation that lands the most original holes on factory holes (rotation already applied)."""
    if not orig_pts or not fact_pts:
        raise SystemExit("error: --offset auto needs drill hits in both sets; give --offset DX DY")
    grid = Grid(fact_pts)

    def score(t, pts):
        return sum(1 for x, y in pts if next(grid.near(x + t[0], y + t[1], tol), None) is not None)

    step = max(1, len(orig_pts) // 6)
    refs = orig_pts[::step][:6]
    sample = orig_pts[:: max(1, len(orig_pts) // 20)][:20]
    seen, cands = set(), []
    for ox, oy in refs:
        for fx, fy in fact_pts:
            t = (fx - ox, fy - oy)
            key = (round(t[0], 2), round(t[1], 2))
            if key in seen:
                continue
            seen.add(key)
            if score(t, sample) < 0.5 * len(sample):
                continue
            cands.append((score(t, orig_pts), t))
    if not cands:
        raise SystemExit("error: could not estimate the offset from drill hits; "
                         "check --rotate or give --offset DX DY")
    best = max(s for s, _ in cands)
    top = []  # distinct board positions (a panel with copies gives several)
    for s, t in sorted(cands, key=lambda st: (-st[0], st[1][1], st[1][0])):
        if s < 0.9 * best:
            break
        if all(math.hypot(t[0] - k[0], t[1] - k[1]) > 0.05 for _, k in top):
            top.append((s, t))
    s, t = top[0]
    # refine with the median residual of the matched holes
    rx, ry = [], []
    for x, y in orig_pts:
        hit = min(grid.near(x + t[0], y + t[1], tol), default=None)
        if hit:
            _, k = hit
            rx.append(fact_pts[k][0] - x)
            ry.append(fact_pts[k][1] - y)
    rx.sort()
    ry.sort()
    t = (rx[len(rx) // 2], ry[len(ry) // 2])
    others = [{"offset_mm": [round(o[1][0], 4), round(o[1][1], 4)], "matched": o[0]} for o in top[1:10]]
    return t, s, others


def match_drills(orig, fact, tf: Transform, window, match_radius, moved_tol):
    for h in orig:
        h["X"], h["Y"] = tf.fwd(h["x"], h["y"])
    grid = Grid([(f["x"], f["y"]) for f in fact])
    pairs = []
    for i, h in enumerate(orig):
        for d, k in grid.near(h["X"], h["Y"], match_radius):
            pairs.append((d, i, k))
    pairs.sort()
    used_o, used_f, matches = set(), set(), []
    for d, i, k in pairs:
        if i in used_o or k in used_f:
            continue
        used_o.add(i)
        used_f.add(k)
        matches.append((d, i, k))
    (wx0, wy0), (wx1, wy1) = window

    def inside(f):
        return wx0 <= f["x"] <= wx1 and wy0 <= f["y"] <= wy1

    moved = []
    diam = Counter()
    for d, i, k in matches:
        o, f = orig[i], fact[k]
        diam[f"{o['d']:.3f} -> {f['d']:.3f}"] += 1
        if d > moved_tol:
            bx, by = tf.inv(f["x"], f["y"])
            moved.append({
                "original_mm": [round(o["x"], 6), round(o["y"], 6)],
                "factory_back_in_original_frame_mm": [round(bx, 6), round(by, 6)],
                "delta_mm": [round(bx - o["x"], 6), round(by - o["y"], 6)],
                "distance_mm": round(d, 6),
                "factory_frame_mm": [round(f["x"], 6), round(f["y"], 6)],
                "original_d": o["d"], "factory_d": f["d"], "original_file": o["file"],
            })
    missing = [{"original_mm": [round(orig[i]["x"], 6), round(orig[i]["y"], 6)], "d": orig[i]["d"],
                "file": orig[i]["file"]} for i in range(len(orig)) if i not in used_o]
    extra_in, outside = [], Counter()
    for k, f in enumerate(fact):
        if k in used_f:
            continue
        if inside(f):
            bx, by = tf.inv(f["x"], f["y"])
            extra_in.append({"factory_frame_mm": [round(f["x"], 6), round(f["y"], 6)],
                             "original_frame_mm": [round(bx, 6), round(by, 6)], "d": f["d"]})
        else:
            outside[f"{f['d']:.3f}"] += 1
    return {
        "original_count": len(orig),
        "factory_count": len(fact),
        "matched": len(matches),
        "max_match_error_mm": round(max((d for d, _, _ in matches), default=0.0), 6),
        "moved_tolerance_mm": moved_tol,
        "moved": moved,
        "missing_in_factory": missing,
        "extra_inside_board": extra_in,
        "outside_board_by_diameter": dict(outside),
        "diameter_original_to_factory": dict(diam),
        "original_holes": [{"x": round(h["x"], 6), "y": round(h["y"], 6), "X": round(h["X"], 6),
                            "Y": round(h["Y"], 6), "d": h["d"], "file": h["file"], "plated": h["plated"]}
                           for h in orig],
    }


# ----------------------------------------------------------------------------- main
def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Align factory CAM Gerbers to your original release Gerbers, rasterize matching layers "
                    "into one window, and match drill holes. Step 1 of cam-diff.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python render_compare.py --original gerbers.zip --factory factory.zip "
               "--offset auto --out cam-diff-out\nThen run pixel_compare.py --renders cam-diff-out.")
    ap.add_argument("--original", required=True, help="your release Gerbers + drill files (folder or .zip)")
    ap.add_argument("--factory", required=True, help="the factory production/CAM file (folder or .zip)")
    ap.add_argument("--out", required=True, help="output folder (created if missing)")
    ap.add_argument("--offset", nargs="+", default=["auto"], metavar="DX DY|auto",
                    help="translation original -> factory frame in mm, applied after --rotate; "
                         "'auto' estimates it from drill hits (default: auto)")
    ap.add_argument("--rotate", type=float, default=0.0,
                    help="rotate the original CCW by this many degrees about its origin before the offset")
    ap.add_argument("--window", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"),
                    help="comparison window in the factory frame (mm); default: original outline moved "
                         "into the factory frame")
    ap.add_argument("--margin", type=float, default=0.0, help="extra mm around the default window")
    ap.add_argument("--ppmm", type=float, default=40.0, help="pixels per mm of the output PNGs (default 40)")
    ap.add_argument("--supersample", type=int, default=3, help="internal oversampling before thresholding")
    ap.add_argument("--panel-ppmm", type=float, default=10.0, help="pixels per mm for factory panel overviews")
    ap.add_argument("--pair", action="append", default=[], metavar="LABEL=ORIG_PATTERN,FACTORY_PATTERN",
                    help="add or override a layer pair, e.g. In1_Cu=*-In1_Cu.*,l2 (repeatable)")
    ap.add_argument("--only-pairs", action="store_true", help="ignore the built-in layer pairs, use --pair only")
    ap.add_argument("--match-radius", type=float, default=0.5, help="max mm between holes to pair them")
    ap.add_argument("--moved-tol", type=float, default=0.005, help="report matched holes further apart than this (mm)")
    ap.add_argument("--auto-tol", type=float, default=0.02, help="hole tolerance (mm) for --offset auto")
    ap.add_argument("--check-upload", metavar="PATH",
                    help="factory copy of your original upload (folder or .zip): compare member SHA-256 "
                         "with --original")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        import gerbonara  # noqa: F401
        import PIL  # noqa: F401
    except ImportError as e:
        raise SystemExit(f"error: missing dependency ({e.name}); run: python -m pip install gerbonara pillow")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    orig_src, fact_src = Source(args.original), Source(args.factory)

    layers = [] if args.only_pairs else [list(x) for x in DEFAULT_LAYERS]
    for spec in args.pair:
        try:
            label, pats = spec.split("=", 1)
            o_pat, f_pat = pats.split(",", 1)
        except ValueError:
            raise SystemExit(f"error: bad --pair {spec!r}; use LABEL=ORIG_PATTERN,FACTORY_PATTERN")
        layers = [x for x in layers if x[0] != label] + [[label, [o_pat], [f_pat]]]

    summary = {
        "tool": "render_compare.py",
        "ppmm": args.ppmm,
        "original_source": orig_src.describe(),
        "factory_source": fact_src.describe(),
        "layers": {},
        "factory_files": {},
        "notes": [],
    }

    # --- drills first (they can define the offset)
    drill_o_files = orig_src.find(DRILL_ORIGINAL)
    drill_f_files = fact_src.find(DRILL_FACTORY)
    orig_holes, fact_holes, slot_count = [], [], {"original": 0, "factory": 0}
    for rel in drill_o_files:
        cam, kind, _ = load_cam(rel, orig_src.files[rel])
        h, s = drill_hits(cam, kind, rel)
        orig_holes += h
        slot_count["original"] += s
    for rel in drill_f_files:
        cam, kind, _ = load_cam(rel, fact_src.files[rel])
        h, s = drill_hits(cam, kind, rel)
        fact_holes += h
        slot_count["factory"] += s

    rot_only = Transform(args.rotate)
    if len(args.offset) == 1 and args.offset[0].lower() == "auto":
        rotated = [rot_only.rot(h["x"], h["y"]) for h in orig_holes]
        (dx, dy), score, others = estimate_offset(rotated, [(f["x"], f["y"]) for f in fact_holes], args.auto_tol)
        summary["offset_estimate"] = {"matched_holes": score, "of": len(orig_holes), "other_candidates": others}
        if others:
            summary["notes"].append("several board positions match (panel with copies?); "
                                    "pass --offset explicitly to pick another one")
        print(f"estimated offset: ({dx:.4f}, {dy:.4f}) mm, {score}/{len(orig_holes)} holes within {args.auto_tol} mm")
        for o in others:
            print(f"  other candidate: {o['offset_mm']} ({o['matched']} holes)")
    elif len(args.offset) == 2:
        dx, dy = (float(v) for v in args.offset)
    else:
        raise SystemExit("error: --offset takes DX DY or auto")
    tf = Transform(args.rotate, dx, dy)
    summary["transform"] = {"rotate_deg_ccw": args.rotate, "offset_mm": [round(dx, 6), round(dy, 6)],
                            "meaning": "factory = rotate(original) + offset"}

    # --- load layer pairs
    used_factory = set(drill_f_files)
    loaded = {}
    for label, o_pats, f_pats in layers:
        o_hits, f_hits = orig_src.find(o_pats), fact_src.find(f_pats, exclude=used_factory)
        if not o_hits or not f_hits:
            if o_hits or f_hits:
                summary["notes"].append(f"{label}: only found on one side "
                                        f"(original={o_hits[:1]}, factory={f_hits[:1]})")
            continue
        if len(o_hits) > 1 or len(f_hits) > 1:
            summary["notes"].append(f"{label}: several files match, used the first: {o_hits[0]} / {f_hits[0]}")
        o_rel, f_rel = o_hits[0], f_hits[0]
        used_factory.add(f_rel)
        o_cam, _, o_warn = load_cam(o_rel, orig_src.files[o_rel])
        f_cam, _, f_warn = load_cam(f_rel, fact_src.files[f_rel])
        loaded[label] = (o_rel, f_rel, o_cam, f_cam, o_warn, f_warn)

    if not loaded:
        raise SystemExit("error: no layer pairs found; check the inputs or use --pair")

    # --- window: original outline (centre line) in the factory frame
    if args.window:
        x0, y0, x1, y1 = args.window
        window_src = "--window"
    else:
        base = loaded.get("Outline")
        bnds = centerline_bounds(base[2], tf) if base else None
        window_src = "original Outline centre line"
        if bnds is None:
            xs, ys = [], []
            for label, (_, _, o_cam, _, _, _) in loaded.items():
                b = centerline_bounds(o_cam, tf)
                if b:
                    xs += [b[0][0], b[1][0]]
                    ys += [b[0][1], b[1][1]]
            bnds = [[min(xs), min(ys)], [max(xs), max(ys)]]
            window_src = "union of original layers (no outline found)"
        (x0, y0), (x1, y1) = bnds
        x0, y0, x1, y1 = x0 - args.margin, y0 - args.margin, x1 + args.margin, y1 + args.margin
    window = [[x0, y0], [x1, y1]]
    # snap the window size to whole pixels so every PNG has the same grid
    w_px, h_px = max(1, round((x1 - x0) * args.ppmm)), max(1, round((y1 - y0) * args.ppmm))
    window = [[x0, y0], [x0 + w_px / args.ppmm, y0 + h_px / args.ppmm]]
    summary["window_mm"] = window
    summary["window_source"] = window_src
    if "Outline" in loaded:
        ob = centerline_bounds(loaded["Outline"][2], None)
        summary["original_board_size_mm"] = [round(ob[1][0] - ob[0][0], 4), round(ob[1][1] - ob[0][1], 4)]

    # --- rasterize pairs
    for label, (o_rel, f_rel, o_cam, f_cam, o_warn, f_warn) in loaded.items():
        print(f"rendering {label}: {o_rel} vs {f_rel}")
        rasterize(o_cam, tf, window, args.ppmm, args.supersample).save(out / f"{label}-orig.png")
        rasterize(f_cam, None, window, args.ppmm, args.supersample).save(out / f"{label}-cam.png")
        summary["layers"][label] = {
            "original_file": o_rel, "factory_file": f_rel,
            "original_bounds_mm": bounds_of(o_cam), "factory_bounds_mm": bounds_of(f_cam),
            "original_objects": len(o_cam.objects), "factory_objects": len(f_cam.objects),
            "original_parser_warnings": o_warn, "factory_parser_warnings": f_warn,
            "png_original": f"{label}-orig.png", "png_factory": f"{label}-cam.png",
        }

    # --- panel overviews of every factory Gerber/drill file (rails, tooling holes, v-cut, markers)
    for rel, data in fact_src.files.items():
        if kind_of(data) is None:
            continue
        try:
            cam, kind, warn = load_cam(rel, data)
        except Exception as e:  # keep going; report what could not be parsed
            summary["factory_files"][rel] = {"error": str(e)[:200]}
            continue
        b = bounds_of(cam)
        info = {"kind": kind, "objects": len(cam.objects), "bounds_mm": b, "parser_warnings": warn,
                "paired": rel in used_factory}
        if b:
            name = "panel-" + PurePosixPath(rel).name.replace(".", "_") + ".png"
            pad = 1.0
            rasterize(cam, None, [[b[0][0] - pad, b[0][1] - pad], [b[1][0] + pad, b[1][1] + pad]],
                      args.panel_ppmm, 2).save(out / name)
            info["png_panel"] = name
        summary["factory_files"][rel] = info

    # --- drills
    summary["drills"] = {"original_files": drill_o_files, "factory_files": drill_f_files, "slots": slot_count}
    if orig_holes and fact_holes:
        summary["drills"].update(match_drills(orig_holes, fact_holes, tf, window, args.match_radius, args.moved_tol))
    else:
        summary["notes"].append("drill matching skipped: no drill hits on one side")

    # --- factory copy of the original upload
    if args.check_upload:
        up = Source(args.check_upload)
        o_by = {PurePosixPath(r).name: hashlib.sha256(b).hexdigest() for r, b in orig_src.files.items()}
        u_by = {PurePosixPath(r).name: hashlib.sha256(b).hexdigest() for r, b in up.files.items()}
        summary["upload_check"] = {
            "same": sorted(n for n in o_by if n in u_by and o_by[n] == u_by[n]),
            "different": sorted(n for n in o_by if n in u_by and o_by[n] != u_by[n]),
            "only_in_original": sorted(n for n in o_by if n not in u_by),
            "only_in_upload_copy": sorted(n for n in u_by if n not in o_by),
        }

    (out / "layer-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # --- console summary
    d = summary["drills"]
    print(f"\ntransform: rotate {args.rotate} deg CCW, offset ({dx:.4f}, {dy:.4f}) mm")
    print(f"window (factory frame): ({window[0][0]:.3f}, {window[0][1]:.3f}) - ({window[1][0]:.3f}, {window[1][1]:.3f}) mm")
    if "matched" in d:
        print(f"drills: {d['matched']}/{d['original_count']} original holes matched, "
              f"max error {d['max_match_error_mm']} mm")
        print(f"  moved > {args.moved_tol} mm: {len(d['moved'])}; missing in factory: {len(d['missing_in_factory'])}; "
              f"extra inside board: {len(d['extra_inside_board'])}; outside board: {d['outside_board_by_diameter']}")
        for m in d["moved"]:
            print(f"  moved: {m['original_mm']} -> {m['factory_back_in_original_frame_mm']} "
                  f"({m['distance_mm']} mm, original frame)")
    if "upload_check" in summary:
        u = summary["upload_check"]
        print(f"upload copy: {len(u['same'])} same, {len(u['different'])} different, "
              f"{len(u['only_in_original'])} only in original, {len(u['only_in_upload_copy'])} only in copy")
    for n in summary["notes"]:
        print("note:", n)
    print(f"\nwrote {out / 'layer-summary.json'} and {2 * len(loaded)} layer PNGs")


if __name__ == "__main__":
    main()
