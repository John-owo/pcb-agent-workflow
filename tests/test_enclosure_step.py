"""Tests for skills/kicad-enclosure-step scripts that need only the standard library."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "kicad-enclosure-step", "scripts"))

import export_step as ex  # noqa: E402
import inventory_models  # noqa: E402
import kicad_sexpr as ks  # noqa: E402

BOARD = """(kicad_pcb
\t(version 20260206)
\t(general
\t\t(thickness 1.6)
\t)
\t(gr_rect
\t\t(start 100 100)
\t\t(end 125 136.5)
\t\t(layer "Edge.Cuts")
\t)
\t(footprint "Lib:Module"
\t\t(layer "F.Cu")
\t\t(at 110 110 90)
\t\t(property "Reference" "U1")
\t\t(property "Value" "say \\"hi\\"")
\t\t(fp_rect
\t\t\t(start -5 -2)
\t\t\t(end 5 2)
\t\t\t(layer "F.Fab")
\t\t)
\t\t(pad "1" smd rect
\t\t\t(at -4 0)
\t\t\t(size 1 1)
\t\t)
\t)
\t(footprint "Lib:R_0603"
\t\t(layer "F.Cu")
\t\t(at 120 130)
\t\t(property "Reference" "R1")
\t\t(attr smd)
\t)
\t(footprint "Lib:R_0603"
\t\t(layer "B.Cu")
\t\t(at 121 131)
\t\t(property "Reference" "R2")
\t\t(attr smd dnp)
\t\t(model "${KICAD10_3DMODEL_DIR}/old.step"
\t\t\t(offset
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t)
\t)
)
"""


def cfg(**kw):
    base = {"pcb": "board.kicad_pcb", "_base": "/models", "models": {}}
    base.update(kw)
    return base


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.root = ks.parse(BOARD)
        self.fps = {fp["ref"]: fp for fp in ks.footprints(self.root)}

    def test_footprint_fields(self):
        u1 = self.fps["U1"]
        self.assertEqual(u1["lib_id"], "Lib:Module")
        self.assertEqual(u1["value"], 'say "hi"')
        self.assertEqual((u1["x"], u1["y"], u1["rot"], u1["side"]), (110, 110, 90, "top"))
        self.assertEqual(u1["fab"], (-5, 5, -2, 2))
        self.assertFalse(u1["dnp"])
        self.assertTrue(self.fps["R2"]["dnp"])
        self.assertEqual(self.fps["R2"]["side"], "bottom")
        self.assertEqual(self.fps["R2"]["models"], ["${KICAD10_3DMODEL_DIR}/old.step"])

    def test_spans_point_at_parentheses(self):
        node = self.fps["U1"]["node"]
        self.assertEqual(BOARD[node.start], "(")
        self.assertEqual(BOARD[node.end], ")")

    def test_outline_and_thickness(self):
        self.assertEqual(ks.board_outline_bbox(self.root), (100, 125, 100, 136.5))
        self.assertEqual(ks.board_thickness(self.root), 1.6)

    def test_rotation_90_moves_local_x_to_board_up(self):
        # KiCad rotation is CCW on screen with Y down: local +X becomes board -Y.
        box = ks.local_box_to_board(self.fps["U1"], (-5, 5, -2, 2))
        self.assertEqual(tuple(round(v, 6) for v in box), (108, 112, 105, 115))
        step = ks.board_box_to_step(box, (100, 136.5))
        self.assertEqual(tuple(round(v, 6) for v in step), (8, 12, 21.5, 31.5))


class InjectTest(unittest.TestCase):
    def test_reference_beats_lib_id_and_paths_resolve(self):
        c = cfg(models={"Lib:R_0603": [{"file": "lib.step"}],
                        "R1": [{"file": "r1.step", "rotate": [-90, 0, 0]}]},
                replace_existing=True)
        text, _, injected = ex.build_board_text(c, BOARD)
        self.assertEqual(sorted(injected), ["R1", "R2"])
        fps = {fp["ref"]: fp for fp in ks.footprints(ks.parse(text))}
        self.assertEqual(fps["R1"]["models"], ["/models/r1.step"])
        self.assertEqual(fps["R2"]["models"], ["/models/lib.step"])  # old model replaced
        self.assertEqual(fps["U1"]["models"], [])
        rot = ks.find(ks.find(fps["R1"]["node"], "model"), "rotate")
        self.assertEqual(list(ks.find(rot, "xyz")[1:]), ["-90", "0", "0"])

    def test_existing_model_needs_opt_in(self):
        with self.assertRaises(SystemExit):
            ex.build_board_text(cfg(models={"R2": [{"file": "x.step"}]}), BOARD)

    def test_env_paths_are_kept(self):
        text, _, _ = ex.build_board_text(
            cfg(models={"U1": [{"file": "${KICAD10_3DMODEL_DIR}/a.step"}]}), BOARD)
        self.assertIn('(model "${KICAD10_3DMODEL_DIR}/a.step"', text)

    def test_multiple_models_and_wildcards(self):
        text, _, injected = ex.build_board_text(
            cfg(models={"U*": [{"file": "a.step"}, {"file": "b.step"}]}), BOARD)
        self.assertEqual(injected, ["U1"])
        u1 = next(fp for fp in ks.footprints(ks.parse(text)) if fp["ref"] == "U1")
        self.assertEqual(u1["models"], ["/models/a.step", "/models/b.step"])

    def test_origin_options(self):
        root = ks.parse(BOARD)
        self.assertEqual(ex.origin_xy({"origin": "board-bottom-left"}, root), (100, 136.5))
        self.assertEqual(ex.origin_xy({"origin": "board-center"}, root), (112.5, 118.25))
        self.assertEqual(ex.origin_xy({"origin": "100x150mm"}, root), (100.0, 150.0))
        self.assertIsNone(ex.origin_xy({"origin": None}, root))

    def test_missing_skips_dnp(self):
        _, fps, injected = ex.build_board_text(cfg(models={"U1": [{"file": "a.step"}]}), BOARD)
        self.assertEqual([fp["ref"] for fp in ex.missing_models(fps, injected, {})], ["R1"])


class ExampleTest(unittest.TestCase):
    EXAMPLE = os.path.join(ROOT, "examples", "max-m10s-breakout-revc-cad")

    def test_example_config_covers_every_part_with_height(self):
        c = ex.load_config(os.path.join(self.EXAMPLE, "enclosure-step.json"))
        _, fps, injected = ex.build_board_text(c)
        missing = [fp["ref"] for fp in ex.missing_models(fps, injected, c)]
        self.assertEqual(len(injected), 19)
        self.assertTrue(all(r.startswith("TP") for r in missing), missing)
        for spec in c["models"].values():
            path = spec[0]["file"]
            if not path.startswith("${"):
                self.assertTrue(os.path.exists(os.path.join(self.EXAMPLE, path)), path)

    def test_inventory_runs_on_example_board(self):
        pcb = os.path.join(ROOT, "examples", "max-m10s-breakout-revc", "MAX-M10S-Passive.kicad_pcb")
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as out:
            inventory_models.main([pcb, "--csv", os.path.join(tmp, "inv.csv")])
        self.assertIn("24 footprint(s) listed", out.getvalue())

    def test_model_specs_name_their_source(self):
        for name in os.listdir(os.path.join(self.EXAMPLE, "models")):
            if name.endswith(".json"):
                with open(os.path.join(self.EXAMPLE, "models", name), encoding="utf-8") as f:
                    spec = json.load(f)
                self.assertTrue(spec.get("source"), name)


if __name__ == "__main__":
    unittest.main()
