"""Privacy scan and skill lint used by CI. The repository itself must pass both."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_privacy  # noqa: E402
import check_skills  # noqa: E402


# Built from pieces so this file does not trip the scan it tests.
EMAIL = "someone" + "@" + "example.com"
USER_PATH = "C:/" + "Users" + "/someone/x"
APP_DATA = "App" + "Data"


def run(script, *args):
    return subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / script), *args],
                          capture_output=True, text=True, encoding="utf-8")


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_repository_is_clean(self):
        r = run("check_privacy.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_email_and_user_path_are_found(self):
        f = self.root / "note.md"
        f.write_text(f"contact {EMAIL}\n{USER_PATH}\n", encoding="utf-8")
        r = run("check_privacy.py", str(f))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(EMAIL, r.stdout)
        self.assertIn(":2:", r.stdout)

    def test_allowed_env_var_name_is_ignored(self):
        f = self.root / "note.md"
        f.write_text("writes to `%LOCALAPPDATA%` are redirected\n", encoding="utf-8")
        self.assertEqual(run("check_privacy.py", str(f)).returncode, 0)
        f.write_text(f"C:/x/{APP_DATA}/Local\n", encoding="utf-8")
        self.assertEqual(run("check_privacy.py", str(f)).returncode, 1)

    def test_zip_members_are_scanned(self):
        z = self.root / "gerbers.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("board-F_Cu.gbr", f"G04 made by {EMAIL}*\n")
        r = run("check_privacy.py", str(z))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("gerbers.zip!board-F_Cu.gbr", r.stdout)


class SkillLintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_skill(self, name, description, yaml=True, body=""):
        skill = self.root / name
        (skill / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# x\n{body}", encoding="utf-8")
        if yaml:
            (skill / "agents" / "openai.yaml").write_text(
                f'interface:\n  default_prompt: "Use ${name} now."\n', encoding="utf-8")
        return skill

    def test_repository_passes(self):
        r = run("check_skills.py")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_good_skill(self):
        skill = self.make_skill("good-skill", "'中文觸發詞。Use when testing; it''s fine.'")
        self.assertEqual(check_skills.check_skill(skill, []), [])

    def test_problems_are_reported(self):
        skill = self.make_skill("Bad_Skill", "English only", yaml=False,
                                body="Run `python scripts/missing.py`.\n")
        problems = "\n".join(check_skills.check_skill(skill, []))
        self.assertIn("lowercase", problems)
        self.assertIn("Chinese and English", problems)
        self.assertIn("openai.yaml missing", problems)
        self.assertIn("scripts/missing.py", problems)

    def test_broken_link_is_found(self):
        doc = self.root / "doc.md"
        (self.root / "here.md").write_text("x", encoding="utf-8")
        doc.write_text("[ok](here.md#part) [web](https://example.com) [tpl](<path>)\n"
                       "[bad](gone.md)\n```\n[in code](ignored.md)\n```\n", encoding="utf-8")
        self.assertEqual(check_skills.check_links(doc, "doc.md"), ["doc.md: broken link gone.md"])


if __name__ == "__main__":
    unittest.main()
