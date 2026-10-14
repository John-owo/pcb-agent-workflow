"""Netlist equivalence checks for the readable-schematic-layout skill script."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "readable-schematic-layout" / "scripts" / "compare_netlist.py"

COMP = ('<comp ref="{ref}"><value>{value}</value><footprint>R_0603</footprint>'
        '<fields><field name="MPN">X</field></fields></comp>')


def netlist(nets, r1_value="10k"):
    comps = COMP.format(ref="R1", value=r1_value) + COMP.format(ref="R2", value="1k")
    body = "".join(
        f'<net code="{i}" name="{name}">'
        + "".join(f'<node ref="{n.split(".")[0]}" pin="{n.split(".")[1]}"/>' for n in nodes)
        + "</net>"
        for i, (name, nodes) in enumerate(nets, 1))
    return f'<export version="E"><components>{comps}</components><nets>{body}</nets></export>'


BASE = [("GND", ["R1.1", "R2.1"]), ("/SIG", ["R1.2", "R2.2"])]


class CompareNetlistTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_compare(self, new, *flags, r1_value="10k"):
        base, other = self.root / "base.xml", self.root / "new.xml"
        base.write_text(netlist(BASE), encoding="utf-8")
        other.write_text(netlist(new, r1_value), encoding="utf-8")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), str(base), str(other), *flags],
                              capture_output=True, text=True)

    def test_identical(self):
        result = self.run_compare(BASE, "--names")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("IDENTICAL", result.stdout)

    def test_rename_allowed_without_names_flag(self):
        renamed = [("GND", ["R1.1", "R2.1"]), ("/OTHER", ["R1.2", "R2.2"])]
        self.assertEqual(self.run_compare(renamed).returncode, 0)
        self.assertEqual(self.run_compare(renamed, "--names").returncode, 1)

    def test_moved_pin_detected(self):
        moved = [("GND", ["R1.1", "R2.1", "R2.2"]), ("/SIG", ["R1.2"])]
        result = self.run_compare(moved)
        self.assertEqual(result.returncode, 1)
        self.assertIn("only in NEW", result.stdout)

    def test_component_value_change_detected(self):
        result = self.run_compare(BASE, r1_value="12k")
        self.assertEqual(result.returncode, 1)
        self.assertIn("component differs: R1", result.stdout)

    def test_help(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage", result.stdout)


if __name__ == "__main__":
    unittest.main()
