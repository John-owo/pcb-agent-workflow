"""Release packaging checks use synthetic files, never fixed example releases."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "package_release.py"


class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "board-revC"
        self.src.mkdir()
        (self.src / "nested").mkdir()
        (self.src / "top.gbr").write_bytes(b"synthetic top layer\n")
        (self.src / "nested" / "top.gbr").write_bytes(b"different nested layer\n")

    def package(self, out, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--src", str(self.src), "--out", str(out), *extra],
            capture_output=True, text=True, check=False,
        )

    def test_manifest_and_archive_verify_every_relative_path(self):
        original = {p.relative_to(self.src).as_posix(): p.read_bytes()
                    for p in self.src.rglob("*") if p.is_file()}
        out = self.root / "dist"
        result = self.package(out)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["all_entries_verified"])
        self.assertEqual(report["files"], 2)
        manifest = json.loads((out / "SHA256-files.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest, {rel: hashlib.sha256(data).hexdigest()
                                    for rel, data in original.items()})
        archive = out / report["zip"]
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(set(z.namelist()),
                             {f"{self.src.name}/{rel}" for rel in original} | {"SHA256-files.json"})
            self.assertEqual(json.loads(z.read("SHA256-files.json")), manifest)
            for rel, data in original.items():
                self.assertEqual(z.read(f"{self.src.name}/{rel}"), data)
                self.assertEqual((self.src / rel).read_bytes(), data)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(report["sha256"], digest)
        self.assertEqual((out / f"{archive.name}.sha256.txt").read_text(encoding="utf-8"),
                         f"{digest}  {archive.name}\n")

    def test_content_identity_is_stable_but_zip_hash_includes_metadata(self):
        source = self.src / "top.gbr"
        os.utime(source, (1609459200, 1609459200))
        first = self.root / "first"
        a = self.package(first)
        self.assertEqual(a.returncode, 0, a.stderr)
        os.utime(source, (1640995200, 1640995200))
        second = self.root / "second"
        b = self.package(second)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual((first / "SHA256-files.json").read_bytes(),
                         (second / "SHA256-files.json").read_bytes())
        self.assertNotEqual(json.loads(a.stdout)["sha256"], json.loads(b.stdout)["sha256"])

    def test_output_inside_source_is_rejected_without_modifying_source(self):
        for out in (self.src, self.src / "dist"):
            with self.subTest(out=out):
                result = self.package(out)
                self.assertEqual(result.returncode, 2)
                self.assertIn("outside --src", result.stderr)
        self.assertFalse((self.src / "dist").exists())
        self.assertFalse((self.src / "SHA256-files.json").exists())

    def test_missing_source_is_rejected(self):
        self.src = self.root / "missing"
        out = self.root / "dist"
        result = self.package(out)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
