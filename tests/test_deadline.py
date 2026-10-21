"""Deadline arithmetic for the jlc-support skill script."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "jlc-support" / "scripts" / "deadline.py"


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True)


class DeadlineTests(unittest.TestCase):
    def test_72_hours_across_days_with_utc(self):
        r = run("--received", "2026-09-29 16:02", "--tz", "+08:00", "--hours", "72",
                "--now", "2026-09-30 10:00")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("2026-10-02 16:02 Fri (UTC+08:00)", r.stdout)
        self.assertIn("2026-10-02 08:02 Fri (UTC)", r.stdout)
        self.assertIn("2 d 6 h 2 min", r.stdout)

    def test_offset_in_received_and_extra_zone(self):
        r = run("--received", "2026-09-29T23:30+08:00", "--hours", "48", "--show-tz=-07:00",
                "--now", "2026-09-29T23:30+08:00")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("2026-10-01 23:30 Thu (UTC+08:00)", r.stdout)
        self.assertIn("2026-10-01 08:30 Thu (UTC-07:00)", r.stdout)

    def test_expired_exit_code(self):
        r = run("--received", "2026-09-29 16:02", "--tz", "UTC", "--hours", "1",
                "--now", "2026-09-29 18:00")
        self.assertEqual(r.returncode, 1)
        self.assertIn("EXPIRED", r.stdout)
        self.assertIn("0 h 58 min", r.stdout)

    def test_missing_zone_is_error(self):
        r = run("--received", "2026-09-29 16:02", "--hours", "72")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no offset", r.stdout)

    def test_bad_zone_is_error(self):
        r = run("--received", "2026-09-29 16:02", "--tz", "Mars/Olympus", "--hours", "72")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown time zone", r.stdout)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "deadline.json"
            r = run("--received", "2026-09-29 16:02", "--tz", "+0800", "--hours", "72",
                    "--now", "2026-09-29 16:02", "--json", str(out))
            self.assertEqual(r.returncode, 0, r.stdout)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["deadline_utc_iso"], "2026-10-02T08:02:00+00:00")
            self.assertFalse(data["expired"])

    def test_help(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Exit codes", r.stdout)


if __name__ == "__main__":
    unittest.main()
