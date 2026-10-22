"""Minimal KiCad S-expression reader for .kicad_pcb / .kicad_mod files (stdlib only).

Every list node keeps its character span in the source text, so callers can
insert or remove text without re-serialising the whole board.
"""
import math
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


class Q(str):
    """A quoted string token."""


class Node(list):
    """A parenthesised list. `start` is the index of '(' and `end` of ')'."""
    start = 0
    end = 0

    @property
    def head(self):
        return self[0] if self and isinstance(self[0], str) else None


def parse(text):
    stack, pos, root = [], 0, None
    while True:
        m = _TOKEN.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            node = Node()
            node.start = m.start(1)
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif m.group(2):
            node = stack.pop()
            node.end = m.start(2)
            if not stack:
                root = node
                break
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    if root is None:
        raise ValueError("unbalanced S-expression")
    return root


def find(node, name):
    for c in node:
        if isinstance(c, Node) and c.head == name:
            return c
    return None


def findall(node, name):
    return [c for c in node if isinstance(c, Node) and c.head == name]


def _xy(node):
    return float(node[1]), float(node[2])


def _graphic_points(g):
    """Points that bound a graphic item (lines, rects, arcs, circles, polygons)."""
    kind = g.head.split("_", 1)[1]
    if kind in ("line", "rect"):
        return [_xy(find(g, "start")), _xy(find(g, "end"))]
    if kind == "arc":
        return [_xy(find(g, k)) for k in ("start", "mid", "end") if find(g, k)]
    if kind == "circle":
        cx, cy = _xy(find(g, "center"))
        ex, ey = _xy(find(g, "end"))
        r = math.hypot(ex - cx, ey - cy)
        return [(cx - r, cy - r), (cx + r, cy + r)]
    if kind == "poly":
        pts = find(g, "pts")
        return [_xy(p) for p in findall(pts, "xy")] if pts else []
    return []


def bbox(points):
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), max(xs), min(ys), max(ys))


def union(*boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), max(b[1] for b in boxes),
            min(b[2] for b in boxes), max(b[3] for b in boxes))


def board_outline_bbox(root):
    pts = []
    for g in root:
        if isinstance(g, Node) and g.head and g.head.startswith("gr_"):
            layer = find(g, "layer")
            if layer and layer[1] == "Edge.Cuts":
                pts += _graphic_points(g)
    return bbox(pts)


def board_thickness(root):
    general = find(root, "general")
    t = find(general, "thickness") if general else None
    return float(t[1]) if t else 1.6


def footprint_info(fp):
    """Summary of one (footprint ...) node. Graphics and pads stay in footprint-local coordinates."""
    at = find(fp, "at")
    x, y = float(at[1]), float(at[2])
    rot = float(at[3]) if len(at) > 3 else 0.0
    props = {p[1]: p[2] for p in findall(fp, "property") if len(p) > 2}
    ref = props.get("Reference")
    if ref is None:  # KiCad 7 and older
        for t in findall(fp, "fp_text"):
            if len(t) > 2 and t[1] == "reference":
                ref = t[2]
    attr = find(fp, "attr")
    dnp = bool(find(fp, "dnp")) or bool(attr and "dnp" in attr[1:])
    layers = {}
    for g in fp:
        if isinstance(g, Node) and g.head and g.head.startswith("fp_"):
            layer = find(g, "layer")
            if layer:
                layers.setdefault(layer[1], []).extend(_graphic_points(g))
    pad_pts = []
    for p in findall(fp, "pad"):
        pat, size = find(p, "at"), find(p, "size")
        if pat and size:
            px, py = float(pat[1]), float(pat[2])
            w, h = float(size[1]), float(size[2])
            prot = float(pat[3]) if len(pat) > 3 else 0.0
            if round(prot) % 180 == 90:
                w, h = h, w
            pad_pts += [(px - w / 2, py - h / 2), (px + w / 2, py + h / 2)]
    side = "bottom" if find(fp, "layer")[1].startswith("B.") else "top"
    return {
        "ref": ref, "lib_id": str(fp[1]), "value": props.get("Value", ""),
        "x": x, "y": y, "rot": rot, "side": side, "dnp": dnp,
        "props": props, "models": [str(m[1]) for m in findall(fp, "model")],
        "fab": bbox(layers.get("F.Fab", []) + layers.get("B.Fab", [])),
        "courtyard": bbox(layers.get("F.CrtYd", []) + layers.get("B.CrtYd", [])),
        "pads": bbox(pad_pts), "node": fp,
    }


def footprints(root):
    return [footprint_info(fp) for fp in findall(root, "footprint")]


def local_box_to_board(fp, box):
    """Footprint-local bbox -> board bbox (KiCad: rotation CCW on screen, Y down)."""
    if not box:
        return None
    th = math.radians(fp["rot"])
    c, s = math.cos(th), math.sin(th)
    pts = []
    for lx in (box[0], box[1]):
        for ly in (box[2], box[3]):
            pts.append((fp["x"] + lx * c + ly * s, fp["y"] - lx * s + ly * c))
    return bbox(pts)


def board_box_to_step(box, origin):
    """Board bbox (Y down) -> STEP bbox (Y up) for a given (ox, oy) user origin."""
    if not box:
        return None
    ox, oy = origin
    return (box[0] - ox, box[1] - ox, oy - box[3], oy - box[2])
