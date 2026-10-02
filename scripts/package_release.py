"""Package a fixed PCB release folder with a per-file SHA-256 manifest.

Usage:
    python package_release.py --src releases/my-board-revC --out dist
    python package_release.py --src releases/my-board-revC --out dist --name my-board-revC-20260921

Writes into --out:
    SHA256-files.json        sha256 of every file under --src (paths relative to --src)
    <name>.zip               the --src folder plus the manifest
    <name>.zip.sha256.txt    sha256 of the zip itself

After writing, the zip is reopened and every entry is checked against the manifest.
Standard library only.
"""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", required=True, type=Path, help="release folder to package")
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    parser.add_argument("--name", help="zip base name (default: name of --src)")
    args = parser.parse_args()

    src = args.src.resolve()
    if not src.is_dir():
        print(f"--src is not a directory: {src}", file=sys.stderr)
        return 2
    out = args.out.resolve()
    if out == src or src in out.parents:
        print("--out must be outside --src", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.rglob("*") if p.is_file())
    manifest = {p.relative_to(src).as_posix(): sha256(p.read_bytes()) for p in files}
    manifest_path = out / "SHA256-files.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    name = args.name or src.name
    zip_path = out / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, f"{src.name}/{p.relative_to(src).as_posix()}")
        z.write(manifest_path, "SHA256-files.json")

    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad is not None:
            print(f"corrupt zip entry: {bad}", file=sys.stderr)
            return 1
        for rel, digest in manifest.items():
            if sha256(z.read(f"{src.name}/{rel}")) != digest:
                print(f"hash mismatch in zip: {rel}", file=sys.stderr)
                return 1

    zip_digest = sha256(zip_path.read_bytes())
    (out / f"{zip_path.name}.sha256.txt").write_text(f"{zip_digest}  {zip_path.name}\n", encoding="utf-8")
    print(json.dumps({"zip": zip_path.name, "files": len(manifest), "sha256": zip_digest,
                      "all_entries_verified": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
