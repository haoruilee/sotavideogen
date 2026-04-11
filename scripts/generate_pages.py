#!/usr/bin/env python3
"""Generate static HTML from site/routes.yaml + Jinja2 templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def abs_url(base: str, path: str) -> str:
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def tool_slugs(pages: dict) -> list[str]:
    return sorted(s for s, m in pages.items() if m.get("kind") == "studio")


def all_slugs(data: dict) -> list[str]:
    skip = set(data.get("skip_slugs") or [])
    return sorted(s for s in (data.get("pages") or {}) if s not in skip)


def hreflang_alternates(
    *,
    base: str,
    slug: str | None,
    locales: tuple[str, ...],
    html_lang_map: dict[str, str],
) -> list[dict[str, str]]:
    """hreflang alternates for a logical page (same slug under each locale)."""
    alts: list[dict[str, str]] = []
    if slug is None:
        return alts

    def pfx(loc: str) -> str:
        return page_path(loc, slug)

    alts.append({"hreflang": "x-default", "href": abs_url(base, pfx(""))})

    seen_lang: set[str] = set()
    for loc in locales:
        code = html_lang_map.get(loc, loc)
        if code == "zh-Hans" and "zh" in locales and loc != "zh":
            continue
        if code in seen_lang:
            continue
        seen_lang.add(code)
        alts.append({"hreflang": code, "href": abs_url(base, pfx(loc))})

    if "zh-Hans" not in seen_lang:
        alts.append({"hreflang": "zh-Hans", "href": abs_url(base, pfx(""))})
        seen_lang.add("zh-Hans")

    return alts


def hreflang_locale_roots(*, base: str, locales: tuple[str, ...], html_lang_map: dict[str, str]) -> list[dict[str, str]]:
    alts = [{"hreflang": "x-default", "href": abs_url(base, "/")}]
    seen_lang: set[str] = set()
    for loc in locales:
        code = html_lang_map.get(loc, loc)
        if code == "zh-Hans" and "zh" in locales and loc != "zh":
            continue
        if code in seen_lang:
            continue
        seen_lang.add(code)
        alts.append({"hreflang": code, "href": abs_url(base, root_path(loc))})
    if "zh-Hans" not in seen_lang:
        alts.append({"hreflang": "zh-Hans", "href": abs_url(base, "/")})
    return alts


def hreflang_locale_blogs(
    *, base: str, locales: tuple[str, ...], html_lang_map: dict[str, str]
) -> list[dict[str, str]]:
    alts = [{"hreflang": "x-default", "href": abs_url(base, "/blog/")}]
    seen_lang: set[str] = set()
    for loc in locales:
        code = html_lang_map.get(loc, loc)
        if code == "zh-Hans" and "zh" in locales and loc != "zh":
            continue
        if code in seen_lang:
            continue
        seen_lang.add(code)
        alts.append({"hreflang": code, "href": abs_url(base, page_path(loc, "blog"))})
    if "zh-Hans" not in seen_lang:
        alts.append({"hreflang": "zh-Hans", "href": abs_url(base, "/blog/")})
    return alts


def json_ld_webpage(site: dict, *, name: str, description: str, url: str) -> str:
    doc = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": name,
        "description": description,
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": site.get("name", "Sota Video Gen"), "url": site.get("url", url)},
    }
    return json.dumps(doc, ensure_ascii=False)


def json_ld_org_and_website(site: dict, *, base: str) -> str:
    org_id = f"{base}/#organization"
    org: dict[str, Any] = {
        "@type": "Organization",
        "@id": org_id,
        "name": site.get("legal_name", site.get("name")),
        "url": base + "/",
    }
    if site.get("contact_email"):
        org["email"] = site["contact_email"]
    web = {
        "@type": "WebSite",
        "@id": f"{base}/#website",
        "name": site.get("name"),
        "url": base + "/",
        "description": site.get("home_description", site.get("tagline", "")),
        "publisher": {"@id": org_id},
    }
    graph = [org, web]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def json_ld_software(site: dict, *, url: str) -> str:
    doc = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": site.get("name", "Sota Video Gen"),
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Web",
        "url": url,
        "description": site.get("tagline", "AI video and image creation workspace."),
    }
    if site.get("contact_email"):
        doc["provider"] = {
            "@type": "Organization",
            "name": site.get("legal_name", site.get("name")),
            "email": site["contact_email"],
        }
    return json.dumps(doc, ensure_ascii=False)


def merge_site_dict(data: dict) -> dict[str, Any]:
    site = dict(data.get("site") or {})
    base = (data.get("sitemap") or {}).get("base_url", "https://example.com").rstrip("/")
    site.setdefault("name", "Sota Video Gen")
    site.setdefault("legal_name", site["name"])
    site.setdefault("brand_keywords", "sota video gen")
    site.setdefault("twitter_site", "")
    site.setdefault("contact_email", "")
    site.setdefault("og_image", "")
    site.setdefault("tagline", "AI 视频与图像创作工作台。")
    site.setdefault(
        "home_title",
        f"{site['name']} — AI 视频与图像创作工作台",
    )
    site.setdefault("home_description", site["tagline"])
    site["url"] = base + "/"
    return site


def seo_head_context(
    data: dict,
    *,
    title: str,
    description: str,
    canonical_rel: str,
    hreflang: list[dict[str, str]],
    og_type: str = "website",
    json_ld: str | None = None,
    head_display_title: str | None = None,
) -> dict[str, Any]:
    base = (data.get("sitemap") or {}).get("base_url", "https://example.com").rstrip("/")
    site = merge_site_dict(data)
    canonical_url = abs_url(base, canonical_rel)
    return {
        "site": site,
        "canonical_url": canonical_url,
        "hreflang_alternates": hreflang,
        "og_type": og_type,
        "json_ld": json_ld,
        "abs_base": base,
        "head_display_title": head_display_title,
    }


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
    site = merge_site_dict(data)
    base = (data.get("sitemap") or {}).get("base_url", "https://example.com").rstrip("/")

    env = build_env()
    count = 0

    for prefix in ("", *locales):
        html_lang = html_lang_map.get(prefix, "zh-Hans")

        if prefix:
            label = locale_labels.get(prefix, prefix)
            title = f"{label} · 入口"
            desc = f"语言前缀路由 /{prefix}/ 的演示首页（sota video gen）。工具与定价链接保持在该前缀下。"
            canonical_rel = root_path(prefix)
            ld = json_ld_webpage(
                site, name=title, description=desc, url=abs_url(base, canonical_rel)
            )
            hlang = hreflang_locale_roots(base=base, locales=locales, html_lang_map=html_lang_map)
            seo = seo_head_context(
                data,
                title=title,
                description=desc,
                canonical_rel=canonical_rel,
                hreflang=hlang,
                json_ld=ld,
            )
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
                    "locales": locales,
                    "locale_labels": locale_labels,
                    "switcher_slug": None,
                    "switcher": "home",
                    "nav_active": "home",
                    **seo,
                },
            )
            write_html((prefix,), html)
            count += 1

            blog_title = f"博客 · {label}"
            blog_desc = f"博客路由 /{prefix}/blog/（演示）。正文仓库默认维护在 /blog/。"
            canonical_blog = page_path(prefix, "blog")
            ld_blog = json_ld_webpage(
                site, name=blog_title, description=blog_desc, url=abs_url(base, canonical_blog)
            )
            hlang_blog = hreflang_locale_blogs(base=base, locales=locales, html_lang_map=html_lang_map)
            seo_blog = seo_head_context(
                data,
                title=blog_title,
                description=blog_desc,
                canonical_rel=canonical_blog,
                hreflang=hlang_blog,
                json_ld=ld_blog,
            )
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
                    "locales": locales,
                    "locale_labels": locale_labels,
                    "switcher_slug": None,
                    "switcher": "blog",
                    "nav_active": "blog",
                    **seo_blog,
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
            canonical_rel = page_path(prefix, slug)

            if kind == "studio":
                nav_active = "tools"
                template = "studio.html"
                ld = json_ld_webpage(
                    site, name=title, description=desc, url=abs_url(base, canonical_rel)
                )
                hlang = hreflang_alternates(
                    base=base, slug=slug, locales=locales, html_lang_map=html_lang_map
                )
                seo = seo_head_context(
                    data,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    og_type="website",
                    json_ld=ld,
                )
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "locales": locales,
                    "locale_labels": locale_labels,
                    "switcher_slug": slug,
                    "nav_active": nav_active,
                    "page_path": canonical_rel,
                    "mode": meta.get("mode", "video"),
                    **seo,
                }
            elif kind == "marketing":
                nav_active = "pricing" if slug == "pricing" else "home"
                template = "marketing.html"
                ld = json_ld_webpage(
                    site, name=title, description=desc, url=abs_url(base, canonical_rel)
                )
                hlang = hreflang_alternates(
                    base=base, slug=slug, locales=locales, html_lang_map=html_lang_map
                )
                seo = seo_head_context(
                    data,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    json_ld=ld,
                )
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "locales": locales,
                    "locale_labels": locale_labels,
                    "switcher_slug": slug,
                    "nav_active": nav_active,
                    "page_path": canonical_rel,
                    **seo,
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
                ld = json_ld_software(site, url=abs_url(base, canonical_rel))
                hlang = hreflang_alternates(
                    base=base, slug="ai-tools", locales=locales, html_lang_map=html_lang_map
                )
                seo = seo_head_context(
                    data,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    json_ld=ld,
                )
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "locales": locales,
                    "locale_labels": locale_labels,
                    "switcher_slug": "ai-tools",
                    "nav_active": "tools",
                    "tool_items": tool_items,
                    **seo,
                }
            elif kind == "category":
                template = "category.html"
                ld = json_ld_webpage(
                    site, name=title, description=desc, url=abs_url(base, canonical_rel)
                )
                hlang = hreflang_alternates(
                    base=base, slug=slug, locales=locales, html_lang_map=html_lang_map
                )
                seo = seo_head_context(
                    data,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    json_ld=ld,
                )
                ctx = {
                    "title": title,
                    "description": desc,
                    "desc": desc,
                    "html_lang": html_lang,
                    "prefix": prefix,
                    "locales": locales,
                    "locale_labels": locale_labels,
                    "switcher_slug": slug,
                    "nav_active": "tools",
                    "category": meta.get("cat", "video"),
                    **seo,
                }
            else:
                raise SystemExit(f"Unknown kind for {slug}: {kind}")

            html = render_page(env, template, ctx)
            write_html(slug_output_parts(prefix, slug), html)
            count += 1

    home_title_full = site.get("home_title", f"{site['name']} — AI 视频与图像创作工作台")
    home_desc = site.get("home_description", site.get("tagline", ""))
    hlang_home = hreflang_locale_roots(base=base, locales=locales, html_lang_map=html_lang_map)
    ld_home = json_ld_org_and_website(site, base=base)
    seo_home = seo_head_context(
        data,
        title=site["name"],
        description=home_desc,
        canonical_rel="/",
        hreflang=hlang_home,
        json_ld=ld_home,
        head_display_title=home_title_full,
    )
    html_home = render_page(
        env,
        "home.html",
        {
            "title": site["name"],
            "description": home_desc,
            "html_lang": html_lang_map.get("", "zh-Hans"),
            "prefix": "",
            "locales": locales,
            "locale_labels": locale_labels,
            "switcher_slug": None,
            "switcher": "home",
            "nav_active": "home",
            **seo_home,
        },
    )
    PUBLIC.joinpath("index.html").write_text(html_home, encoding="utf-8")
    count += 1

    write_sitemap(data)
    print(f"Wrote {count} generated pages under public/ (+ sitemap). Locales: {len(locales)}.")


if __name__ == "__main__":
    main()
