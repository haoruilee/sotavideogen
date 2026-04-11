#!/usr/bin/env python3
"""Generate static HTML for tool and marketing routes (original copy, path parity with reference sitemap)."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

# Slugs from heyvid.ai sitemap (non-locale), minus pages we maintain by hand.
SKIP_SLUGS = {"blog"}


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# Display titles & descriptions: neutral/original wording (not copying third-party pages).
SLUG_META: dict[str, dict[str, str]] = {
    "about-us": {"title": "关于我们", "desc": "Sota Video Gen 团队与产品方向（演示页）。", "kind": "marketing"},
    "affiliate": {"title": "联盟合作", "desc": "合作伙伴与分佣说明（占位，上线前请法务审核）。", "kind": "marketing"},
    "refer-a-friend": {"title": "邀请好友", "desc": "邀请奖励与规则（占位）。", "kind": "marketing"},
    "pricing": {"title": "定价方案", "desc": "Sota Video Gen 套餐与额度说明（示意）。", "kind": "marketing"},
    "ai-tools": {
        "title": "AI 工具目录",
        "desc": "按任务类型浏览视频、图像与音频工具（静态演示）。",
        "kind": "hub",
    },
    "ai-video-generator": {
        "title": "AI 视频生成",
        "desc": "文本驱动、参考图驱动与视频变换等入口汇总。",
        "kind": "category",
        "cat": "video",
    },
    "ai-image-generator": {
        "title": "AI 图像生成",
        "desc": "文生图、图生图与画面效果工具汇总。",
        "kind": "category",
        "cat": "image",
    },
    "text-to-video": {"title": "文本生成视频", "desc": "用结构化提示词生成短片与分镜预览。", "kind": "studio", "mode": "video"},
    "image-to-video": {"title": "图片生成视频", "desc": "以关键帧或参考图驱动运动与镜头。", "kind": "studio", "mode": "image_to_video"},
    "video-to-video": {"title": "视频到视频", "desc": "在保留结构的前提下重绘风格或替换外观。", "kind": "studio", "mode": "video_rewrite"},
    "reference-to-video": {"title": "参考生成视频", "desc": "多参考拼贴：角色、场景与风格对齐。", "kind": "studio", "mode": "reference_video"},
    "video-transition": {"title": "视频转场", "desc": "两段素材之间的过渡与衔接生成。", "kind": "studio", "mode": "transition"},
    "video-effects": {"title": "视频特效", "desc": "粒子、光效与氛围增强（示意控件）。", "kind": "studio", "mode": "effects"},
    "text-to-image": {"title": "文本生成图片", "desc": "生成概念图、海报与关键帧。", "kind": "studio", "mode": "image"},
    "image-to-image": {"title": "图片到图片", "desc": "在参考图上进行变体、修复与扩展。", "kind": "studio", "mode": "image_edit"},
    "photo-effects": {"title": "照片效果", "desc": "人像润饰与画面质感调整（演示）。", "kind": "studio", "mode": "photo"},
    "text-to-speech": {"title": "文本转语音", "desc": "多语种配音与旁白生成。", "kind": "studio", "mode": "tts"},
    "voice-cloning": {"title": "声音克隆", "desc": "上传样本并生成接近音色（需合规授权）。", "kind": "studio", "mode": "voice"},
    "ai-avatar": {"title": "AI 形象", "desc": "数字人出镜与口型同步前置流程（演示）。", "kind": "studio", "mode": "avatar"},
    "lip-sync": {"title": "口型同步", "desc": "将音频对齐到角色面部动作。", "kind": "studio", "mode": "lip"},
    "motion-control": {"title": "动作控制", "desc": "姿态参考与镜头路径约束。", "kind": "studio", "mode": "motion"},
    "noise-reduction": {"title": "降噪修复", "desc": "清理底噪与齿音，提升口播可用性。", "kind": "studio", "mode": "denoise"},
    # Model / provider-style routes: same URL shape, generic product wording.
    "seedance": {"title": "律动视频", "desc": "舞蹈与肢体语言强调的运动视频工作流（演示路由 /seedance）。", "kind": "studio", "mode": "model"},
    "seedance-2-0": {
        "title": "律动视频 2.0",
        "desc": "改进版运动控制与细节保留（演示路由 /seedance-2-0）。",
        "kind": "studio",
        "mode": "model",
    },
    "hailuo-ai": {"title": "海螺路线", "desc": "高动态场景与卡通渲染风格（演示）。", "kind": "studio", "mode": "model"},
    "kling-2-6": {"title": "可灵路线", "desc": "写实场景与复杂运镜示意（演示）。", "kind": "studio", "mode": "model"},
    "nano-banana": {"title": "轻量趣味模型", "desc": "快速草稿与社交短视频风格。", "kind": "studio", "mode": "model"},
    "pika-ai": {"title": "皮卡车路线", "desc": "强调节奏剪辑与转场模板。", "kind": "studio", "mode": "model"},
    "pixverse-ai": {"title": "像素宇宙路线", "desc": "科幻与像素风画面实验。", "kind": "studio", "mode": "model"},
    "runway": {"title": "跑道级工作流", "desc": "专业时间线与遮罩编辑占位。", "kind": "studio", "mode": "model"},
    "runway-ai": {"title": "跑道级工作流 Pro", "desc": "扩展控件与批量任务队列（示意）。", "kind": "studio", "mode": "model"},
    "sora-2": {"title": "长镜头叙事", "desc": "长时长与复杂因果链提示词（演示）。", "kind": "studio", "mode": "model"},
    "suno": {"title": "配乐生成", "desc": "背景音乐与氛围音效占位。", "kind": "studio", "mode": "music"},
    "veo-3": {"title": "高清写实路线", "desc": "高分辨率与稳定肤色（示意）。", "kind": "studio", "mode": "model"},
    "vidu-ai": {"title": "叙事分镜路线", "desc": "多分镜一致性与对白同步占位。", "kind": "studio", "mode": "model"},
    "wan-ai": {"title": "万用综合模型", "desc": "通用提示词与多比例输出。", "kind": "studio", "mode": "model"},
}


def nav_html(active: str) -> str:
    """active: home | tools | pricing | app | blog | docs"""

    def cur(key: str) -> str:
        return ' aria-current="page"' if active == key else ""

    return dedent(
        f"""
        <nav id="site-nav" class="nav" data-nav aria-label="主导航">
          <a href="/"{cur("home")}>首页</a>
          <a href="/ai-tools/"{cur("tools")}>AI 工具</a>
          <a href="/pricing/"{cur("pricing")}>定价</a>
          <a href="/app/"{cur("app")}>应用</a>
          <a href="/blog/"{cur("blog")}>博客</a>
          <a href="/docs/"{cur("docs")}>文档</a>
          <a class="btn btn-primary" href="/app/">打开工作台</a>
        </nav>
        """
    ).strip()


def header_html(active: str) -> str:
    return dedent(
        f"""
    <header class="site-header">
      <div class="wrap header-inner">
        <a class="brand" href="/">
          <span class="brand-mark" aria-hidden="true">SV</span>
          <span>Sota Video Gen</span>
        </a>
        <button
          type="button"
          class="nav-toggle"
          data-nav-toggle
          aria-expanded="false"
          aria-controls="site-nav"
        >
          菜单
        </button>
        {nav_html(active)}
      </div>
    </header>
    """
    ).strip()


def footer_html() -> str:
    return dedent(
        """
    <footer class="site-footer">
      <div class="wrap footer-grid">
        <div>
          <div class="brand" style="margin-bottom: 0.75rem">
            <span class="brand-mark" aria-hidden="true">SV</span>
            <span>Sota Video Gen</span>
          </div>
          <p style="margin: 0; max-width: 28rem">
            品牌词：<strong>sota video gen</strong>。页面为演示用途，请替换为你的域名、分析与法务文本。
          </p>
        </div>
        <div>
          <h4>产品</h4>
          <ul>
            <li><a href="/ai-tools/">AI 工具</a></li>
            <li><a href="/app/">应用</a></li>
            <li><a href="/pricing/">定价</a></li>
          </ul>
        </div>
        <div>
          <h4>内容</h4>
          <ul>
            <li><a href="/blog/">博客</a></li>
            <li><a href="/docs/">文档</a></li>
          </ul>
        </div>
        <div>
          <h4>公司</h4>
          <ul>
            <li><a href="/about-us/">关于我们</a></li>
            <li><a href="/affiliate/">联盟合作</a></li>
            <li><a href="/refer-a-friend/">邀请好友</a></li>
          </ul>
        </div>
      </div>
      <div class="wrap legal">
        <span>© <span id="y"></span> Sota Video Gen</span>
        <span>独立演示站点</span>
      </div>
    </footer>
    <script>
      document.getElementById("y").textContent = new Date().getFullYear();
    </script>
    <script src="/js/site.js" defer></script>
    """
    ).strip()


def studio_form(mode: str) -> str:
    prompt = """
        <label class="field">
          <span class="field-label">提示词</span>
          <textarea class="input input-textarea" rows="5" placeholder="主体、场景、动作、光线、镜头与节奏…"></textarea>
        </label>
    """
    aspect = """
        <div class="field-row">
          <label class="field">
            <span class="field-label">比例</span>
            <select class="input">
              <option>16:9</option>
              <option>9:16</option>
              <option>1:1</option>
              <option>4:3</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">时长</span>
            <select class="input">
              <option>5 秒</option>
              <option>10 秒</option>
              <option>15 秒</option>
            </select>
          </label>
        </div>
    """
    image_upload = """
        <label class="field">
          <span class="field-label">参考图</span>
          <input class="input" type="file" accept="image/*" />
          <span class="field-hint">静态演示：未实际上传；接入 API 后绑定存储桶。</span>
        </label>
    """
    video_upload = """
        <label class="field">
          <span class="field-label">源视频</span>
          <input class="input" type="file" accept="video/*" />
          <span class="field-hint">演示控件，无后端处理。</span>
        </label>
    """
    audio_upload = """
        <label class="field">
          <span class="field-label">音色样本</span>
          <input class="input" type="file" accept="audio/*" />
          <span class="field-hint">请确保拥有合法授权后再开启克隆。</span>
        </label>
    """
    voice_select = """
        <label class="field">
          <span class="field-label">预设音色</span>
          <select class="input">
            <option>中性 · 旁白</option>
            <option>明亮 · 广告</option>
            <option>低沉 · 纪录</option>
          </select>
        </label>
    """
    strength = """
        <label class="field">
          <span class="field-label">变化强度</span>
          <input class="input" type="range" min="0" max="100" value="45" />
        </label>
    """

    if mode == "video":
        body = prompt + aspect
    elif mode == "image_to_video":
        body = image_upload + prompt + aspect
    elif mode == "video_rewrite":
        body = video_upload + prompt + strength + aspect
    elif mode == "reference_video":
        body = image_upload + prompt + dedent(
            """
            <label class="field">
              <span class="field-label">参考权重</span>
              <input class="input" type="range" min="0" max="100" value="60" />
            </label>
            """
        ) + aspect
    elif mode == "transition":
        body = (
            video_upload
            + dedent(
                """
            <label class="field">
              <span class="field-label">第二段视频</span>
              <input class="input" type="file" accept="video/*" />
            </label>
            """
            )
            + prompt
        )
    elif mode == "effects":
        body = video_upload + prompt
    elif mode == "image":
        body = prompt + aspect
    elif mode == "image_edit":
        body = image_upload + prompt + strength
    elif mode == "photo":
        body = image_upload + strength
    elif mode == "tts":
        body = (
            """
        <label class="field">
          <span class="field-label">脚本</span>
          <textarea class="input input-textarea" rows="6" placeholder="粘贴口播稿，按段落分行…"></textarea>
        </label>
        """
            + voice_select
        )
    elif mode == "voice":
        body = audio_upload + prompt
    elif mode == "avatar":
        body = image_upload + prompt + aspect
    elif mode == "lip":
        body = video_upload + audio_upload
    elif mode == "motion":
        body = image_upload + prompt + aspect
    elif mode == "denoise":
        body = audio_upload
    elif mode == "music":
        body = prompt + dedent(
            """
            <label class="field">
              <span class="field-label">情绪</span>
              <select class="input">
                <option>轻快</option>
                <option>史诗</option>
                <option>氛围</option>
              </select>
            </label>
            """
        )
    elif mode == "model":
        body = prompt + aspect + dedent(
            """
            <label class="field">
              <span class="field-label">细节等级</span>
              <select class="input">
                <option>标准</option>
                <option>高细节</option>
                <option>草稿</option>
              </select>
            </label>
            """
        )
    else:
        body = prompt + aspect

    return dedent(
        f"""
        <form class="tool-form" action="#" method="get" onsubmit="return false;">
          {body}
          <div class="form-actions">
            <button type="button" class="btn btn-primary">加入队列（演示）</button>
            <button type="reset" class="btn btn-ghost">重置</button>
          </div>
          <p class="form-note">此为前端占位：接入后端后把表单提交到你的任务 API。</p>
        </form>
        """
    ).strip()


def studio_sidebar() -> str:
    return dedent(
        """
        <div class="tool-sidebar card">
          <h3>工作流提示</h3>
          <ul class="checklist">
            <li>先写清主体与场景，再补充镜头与节奏。</li>
            <li>同一项目固定调色与字体，减少风格漂移。</li>
            <li>导出前检查分辨率与平台安全区。</li>
          </ul>
          <h3>快捷链接</h3>
          <p class="muted"><a href="/ai-tools/">返回工具目录</a></p>
        </div>
        """
    ).strip()


def page_shell(*, title: str, description: str, active: str, main: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(title)} — Sota Video Gen</title>
    <meta name="description" content="{esc(description)}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="/css/site.css" />
  </head>
  <body>
    <a class="sr-only" href="#main">跳到主要内容</a>
    {header_html(active)}
    <main id="main" class="wrap tool-page">
      {main}
    </main>
    {footer_html()}
  </body>
</html>
"""


