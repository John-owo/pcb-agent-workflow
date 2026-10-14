"""Compare two KiCad XML netlists (kicad-cli sch export netlist --format kicadxml).

Usage: python -I compare_netlist.py BASE.xml NEW.xml [--names]

Checks that the connectivity grouping is identical: every net is compared as the set of
"ref.pin" nodes it contains, independent of net names. With --names the net names must
also match. Also compares components (ref, value, footprint, fields, DNP).
Exit code 0 = identical, 1 = differences printed.
"""
import sys, xml.etree.ElementTree as ET


def load(path):
    root = ET.parse(path).getroot()
    nets = {}
    for n in root.find("nets").findall("net"):
        nodes = frozenset(f"{x.get('ref')}.{x.get('pin')}" for x in n.findall("node"))
        nets[nodes] = n.get("name")
    comps = {}
    for c in root.find("components").findall("comp"):
        fields = {f.get("name"): (f.text or "") for f in c.iter("field")}
        props = {p.get("name"): p.get("value") for p in c.findall("property")
                 if p.get("name") in ("dnp", "exclude_from_bom", "exclude_from_board")}
        comps[c.get("ref")] = (c.findtext("value"), c.findtext("footprint"),
                               tuple(sorted(fields.items())), tuple(sorted(props.items())))
    return nets, comps


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--help" in sys.argv or "-h" in args or len(args) != 2:
        print(__doc__.strip())
        sys.exit(0 if "--help" in sys.argv or "-h" in args else 2)
    check_names = "--names" in sys.argv
    (bn, bc), (nn, nc) = load(args[0]), load(args[1])
    fail = 0
    for g in sorted(set(bn) - set(nn), key=sorted):
        print(f"only in BASE: {bn[g]}: {sorted(g)}"); fail += 1
    for g in sorted(set(nn) - set(bn), key=sorted):
        print(f"only in NEW:  {nn[g]}: {sorted(g)}"); fail += 1
    if check_names:
        for g in set(bn) & set(nn):
            if bn[g] != nn[g]:
                print(f"renamed: {bn[g]} -> {nn[g]}"); fail += 1
    for ref in sorted(set(bc) | set(nc)):
        if bc.get(ref) != nc.get(ref):
            print(f"component differs: {ref}\n  BASE {bc.get(ref)}\n  NEW  {nc.get(ref)}"); fail += 1
    print(f"nets {len(bn)} -> {len(nn)}, components {len(bc)} -> {len(nc)}:",
          "IDENTICAL" if not fail else f"{fail} DIFFERENCES")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
