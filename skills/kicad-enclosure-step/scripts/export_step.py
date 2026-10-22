#!/usr/bin/env python3
"""Export a KiCad board to STEP with extra 3D models, without touching the board file.

A JSON config maps reference designators or footprint lib IDs to model files.
The script copies the board text, inserts (model ...) blocks into the matching
footprints, writes the copy to a temporary folder and runs `kicad-cli pcb export step`.

Config (paths are relative to the config file):

{
  "pcb": "../my-board/board.kicad_pcb",
  "output": "board.step",
  "origin": "board-bottom-left",          // or "board-center", "100x150mm", null (KiCad default)
  "no_dnp": true,                          // leave out DNP parts
  "define_vars": {"KICAD10_3DMODEL_DIR": "C:/Program Files/KiCad/10.0/share/kicad/3dmodels"},
  "replace_existing": false,               // true: drop models already in matched footprints
  "models": {
    "U1": [{"file": "models/module.step", "offset": [0, 0, 0], "rotate": [0, 0, 0]}],
    "MyLib:R_0603": [{"file": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0603_1608Metric.step"}]
  }
}

Keys with ':' match a footprint lib ID; other keys match a reference (wildcards
allowed). A reference match wins over a lib-ID match.

Usage:
  python export_step.py config.json [--only U1] [--no-board-body] [-o out.step] [--print-missing]
"""
import argparse
import fnmatch
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicad_sexpr as ks  # noqa: E402


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(path))
    cfg["_base"] = base
    cfg["pcb"] = os.path.normpath(os.path.join(base, cfg["pcb"]))
    cfg["output"] = os.path.normpath(os.path.join(base, cfg.get("output", "board.step")))
    return cfg


def resolve_model_path(path, base):
    if path.startswith("${") or os.path.isabs(path):
        return path.replace("\\", "/")
    return os.path.normpath(os.path.join(base, path)).replace("\\", "/")


def models_for(fp, cfg):
    models = cfg.get("models", {})
    for key, spec in models.items():
        if ":" not in key and fp["ref"] and fnmatch.fnmatchcase(fp["ref"], key):
            return spec
    for key, spec in models.items():
        if ":" in key and fnmatch.fnmatchcase(fp["lib_id"], key):
            return spec
    return None


def model_block(spec, base):
    v = lambda key, d: " ".join(f"{float(x):g}" for x in spec.get(key, d))
    path = resolve_model_path(spec["file"], base)
    return (f'\n\t\t(model "{path}"\n\t\t\t(offset\n\t\t\t\t(xyz {v("offset", (0, 0, 0))})\n\t\t\t)'
            f'\n\t\t\t(scale\n\t\t\t\t(xyz {v("scale", (1, 1, 1))})\n\t\t\t)'
            f'\n\t\t\t(rotate\n\t\t\t\t(xyz {v("rotate", (0, 0, 0))})\n\t\t\t)\n\t\t)')


def build_board_text(cfg, text=None):
    """Return (new_text, footprints, injected_refs). Raises on a model that would duplicate."""
    if text is None:
        with open(cfg["pcb"], encoding="utf-8") as f:
            text = f.read()
    root = ks.parse(text)
    fps = ks.footprints(root)
    edits = []  # (start, end, replacement)
    injected = []
    for fp in fps:
        spec = models_for(fp, cfg)
        if not spec:
            continue
        node = fp["node"]
        if fp["models"]:
            if not cfg.get("replace_existing"):
                raise SystemExit(f'{fp["ref"]} already has a 3D model ({fp["models"][0]}); '
                                 'remove it from the config or set "replace_existing": true')
            for m in ks.findall(node, "model"):
                edits.append((m.start, m.end + 1, ""))
        edits.append((node.end, node.end, "".join(model_block(s, cfg["_base"]) for s in spec) + "\n\t"))
        injected.append(fp["ref"])
    for start, end, rep in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:start] + rep + text[end:]
    return text, fps, injected


