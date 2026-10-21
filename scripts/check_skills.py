"""Lint the skills and Markdown links of this repo.

Usage:
  python -I scripts/check_skills.py

Checks, for every skills/<name>/:
  - SKILL.md has frontmatter with name (= folder name, lowercase-hyphen) and description
  - description is at most 1024 characters and has both Chinese and English trigger text
  - agents/openai.yaml exists and its default_prompt mentions $<name>
  - every `scripts/<file>` named in SKILL.md exists in that skill (or a sibling skill)
And for every git-tracked .md file: relative links point to files that exist
(placeholder links such as <path> in templates are skipped).

Exit codes: 0 PASS, 1 problems printed, 2 error.
Standard library only. Read-only.
"""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SCRIPT_RE = re.compile(r"`(?:[^`]*?\s)?(scripts/[\w.-]+\.(?:py|mjs|txt))")
CJK_RE = re.compile(r"[一-鿿]")
LATIN_RE = re.compile(r"[A-Za-z]{3,}")


def frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return None
    fields = {}
    for line in lines[1:lines[1:].index("---") + 1]:
        key, sep, value = line.partition(":")
        if sep and key and not key.startswith(" "):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] == "'":
                value = value[1:-1].replace("''", "'")
            elif len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            fields[key.strip()] = value
    return fields


def check_skill(skill, siblings):
    problems = []
    name = skill.name
    skill_md = skill / "SKILL.md"
    if not skill_md.is_file():
        return [f"{name}: SKILL.md missing"]
    text = skill_md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return [f"{name}: SKILL.md has no frontmatter"]
    if fm.get("name") != name:
        problems.append(f"{name}: frontmatter name {fm.get('name')!r} differs from folder name")
    if not NAME_RE.match(name):
        problems.append(f"{name}: folder name must be lowercase words joined by hyphens")
    desc = fm.get("description", "")
    if not desc:
        problems.append(f"{name}: description missing")
    elif len(desc) > 1024:
        problems.append(f"{name}: description is {len(desc)} characters (max 1024)")
    if desc and not (CJK_RE.search(desc) and LATIN_RE.search(desc)):
        problems.append(f"{name}: description needs both Chinese and English trigger text")
    yaml = skill / "agents" / "openai.yaml"
    if not yaml.is_file():
        problems.append(f"{name}: agents/openai.yaml missing")
    elif f"${name}" not in yaml.read_text(encoding="utf-8"):
        problems.append(f"{name}: agents/openai.yaml default_prompt does not mention ${name}")
    for ref in sorted(set(SCRIPT_RE.findall(text))):
        if not any((s / ref).is_file() for s in [skill, *siblings]):
            problems.append(f"{name}: SKILL.md names {ref}, which does not exist")
    return problems


def check_links(path, rel):
    problems = []
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for target in LINK_RE.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith(("#", "<")):
            continue
        file_part = unquote(target.split("#", 1)[0])
        if file_part and not (path.parent / file_part).exists():
            problems.append(f"{rel}: broken link {target}")
    return problems


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    try:
        skills = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
        problems = []
        for skill in skills:
            problems += check_skill(skill, [s for s in skills if s != skill])
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
                             capture_output=True, check=True)
        docs = [p for p in out.stdout.decode("utf-8").split("\0") if p]
        for rel in docs:
            if (ROOT / rel).is_file():
                problems += check_links(ROOT / rel, rel)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return 2
    for p in problems:
        print(p)
    print(f"skills {len(skills)}, markdown files {len(docs)}, problems {len(problems)}: "
          f"{'PASS' if not problems else 'FAIL'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
