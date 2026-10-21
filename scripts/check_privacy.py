"""Scan tracked files (and members of tracked zip files) for personal-data patterns.

Usage:
  python -I scripts/check_privacy.py              # scan git-tracked files of this repo
  python -I scripts/check_privacy.py FILE ...     # scan only these files

Patterns come from scripts/privacy-patterns.txt (one regular expression per line,
case-insensitive). Matches that fall entirely inside an allowed token, such as the
environment variable name %LOCALAPPDATA%, are ignored. PNG, PDF and other binary files
cannot be scanned this way; they are listed so a person opens and checks them.

This does not replace checking your own name, account, mailbox and customer code by hand.

Exit codes: 0 no matches, 1 matches printed, 2 error.
Standard library only. Read-only.
"""
import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ROOT / "scripts" / "privacy-patterns.txt"
SKIP = {"scripts/privacy-patterns.txt"}
ALLOWED_TOKENS = ["%LOCALAPPDATA%"]
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".webp"}


def load_patterns(path=PATTERNS):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [re.compile(line, re.IGNORECASE) for line in lines if line.strip() and not line.startswith("#")]


def allowed(line, start, end):
    for token in ALLOWED_TOKENS:
        for m in re.finditer(re.escape(token), line, re.IGNORECASE):
            if m.start() <= start and end <= m.end():
                return True
    return False


def scan_text(name, text, patterns):
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            for m in pat.finditer(line):
                if not allowed(line, m.start(), m.end()):
                    hits.append(f"{name}:{no}: {pat.pattern!r} matched {m.group(0)!r}")
    return hits


def scan_file(rel, data, patterns, unscanned):
    suffix = Path(rel).suffix.lower()
    if suffix in BINARY:
        unscanned.append(rel)
        return []
    if suffix == ".zip":
        hits = []
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as z:
            for member in z.namelist():
                if member.endswith("/"):
                    continue
                hits += scan_file(f"{rel}!{member}", z.read(member), patterns, unscanned)
        return hits
    return scan_text(rel, data.decode("utf-8", errors="replace"), patterns)


def tracked_files():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan for personal-data patterns (read-only).",
                                 epilog="Exit codes: 0 clean, 1 matches, 2 error.")
    ap.add_argument("files", nargs="*", help="files to scan (default: all git-tracked files)")
    args = ap.parse_args(argv)
    try:
        patterns = load_patterns()
        files = args.files or tracked_files()
        hits, unscanned = [], []
        for rel in files:
            rel = rel.replace("\\", "/")
            if rel in SKIP:
                continue
            path = Path(rel) if args.files else ROOT / rel
            hits += scan_file(rel, path.read_bytes(), patterns, unscanned)
    except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile, re.error) as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return 2
    for hit in hits:
        print(hit)
    if unscanned:
        print(f"not scanned (open and check by hand): {', '.join(unscanned)}")
    print(f"files {len(files)}, matches {len(hits)}: {'CLEAN' if not hits else 'MATCHES FOUND'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