def render_studio(slug: str, meta: dict[str, str]) -> str:
    title = meta["title"]
    desc = meta["desc"]
    mode = meta.get("mode", "video")
    path = f"/{slug}/"
    main = dedent(
        f"""
      <div class="page-hero tool-hero">
        <p class="eyebrow">sota video gen · {esc(slug)}</p>
        <h1 class="section-title">{esc(title)}</h1>
        <p class="section-sub">{esc(desc)}</p>
      </div>
      <div class="tool-layout">
        <section class="tool-panel card" aria-label="生成参数">
          {studio_form(mode)}
        </section>
        <aside aria-label="说明">
          {studio_sidebar()}
        </aside>
      </div>
    """
    ).strip()
    return page_shell(title=title, description=desc, active="tools", main=main)


def render_marketing(slug: str, meta: dict[str, str]) -> str:
    title = meta["title"]
    desc = meta["desc"]
    active = "pricing" if slug == "pricing" else "home"
    main = dedent(
        f"""
      <article class="page-hero prose marketing-page">
        <p class="eyebrow">sota video gen</p>
        <h1 class="section-title">{esc(title)}</h1>
        <p>{esc(desc)}</p>
        <p>本页为占位内容，用于匹配路由 <code>/{esc(slug)}/</code>。上线前请替换为正式文案与设计稿。</p>
        <p><a class="btn btn-primary" href="/ai-tools/">浏览 AI 工具</a>
        <a class="btn btn-ghost" href="/app/">打开应用</a></p>
      </article>
    """
    ).strip()
    return page_shell(title=title, description=desc, active=active, main=main)


