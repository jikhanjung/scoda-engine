#!/usr/bin/env python3
"""
Manifest Validator / Linter for .scoda packages — CLI wrapper.

Validation logic lives in scoda_engine_core.validate_manifest.

Usage:
  python scripts/validate_manifest.py trilobase.db
  python scripts/validate_manifest.py paleocore.db
  # exit code 0: no errors (warnings only), exit code 1: errors found
"""

import sys

from scoda_engine_core import validate_manifest, validate_db


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_manifest.py <db_path>", file=sys.stderr)
        sys.exit(2)

    db_path = sys.argv[1]
    errors, warnings = validate_db(db_path)

    for w in warnings:
        print(f"  WARNING: {w}")
    for e in errors:
        print(f"  ERROR: {e}")

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"\nOK — {len(warnings)} warning(s), 0 errors")
        sys.exit(0)


if __name__ == '__main__':
    main()
