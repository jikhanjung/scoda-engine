#!/usr/bin/env python3
"""Bump version in all locations that track it.

Usage:
    python scripts/bump_version.py 0.1.9
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VERSION_FILES = [
    (ROOT / "pyproject.toml", re.compile(r'^(version\s*=\s*")([^"]+)(")', re.MULTILINE)),
    (ROOT / "scoda_engine" / "__init__.py", re.compile(r'^(__version__\s*=\s*")([^"]+)(")', re.MULTILINE)),
    (ROOT / "deploy" / "docker-compose.yml", re.compile(r'(image:\s*honestjung/scoda-server:)([^\s]+)()')),
]


def bump(new_version: str) -> None:
    for path, pattern in VERSION_FILES:
        text = path.read_text(encoding="utf-8")
        m = pattern.search(text)
        if not m:
            print(f"  WARNING: version pattern not found in {path}")
            continue
        old = m.group(2)
        updated = pattern.sub(rf"\g<1>{new_version}\3", text)
        path.write_text(updated, encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}: {old} -> {new_version}")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <new-version>")
        print(f"Example: {sys.argv[0]} 0.1.9")
        sys.exit(1)

    new_version = sys.argv[1].lstrip("v")
    print(f"Bumping version to {new_version}:")
    bump(new_version)
    print("Done.")


if __name__ == "__main__":
    main()