def tool_slugs() -> list[str]:
    return sorted(k for k, v in SLUG_META.items() if v.get("kind") == "studio")


def render_hub() -> str:
    title = SLUG_META["ai-tools"]["title"]
    desc = SLUG_META["ai-tools"]["desc"]
    items = []
    for s in tool_slugs():
        m = SLUG_META[s]
        items.append(f'<li><a href="/{s}/">{esc(m["title"])}</a> — <span class="muted">{esc(m["desc"])}</span></li>')
    list_html = "\n".join(items)
    main = dedent(
        f"""
      <div class="page-hero">
        <p class="eyebrow">sota video gen</p>
        <h1 class="section-title">{esc(title)}</h1>
        <p class="section-sub">{esc(desc)}</p>
      </div>
      <div class="hub-grid">
        <section class="card hub-card">
          <h2>视频</h2>
          <ul class="hub-list">
            <li><a href="/text-to-video/">文本生成视频</a></li>
            <li><a href="/image-to-video/">图片生成视频</a></li>
            <li><a href="/video-to-video/">视频到视频</a></li>
            <li><a href="/reference-to-video/">参考生成视频</a></li>
            <li><a href="/video-transition/">视频转场</a></li>
            <li><a href="/video-effects/">视频特效</a></li>
          </ul>
        </section>
        <section class="card hub-card">
          <h2>图像</h2>
          <ul class="hub-list">
            <li><a href="/text-to-image/">文本生成图片</a></li>
            <li><a href="/image-to-image/">图片到图片</a></li>
            <li><a href="/photo-effects/">照片效果</a></li>
          </ul>
        </section>
        <section class="card hub-card">
          <h2>音频 / 口型</h2>
          <ul class="hub-list">
            <li><a href="/text-to-speech/">文本转语音</a></li>
            <li><a href="/voice-cloning/">声音克隆</a></li>
            <li><a href="/lip-sync/">口型同步</a></li>
            <li><a href="/noise-reduction/">降噪修复</a></li>
            <li><a href="/suno/">配乐生成</a></li>
          </ul>
        </section>
        <section class="card hub-card">
          <h2>模型路线（演示）</h2>
          <ul class="hub-list">
            <li><a href="/seedance/">律动视频</a> <span class="mono">/seedance</span></li>
            <li><a href="/seedance-2-0/">律动视频 2.0</a> <span class="mono">/seedance-2-0</span></li>
            <li><a href="/kling-2-6/">可灵路线</a></li>
            <li><a href="/hailuo-ai/">海螺路线</a></li>
            <li><a href="/pika-ai/">皮卡车路线</a></li>
            <li><a href="/pixverse-ai/">像素宇宙路线</a></li>
            <li><a href="/runway/">跑道级工作流</a></li>
            <li><a href="/runway-ai/">跑道级工作流 Pro</a></li>
            <li><a href="/sora-2/">长镜头叙事</a></li>
            <li><a href="/veo-3/">高清写实路线</a></li>
            <li><a href="/vidu-ai/">叙事分镜路线</a></li>
            <li><a href="/wan-ai/">万用综合模型</a></li>
            <li><a href="/nano-banana/">轻量趣味模型</a></li>
          </ul>
        </section>
        <section class="card hub-card hub-card-wide">
          <h2>全部工具页（自动生成清单）</h2>
          <ul class="hub-list compact">
            {list_html}
          </ul>
        </section>
      </div>
    """
    ).strip()
    return page_shell(title=title, description=desc, active="tools", main=main)


