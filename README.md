# Sota Video Gen（sota video gen）

原创静态营销站与应用入口演示，仓库内文件位于 `public/`。

## 本地预览

```bash
cd public && python3 -m http.server 8080
```

浏览器访问 `http://127.0.0.1:8080/`。请勿直接双击打开 HTML（绝对路径 `/css/...` 需要 HTTP 根路径）。

## 生成工具路由页面

- **路由与文案**：编辑 `site/routes.yaml`（每个 slug 的 `kind`、`title`、`desc`、`mode`，以及 `locales` 列表）。**新增模型落地页**只需加一段 `pages` 配置并重新生成，详见 [`site/ADDING_MODELS.md`](site/ADDING_MODELS.md)。
- **版式与组件**：编辑 `site/templates/`（Jinja2：`base.html`、各页面模板、`partials/`）。
- **营销首页**：由 `site/templates/home.html` 生成 `public/index.html`（与工具页共享 `base`、canonical、hreflang、OG）。
- **全局 SEO**：`site.site`（`name`、`home_title`、`contact_email`、`og_image` 等）与 `sitemap.base_url` 写入 `<head>` 与 JSON-LD。

首次安装依赖后生成静态页：

```bash
pip install -r requirements.txt
python3 scripts/generate_pages.py
```

会更新 `public/sitemap.xml` 与 `public/robots.txt`（默认域名占位在 `site/routes.yaml` 的 `sitemap.base_url`）。同时生成 **17 个语言前缀** 下的同款路由，以及各 `/locale/` 首页与 `/locale/blog/` 镜像页。`public/index.html` 与 `public/blog/` 下已有手工页面不会被覆盖。

核对参考站 sitemap 中的路径集合（只读）：

```bash
python3 scripts/fetch_sitemap_routes.py
```

校验英文根路径 slug 是否与 heyvid sitemap 一致（CI 可跑）：

```bash
python3 scripts/verify_sitemap_parity.py
```

### GitHub Pages（Actions 部署）

仓库已包含 [`.github/workflows/pages.yml`](.github/workflows/pages.yml)：推送到 **`main`** 时用 `SITE_BASE_URL=https://<owner>.github.io/<repo>/` 生成站点并部署到 Pages（**项目页**带 `/repo/` 前缀，站内链接与静态资源已对齐）。

- **Settings → Pages**：Source 选 **GitHub Actions**。  
- 若使用 **`username.github.io`** 用户主页（站点在根路径、无 `/repo/`），请改工作流里的 `SITE_BASE_URL` 为 `https://<username>.github.io/` 或去掉路径段。

### aiping.cn API 冒烟（GitHub Actions）

仓库 Secret：`AIPING_TOKEN`。工作流 [`.github/workflows/aiping-api-smoke.yml`](.github/workflows/aiping-api-smoke.yml) 会执行 [`scripts/aiping_api_smoke.sh`](scripts/aiping_api_smoke.sh)（POST 创建任务 + 轮询 GET），**日志中不会打印 Token**。  
合并到默认分支后可在 **Actions** 里手动 **Run workflow**，或修改相关文件触发推送。本地未设置 `AIPING_TOKEN` 时脚本会直接跳过（exit 0）。

## 上线前

- 将 `public/sitemap.xml` 与 `public/robots.txt` 中的 `https://example.com` 换成你的正式域名。
- 子域（如 `app.`、`blog.`、`docs.`）可通过 CDN/反向代理映射到 `public/app/`、`public/blog/`、`public/docs/` 等路径；详见 `public/docs/`。

## 说明

本站为独立设计与文案，**不**复制或镜像第三方网站（包括 heyvid.ai）。若需「同类」产品站，请在此基础上替换为你的品牌素材、定价与法务文本。
