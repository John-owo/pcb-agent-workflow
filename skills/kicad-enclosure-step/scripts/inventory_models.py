#!/usr/bin/env python3
"""List every footprint on a KiCad board with its 3D model status (stdlib only).

Shows reference, side, lib ID, value, supplier part number, DNP flag and whether
the referenced model file exists. Use it first, to see which parts need a model.

Usage:
  python inventory_models.py board.kicad_pcb [--missing] [-D KICAD10_3DMODEL_DIR=...] [--csv out.csv]
"""
import argparse
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_sexpr as ks  # noqa: E402

PART_FIELDS = ("LCSC", "LCSC Part", "JLCPCB Part", "MPN", "Manufacturer Part Number", "Manufacturer")


def default_vars(pcb):
    env = {"KIPRJMOD": os.path.dirname(os.path.abspath(pcb))}
    for d in sorted(glob.glob(r"C:\Program Files\KiCad\*\share\kicad\3dmodels")):
        ver = d.split(os.sep)[-4].split(".")[0]
        env.setdefault(f"KICAD{ver}_3DMODEL_DIR", d)
    env.update({k: v for k, v in os.environ.items() if k.endswith("_3DMODEL_DIR")})
    return env


def expand(path, env):
    return re.sub(r"\$\{([^}]+)\}", lambda m: env.get(m.group(1), m.group(0)), path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pcb")
    ap.add_argument("--missing", action="store_true", help="only footprints without a usable model")
    ap.add_argument("-D", action="append", default=[], metavar="VAR=PATH", help="path variable")
    ap.add_argument("--csv", help="also write the table to this CSV file")
    args = ap.parse_args(argv)

    with open(args.pcb, encoding="utf-8") as f:
        root = ks.parse(f.read())
    env = default_vars(args.pcb)
    env.update(dict(d.split("=", 1) for d in args.D))

    rows = []
    for fp in ks.footprints(root):
        part = next((fp["props"][k] for k in PART_FIELDS if fp["props"].get(k)), "")
        if not fp["models"]:
            status = "NONE"
        else:
            paths = [expand(m, env) for m in fp["models"]]
            status = "ok" if all(os.path.exists(p) for p in paths) else "MISSING FILE"
        rows.append({"ref": fp["ref"], "side": fp["side"], "lib_id": fp["lib_id"], "value": fp["value"],
                     "part": part, "dnp": "DNP" if fp["dnp"] else "", "model": status,
                     "model_path": ";".join(fp["models"])})
    rows.sort(key=lambda r: (r["model"] == "ok", r["ref"] or ""))
    if args.missing:
        rows = [r for r in rows if r["model"] != "ok"]

    for r in rows:
        print(f'{r["ref"]:8} {r["side"]:6} {r["model"]:12} {r["dnp"]:3} {r["lib_id"]:40} {r["value"]:22} {r["part"]}')
    need = sum(r["model"] != "ok" and not r["dnp"] for r in rows)
    print(f"\n{len(rows)} footprint(s) listed; {need} populated part(s) need a model")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["ref"])
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
