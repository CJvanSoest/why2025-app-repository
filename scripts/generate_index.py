#!/usr/bin/env python3
"""Generate index.json at the repo root: the single manifest the badge polls.

The badge fetches this one file (raw.githubusercontent.com, public repo, no auth)
instead of a multi-endpoint REST API. Each entry carries the app's metadata plus a
direct raw download URL for its ELF, so the updater can compare versions and pull
the binary in one pass.

Run from the repo root: python3 scripts/generate_index.py
"""
import json
import os
import sys

OWNER = "CJvanSoest"
REPO = "why2025-app-repository"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}"

IGNORE_DIRS = {".git", ".github", "scripts"}


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    apps = []
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not os.path.isdir(full) or name in IGNORE_DIRS or name.startswith("."):
            continue
        meta_path = os.path.join(full, f"{name}.json")
        if not os.path.isfile(meta_path):
            print(f"warning: skipping {name} (no {name}.json)", file=sys.stderr)
            continue
        with open(meta_path) as f:
            meta = json.load(f)

        uid = meta["unique_identifier"]
        binary_path = meta["binary_path"]
        apps.append(
            {
                "unique_identifier": uid,
                "name": meta.get("name", uid),
                "author": meta.get("author", ""),
                "version": meta.get("version"),
                "interpreter": meta.get("interpreter", ""),
                "metadata_file": meta.get("metadata_file", ""),
                "binary_path": binary_path,
                "source": meta.get("source", 1),
                # Direct, auth-free download URLs (public repo).
                "metadata_url": f"{RAW_BASE}/{uid}/{uid}.json",
                "download_url": f"{RAW_BASE}/{uid}/{binary_path}",
            }
        )

    index = {
        "schema_version": 1,
        "repository": f"{OWNER}/{REPO}",
        "app_count": len(apps),
        "apps": apps,
    }

    out_path = os.path.join(root, "index.json")
    with open(out_path, "w") as f:
        json.dump(index, f, indent=2)
        f.write("\n")

    print(f"Wrote {out_path} with {len(apps)} app(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
