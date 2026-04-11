#!/usr/bin/env python3
"""Compare heyvid.ai (EN) sitemap slugs with site/routes.yaml — exit 0 if aligned."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "site" / "routes.yaml"

LOCALES = frozenset(
    {"es", "fr", "pt", "it", "ja", "th", "pl", "ko", "de", "ru", "da", "nb", "nl", "id", "tr", "zh", "zh-Hant"}
)


def heyvid_en_slugs() -> set[str]:
    req = Request("https://heyvid.ai/sitemap.xml", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        xml = resp.read().decode("utf-8", "replace")
    locs = re.findall(r"<loc>(https://heyvid\.ai[^<]*)</loc>", xml)
    out: set[str] = set()
    for raw in locs:
        p = raw.replace("https://heyvid.ai", "").strip().rstrip("/")
        if not p:
            continue
        segs = [s for s in p.split("/") if s]
        if segs[0] in LOCALES:
            continue
        out.add(segs[0])
    return out


def our_slugs(data: dict) -> set[str]:
    pages = set(data.get("pages") or {})
    skip = set(data.get("skip_slugs") or [])
    return pages | skip


def main() -> int:
    data = yaml.safe_load(ROUTES.read_text(encoding="utf-8"))
    ref = heyvid_en_slugs()
    ours = our_slugs(data)
    missing = ref - ours
    extra = ours - ref
    if missing or extra:
        print("Parity check FAILED")
        if missing:
            print("  In heyvid EN sitemap, not in routes.yaml (+ skip_slugs):", sorted(missing))
        if extra:
            print("  In routes.yaml/skip, not in heyvid EN first-segment set:", sorted(extra))
        return 1
    print("Parity OK: EN slug set matches heyvid sitemap (first path segment).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
