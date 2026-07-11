#!/usr/bin/env python3
"""Validate the WHY2025 app-repository layout.

For every app directory (one per unique_identifier at the repo root) this checks:
  - <uid>/<uid>.json exists and is valid JSON,
  - it contains every required manifest field with the right type,
  - the directory name matches the manifest's unique_identifier,
  - the referenced binary (binary_path) exists inside the app dir and is a
    real ELF (0x7f 'E' 'L' 'F' magic),
  - 'name' (and 'description', if present) is ASCII/Latin text only.

The English-text rule is enforced as an ASCII-charset check, not real
language detection - it blocks non-Latin scripts (CJK, Cyrillic, Arabic,
emoji spam) reliably, but it cannot tell English from e.g. Dutch since both
use the same character set. Good enough as a first filter; a human reviewer
still reads the PR.

Exit code is non-zero if any app fails, so CI can gate merges on it.
Run from the repo root: python3 scripts/validate.py
"""
import json
import os
import re
import sys

# Reuse the exact app manifest schema used by every WHY app (apps/<name>/manifest.json).
REQUIRED_FIELDS = {
    "unique_identifier": str,
    "name": str,
    "author": str,
    "version": (str, int),  # cj_hello ships version 1 (int); most ship "x.y.z"
    "interpreter": str,
    "metadata_file": str,
    "binary_path": str,
    "source": int,
}

# Fields that, if present, must be ASCII/Latin text (see module docstring for
# what this rule does and does not guarantee).
TEXT_FIELDS = ("name", "description")
ASCII_TEXT_RE = re.compile(r"^[A-Za-z0-9 _\-.,!?()'\"/:&+#]*$")

# Directories that are not apps.
IGNORE_DIRS = {".git", ".github", "scripts"}


def fail(app, msg):
    print(f"::error::[{app}] {msg}")
    return False


def validate_app(app_dir):
    app = os.path.basename(app_dir.rstrip("/"))
    ok = True

    meta_path = os.path.join(app_dir, f"{app}.json")
    if not os.path.isfile(meta_path):
        return fail(app, f"missing metadata file {app}.json")

    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except json.JSONDecodeError as e:
        return fail(app, f"invalid JSON in {app}.json: {e}")

    for field, ftype in REQUIRED_FIELDS.items():
        if field not in meta:
            ok = fail(app, f"missing required field '{field}'")
            continue
        if not isinstance(meta[field], ftype):
            ok = fail(app, f"field '{field}' has wrong type (got {type(meta[field]).__name__})")

    uid = meta.get("unique_identifier")
    if uid is not None and uid != app:
        ok = fail(app, f"unique_identifier '{uid}' does not match directory name '{app}'")

    for field in TEXT_FIELDS:
        value = meta.get(field)
        if isinstance(value, str) and value and not ASCII_TEXT_RE.match(value):
            ok = fail(
                app,
                f"field '{field}' contains non-Latin characters ('{value}') - "
                "store text must be English/ASCII",
            )

    binary_path = meta.get("binary_path")
    if isinstance(binary_path, str) and binary_path:
        bin_full = os.path.join(app_dir, binary_path)
        if not os.path.isfile(bin_full):
            ok = fail(app, f"binary '{binary_path}' referenced by manifest does not exist")
        else:
            with open(bin_full, "rb") as f:
                magic = f.read(4)
            if magic != b"\x7fELF":
                ok = fail(app, f"binary '{binary_path}' is not a valid ELF (magic={magic!r})")

    if ok:
        print(f"[{app}] OK (v{meta.get('version')})")
    return ok


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_ok = True
    found = 0
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not os.path.isdir(full) or name in IGNORE_DIRS or name.startswith("."):
            continue
        found += 1
        if not validate_app(full):
            all_ok = False

    if found == 0:
        print("::error::no app directories found")
        return 1

    print(f"\nValidated {found} app(s): {'ALL OK' if all_ok else 'FAILURES PRESENT'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
