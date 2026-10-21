"""Pin-to-pad checks for the readable-schematic-layout skill script."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "readable-schematic-layout" / "scripts" / "check_pin_pad.py"
EXAMPLE_PCB = ROOT / "examples" / "max-m10s-breakout-revc" / "MAX-M10S-Passive.kicad_pcb"

sys.path.insert(0, str(SCRIPT.parent))
import check_pin_pad  # noqa: E402


def netlist(comps, nets):
    body = "".join(
        f'<comp ref="{ref}"><value>x</value><footprint>{fp}</footprint>{extra}</comp>'
        for ref, fp, extra in comps)
    nodes = "".join(
        f'<net code="{i}" name="{name}">'
        + "".join(f'<node ref="{n.split(".")[0]}" pin="{n.split(".")[1]}"/>' for n in members)
        + "</net>"
        for i, (name, members) in enumerate(nets, 1))
    return f'<export version="E"><components>{body}</components><nets>{nodes}</nets></export>'


def footprint(ref, name, pads):
    pad_text = "".join(f'\n    (pad "{p}" smd rect (at 0 0) (size 1 1) (layers "F.Cu"))' for p in pads)
    return (f'  (footprint "Lib:{name}"\n    (layer "F.Cu")\n'
            f'    (property "Reference" "{ref}" (at 0 0 0))\n'
            f'    (property "Description" "has (parens) and \\"quotes\\"" (at 0 0 0)){pad_text})\n')


COMPS = [("Q1", "Lib:SOT23", ""), ("R1", "Lib:R_0603", ""),
         ("TP9", "", '<property name="exclude_from_board"/>')]
NETS = [("GND", ["Q1.2", "R1.1"]), ("/G", ["Q1.1", "R1.2"]), ("unconnected-(Q1-D-Pad3)", ["Q1.3"])]


class CheckPinPadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_check(self, board_footprints, comps=COMPS, nets=NETS):
        net = self.root / "net.xml"
        pcb = self.root / "board.kicad_pcb"
        net.write_text(netlist(comps, nets), encoding="utf-8")
        pcb.write_text("(kicad_pcb\n" + "".join(board_footprints) + ")\n", encoding="utf-8")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), str(net), "--pcb", str(pcb)],
                              capture_output=True, text=True)

    def test_matching_sets_pass(self):
        r = self.run_check([footprint("Q1", "SOT23", ["1", "2", "3"]),
                            footprint("R1", "R_0603", ["1", "2", ""])])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS", r.stdout)
        self.assertIn("skipped 1", r.stdout)

    def test_swapped_pin_numbering_is_reported(self):
        r = self.run_check([footprint("Q1", "SOT23", ["G", "S", "D"]),
                            footprint("R1", "R_0603", ["1", "2"])])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Q1 (Lib:SOT23): pin without pad: 1, 2, 3", r.stdout)
        self.assertIn("Q1 (Lib:SOT23): pad without pin: D, G, S", r.stdout)

    def test_extra_pad_is_a_warning(self):
        r = self.run_check([footprint("Q1", "SOT23", ["1", "2", "3", "4"]),
                            footprint("R1", "R_0603", ["1", "2"])])
        self.assertEqual(r.returncode, 1)
        self.assertIn("pad without pin: 4", r.stdout)

    def test_missing_footprint_on_board_is_incomplete(self):
        r = self.run_check([footprint("Q1", "SOT23", ["1", "2", "3"])])
        self.assertEqual(r.returncode, 2)
        self.assertIn("INCOMPLETE R1", r.stdout)

    def test_footprint_library_mode(self):
        lib = self.root / "Lib.pretty"
        lib.mkdir()
        (lib / "SOT23.kicad_mod").write_text(footprint("REF**", "SOT23", ["1", "2", "3"]), encoding="utf-8")
        (lib / "R_0603.kicad_mod").write_text(footprint("REF**", "R_0603", ["1", "2"]), encoding="utf-8")
        net = self.root / "net.xml"
        net.write_text(netlist(COMPS, NETS), encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(net), "--footprints", str(self.root)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_unreadable_netlist_is_error(self):
        bad = self.root / "bad.xml"
        bad.write_text("<export>", encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(bad), "--pcb", str(bad)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("ERROR", r.stdout)

    def test_example_board_is_parsed_read_only(self):
        before = EXAMPLE_PCB.read_bytes()
        pads = check_pin_pad.board_pads(EXAMPLE_PCB)
        self.assertEqual(EXAMPLE_PCB.read_bytes(), before)
        self.assertEqual(len(pads), EXAMPLE_PCB.read_text(encoding="utf-8").count("\n\t(footprint "))
        self.assertEqual(sorted(pads["Q1"]), ["1", "2", "3"])
        self.assertEqual(len(pads["U1"]), 18)

    def test_help(self):
        r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Exit codes", r.stdout)


if __name__ == "__main__":
    unittest.main()
