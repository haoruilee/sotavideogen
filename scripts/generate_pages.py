#!/usr/bin/env python3
"""Generate static HTML from site/routes.yaml + Jinja2 templates."""

from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
ROUTES_FILE = ROOT / "site" / "routes.yaml"
TEMPLATES_DIR = ROOT / "site" / "templates"


def load_routes() -> dict:
    with ROUTES_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def page_path(prefix: str, slug: str) -> str:
    slug = slug.strip("/")
    if prefix:
        return f"/{prefix}/{slug}/"
    return f"/{slug}/"


def root_path(prefix: str) -> str:
    return f"/{prefix}/" if prefix else "/"


def slug_output_parts(prefix: str, slug: str) -> tuple[str, ...]:
    if prefix:
        return (prefix, slug)
    return (slug,)


def write_html(path_parts: tuple[str, ...], html: str) -> None:
    out_dir = PUBLIC.joinpath(*path_parts)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def tool_slugs(pages: dict) -> list[str]:
    return sorted(s for s, m in pages.items() if m.get("kind") == "studio")


def all_slugs(data: dict) -> list[str]:
    skip = set(data.get("skip_slugs") or [])
    return sorted(s for s in (data.get("pages") or {}) if s not in skip)


def collect_urls(data: dict) -> list[str]:
    pages = data["pages"]
    skip = set(data.get("skip_slugs") or [])
    locales = tuple(data.get("locales") or ())
    extra = list((data.get("sitemap") or {}).get("extra_paths") or [])

    urls: list[str] = list(extra)
    for slug in sorted(pages.keys()):
        if slug in skip:
            continue
        urls.append(page_path("", slug))
    for loc in locales:
        urls.append(root_path(loc))
        urls.append(page_path(loc, "blog"))
        for slug in sorted(pages.keys()):
            if slug in skip:
                continue
            urls.append(page_path(loc, slug))
    return urls


def write_sitemap(data: dict) -> None:
    base = (data.get("sitemap") or {}).get("base_url", "https://example.com").rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    seen: set[str] = set()
    for u in collect_urls(data):
        if u.endswith(".html"):
            loc = base + u
        else:
            loc = base + (u if u.endswith("/") else u + "/")
        if loc in seen:
            continue
        seen.add(loc)
        prio = "1.0" if loc == base + "/" else "0.8"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append(f"    <priority>{prio}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (PUBLIC / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"
    (PUBLIC / "robots.txt").write_text(robots, encoding="utf-8")


def build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_page(env: Environment, template_name: str, context: dict) -> str:
    return env.get_template(template_name).render(**context)


def main() -> None:
    data = load_routes()
    pages: dict = data["pages"]
    skip = set(data.get("skip_slugs") or [])
    locales = tuple(data.get("locales") or ())
    html_lang_map: dict = dict(data.get("html_lang") or {})
    locale_labels: dict = dict(data.get("locale_labels") or {})

    env = build_env()
    count = 0

    for prefix in ("", *locales):
        html_lang = html_lang_map.get(prefix, "zh-Hans")

        if prefix:
            label = locale_labels.get(prefix, prefix)
            title = f"{label} · 入口"
            desc = f"语言前缀路由 /{prefix}/ 的演示首页（sota video gen）。工具与定价链接保持在该前缀下。"
            html = render_page(
                env,
                "locale_home.html",
                {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "locale": prefix,
                    "nav_active": "home",
                },
            )
            write_html((prefix,), html)
            count += 1

            blog_title = f"博客 · {label}"
            blog_desc = f"博客路由 /{prefix}/blog/（演示）。正文仓库默认维护在 /blog/。"
            html = render_page(
                env,
                "locale_blog.html",
                {
                    "title": blog_title,
                    "description": blog_desc,
                    "desc": blog_desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "locale_label": label,
                    "nav_active": "blog",
                },
            )
            write_html((prefix, "blog"), html)
            count += 1

        for slug, meta in pages.items():
            if slug in skip:
                continue

            kind = meta["kind"]
            title = meta["title"]
            desc = meta["desc"]

            if kind == "studio":
                nav_active = "tools"
                template = "studio.html"
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "nav_active": nav_active,
                    "page_path": page_path(prefix, slug),
                    "mode": meta.get("mode", "video"),
                }
            elif kind == "marketing":
                nav_active = "pricing" if slug == "pricing" else "home"
                template = "marketing.html"
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "nav_active": nav_active,
                    "page_path": page_path(prefix, slug),
                }
            elif kind == "hub":
                tool_items = []
                for s in tool_slugs(pages):
                    m = pages[s]
                    tool_items.append(
                        {
                            "href": page_path(prefix, s),
                            "title": m["title"],
                            "desc": m["desc"],
                        }
                    )
                template = "hub.html"
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "nav_active": "tools",
                    "tool_items": tool_items,
                }
            elif kind == "category":
                template = "category.html"
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "nav_active": "tools",
                    "category": meta.get("cat", "video"),
                }
            else:
                raise SystemExit(f"Unknown kind for {slug}: {kind}")

            html = render_page(env, template, ctx)
            write_html(slug_output_parts(prefix, slug), html)
            count += 1

    write_sitemap(data)
    print(f"Wrote {count} generated pages under public/ (+ sitemap). Locales: {len(locales)}.")


if __name__ == "__main__":
    main()
