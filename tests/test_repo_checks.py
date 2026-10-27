"""Privacy scan and skill lint used by CI. The repository itself must pass both."""

from pathlib import Path
import json
import os
import re
import shutil
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
        skill = self.make_skill("good-skill", "'Use when testing; it''s fine.'")
        self.assertEqual(check_skills.check_skill(skill, []), [])

    def test_problems_are_reported(self):
        skill = self.make_skill("Bad_Skill", "12 34", yaml=False,
                                body="Run `python scripts/missing.py`.\n")
        problems = "\n".join(check_skills.check_skill(skill, []))
        self.assertIn("lowercase", problems)
        self.assertIn("English trigger text", problems)
        self.assertIn("openai.yaml missing", problems)
        self.assertIn("scripts/missing.py", problems)

    def test_broken_link_is_found(self):
        doc = self.root / "doc.md"
        (self.root / "here.md").write_text("x", encoding="utf-8")
        doc.write_text("[ok](here.md#part) [web](https://example.com) [tpl](<path>)\n"
                       "[bad](gone.md)\n```\n[in code](ignored.md)\n```\n", encoding="utf-8")
        self.assertEqual(check_skills.check_links(doc, "doc.md"), ["doc.md: broken link gone.md"])


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("one", "two"):
            (self.root / "skills" / name).mkdir(parents=True)
            (self.root / "skills" / name / "SKILL.md").write_text("x", encoding="utf-8")
        (self.root / ".claude-plugin").mkdir()

    def write(self, plugins):
        (self.root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "m", "owner": {"name": "o"}, "plugins": plugins}), encoding="utf-8")
        return check_skills.check_marketplace(self.root, ["one", "two"])

    def entry(self, name, skills, source="./", version="0.1.0"):
        return {"name": name, "source": source, "skills": skills, "version": version}

    def test_one_plugin_per_skill_passes(self):
        self.assertEqual(self.write([self.entry("one", ["./skills/one"]),
                                     self.entry("two", ["./skills/two"])]), [])

    def test_missing_skill_duplicate_and_root_with_two_skills(self):
        problems = "\n".join(self.write([self.entry("one", ["./skills/one", "./skills/two"]),
                                         self.entry("one", ["./skills/gone"], version="")]))
        self.assertIn("duplicate plugin name one", problems)
        self.assertIn("must list exactly one skill", problems)
        self.assertIn("./skills/gone, which has no SKILL.md", problems)
        self.assertIn("one has no version", problems)

    def test_skill_without_entry(self):
        problems = self.write([self.entry("one", ["./skills/one"])])
        self.assertEqual(problems, ["marketplace: skill two is listed 0 times (want 1)"])

    def test_plugin_json_must_match(self):
        guard = self.root / "plugins" / "guard"
        (guard / ".claude-plugin").mkdir(parents=True)
        (guard / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "other", "version": "9"}), encoding="utf-8")
        problems = "\n".join(self.write([self.entry("one", ["./skills/one"]),
                                         self.entry("two", ["./skills/two"]),
                                         {"name": "guard", "source": "./plugins/guard", "version": "0.1.0"}]))
        self.assertIn("differs from plugin.json name", problems)
        self.assertIn("version differs from plugin.json", problems)


def find_bash():
    """Git Bash on Windows; plain PATH lookup can hit the WSL launcher in System32."""
    if sys.platform == "win32":
        for var in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(var)
            if not base:
                continue
            cand = Path(base) / "Git" / "bin" / "bash.exe"
            if cand.is_file():
                return str(cand)
        return None
    return shutil.which("bash")


class SendGuardTests(unittest.TestCase):
    HOOKS = ROOT / "plugins" / "jlc-send-guard" / "hooks" / "hooks.json"

    def setUp(self):
        entry = json.loads(self.HOOKS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]
        self.matcher = re.compile(entry["matcher"])
        self.command = entry["hooks"][0]["command"]

    def test_send_tools_are_matched(self):
        for name in ("mcp__claude_ai_Gmail__send_message", "mcp__claude_ai_Gmail__reply",
                     "mcp__claude_ai_Gmail__forward", "mcp__gmail__gmail_send_email",
                     "mcp__plugin_x_gmail__send_draft"):
            self.assertTrue(self.matcher.search(name), name)

    def test_read_and_draft_tools_are_not_matched(self):
        for name in ("mcp__claude_ai_Gmail__create_draft", "mcp__claude_ai_Gmail__search_threads",
                     "mcp__claude_ai_Gmail__get_thread", "mcp__slack__send_message",
                     "mcp__claude-in-chrome__computer", "Bash"):
            self.assertFalse(self.matcher.search(name), name)

    def test_command_prints_an_ask_decision(self):
        bash = find_bash()
        if bash is None:
            self.skipTest("Git Bash not found")
        r = subprocess.run([bash, "-c", self.command], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main()
