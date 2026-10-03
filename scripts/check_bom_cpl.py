"""Check that a JLCPCB-style BOM and CPL describe the same placed parts.

Usage:
    python check_bom_cpl.py --bom BOM.csv --cpl CPL.csv
    python check_bom_cpl.py --bom BOM.csv --cpl CPL.csv --json out/bom-cpl-check.json

Expected column names (JLCPCB sample format):
    BOM: Comment, Designator, Footprint, LCSC Part #
    CPL: Designator, Mid X, Mid Y, Layer, Rotation

Checks: required columns, designator sets equal, no duplicates, no unexpanded
ranges such as R1-R3, LCSC part number present and shaped like C12345,
CPL coordinates/rotation numeric, Layer is Top or Bottom.
Not checked: rotation/polarity correctness, part stock or assembly eligibility,
footprint-to-part match, Basic/Extended classification, Gerber consistency.
Confirm those in the JLCPCB preview.

Exit codes: 0 PASS, 1 WARNING, 2 INCOMPLETE or ERROR.
Standard library only.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

DOC = __doc__ or ""
BOM_COLUMNS = ("Comment", "Designator", "Footprint", "LCSC Part #")
CPL_COLUMNS = ("Designator", "Mid X", "Mid Y", "Layer", "Rotation")
SEVERITY = {"PASS": 0, "WARNING": 1, "INCOMPLETE": 2, "ERROR": 3}
NOT_CHECKED = [
    "rotation and polarity correctness",
    "part stock and assembly eligibility",
    "footprint matches the ordered part",
    "Basic/Extended classification and fees",
    "consistency with Gerber files",
]
RANGE = re.compile(r"^([A-Za-z_]+)(\d+)-([A-Za-z_]*)(\d+)$")
LCSC = re.compile(r"^C\d+$")
COORD = re.compile(r"^(-?\d+(?:\.\d+)?)\s*(mm)?$", re.IGNORECASE)


def issue(report, status, message):
    report["issues"].append({"status": status, "message": message})


def read_table(path, required, label, report):
    """Return a list of (line number, row dict), or None when the file is unusable."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        issue(report, "ERROR", f"{label}: file not found")
        return None
    except UnicodeDecodeError:
        issue(report, "ERROR", f"{label}: not UTF-8 text; save the CSV as UTF-8")
        return None
    except OSError as e:
        issue(report, "ERROR", f"{label}: cannot read file ({type(e).__name__})")
        return None
    reader = csv.reader(text.splitlines())
    header = next(reader, None)
    if not header:
        issue(report, "ERROR", f"{label}: empty file")
        return None
    header = [h.strip() for h in header]
    duplicated = sorted(h for h, n in Counter(header).items() if n > 1)
    if duplicated:
        issue(report, "ERROR", f"{label}: duplicated columns {duplicated}")
        return None
    missing = [c for c in required if c not in header]
    if missing:
        issue(report, "ERROR", f"{label}: missing columns {missing}; expected {list(required)}")
        return None
    rows = []
    for line, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        if len(values) != len(header):
            issue(report, "ERROR",
                  f"{label} line {line}: {len(values)} fields, header has {len(header)}")
            continue
        rows.append((line, {h: v.strip() for h, v in zip(header, values)}))
    return rows


def split_designators(cell, where, report):
    names = []
    tokens = cell.split(",")
    if any(not t.strip() for t in tokens):
        issue(report, "WARNING", f"{where}: empty entry in Designator list")
    for token in (t.strip() for t in tokens):
        if not token:
            continue
        if RANGE.match(token):
            issue(report, "ERROR",
                  f"{where}: range '{token}' is not expanded; list every designator")
        elif re.search(r"\s", token):
            issue(report, "ERROR",
                  f"{where}: designator '{token}' contains spaces; separate with commas")
        else:
            names.append(token)
    return names


def check_bom(rows, report):
    names = []
    for line, row in rows:
        where = f"BOM line {line}"
        if not row["Designator"]:
            issue(report, "ERROR", f"{where}: empty Designator")
            continue
        refs = split_designators(row["Designator"], where, report)
        names.extend(refs)
        label = ",".join(refs) or row["Designator"]
        part = row["LCSC Part #"]
        if not part:
            issue(report, "WARNING",
                  f"{where} ({label}): no LCSC Part #; JLCPCB will not place it")
        elif not LCSC.match(part):
            issue(report, "WARNING",
                  f"{where} ({label}): LCSC Part # '{part}' does not look like C12345")
        for column in ("Comment", "Footprint"):
            if not row[column]:
                issue(report, "WARNING", f"{where} ({label}): empty {column}")
    return names


