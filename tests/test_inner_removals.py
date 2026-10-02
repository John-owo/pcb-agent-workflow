import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cam-diff" / "check_inner_removals.py"
spec = importlib.util.spec_from_file_location("inner_removals", SCRIPT)
inner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inner)


class ComponentsTests(unittest.TestCase):
    def test_horizontal_row_wrap_is_not_connected(self):
        self.assertEqual(sorted(map(len, inner.components([4, 5], 5))), [1, 1])

    def test_diagonal_row_wrap_is_not_connected(self):
        self.assertEqual(sorted(map(len, inner.components([4, 10], 5))), [1, 1])

    def test_real_diagonal_remains_connected(self):
        self.assertEqual(sorted(map(len, inner.components([3, 9], 5))), [2])


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.summary = {
            "status": "PASS", "ppmm": 1, "window_mm": [[0, 0], [10, 10]],
            "layers": {"In1_Cu": {"png_original": "original.png", "png_factory": "factory.png"}},
            "drills": {"original_holes": [{"x": 5, "y": 5, "X": 5, "Y": 5}]},
        }
        Image.new("L", (10, 10), 255).save(self.root / "original.png")
        Image.new("L", (10, 10), 255).save(self.root / "factory.png")

    def run_check(self, *args):
        (self.root / "layer-summary.json").write_text(json.dumps(self.summary), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            code = inner.main(["--renders", str(self.root), *args])
        return code, json.loads((self.root / "inner-check.json").read_text(encoding="utf-8"))

    def test_complete_equal_renders_pass(self):
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (0, "PASS"))

    def test_missing_requested_layer_is_incomplete(self):
        code, result = self.run_check("--layers", "In1_Cu", "In2_Cu")
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))
        self.assertIn("In1_Cu", result["layers"])

    def test_empty_explicit_selection_is_incomplete(self):
        code, result = self.run_check("--layers")
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def test_missing_holes_is_incomplete(self):
        self.summary["drills"]["original_holes"] = []
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def test_nonpass_or_legacy_upstream_cannot_pass(self):
        for status in (None, "WARNING", "INCOMPLETE", "ERROR"):
            with self.subTest(status=status):
                self.summary["status"] = status
                code, result = self.run_check()
                self.assertEqual(code, 2)
                self.assertNotEqual(result["status"], "PASS")
                self.assertNotEqual(result["layers"]["In1_Cu"]["status"], "PASS")

    def test_plane_net_check_without_nets_is_incomplete(self):
        code, result = self.run_check("--plane-nets", "GND")
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def custom_holes_path(self, holes):
        path = self.root / "holes.json"
        path.write_text(json.dumps(holes), encoding="utf-8")
        return str(path)

    def test_complete_custom_holes_with_nets_pass(self):
        path = self.custom_holes_path([{"x": 5, "y": 5, "net": "GND"}])
        code, result = self.run_check("--holes", path, "--plane-nets", "GND")
        self.assertEqual((code, result["status"]), (0, "PASS"))
        self.assertTrue(result["custom_holes_verified"])
        self.assertEqual(result["layers"]["In1_Cu"]["holes"][0]["net"], "GND")

    def test_truncated_custom_holes_cannot_hide_connected_pad_removal(self):
        self.summary["drills"]["original_holes"] = [
            {"x": x, "y": 5, "X": x, "Y": 5} for x in (4, 5)]
        original = Image.new("L", (10, 10), 255)
        for x in (4, 5):
            original.putpixel((x, 5), 0)
        original.save(self.root / "original.png")
        path = self.custom_holes_path([{"x": 4, "y": 5, "net": "GND"}])
        code, result = self.run_check("--holes", path, "--tolerance-px", "0")
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))
        self.assertFalse(result["custom_holes_verified"])
        self.assertEqual(result["layers"]["In1_Cu"]["connected_pads_lost_center"], 2)
        self.assertNotIn("net", result["layers"]["In1_Cu"]["holes"][0])

    def test_custom_holes_without_reference_cannot_pass(self):
        self.summary["drills"]["original_holes"] = []
        path = self.custom_holes_path([{"x": 5, "y": 5, "net": "GND"}])
        code, result = self.run_check("--holes", path)
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def test_shifted_or_duplicate_custom_holes_cannot_pass(self):
        for holes in ([{"x": 5.001, "y": 5}], [{"x": 5, "y": 5}, {"x": 5, "y": 5}]):
            with self.subTest(holes=holes):
                code, result = self.run_check("--holes", self.custom_holes_path(holes))
                self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def test_ambiguous_duplicate_reference_holes_cannot_pass(self):
        hole = self.summary["drills"]["original_holes"][0]
        self.summary["drills"]["original_holes"] = [hole, dict(hole)]
        path = self.custom_holes_path([{"x": 5, "y": 5}, {"x": 5, "y": 5}])
        code, result = self.run_check("--holes", path)
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def test_hole_outside_window_is_incomplete(self):
        self.summary["drills"]["original_holes"][0]["X"] = 20
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (2, "INCOMPLETE"))

    def test_missing_image_is_machine_readable_error(self):
        self.summary["layers"]["In1_Cu"]["png_factory"] = "missing.png"
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (2, "ERROR"))
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_subthreshold_suspicious_pixel_requires_review(self):
        original = Image.new("L", (10, 10), 255)
        original.putpixel((1, 1), 0)
        original.save(self.root / "original.png")
        code, result = self.run_check("--tolerance-px", "0", "--min-region-px", "2")
        self.assertEqual((code, result["status"]), (1, "WARNING"))
        self.assertEqual(result["layers"]["In1_Cu"]["suspicious_regions_total"], 0)
        self.assertEqual(result["layers"]["In1_Cu"]["removed_outside_unused_pads_px"], 1)

    def test_image_size_mismatch_is_error(self):
        Image.new("L", (9, 10), 255).save(self.root / "factory.png")
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (2, "ERROR"))

    def test_equal_truncated_images_cannot_pass(self):
        for name in ("original.png", "factory.png"):
            Image.new("L", (9, 10), 255).save(self.root / name)
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (2, "ERROR"))

    def test_invalid_frame_is_error(self):
        self.summary["ppmm"] = 0
        code, result = self.run_check()
        self.assertEqual((code, result["status"]), (2, "ERROR"))

    def test_negative_tolerance_is_error(self):
        code, result = self.run_check("--tolerance-px", "-1")
        self.assertEqual((code, result["status"]), (2, "ERROR"))

    def test_connected_pad_removal_requires_review(self):
        Image.new("L", (10, 10), 0).save(self.root / "original.png")
        code, result = self.run_check("--tolerance-px", "0")
        self.assertEqual((code, result["status"]), (1, "WARNING"))
        self.assertEqual(result["layers"]["In1_Cu"]["connected_pads_lost_center"], 1)

    def test_isolated_unused_pad_removal_passes(self):
        original = Image.new("L", (10, 10), 255)
        original.putpixel((5, 5), 0)
        original.save(self.root / "original.png")
        code, result = self.run_check("--tolerance-px", "0")
        self.assertEqual((code, result["status"]), (0, "PASS"))
        self.assertEqual(result["layers"]["In1_Cu"]["isolated_pads_removed"], 1)


if __name__ == "__main__":
    unittest.main()
