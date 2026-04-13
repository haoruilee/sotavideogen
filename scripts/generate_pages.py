#!/usr/bin/env python3
"""Generate static HTML from site/routes.yaml + Jinja2 templates."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
ROUTES_FILE = ROOT / "site" / "routes.yaml"
TEMPLATES_DIR = ROOT / "site" / "templates"


def load_routes() -> dict:
    with ROUTES_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_base_url_override(data: dict) -> None:
    """CI: SITE_BASE_URL=https://owner.github.io/repo/ overrides sitemap.base_url for this run."""
    o = os.environ.get("SITE_BASE_URL", "").strip()
    if not o:
        return
    data.setdefault("sitemap", {})
    data["sitemap"]["base_url"] = o.rstrip("/")


def parse_site_base(base_url: str) -> tuple[str, str]:
    """Return (origin without path, base_path like '' or '/repo')."""
    raw = (base_url or "https://example.com").strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    p = urlparse(raw)
    scheme = p.scheme or "https"
    netloc = p.netloc or "example.com"
    origin = f"{scheme}://{netloc}".rstrip("/")
    path = p.path or "/"
    if path in ("/", ""):
        base_path = ""
    else:
        base_path = path.rstrip("/") or ""
    return origin, base_path


class PathCtx:
    """Relative URL prefixes for GitHub Pages project sites (base_path=/repo)."""

    __slots__ = ("base_path",)

    def __init__(self, base_path: str) -> None:
        self.base_path = (base_path or "").rstrip("/")

    def root(self, prefix: str) -> str:
        if prefix:
            core = f"/{prefix}/"
        else:
            core = "/"
        return f"{self.base_path}{core}" if self.base_path else core

    def page(self, prefix: str, slug: str) -> str:
        slug = slug.strip("/")
        if prefix:
            core = f"/{prefix}/{slug}/"
        else:
            core = f"/{slug}/"
        return f"{self.base_path}{core}" if self.base_path else core

    def static_file(self, rel: str) -> str:
        rel = rel.lstrip("/")
        return f"{self.base_path}/{rel}" if self.base_path else f"/{rel}"


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


def mode_to_hub_section(mode: str) -> str:
    """Map studio form mode → hub section id (see site/routes.yaml hub.sections)."""
    if mode == "music":
        return "audio"
    if mode == "model":
        return "models"
    if mode in (
        "video",
        "image_to_video",
        "video_rewrite",
        "reference_video",
        "transition",
        "effects",
        "motion",
        "avatar",
        "lip",
    ):
        return "video"
    if mode in ("image", "image_edit", "photo"):
        return "image"
    if mode in ("tts", "voice", "denoise"):
        return "audio"
    return "video"


def studio_hub_section(meta: dict, mode: str) -> str:
    override = meta.get("hub_section")
    if override:
        return str(override)
    return mode_to_hub_section(mode)


def category_items_for(
    pages: dict, *, prefix: str, cat: str, paths: PathCtx
) -> list[dict[str, str]]:
    """Studio slugs listed on ai-video-generator / ai-image-generator (subset of hub, not 1:1)."""
    out: list[dict[str, str]] = []
    for s in tool_slugs(pages):
        meta = pages[s]
        mode = meta.get("mode", "video")
        explicit = meta.get("category")
        if explicit is not None:
            if explicit == cat:
                out.append({"href": paths.page(prefix, s), "title": meta["title"]})
            continue
        if cat == "image":
            if mode in ("image", "image_edit", "photo"):
                out.append({"href": paths.page(prefix, s), "title": meta["title"]})
        else:
            if mode in (
                "video",
                "image_to_video",
                "video_rewrite",
                "reference_video",
                "transition",
                "effects",
                "motion",
                "avatar",
            ):
                out.append({"href": paths.page(prefix, s), "title": meta["title"]})
    out.sort(key=lambda x: x["title"])
    return out


