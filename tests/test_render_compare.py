"""Real minimal Gerber/Excellon fixtures, independent of frozen releases."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "jlc-production-review" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import render_compare as render
import pixel_compare as pixel

GERBER = b"""G04 synthetic test*
%FSLAX24Y24*%
%MOMM*%
%ADD10C,0.100*%
D10*
X000000Y000000D02*
X020000Y000000D01*
X020000Y020000D01*
X000000Y020000D01*
X000000Y000000D01*
M02*
"""
DRILL = b"M48\nMETRIC,TZ\nT01C0.3\n%\nT01\nX1.0Y1.0\nM30\n"


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.orig = self.root / "original"
        self.fact = self.root / "factory"
        self.orig.mkdir()
        self.fact.mkdir()
        for folder in (self.orig, self.fact):
            for name in ("board-F_Cu.gbr", "board-B_Cu.gbr", "board-Edge_Cuts.gbr"):
                (folder / name).write_bytes(GERBER)
            (folder / "board.drl").write_bytes(DRILL)
        self.out = self.root / "out"

    def run_render(self, extra=(), check_upload=True):
        args = ["--original", str(self.orig), "--factory", str(self.fact),
                "--out", str(self.out), "--offset", "0", "0", "--ppmm", "10"]
        if check_upload:
            args += ["--check-upload", str(self.orig)]
        with contextlib.redirect_stdout(io.StringIO()):
            code = render.main(args + list(extra))
        summary = json.loads((self.out / "layer-summary.json").read_text())
        return code, summary

    def test_complete_real_parse_and_pixel_self_comparison_pass(self):
        code, summary = self.run_render()
        self.assertEqual((code, summary["status"]), (0, "PASS"))
        self.assertEqual(summary["drills"]["matched"], 1)
        self.assertEqual(set(summary["layers"]), {"F_Cu", "B_Cu", "Outline"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pixel.main(["--renders", str(self.out)]), 0)
        self.assertEqual(json.loads((self.out / "pixel-summary.json").read_text())["status"], "PASS")

    def test_missing_layer_is_incomplete(self):
        (self.fact / "board-B_Cu.gbr").unlink()
        code, s = self.run_render()
        self.assertEqual((code, s["status"]), (2, "INCOMPLETE"))
        self.assertNotIn("B_Cu", s["layers"])

    def test_missing_core_layer_on_both_sides_is_incomplete(self):
        for folder in (self.orig, self.fact):
            (folder / "board-B_Cu.gbr").unlink()
        self.assertEqual(self.run_render()[1]["status"], "INCOMPLETE")

    def test_missing_drill_with_explicit_offset_is_incomplete(self):
        (self.fact / "board.drl").unlink()
        self.assertEqual(self.run_render()[1]["status"], "INCOMPLETE")

    def test_all_layer_aliases_checked_not_first_pattern(self):
        (self.fact / "tl").write_bytes(GERBER)
        code, s = self.run_render()
        self.assertEqual((code, s["status"]), (2, "INCOMPLETE"))
        self.assertNotIn("F_Cu", s["layers"])

    def test_relative_path_pair_resolves_ambiguity(self):
        nested = self.fact / "extra"
        nested.mkdir()
        (nested / "board-F_Cu.gbr").write_bytes(GERBER)
        _, s = self.run_render(["--pair", "F_Cu=board-F_Cu.gbr,./board-F_Cu.gbr"])
        # './' is not a stored relative path; explicit wrong paths must fail.
        self.assertEqual(s["status"], "INCOMPLETE")
        out2 = self.root / "out2"
        self.out = out2
        (self.fact / "selected").mkdir()
        (self.fact / "board-F_Cu.gbr").rename(self.fact / "selected/board-F_Cu.gbr")
        _, s = self.run_render(["--pair", "F_Cu=board-F_Cu.gbr,selected/board-F_Cu.gbr"])
        self.assertEqual(s["layers"]["F_Cu"]["factory_file"], "selected/board-F_Cu.gbr")

    def test_upload_mismatch_is_incomplete(self):
        up = self.root / "upload"
        up.mkdir()
        (up / "board-F_Cu.gbr").write_bytes(b"changed")
        _, s = self.run_render(["--check-upload", str(up)])
        self.assertEqual(s["status"], "INCOMPLETE")
        self.assertEqual(s["upload_check"]["different"], ["board-F_Cu.gbr"])

    def test_upload_nested_same_basenames_are_not_collapsed(self):
        for folder in (self.orig, self.fact):
            (folder / "a").mkdir()
            (folder / "b").mkdir()
            (folder / "a/readme.txt").write_bytes(b"a")
            (folder / "b/readme.txt").write_bytes(b"b")
        (self.fact / "a/readme.txt").write_bytes(b"wrong")
        result = render.compare_upload(render.Source(str(self.orig)), render.Source(str(self.fact)))
        self.assertEqual(result["different"], ["a/readme.txt"])
        self.assertIn("b/readme.txt", result["same"])

    def test_panel_names_do_not_collide(self):
        for name in ("a", "b"):
            (self.fact / name).mkdir()
            (self.fact / name / "marker.gbr").write_bytes(GERBER)
        _, s = self.run_render()
        a = s["factory_files"]["a/marker.gbr"]["png_panel"]
        b = s["factory_files"]["b/marker.gbr"]["png_panel"]
        self.assertNotEqual(a, b)
        self.assertTrue((self.out / a).exists() and (self.out / b).exists())

    def test_duplicate_zip_member_rejected(self):
        path = self.root / "duplicate.zip"
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("same.gbr", GERBER)
                z.writestr("same.gbr", b"wrong")
        with self.assertRaisesRegex(ValueError, "duplicate ZIP member"):
            render.Source(str(path))

    def test_no_upload_check_warns(self):
        self.assertEqual(self.run_render(check_upload=False)[0], 1)

    def test_auto_offset_ambiguity_is_error(self):
        (self.fact / "board.drl").write_bytes(DRILL.replace(b"M30", b"X5.0Y5.0\nM30"))
        code, s = self.run_render(["--offset", "auto"])
        self.assertEqual((code, s["status"]), (2, "ERROR"))
        self.assertFalse(s["layers"])

    def test_omission_partial_window_and_only_pairs_never_pass(self):
        for i, args in enumerate((["--omit-layer", "B_Cu=separate review"],
                                  ["--window", "0", "0", "2", "2"],
                                  ["--only-pairs", "--pair", "F_Cu=*.gbr,*.gbr"])):
            self.out = self.root / f"out{i}"
            self.assertNotEqual(self.run_render(args)[1]["status"], "PASS")

    def test_stale_output_is_rejected_without_overwrite(self):
        self.run_render()
        before = (self.out / "layer-summary.json").read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            code = render.main(["--original", str(self.orig), "--factory", str(self.fact), "--out", str(self.out)])
        self.assertEqual(code, 2)
        self.assertEqual((self.out / "layer-summary.json").read_bytes(), before)

    def test_bad_input_writes_error_without_private_path(self):
        _, s = self.run_render(["--original", str(self.root / "missing")])
        self.assertEqual(s["status"], "ERROR")
        self.assertNotIn(str(self.root), json.dumps(s))

    def test_pixel_nonpass_missing_layer_and_partial_selection(self):
        self.run_render()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pixel.main(["--renders", str(self.out), "--layers", "NoSuchLayer"]), 2)
            self.assertEqual(pixel.main(["--renders", str(self.out), "--layers", "F_Cu"]), 2)
        s = json.loads((self.out / "layer-summary.json").read_text())
        s["status"] = "INCOMPLETE"
        (self.out / "layer-summary.json").write_text(json.dumps(s))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pixel.main(["--renders", str(self.out)]), 2)

    def test_pixel_subthreshold_change_still_warns(self):
        from PIL import Image
        self.run_render()
        path = self.out / "F_Cu-cam.png"
        with Image.open(path) as image:
            image = image.copy()
        image.putpixel((5, 5), 0)
        image.save(path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pixel.main(["--renders", str(self.out), "--min-region-px", "1000"]), 1)

    def test_drill_tie_is_incomplete_without_guessed_assignment(self):
        orig = [{"x": x, "y": 0, "d": .3, "file": "drill", "plated": None} for x in (0, .004)]
        fact = [{"x": .002, "y": 0, "d": .3} for _ in range(2)]
        result = render.match_drills(orig, fact, render.Transform(), [[-1, -1], [1, 1]], .5, .005)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(result["ambiguous_candidates"])
        self.assertNotIn("matched", result)

    def test_drill_alias_patterns_collect_pth_and_npth(self):
        (self.orig / "holes-NPTH.gbr").write_bytes(GERBER)
        hits = render.Source(str(self.orig)).find(render.DRILL_ORIGINAL)
        self.assertEqual(hits, ["board.drl", "holes-NPTH.gbr"])

    def test_duplicate_nested_drills_rejected(self):
        (self.fact / "nested").mkdir()
        (self.fact / "nested/board.drl").write_bytes(DRILL)
        self.assertEqual(self.run_render()[1]["status"], "ERROR")

    def test_corrupt_unmapped_cam_cannot_pass(self):
        for i, folder in enumerate((self.orig, self.fact)):
            path = folder / "custom-plane.gbr"
            path.write_bytes(b"corrupt header")
            self.out = self.root / f"corrupt{i}"
            self.assertEqual(self.run_render()[1]["status"], "INCOMPLETE")
            path.unlink()

    def test_rejected_source_output_does_not_create_directory(self):
        target = self.orig / "new-output"
        with contextlib.redirect_stdout(io.StringIO()):
            code = render.main(["--original", str(self.orig), "--factory", str(self.fact), "--out", str(target)])
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())

    def test_equal_cropped_renders_are_error(self):
        from PIL import Image
        self.run_render()
        for kind in ("orig", "cam"):
            path = self.out / f"F_Cu-{kind}.png"
            with Image.open(path) as im:
                cropped = im.crop((0, 0, im.width - 1, im.height - 1))
            cropped.save(path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pixel.main(["--renders", str(self.out)]), 2)

    def test_drill_missing_hole_has_warning_substatus(self):
        orig = [{"x": 0, "y": 0, "d": .3, "file": "drill", "plated": None}]
        result = render.match_drills(orig, [], render.Transform(), [[-1, -1], [1, 1]], .5, .005)
        self.assertEqual(result["status"], "WARNING")
        self.assertEqual(len(result["missing_in_factory"]), 1)

    def test_real_polygon_render(self):
        polygon = GERBER.replace(b"D10*", b"D10*\nG36*", 1).replace(b"M02*", b"G37*\nM02*")
        cam, _, warn = render.load_cam("polygon.gbr", polygon)
        self.assertEqual(warn, 0)
        im = render.rasterize(cam, None, [[0, 0], [2, 2]], 10, 1)
        self.assertEqual(im.getpixel((10, 10)), 0)

    def test_empty_optional_layer_both_sides_is_complete(self):
        for folder in (self.orig, self.fact):
            (folder / "board-B_Paste.gbr").write_bytes(b"%FSLAX24Y24*%\n%MOMM*%\nM02*\n")
        self.assertEqual(self.run_render()[1]["status"], "PASS")

    def test_empty_required_layer_is_incomplete(self):
        for folder in (self.orig, self.fact):
            (folder / "board-F_Cu.gbr").write_bytes(b"%FSLAX24Y24*%\n%MOMM*%\nM02*\n")
        self.assertEqual(self.run_render()[1]["status"], "INCOMPLETE")

    def test_parser_warnings_are_incomplete(self):
        for folder in (self.orig, self.fact):
            path = folder / "board.drl"
            path.write_bytes(DRILL.replace(b"%\nT01", b"%\nG90\nT01"))
        self.assertEqual(self.run_render()[1]["status"], "INCOMPLETE")

    def test_drill_slots_are_incomplete(self):
        for folder in (self.orig, self.fact):
            path = folder / "board.drl"
            path.write_bytes(DRILL.replace(b"M30", b"X1.0Y1.0G85X1.2Y1.0\nM30"))
        _, s = self.run_render()
        self.assertEqual(s["status"], "INCOMPLETE")
        self.assertGreater(s["drills"]["slots"]["original"], 0)

    def test_invalid_numeric_options_are_error(self):
        for i, extra in enumerate((["--ppmm", "0"], ["--offset", "nan", "0"], ["--supersample", "0"])):
            self.out = self.root / f"badnumber{i}"
            self.assertEqual(self.run_render(extra)[1]["status"], "ERROR")

    def test_unwritable_output_target_returns_error_code(self):
        target = self.root / "output-file"
        target.write_bytes(b"preserve this file")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(render.main(["--original", str(self.orig), "--factory", str(self.fact),
                                          "--out", str(target)]), 2)
            self.assertEqual(pixel.main(["--renders", str(self.out), "--out", str(target)]), 2)
        self.assertEqual(target.read_bytes(), b"preserve this file")

    def test_fixed_release_read_only_self_comparison(self):
        import hashlib
        archive = SCRIPTS.parents[2] / "examples/max-m10s-breakout-revc/manufacturing/gerbers-board.zip"
        before = hashlib.sha256(archive.read_bytes()).hexdigest()
        with contextlib.redirect_stdout(io.StringIO()):
            code = render.main(["--original", str(archive), "--factory", str(archive),
                                "--check-upload", str(archive), "--out", str(self.out),
                                "--ppmm", "10", "--supersample", "1"])
            self.assertEqual(pixel.main(["--renders", str(self.out)]), 2)
        s = json.loads((self.out / "layer-summary.json").read_text())
        self.assertEqual((code, s["status"]), (2, "INCOMPLETE"))
        self.assertTrue(all("parser warnings" in i["message"] for i in s["issues"]))
        self.assertEqual((s["drills"]["matched"], s["drills"]["original_count"]), (60, 60))
        self.assertEqual(s["upload_check"]["status"], "PASS")
        p = json.loads((self.out / "pixel-summary.json").read_text())
        self.assertTrue(all(layer["changed_pixels"] == 0 for layer in p["layers"].values()))
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
