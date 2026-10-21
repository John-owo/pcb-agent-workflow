"""Check that every symbol pin number has a matching footprint pad number.

Usage:
  python -I check_pin_pad.py NETLIST.xml --pcb BOARD.kicad_pcb
  python -I check_pin_pad.py NETLIST.xml --footprints FOOTPRINT_DIR [FOOTPRINT_DIR ...]

NETLIST.xml comes from: kicad-cli sch export netlist --format kicadxml -o NETLIST.xml ROOT.kicad_sch

Pin numbers are read from the netlist nets (every pin appears as a node, unconnected
pins in their own net), so multi-unit symbols and alternate pin names need no special
handling. Pad numbers come either from the footprints placed on BOARD.kicad_pcb
(matched by reference) or from .kicad_mod files under FOOTPRINT_DIR (matched by the
footprint name after the library nickname). Pads with an empty number (mechanical or
NPTH) are ignored. Components marked exclude_from_board and #PWR/#FLG symbols are skipped.

Reported per reference:
  pin without pad   the pin cannot connect on the board (likely wrong symbol or pin map)
  pad without pin   the pad is left unconnected (sometimes intended, e.g. mounting tabs;
                    explain each one)

Exit codes: 0 PASS (all sets equal), 1 WARNING (differences printed),
2 INCOMPLETE or ERROR (missing footprint/reference, unreadable input).
Standard library only. Read-only: never writes the inputs.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PAD_RE = re.compile(r'\(pad\s+"((?:[^"\\]|\\.)*)"')
REF_RE = re.compile(r'\(property\s+"Reference"\s+"((?:[^"\\]|\\.)*)"|\(fp_text\s+reference\s+"((?:[^"\\]|\\.)*)"')
NAME_RE = re.compile(r'\(footprint\s+"((?:[^"\\]|\\.)*)"')


def netlist_pins(path):
    """Return ({ref: set(pin)}, {ref: footprint}, skipped refs) from a kicadxml netlist."""
    root = ET.parse(path).getroot()
    footprints, skipped = {}, set()
    for comp in root.find("components").findall("comp"):
        ref = comp.get("ref")
        props = {p.get("name") for p in comp.findall("property")}
        if ref.startswith("#") or "exclude_from_board" in props:
            skipped.add(ref)
            continue
        footprints[ref] = (comp.findtext("footprint") or "").strip()
    pins = {ref: set() for ref in footprints}
    for net in root.find("nets").findall("net"):
        for node in net.findall("node"):
            ref = node.get("ref")
            if ref in pins:
                pins[ref].add(node.get("pin"))
    return pins, footprints, skipped


def blocks(text, head):
    """Yield the text of every balanced s-expression that starts with '(head '."""
    token = "(" + head
    i = 0
    while True:
        start = text.find(token, i)
        if start < 0:
            return
        nxt = text[start + len(token):start + len(token) + 1]
        if nxt and not nxt.isspace():
            i = start + 1
            continue
        depth, j, in_str = 0, start, False
        while j < len(text):
            c = text[j]
            if in_str:
                if c == "\\":
                    j += 1
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield text[start:j + 1]
        i = j + 1


def pads_of(block):
    return {m for m in PAD_RE.findall(block) if m != ""}


def board_pads(path):
    """Return {ref: set(pad)} for the footprints placed on a .kicad_pcb."""
    text = Path(path).read_text(encoding="utf-8")
    pads = {}
    for block in blocks(text, "footprint"):
        m = REF_RE.search(block)
        if not m:
            continue
        ref = m.group(1) if m.group(1) is not None else m.group(2)
        pads.setdefault(ref, set()).update(pads_of(block))
    return pads


def library_pads(dirs):
    """Return {footprint name: [(path, set(pad))]} for .kicad_mod files under dirs."""
    found = {}
    for d in dirs:
        for f in sorted(Path(d).rglob("*.kicad_mod")):
            text = f.read_text(encoding="utf-8")
            m = NAME_RE.search(text)
            name = m.group(1).split(":")[-1] if m else f.stem
            found.setdefault(name, []).append((f, pads_of(text)))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check symbol pin numbers against footprint pad numbers (read-only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 PASS, 1 WARNING (differences), 2 INCOMPLETE or ERROR.\n"
               "Example:\n  python -I check_pin_pad.py out/schematic.xml --pcb board.kicad_pcb")
    ap.add_argument("netlist", help="kicadxml netlist from kicad-cli sch export netlist")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pcb", help="board whose placed footprints supply the pad numbers")
    src.add_argument("--footprints", nargs="+", metavar="DIR",
                     help="folders searched recursively for .kicad_mod files")
    args = ap.parse_args(argv)

    try:
        pins, footprints, skipped = netlist_pins(args.netlist)
        if args.pcb:
            on_board = board_pads(args.pcb)
            pads = {ref: on_board.get(ref) for ref in pins}
            source = {ref: "board" for ref in pins}
        else:
            lib = library_pads(args.footprints)
            pads, source = {}, {}
            for ref, fp in footprints.items():
                name = fp.split(":")[-1]
                hits = lib.get(name, [])
                if len(hits) == 1:
                    pads[ref], source[ref] = hits[0][1], str(hits[0][0])
                else:
                    pads[ref] = None
                    source[ref] = f"{len(hits)} files named {name!r}"
    except (OSError, ET.ParseError, AttributeError, UnicodeDecodeError) as e:
        print(f"ERROR: cannot read input: {type(e).__name__}: {e}")
        return 2

    differences, incomplete = 0, 0
    for ref in sorted(pins):
        fp = footprints[ref]
        if not fp:
            print(f"INCOMPLETE {ref}: no footprint assigned")
            incomplete += 1
            continue
        if pads[ref] is None:
            where = "not placed on the board" if args.pcb else source[ref]
            print(f"INCOMPLETE {ref} ({fp}): footprint pads not found ({where})")
            incomplete += 1
            continue
        missing = sorted(pins[ref] - pads[ref])
        extra = sorted(pads[ref] - pins[ref])
        if missing:
            print(f"DIFF {ref} ({fp}): pin without pad: {', '.join(missing)}")
        if extra:
            print(f"DIFF {ref} ({fp}): pad without pin: {', '.join(extra)}")
        differences += bool(missing or extra)

    checked = len(pins) - incomplete
    if incomplete:
        status, code = "INCOMPLETE", 2
    elif differences:
        status, code = "WARNING", 1
    else:
        status, code = "PASS", 0
    print(f"components checked {checked}, with differences {differences}, "
          f"incomplete {incomplete}, skipped {len(skipped)}: {status}")
    return code


if __name__ == "__main__":
    sys.exit(main())