def build_hub_sections(
    data: dict, pages: dict, *, prefix: str, paths: PathCtx
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Sectioned links for /ai-tools/ + flat tool_items for the wide card."""
    hub_cfg = data.get("hub") or {}
    section_defs = list(hub_cfg.get("sections") or [])
    if not section_defs:
        section_defs = [
            {"id": "video", "title": "视频", "show_path": False},
            {"id": "image", "title": "图像", "show_path": False},
            {"id": "audio", "title": "音频 / 口型", "show_path": False},
            {"id": "models", "title": "模型路线（演示）", "show_path": True},
        ]

    by_id: dict[str, list[dict[str, Any]]] = {s["id"]: [] for s in section_defs}
    tool_items: list[dict[str, str]] = []

    for s in tool_slugs(pages):
        meta = pages[s]
        mode = meta.get("mode", "video")
        sec = studio_hub_section(meta, mode)
        by_id.setdefault(sec, [])
        href = paths.page(prefix, s)
        entry = {
            "href": href,
            "title": meta["title"],
            "show_path": sec == "models",
        }
        by_id[sec].append(entry)
        tool_items.append({"href": href, "title": meta["title"], "desc": meta["desc"]})

    known_ids = {s["id"] for s in section_defs}
    extra_ids = sorted(k for k in by_id if k not in known_ids)

    sections_out: list[dict[str, Any]] = []
    for sec in section_defs:
        sid = sec["id"]
        links = sorted(by_id.get(sid, []), key=lambda x: x["title"])
        if not links:
            continue
        sections_out.append(
            {
                "id": sid,
                "title": sec.get("title", sid),
                "show_path": bool(sec.get("show_path", False)),
                "links": links,
            }
        )
    for eid in extra_ids:
        links = sorted(by_id[eid], key=lambda x: x["title"])
        if not links:
            continue
        sections_out.append(
            {
                "id": eid,
                "title": eid,
                "show_path": eid == "models",
                "links": links,
            }
        )

    tool_items.sort(key=lambda x: x["title"])
    return sections_out, tool_items


def all_slugs(data: dict) -> list[str]:
    skip = set(data.get("skip_slugs") or [])
    return sorted(s for s in (data.get("pages") or {}) if s not in skip)


def hreflang_alternates(
    *,
    origin: str,
    paths: PathCtx,
    slug: str | None,
    locales: tuple[str, ...],
    html_lang_map: dict[str, str],
) -> list[dict[str, str]]:
    """hreflang alternates for a logical page (same slug under each locale)."""
    alts: list[dict[str, str]] = []
    if slug is None:
        return alts

    def pfx(loc: str) -> str:
        return paths.page(loc, slug)

    alts.append({"hreflang": "x-default", "href": abs_url(origin, pfx(""))})

    seen_lang: set[str] = set()
    for loc in locales:
        code = html_lang_map.get(loc, loc)
        if code == "zh-Hans" and "zh" in locales and loc != "zh":
            continue
        if code in seen_lang:
            continue
        seen_lang.add(code)
        alts.append({"hreflang": code, "href": abs_url(origin, pfx(loc))})

    if "zh-Hans" not in seen_lang:
        alts.append({"hreflang": "zh-Hans", "href": abs_url(origin, pfx(""))})
        seen_lang.add("zh-Hans")

    return alts


def hreflang_locale_roots(
    *, origin: str, paths: PathCtx, locales: tuple[str, ...], html_lang_map: dict[str, str]
) -> list[dict[str, str]]:
    alts = [{"hreflang": "x-default", "href": abs_url(origin, paths.root(""))}]
    seen_lang: set[str] = set()
    for loc in locales:
        code = html_lang_map.get(loc, loc)
        if code == "zh-Hans" and "zh" in locales and loc != "zh":
            continue
        if code in seen_lang:
            continue
        seen_lang.add(code)
        alts.append({"hreflang": code, "href": abs_url(origin, paths.root(loc))})
    if "zh-Hans" not in seen_lang:
        alts.append({"hreflang": "zh-Hans", "href": abs_url(origin, paths.root(""))})
    return alts


def hreflang_locale_blogs(
    *,
    origin: str,
    paths: PathCtx,
    locales: tuple[str, ...],
    html_lang_map: dict[str, str],
) -> list[dict[str, str]]:
    alts = [{"hreflang": "x-default", "href": abs_url(origin, paths.page("", "blog"))}]
    seen_lang: set[str] = set()
    for loc in locales:
        code = html_lang_map.get(loc, loc)
        if code == "zh-Hans" and "zh" in locales and loc != "zh":
            continue
        if code in seen_lang:
            continue
        seen_lang.add(code)
        alts.append({"hreflang": code, "href": abs_url(origin, paths.page(loc, "blog"))})
    if "zh-Hans" not in seen_lang:
        alts.append({"hreflang": "zh-Hans", "href": abs_url(origin, paths.page("", "blog"))})
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


def json_ld_org_and_website(site: dict, *, site_root: str) -> str:
    base = site_root.rstrip("/")
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
    gen = data.get("_gen") or {}
    base = gen.get("site_root") or (data.get("sitemap") or {}).get("base_url", "https://example.com").rstrip("/")
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
    origin: str,
    title: str,
    description: str,
    canonical_rel: str,
    hreflang: list[dict[str, str]],
    og_type: str = "website",
    json_ld: str | None = None,
    head_display_title: str | None = None,
    base_path: str = "",
) -> dict[str, Any]:
    site = merge_site_dict(data)
    canonical_url = abs_url(origin, canonical_rel)
    return {
        "site": site,
        "canonical_url": canonical_url,
        "hreflang_alternates": hreflang,
        "og_type": og_type,
        "json_ld": json_ld,
        "abs_base": origin,
        "base_path": base_path,
        "head_display_title": head_display_title,
    }


def with_site_path(url_path: str, paths: PathCtx) -> str:
    """Prefix extra_paths with base_path for GitHub project pages."""
    if url_path == "/":
        return paths.root("")
    if paths.base_path:
        return paths.base_path + (url_path if url_path.startswith("/") else "/" + url_path)
    return url_path if url_path.startswith("/") else "/" + url_path


def collect_urls(data: dict, paths: PathCtx) -> list[str]:
    pages = data["pages"]
    skip = set(data.get("skip_slugs") or [])
    locales = tuple(data.get("locales") or ())
    raw_extra = list((data.get("sitemap") or {}).get("extra_paths") or [])
    extra = [with_site_path(p, paths) for p in raw_extra]

    urls: list[str] = list(extra)
    for slug in sorted(pages.keys()):
        if slug in skip:
            continue
        urls.append(paths.page("", slug))
    for loc in locales:
        urls.append(paths.root(loc))
        urls.append(paths.page(loc, "blog"))
        for slug in sorted(pages.keys()):
            if slug in skip:
                continue
            urls.append(paths.page(loc, slug))
    return urls


def write_sitemap(data: dict, paths: PathCtx, origin: str) -> None:
    base = origin.rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    seen: set[str] = set()
    for u in collect_urls(data, paths):
        if u.endswith(".html"):
            loc = base + u
        else:
            loc = base + (u if u.endswith("/") else u + "/")
        if loc in seen:
            continue
        seen.add(loc)
        home_path = paths.root("")
        prio = "1.0" if loc.rstrip("/") == (base + home_path).rstrip("/") else "0.8"
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
    apply_base_url_override(data)
    raw_base = (data.get("sitemap") or {}).get("base_url", "https://example.com")
    origin, base_path = parse_site_base(raw_base)
    site_root = origin + base_path if base_path else origin
    paths = PathCtx(base_path)
    data["_gen"] = {"site_root": site_root, "origin": origin, "base_path": base_path}

    pages: dict = data["pages"]
    skip = set(data.get("skip_slugs") or [])
    locales = tuple(data.get("locales") or ())
    html_lang_map: dict = dict(data.get("html_lang") or {})
    locale_labels: dict = dict(data.get("locale_labels") or {})
    site = merge_site_dict(data)
    bp = base_path

    env = build_env()
    count = 0

    for prefix in ("", *locales):
        html_lang = html_lang_map.get(prefix, "zh-Hans")

        if prefix:
            label = locale_labels.get(prefix, prefix)
            title = f"{label} · 入口"
            desc = f"语言前缀路由 /{prefix}/ 的演示首页（sota video gen）。工具与定价链接保持在该前缀下。"
            canonical_rel = paths.root(prefix)
            ld = json_ld_webpage(
                site, name=title, description=desc, url=abs_url(origin, canonical_rel)
            )
            hlang = hreflang_locale_roots(
                origin=origin, paths=paths, locales=locales, html_lang_map=html_lang_map
            )
            seo = seo_head_context(
                data,
                origin=origin,
                title=title,
                description=desc,
                canonical_rel=canonical_rel,
                hreflang=hlang,
                json_ld=ld,
                base_path=bp,
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
            canonical_blog = paths.page(prefix, "blog")
            ld_blog = json_ld_webpage(
                site, name=blog_title, description=blog_desc, url=abs_url(origin, canonical_blog)
            )
            hlang_blog = hreflang_locale_blogs(
                origin=origin, paths=paths, locales=locales, html_lang_map=html_lang_map
            )
            seo_blog = seo_head_context(
                data,
                origin=origin,
                title=blog_title,
                description=blog_desc,
                canonical_rel=canonical_blog,
                hreflang=hlang_blog,
                json_ld=ld_blog,
                base_path=bp,
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
            canonical_rel = paths.page(prefix, slug)

            if kind == "studio":
                nav_active = "tools"
                template = "studio.html"
                ld = json_ld_webpage(
                    site, name=title, description=desc, url=abs_url(origin, canonical_rel)
                )
                hlang = hreflang_alternates(
                    origin=origin,
                    paths=paths,
                    slug=slug,
                    locales=locales,
                    html_lang_map=html_lang_map,
                )
                seo = seo_head_context(
                    data,
                    origin=origin,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    og_type="website",
                    json_ld=ld,
                    base_path=bp,
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
                    site, name=title, description=desc, url=abs_url(origin, canonical_rel)
                )
                hlang = hreflang_alternates(
                    origin=origin,
                    paths=paths,
                    slug=slug,
                    locales=locales,
                    html_lang_map=html_lang_map,
                )
                seo = seo_head_context(
                    data,
                    origin=origin,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    json_ld=ld,
                    base_path=bp,
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
                hub_sections, tool_items = build_hub_sections(data, pages, prefix=prefix, paths=paths)
                template = "hub.html"
                ld = json_ld_software(site, url=abs_url(origin, canonical_rel))
                hlang = hreflang_alternates(
                    origin=origin,
                    paths=paths,
                    slug="ai-tools",
                    locales=locales,
                    html_lang_map=html_lang_map,
                )
                seo = seo_head_context(
                    data,
                    origin=origin,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    json_ld=ld,
                    base_path=bp,
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
                    "hub_sections": hub_sections,
                    "tool_items": tool_items,
                    **seo,
                }
            elif kind == "category":
                cat = meta.get("cat", "video")
                cat_items = category_items_for(pages, prefix=prefix, cat=cat, paths=paths)
                template = "category.html"
                ld = json_ld_webpage(
                    site, name=title, description=desc, url=abs_url(origin, canonical_rel)
                )
                hlang = hreflang_alternates(
                    origin=origin,
                    paths=paths,
                    slug=slug,
                    locales=locales,
                    html_lang_map=html_lang_map,
                )
                seo = seo_head_context(
                    data,
                    origin=origin,
                    title=title,
                    description=desc,
                    canonical_rel=canonical_rel,
                    hreflang=hlang,
                    json_ld=ld,
                    base_path=bp,
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
                    "category_items": cat_items,
                    **seo,
                }
            else:
                raise SystemExit(f"Unknown kind for {slug}: {kind}")

            html = render_page(env, template, ctx)
            write_html(slug_output_parts(prefix, slug), html)
            count += 1

    home_title_full = site.get("home_title", f"{site['name']} — AI 视频与图像创作工作台")
    home_desc = site.get("home_description", site.get("tagline", ""))
    home_canonical = paths.root("")
    hlang_home = hreflang_locale_roots(
        origin=origin, paths=paths, locales=locales, html_lang_map=html_lang_map
    )
    ld_home = json_ld_org_and_website(site, site_root=site_root)
    seo_home = seo_head_context(
        data,
        origin=origin,
        title=site["name"],
        description=home_desc,
        canonical_rel=home_canonical,
        hreflang=hlang_home,
        json_ld=ld_home,
        head_display_title=home_title_full,
        base_path=bp,
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

    # Hand-style pages: same shell as generated pages, correct base_path links
    app_desc = "Sota Video Gen 应用入口（演示）。"
    ld_app = json_ld_webpage(
        site, name="应用", description=app_desc, url=abs_url(origin, paths.page("", "app"))
    )
    h_app = hreflang_alternates(
        origin=origin, paths=paths, slug="app", locales=locales, html_lang_map=html_lang_map
    )
    seo_app = seo_head_context(
        data,
        origin=origin,
        title="应用",
        description=app_desc,
        canonical_rel=paths.page("", "app"),
        hreflang=h_app,
        json_ld=ld_app,
        base_path=bp,
    )
    html_app = render_page(
        env,
        "app.html",
        {
            "title": "应用",
            "description": app_desc,
            "html_lang": html_lang_map.get("", "zh-Hans"),
            "prefix": "",
            "locales": locales,
            "locale_labels": locale_labels,
            "switcher_slug": "app",
            "nav_active": "app",
            **seo_app,
        },
    )
    write_html(("app",), html_app)
    count += 1

    blog_list_desc = "Sota Video Gen 博客：产品与 AI 创作实践。品牌词：sota video gen。"
    ld_blog_root = json_ld_webpage(
        site, name="博客", description=blog_list_desc, url=abs_url(origin, paths.page("", "blog"))
    )
    h_blog_root = hreflang_locale_blogs(
        origin=origin, paths=paths, locales=locales, html_lang_map=html_lang_map
    )
    seo_blog_root = seo_head_context(
        data,
        origin=origin,
        title="博客",
        description=blog_list_desc,
        canonical_rel=paths.page("", "blog"),
        hreflang=h_blog_root,
        json_ld=ld_blog_root,
        base_path=bp,
    )
    html_blog = render_page(
        env,
        "blog_index.html",
        {
            "title": "博客",
            "description": blog_list_desc,
            "html_lang": html_lang_map.get("", "zh-Hans"),
            "prefix": "",
            "locales": locales,
            "locale_labels": locale_labels,
            "switcher_slug": None,
            "switcher": "blog",
            "nav_active": "blog",
            **seo_blog_root,
        },
    )
    write_html(("blog",), html_blog)
    count += 1

    post_desc = "Sota Video Gen 入门文章（演示）。sota video gen。"
    post_canonical = paths.static_file("blog/getting-started.html")
    ld_post = json_ld_webpage(
        site,
        name="五分钟了解工作流",
        description=post_desc,
        url=abs_url(origin, post_canonical),
    )
    seo_post = seo_head_context(
        data,
        origin=origin,
        title="五分钟了解工作流",
        description=post_desc,
        canonical_rel=post_canonical,
        hreflang=[],
        json_ld=ld_post,
        base_path=bp,
    )
    html_post = render_page(
        env,
        "blog_post.html",
        {
            "title": "五分钟了解工作流",
            "description": post_desc,
            "html_lang": html_lang_map.get("", "zh-Hans"),
            "prefix": "",
            "locales": locales,
            "locale_labels": locale_labels,
            "nav_active": "blog",
            **seo_post,
        },
    )
    PUBLIC.joinpath("blog", "getting-started.html").parent.mkdir(parents=True, exist_ok=True)
    PUBLIC.joinpath("blog", "getting-started.html").write_text(html_post, encoding="utf-8")
    count += 1

    docs_desc = "Sota Video Gen 部署与子域配置文档。sota video gen。"
    ld_docs = json_ld_webpage(
        site, name="文档", description=docs_desc, url=abs_url(origin, paths.page("", "docs"))
    )
    h_docs = hreflang_alternates(
        origin=origin, paths=paths, slug="docs", locales=locales, html_lang_map=html_lang_map
    )
    seo_docs = seo_head_context(
        data,
        origin=origin,
        title="文档",
        description=docs_desc,
        canonical_rel=paths.page("", "docs"),
        hreflang=h_docs,
        json_ld=ld_docs,
        base_path=bp,
    )
    html_docs = render_page(
        env,
        "docs.html",
        {
            "title": "文档",
            "description": docs_desc,
            "html_lang": html_lang_map.get("", "zh-Hans"),
            "prefix": "",
            "locales": locales,
            "locale_labels": locale_labels,
            "switcher_slug": "docs",
            "nav_active": "docs",
            **seo_docs,
        },
    )
    write_html(("docs",), html_docs)
    count += 1

    write_sitemap(data, paths, origin)
    (PUBLIC / ".nojekyll").touch(exist_ok=True)
    print(f"Wrote {count} generated pages under public/ (+ sitemap). Locales: {len(locales)}.")


if __name__ == "__main__":
    main()