def render_category(slug: str, meta: dict[str, str]) -> str:
    title = meta["title"]
    desc = meta["desc"]
    cat = meta.get("cat", "video")
    if cat == "video":
        links = """
        <ul class="hub-list">
          <li><a href="/text-to-video/">文本生成视频</a></li>
          <li><a href="/image-to-video/">图片生成视频</a></li>
          <li><a href="/video-to-video/">视频到视频</a></li>
          <li><a href="/reference-to-video/">参考生成视频</a></li>
          <li><a href="/video-transition/">视频转场</a></li>
          <li><a href="/video-effects/">视频特效</a></li>
          <li><a href="/motion-control/">动作控制</a></li>
          <li><a href="/ai-avatar/">AI 形象</a></li>
        </ul>
        """
    else:
        links = """
        <ul class="hub-list">
          <li><a href="/text-to-image/">文本生成图片</a></li>
          <li><a href="/image-to-image/">图片到图片</a></li>
          <li><a href="/photo-effects/">照片效果</a></li>
        </ul>
        """
    main = dedent(
        f"""
      <div class="page-hero">
        <p class="eyebrow">sota video gen</p>
        <h1 class="section-title">{esc(title)}</h1>
        <p class="section-sub">{esc(desc)}</p>
      </div>
      <section class="card hub-card">
        {links}
        <p class="muted" style="margin-top:1rem"><a href="/ai-tools/">返回 AI 工具目录</a></p>
      </section>
    """
    ).strip()
    return page_shell(title=title, description=desc, active="tools", main=main)


