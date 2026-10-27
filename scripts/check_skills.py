"""Lint the skills and Markdown links of this repo.

Usage:
  python -I scripts/check_skills.py

Checks, for every skills/<name>/:
  - SKILL.md has frontmatter with name (= folder name, lowercase-hyphen) and description
  - description is at most 1024 characters and has English trigger text
  - agents/openai.yaml exists and its default_prompt mentions $<name>
  - every `scripts/<file>` named in SKILL.md exists in that skill (or a sibling skill)
And for .claude-plugin/marketplace.json: every skill has exactly one plugin entry that
lists only that skill, entry names are unique and carry a version, every path exists, and a
plugin with its own plugin.json has the same name and version.
And for every git-tracked .md file: relative links point to files that exist
(placeholder links such as <path> in templates are skipped).

Exit codes: 0 PASS, 1 problems printed, 2 error.
Standard library only. Read-only.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SCRIPT_RE = re.compile(r"`(?:[^`]*?\s)?(scripts/[\w.-]+\.(?:py|mjs|txt))")
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
    if desc and not LATIN_RE.search(desc):
        problems.append(f"{name}: description needs English trigger text")
    yaml = skill / "agents" / "openai.yaml"
    if not yaml.is_file():
        problems.append(f"{name}: agents/openai.yaml missing")
    elif f"${name}" not in yaml.read_text(encoding="utf-8"):
        problems.append(f"{name}: agents/openai.yaml default_prompt does not mention ${name}")
    for ref in sorted(set(SCRIPT_RE.findall(text))):
        if not any((s / ref).is_file() for s in [skill, *siblings]):
            problems.append(f"{name}: SKILL.md names {ref}, which does not exist")
    return problems


def check_marketplace(root, skill_names):
    problems = []
    path = root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        return ["marketplace.json missing"]
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("plugins", [])
    names = [e.get("name") for e in entries]
    for name in sorted({n for n in names if names.count(n) > 1}):
        problems.append(f"marketplace: duplicate plugin name {name}")
    covered = []
    for e in entries:
        name, source = e.get("name"), e.get("source", "")
        if not e.get("version"):
            problems.append(f"marketplace: {name} has no version")
        if not isinstance(source, str) or not source.startswith("./") or ".." in source:
            problems.append(f"marketplace: {name} source must be a ./ path inside the repo")
            continue
        plugin_root = root / source
        if not plugin_root.is_dir():
            problems.append(f"marketplace: {name} source {source} does not exist")
            continue
        for skill in e.get("skills", []):
            if not (plugin_root / skill / "SKILL.md").is_file():
                problems.append(f"marketplace: {name} lists {skill}, which has no SKILL.md")
            covered.append(Path(skill).name)
        if source in ("./", ".") and len(e.get("skills", [])) != 1:
            problems.append(f"marketplace: {name} uses the repo root and must list exactly one skill")
        manifest = plugin_root / ".claude-plugin" / "plugin.json"
        if manifest.is_file():
            m = json.loads(manifest.read_text(encoding="utf-8"))
            if m.get("name") != name:
                problems.append(f"marketplace: {name} differs from plugin.json name {m.get('name')!r}")
            if e.get("version") and m.get("version") != e.get("version"):
                problems.append(f"marketplace: {name} version differs from plugin.json")
        hooks = plugin_root / "hooks" / "hooks.json"
        if hooks.is_file() and "hooks" not in json.loads(hooks.read_text(encoding="utf-8")):
            problems.append(f"marketplace: {name} hooks/hooks.json needs a top-level \"hooks\" key")
    for skill in skill_names:
        if covered.count(skill) != 1:
            problems.append(f"marketplace: skill {skill} is listed {covered.count(skill)} times (want 1)")
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
        problems += check_marketplace(ROOT, [s.name for s in skills])
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
                             capture_output=True, check=True)
        docs = [p for p in out.stdout.decode("utf-8").split("\0") if p]
        for rel in docs:
            if (ROOT / rel).is_file():
                problems += check_links(ROOT / rel, rel)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return 2
    for p in problems:
        print(p)
    print(f"skills {len(skills)}, markdown files {len(docs)}, problems {len(problems)}: "
          f"{'PASS' if not problems else 'FAIL'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
