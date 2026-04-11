# Sota Video Gen（sota video gen）

原创静态营销站与应用入口演示，仓库内文件位于 `public/`。

## 本地预览

```bash
cd public && python3 -m http.server 8080
```

浏览器访问 `http://127.0.0.1:8080/`。请勿直接双击打开 HTML（绝对路径 `/css/...` 需要 HTTP 根路径）。

## 生成工具路由页面

扁平工具路径（如 `/seedance/`、`/seedance-2-0/`、`/text-to-video/` 等）由脚本批量生成：

```bash
python3 scripts/generate_pages.py
```

会更新 `public/sitemap.xml` 与 `public/robots.txt`（域名占位仍为 `https://example.com`）。`public/blog/` 等手工页面不会被脚本覆盖。

## 上线前

- 将 `public/sitemap.xml` 与 `public/robots.txt` 中的 `https://example.com` 换成你的正式域名。
- 子域（如 `app.`、`blog.`、`docs.`）可通过 CDN/反向代理映射到 `public/app/`、`public/blog/`、`public/docs/` 等路径；详见 `public/docs/`。

## 说明

本站为独立设计与文案，**不**复制或镜像第三方网站（包括 heyvid.ai）。若需「同类」产品站，请在此基础上替换为你的品牌素材、定价与法务文本。
