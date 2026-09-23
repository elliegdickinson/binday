#!/usr/bin/env python3
"""Regenerate app/data/councils.json from UKBinCollectionData's input.json.

Run this after bumping uk_bin_collection in requirements.txt.

    python3 tools/build_registry.py [path/to/UKBinCollectionData]

With no path it fetches input.json from GitHub. Councils needing a headless
browser are excluded - this build has no Chrome.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.request

UPSTREAM = ("https://raw.githubusercontent.com/robbrad/UKBinCollectionData/"
            "master/uk_bin_collection/tests/input.json")
FIELDS = ("postcode", "house_number", "uprn", "paon", "usrn")
OUT = pathlib.Path(__file__).resolve().parent.parent / "app" / "data" / "councils.json"

# Councils upstream marks as needing a headless browser, but which this app
# collects natively over plain HTTP (see app/pickers/). They are kept in the
# registry despite the web_driver flag.
NATIVE = {"StaffordshireMoorlandsDistrictCouncil", "HighPeakCouncil"}


def load(source: str | None) -> dict:
    if source:
        path = pathlib.Path(source)
        if path.is_dir():
            path = path / "uk_bin_collection" / "tests" / "input.json"
        return json.loads(path.read_text())
    with urllib.request.urlopen(UPSTREAM, timeout=60) as response:
        return json.loads(response.read())


def main() -> None:
    src = load(sys.argv[1] if len(sys.argv) > 1 else None)
    out = {}
    for key, cfg in src.items():
        if cfg.get("web_driver") and key not in NATIVE:
            continue
        out[key] = {
            "name": cfg.get("wiki_name") or re.sub(r"(?<!^)(?=[A-Z])", " ", key),
            "url": cfg.get("url", ""),
            "needs": [f for f in FIELDS if cfg.get(f)],
            # ONS local-authority-district code, used to match the council that
            # postcodes.io reports for a postcode.
            "lad": cfg.get("LAD24CD", ""),
            "note": cfg.get("wiki_note", ""),
        }

    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    lad = sum(1 for v in out.values() if v["lad"])
    bare = sum(1 for v in out.values() if not v["needs"])
    uprn = sum(1 for v in out.values() if "uprn" in v["needs"])
    print(f"{len(out)} councils written to {OUT.relative_to(OUT.parents[2])}")
    print(f"  with an LAD code (auto-detectable from postcode): {lad}")
    print(f"  need a uprn:                 {uprn}")
    print(f"  no identifying input at all: {bare}  (unsupported without a picker)")
    print(f"  excluded (headless browser): {len(src) - len(out)}")
    print(f"  re-included via a native collector: {len(NATIVE)}")


if __name__ == "__main__":
    main()
