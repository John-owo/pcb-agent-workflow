"""BOM/CPL consistency checks. The fixed example is only read, never written."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "jlc-production-review" / "scripts" / "check_bom_cpl.py"
EXAMPLE = ROOT / "examples" / "max-m10s-breakout-revc" / "manufacturing"

BOM = ('"Comment","Designator","Footprint","LCSC Part #"\n'
       '"100nF","C1,C2","C_0603","C14663"\n'
       '"10k","R1","R_0603","C25804"\n')
CPL = ('"Designator","Mid X","Mid Y","Layer","Rotation"\n'
       '"C1","1.0mm","2.0mm","Top","0"\n'
       '"C2","3.0mm","2.0mm","Top","90"\n'
       '"R1","5.0mm","2.0mm","Top","180"\n')


class CheckBomCplTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def check(self, bom=BOM, cpl=CPL, encoding="utf-8"):
        bom_path, cpl_path = self.root / "bom.csv", self.root / "cpl.csv"
        bom_path.write_bytes(bom.encode(encoding))
        cpl_path.write_bytes(cpl.encode(encoding))
        return self.run_paths(bom_path, cpl_path)

    def run_paths(self, bom_path, cpl_path):
        report_path = self.root / "out" / "report.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--bom", str(bom_path), "--cpl", str(cpl_path),
             "--json", str(report_path)],
            capture_output=True, text=True, check=False)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return result.returncode, report

    def messages(self, report):
        return " | ".join(i["message"] for i in report["issues"])

    def test_matching_files_pass(self):
        code, report = self.check()
        self.assertEqual((code, report["status"]), (0, "PASS"), self.messages(report))
        self.assertEqual(report["counts"]["bom_designators"], 3)
        self.assertEqual(report["counts"]["top"], 3)
        self.assertIn("rotation and polarity correctness", report["not_checked"])

    def test_fixed_example_passes_read_only(self):
        bom = EXAMPLE / "BOM-JLCPCB-top-only.csv"
        cpl = EXAMPLE / "CPL-board-top-only.csv"
        before = (bom.read_bytes(), cpl.read_bytes())
        code, report = self.run_paths(bom, cpl)
        self.assertEqual((code, report["status"]), (0, "PASS"), self.messages(report))
        self.assertEqual(report["counts"]["bom_designators"], 17)
        self.assertEqual((bom.read_bytes(), cpl.read_bytes()), before)

    def test_utf8_bom_and_bottom_side_are_accepted(self):
        cpl = CPL.replace('"R1","5.0mm","2.0mm","Top"', '"R1","5.0mm","2.0mm","bottom"')
        code, report = self.check(bom="﻿" + BOM, cpl=cpl)
        self.assertEqual(code, 0, self.messages(report))
        self.assertEqual(report["counts"]["bottom"], 1)

    def test_designator_only_in_one_file_is_error(self):
        code, report = self.check(cpl=CPL.replace('"R1",', '"R2",'))
        self.assertEqual((code, report["status"]), (2, "ERROR"))
        self.assertEqual(report["only_in_bom"], ["R1"])
        self.assertEqual(report["only_in_cpl"], ["R2"])

    def test_duplicate_designators_are_error(self):
        code, report = self.check(bom=BOM.replace('"R1"', '"R1,C1"'))
        self.assertEqual(code, 2)
        self.assertIn("more than once ['C1']", self.messages(report))
        code, report = self.check(cpl=CPL + '"R1","7.0mm","2.0mm","Top","0"\n')
        self.assertEqual(code, 2)
        self.assertIn("CPL: designators listed more than once ['R1']", self.messages(report))

    def test_unexpanded_range_is_error_not_guessed(self):
        bom = BOM.replace('"C1,C2"', '"C1-C2"')
        code, report = self.check(bom=bom)
        self.assertEqual(code, 2)
        self.assertIn("range 'C1-C2' is not expanded", self.messages(report))

    def test_missing_or_duplicated_columns_are_error(self):
        code, report = self.check(cpl=CPL.replace('"Mid X"', '"PosX"'))
        self.assertEqual((code, report["status"]), (2, "ERROR"))
        self.assertIn("missing columns ['Mid X']", self.messages(report))
        self.assertNotIn("counts", report)
        code, report = self.check(bom=BOM.replace('"Footprint"', '"Comment"'))
        self.assertEqual(code, 2)
        self.assertIn("duplicated columns", self.messages(report))

    def test_bad_cpl_values_are_error(self):
        cpl = CPL.replace('"Top","90"', '"Middle","ninety"').replace('"5.0mm"', '"5 mil"')
        code, report = self.check(cpl=cpl)
        self.assertEqual(code, 2)
        text = self.messages(report)
        self.assertIn("must be Top or Bottom", text)
        self.assertIn("Rotation 'ninety'", text)
        self.assertIn("Mid X '5 mil' is not a number in mm", text)

    def test_ragged_row_is_error(self):
        code, report = self.check(cpl=CPL + '"R9","1mm"\n')
        self.assertEqual(code, 2)
        self.assertIn("2 fields, header has 5", self.messages(report))

    def test_review_items_are_warning(self):
        bom = BOM.replace('"C25804"', '""').replace('"C14663"', '"14663"')
        cpl = CPL.replace('"3.0mm","2.0mm"', '"1.0mm","2.0mm"').replace('"5.0mm"', '"5.0"')
        code, report = self.check(bom=bom, cpl=cpl)
        self.assertEqual((code, report["status"]), (1, "WARNING"), self.messages(report))
        text = self.messages(report)
        self.assertIn("no LCSC Part #", text)
        self.assertIn("does not look like C12345", text)
        self.assertIn("2 parts share Top position", text)
        self.assertIn("1 rows have coordinates without a unit (first: CPL line 4 (R1))", text)

    def test_full_width_digits_and_odd_rotations_do_not_pass(self):
        bom = BOM.replace('"C25804"', '"C２５８０４"')
        code, report = self.check(bom=bom)
        self.assertEqual(code, 1)
        self.assertIn("does not look like C12345", self.messages(report))
        for rotation in ("nan", "inf", "9_0", "９０"):
            code, report = self.check(cpl=CPL.replace('"Top","90"', f'"Top","{rotation}"'))
            self.assertEqual(code, 2, rotation)
            self.assertIn(f"Rotation '{rotation}' is not a number", self.messages(report))
        code, report = self.check(cpl=CPL.replace('"Top","90"', '"Top","450"'))
        self.assertEqual(code, 1)
        self.assertIn("outside -360..360", self.messages(report))

    def test_mid_coordinate_with_full_width_digits_is_error(self):
        code, report = self.check(cpl=CPL.replace('"3.0mm"', '"３.0mm"'))
        self.assertEqual(code, 2)
        self.assertIn("is not a number in mm", self.messages(report))

    def test_unnamed_trailing_columns_and_multiline_fields(self):
        bom = ('"Comment","Designator","Footprint","LCSC Part #",,\n'
               '"100nF\nX7R","C1,C2","C_0603","C14663",,\n'
               '"10k","R1","R_0603","C25804",,\n')
        code, report = self.check(bom=bom)
        self.assertEqual(code, 0, self.messages(report))
        code, report = self.check(bom=bom.replace('"C25804"', '""'))
        self.assertIn("BOM line 4 (R1)", self.messages(report))

    def test_unprintable_text_and_oversized_field_never_exit_as_warning(self):
        env = dict(os.environ, PYTHONIOENCODING="ascii")
        bom_path, cpl_path = self.root / "bom.csv", self.root / "cpl.csv"
        bom_path.write_text(BOM.replace('"C25804"', '"C25804µ"'), encoding="utf-8")
        cpl_path.write_text(CPL, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--bom", str(bom_path), "--cpl", str(cpl_path)],
            capture_output=True, text=True, check=False, env=env)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("status: WARNING", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        code, report = self.check(bom=BOM.replace('"10k"', '"' + "x" * 200000 + '"'))
        self.assertEqual((code, report["status"]), (2, "ERROR"))
        self.assertIn("CSV cannot be parsed", self.messages(report))

    def test_same_file_for_bom_and_cpl_is_error(self):
        path = self.root / "both.csv"
        path.write_text(BOM, encoding="utf-8")
        code, report = self.run_paths(path, path)
        self.assertEqual((code, report["status"]), (2, "ERROR"))

    def test_empty_tables_are_incomplete(self):
        code, report = self.check(bom=BOM.splitlines()[0] + "\n", cpl=CPL.splitlines()[0] + "\n")
        self.assertEqual((code, report["status"]), (2, "INCOMPLETE"))

    def test_non_utf8_input_is_error(self):
        code, report = self.check(bom=BOM.replace("100nF", "100nF 電容"), encoding="cp950")
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", self.messages(report))

    def test_json_must_not_overwrite_input(self):
        bom_path = self.root / "bom.csv"
        bom_path.write_text(BOM, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--bom", str(bom_path), "--cpl", str(bom_path),
             "--json", str(bom_path)],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(bom_path.read_text(encoding="utf-8"), BOM)


if __name__ == "__main__":
    unittest.main()
