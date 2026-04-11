#!/usr/bin/env python3
"""Fetch https://heyvid.ai/sitemap.xml and print unique route prefixes (for parity checks)."""

from __future__ import annotations

import re
import sys
from urllib.request import Request, urlopen

LOCALES = frozenset(
    {"es", "fr", "pt", "it", "ja", "th", "pl", "ko", "de", "ru", "da", "nb", "nl", "id", "tr", "zh", "zh-Hant"}
)


def main() -> None:
    req = Request("https://heyvid.ai/sitemap.xml", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=60) as resp:
        xml = resp.read().decode("utf-8", "replace")
    locs = re.findall(r"<loc>(https://heyvid\.ai[^<]*)</loc>", xml)

    en: set[str] = set()
    per_locale: dict[str, set[str]] = {}

    for raw in locs:
        p = raw.replace("https://heyvid.ai", "").strip()
        if not p or p == "/":
            en.add("/")
            continue
        p = p.rstrip("/")
        segs = [s for s in p.split("/") if s]
        if not segs:
            en.add("/")
            continue
        if segs[0] in LOCALES:
            loc = segs[0]
            rest = "/".join(segs[1:]) if len(segs) > 1 else ""
            per_locale.setdefault(loc, set()).add(rest or "/")
        else:
            en.add("/" + "/".join(segs))

    print("english", len(en))
    for s in sorted(en):
        print(" ", s)
    print("locales", len(per_locale))
    for loc in sorted(per_locale.keys()):
        n = len(per_locale[loc])
        same = n == len(en) if en else False
        print(f"  {loc}: {n} paths" + (" (matches EN count)" if same else ""))


if __name__ == "__main__":
    main()
