#!/usr/bin/env python3
"""Check that every 3D model lands on its footprint (needs kicad-cli and CadQuery).

For each reference, the board is exported with only that component and no board
body; the model's bounding box is compared with the footprint outline:

  * fab outline (or courtyard, or pads) must lie inside the model box, within --tol
  * the model box must lie inside fab + courtyard + pads, within --overhang
    (raise it for parts that stick out on purpose, e.g. USB shells, switch knobs)
  * a top-side model must rise above the board top; a bottom-side one must hang below the board

Exit code 1 when any check fails. Prints a height table for the enclosure notes.

Usage:
  python verify_placement.py config.json            # refs that the config adds models to
  python verify_placement.py config.json --all      # every footprint with a model
  python verify_placement.py config.json --refs U1 J1 --overhang U1=2.5
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_sexpr as ks  # noqa: E402
import export_step as ex  # noqa: E402


def step_bbox(path):
    import cadquery as cq  # imported here so --help works without CadQuery
    b = cq.importers.importStep(path).val().BoundingBox()
    return b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax


def inside(inner, outer, tol):
    return (inner[0] >= outer[0] - tol and inner[1] <= outer[1] + tol
            and inner[2] >= outer[2] - tol and inner[3] <= outer[3] + tol)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("config")
    ap.add_argument("--refs", nargs="*", help="references to check")
    ap.add_argument("--all", action="store_true", help="check every footprint that has a model")
    ap.add_argument("--tol", type=float, default=0.5, help="mm; outline must be covered by the model")
    ap.add_argument("--overhang", nargs="*", default=[], metavar="[REF=]MM",
                    help="allowed overhang beyond outline+courtyard (default 1.0, or REF=MM)")
    args = ap.parse_args(argv)

    overhang, default_overhang = {}, 1.0
    for item in args.overhang:
        if "=" in item:
            k, v = item.split("=")
            overhang[k] = float(v)
        else:
            default_overhang = float(item)

    cfg = ex.load_config(args.config)
    text, _, injected = ex.build_board_text(cfg)
    root = ks.parse(text)
    fps = {fp["ref"]: fp for fp in ks.footprints(root)}
    origin = ex.origin_xy(cfg, root)
    if origin is None:
        raise SystemExit("verify needs an explicit origin in the config (e.g. board-bottom-left)")
    thick = ks.board_thickness(root)

    if args.refs:
        refs = args.refs
    elif args.all:
        refs = [r for r, fp in fps.items() if fp["models"] and not (fp["dnp"] and cfg.get("no_dnp", True))]
    else:
        refs = injected

    rows, failed = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        board = os.path.join(tmp, "enclosure.kicad_pcb")
        with open(board, "w", encoding="utf-8") as f:
            f.write(text)
        for ref in refs:
            fp = fps[ref]
            out = os.path.join(tmp, f"{ref}.step")
            ex.run_export(cfg, board, out, origin, only=ref, no_board_body=True)
            if not os.path.exists(out):
                rows.append((ref, "FAIL", "no geometry exported", None))
                failed += 1
                continue
            m = step_bbox(out)
            outline_local = fp["fab"] or fp["courtyard"] or fp["pads"]
            outline = ks.board_box_to_step(ks.local_box_to_board(fp, outline_local), origin)
            limit_local = ks.union(fp["fab"], fp["courtyard"], fp["pads"])
            limit = ks.board_box_to_step(ks.local_box_to_board(fp, limit_local), origin)
            issues = []
            if not inside(outline, m[:4], args.tol):
                issues.append("model does not cover the footprint outline")
            if not inside(m[:4], limit, overhang.get(ref, default_overhang)):
                issues.append("model extends past outline/courtyard")
            if fp["side"] == "top" and m[5] <= thick + 0.01:
                issues.append("top-side model is not above the board")
            if fp["side"] == "bottom" and m[4] >= -0.01:
                issues.append("bottom-side model is not below the board")
            failed += bool(issues)
            rows.append((ref, "FAIL" if issues else "ok", "; ".join(issues), (fp, m, outline)))

    print(f"board thickness {thick:g} mm; STEP origin {origin}; z=0 is the board bottom\n")
    print(f'{"ref":8} {"result":6} {"side":6} {"model x":>15} {"model y":>15} {"z range":>15} {"height":>7}  note')
    for ref, res, note, data in rows:
        if not data:
            print(f"{ref:8} {res:6} {note}")
            continue
        fp, m, outline = data
        height = m[5] - thick if fp["side"] == "top" else -m[4]
        print(f'{ref:8} {res:6} {fp["side"]:6} {m[0]:7.2f}..{m[1]:<7.2f}{m[2]:7.2f}..{m[3]:<7.2f}'
              f'{m[4]:7.2f}..{m[5]:<7.2f}{height:7.2f}  {note}')
        if res == "FAIL":
            print(f'{"":15}footprint outline x {outline[0]:.2f}..{outline[1]:.2f}  y {outline[2]:.2f}..{outline[3]:.2f}')
    print(f"\n{len(rows) - failed} ok, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