def parse_coord(value, where, column, report):
    m = COORD.match(value)
    if not m:
        issue(report, "ERROR", f"{where}: {column} '{value}' is not a number in mm")
        return None
    if not m.group(2):
        issue(report, "WARNING", f"{where}: {column} '{value}' has no unit; write e.g. 12.5mm")
    return float(m.group(1))


def check_cpl(rows, report):
    names, sides, positions = [], Counter(), Counter()
    for line, row in rows:
        where = f"CPL line {line}"
        ref = row["Designator"]
        if not ref:
            issue(report, "ERROR", f"{where}: empty Designator")
            continue
        refs = split_designators(ref, where, report)
        if len(refs) > 1:
            issue(report, "ERROR", f"{where}: one CPL row must hold exactly one designator")
        names.extend(refs)
        where = f"{where} ({ref})"
        x = parse_coord(row["Mid X"], where, "Mid X", report)
        y = parse_coord(row["Mid Y"], where, "Mid Y", report)
        side = row["Layer"].capitalize()
        if side not in ("Top", "Bottom"):
            issue(report, "ERROR", f"{where}: Layer '{row['Layer']}' must be Top or Bottom")
        else:
            sides[side] += 1
        try:
            float(row["Rotation"])
        except ValueError:
            issue(report, "ERROR", f"{where}: Rotation '{row['Rotation']}' is not a number")
        if x is not None and y is not None and side in ("Top", "Bottom"):
            positions[(side, x, y)] += 1
    for (side, x, y), count in sorted(positions.items()):
        if count > 1:
            issue(report, "WARNING", f"CPL: {count} parts share {side} position ({x}, {y})")
    return names, sides


def compare(bom_names, cpl_names, report):
    for label, names in (("BOM", bom_names), ("CPL", cpl_names)):
        repeated = sorted(n for n, c in Counter(names).items() if c > 1)
        if repeated:
            issue(report, "ERROR", f"{label}: designators listed more than once {repeated}")
    only_bom = sorted(set(bom_names) - set(cpl_names))
    only_cpl = sorted(set(cpl_names) - set(bom_names))
    if only_bom:
        issue(report, "ERROR", f"in BOM but not in CPL: {only_bom}")
    if only_cpl:
        issue(report, "ERROR", f"in CPL but not in BOM: {only_cpl}")
    report["only_in_bom"], report["only_in_cpl"] = only_bom, only_cpl


def run(bom_path, cpl_path):
    report = {"tool": "check_bom_cpl.py", "schema_version": 1,
              "scope": "BOM/CPL designator and format consistency; not assembly approval",
              "not_checked": NOT_CHECKED, "issues": []}
    bom_rows = read_table(bom_path, BOM_COLUMNS, "BOM", report)
    cpl_rows = read_table(cpl_path, CPL_COLUMNS, "CPL", report)
    if bom_rows is not None and cpl_rows is not None:
        bom_names = check_bom(bom_rows, report)
        cpl_names, sides = check_cpl(cpl_rows, report)
        if not bom_names or not cpl_names:
            issue(report, "INCOMPLETE", "BOM or CPL has no designators to compare")
        compare(bom_names, cpl_names, report)
        report["counts"] = {"bom_rows": len(bom_rows), "bom_designators": len(bom_names),
                            "cpl_rows": len(cpl_rows), "top": sides["Top"],
                            "bottom": sides["Bottom"]}
    report["status"] = max((i["status"] for i in report["issues"]),
                           key=SEVERITY.__getitem__, default="PASS")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=DOC.splitlines()[0], epilog=DOC.split("\n", 2)[2],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bom", required=True, type=Path, help="JLCPCB-style BOM CSV")
    parser.add_argument("--cpl", required=True, type=Path, help="JLCPCB-style CPL CSV")
    parser.add_argument("--json", type=Path, help="also write the report to this JSON file")
    args = parser.parse_args(argv)

    if args.json and args.json.resolve() in (args.bom.resolve(), args.cpl.resolve()):
        print("error: --json must not overwrite an input file", file=sys.stderr)
        return 2
    report = run(args.bom, args.cpl)
    if args.json:
        try:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        except OSError as e:
            print(f"error: cannot write report ({type(e).__name__})", file=sys.stderr)
            return 2
    counts = report.get("counts")
    if counts:
        print(f"BOM: {counts['bom_rows']} rows, {counts['bom_designators']} designators; "
              f"CPL: {counts['cpl_rows']} rows (Top {counts['top']}, Bottom {counts['bottom']})")
    for item in report["issues"]:
        print(f"{item['status']}: {item['message']}")
    print(f"status: {report['status']}")
    print("not checked: " + "; ".join(NOT_CHECKED))
    status = report["status"]
    return 0 if status == "PASS" else 1 if status == "WARNING" else 2


if __name__ == "__main__":
    sys.exit(main())