def write_page(slug: str, html: str) -> None:
    out_dir = PUBLIC / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def all_routes() -> list[str]:
    return sorted(k for k in SLUG_META.keys() if k not in SKIP_SLUGS)


def write_sitemap(routes: list[str], base: str = "https://example.com") -> None:
    base = base.rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    extra = ["/", "/app/", "/blog/", "/blog/getting-started.html", "/docs/"]
    urls: list[str] = list(extra) + [f"/{r}/" for r in routes]
    seen: set[str] = set()
    for u in urls:
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


def main() -> None:
    for slug, meta in SLUG_META.items():
        if slug in SKIP_SLUGS:
            continue
        kind = meta.get("kind")
        if kind == "studio":
            html = render_studio(slug, meta)
        elif kind == "marketing":
            html = render_marketing(slug, meta)
        elif kind == "hub":
            html = render_hub()
        elif kind == "category":
            html = render_category(slug, meta)
        else:
            raise SystemExit(f"Unknown kind for {slug}: {kind}")
        write_page(slug, html)

    routes = all_routes()
    # Keep blog off generator; still list in sitemap via extra paths in write_sitemap
    write_sitemap(routes)
    print(f"Wrote {len(routes)} route dirs under public/ (+ sitemap).")


if __name__ == "__main__":
    main()