def origin_xy(cfg, root):
    origin = cfg.get("origin", "board-bottom-left")
    if origin in (None, ""):
        return None
    if origin in ("board-bottom-left", "board-center"):
        box = ks.board_outline_bbox(root)
        if not box:
            raise SystemExit("no Edge.Cuts outline found; set an explicit origin like 100x150mm")
        if origin == "board-bottom-left":
            return box[0], box[3]
        return (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
    x, y = origin.lower().replace("mm", "").split("x")
    return float(x), float(y)


def find_kicad_cli(cfg):
    for cand in (cfg.get("kicad_cli"), os.environ.get("KICAD_CLI"), shutil.which("kicad-cli")):
        if cand and os.path.exists(cand):
            return cand
    hits = sorted(glob.glob(r"C:\Program Files\KiCad\*\bin\kicad-cli.exe"))
    if hits:
        return hits[-1]
    raise SystemExit("kicad-cli not found; set KICAD_CLI or \"kicad_cli\" in the config")


def run_export(cfg, board_file, out, origin, only=None, no_board_body=False, extra=()):
    cmd = [find_kicad_cli(cfg), "pcb", "export", "step", "-f"]
    if cfg.get("no_dnp", True):
        cmd.append("--no-dnp")
    for k, v in cfg.get("define_vars", {}).items():
        cmd += ["-D", f"{k}={v}"]
    if origin:
        cmd += ["--user-origin", f"{origin[0]:g}x{origin[1]:g}mm"]
    if only:
        cmd += ["--component-filter", only]
    if no_board_body:
        cmd.append("--no-board-body")
    cmd += list(cfg.get("extra_args", [])) + list(extra) + ["-o", out, board_file]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = r.stdout + r.stderr
    if r.returncode:
        raise SystemExit(f"kicad-cli failed ({r.returncode}):\n{log}")
    return log


def render(cfg, board_file, prefix):
    """Isometric top and bottom renders of the board with the added models."""
    views = {"top": ("top", "-45,0,45"), "bottom": ("bottom", "45,0,-30")}
    for name, (side, rot) in views.items():
        cmd = [find_kicad_cli(cfg), "pcb", "render", "--side", side, "--rotate", rot,
               "--quality", "high", "--width", "1600", "--height", "1000"]
        for k, v in cfg.get("define_vars", {}).items():
            cmd += ["-D", f"{k}={v}"]
        cmd += ["-o", f"{prefix}-{name}.png", board_file]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit(f"kicad-cli render failed:\n{r.stdout}{r.stderr}")
        print("wrote", f"{prefix}-{name}.png")


def missing_models(fps, injected, cfg):
    """Footprints that will export with no 3D model (DNP and board-only items listed separately)."""
    out = []
    for fp in fps:
        if fp["models"] or fp["ref"] in injected:
            continue
        if fp["dnp"] and cfg.get("no_dnp", True):
            continue
        out.append(fp)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("config")
    ap.add_argument("-o", "--output", help="override the output path from the config")
    ap.add_argument("--only", help="export just these references (kicad-cli --component-filter)")
    ap.add_argument("--no-board-body", action="store_true")
    ap.add_argument("--print-missing", action="store_true",
                    help="list footprints that still have no 3D model and exit")
    ap.add_argument("--render", metavar="PREFIX",
                    help="also write PREFIX-top.png and PREFIX-bottom.png (kicad-cli pcb render)")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    text, fps, injected = build_board_text(cfg)
    missing = missing_models(fps, injected, cfg)
    if args.print_missing:
        for fp in missing:
            print(f'{fp["ref"]:8} {fp["lib_id"]:40} {fp["value"]}')
        print(f"{len(missing)} footprint(s) without a 3D model")
        return
    root = ks.parse(text)
    origin = origin_xy(cfg, root)
    out = os.path.abspath(args.output or cfg["output"])
    with tempfile.TemporaryDirectory() as tmp:
        board = os.path.join(tmp, "enclosure.kicad_pcb")
        with open(board, "w", encoding="utf-8") as f:
            f.write(text)
        log = run_export(cfg, board, out, origin, args.only, args.no_board_body)
        if args.render:
            render(cfg, board, os.path.abspath(args.render))
    problems = [l for l in log.splitlines() if "Could not add" in l or "not found" in l.lower()]
    print(f"added models to {len(injected)} footprint(s); origin {origin}")
    if missing:
        print("no 3D model (left as bare pads):", ", ".join(fp["ref"] for fp in missing))
    if problems:
        print("kicad-cli warnings:\n  " + "\n  ".join(problems))
    print("wrote", out)
    if problems:
        sys.exit(2)


if __name__ == "__main__":
    main()
