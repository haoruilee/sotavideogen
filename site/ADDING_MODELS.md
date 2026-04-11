# 接入新模型 / 新工具页

只需改 **`site/routes.yaml`**，然后运行：

```bash
python3 scripts/generate_pages.py
```

会自动生成：

- `public/<slug>/index.html` 及全部 `public/<locale>/<slug>/`
- 更新 `public/sitemap.xml`
- `/ai-tools/` 分区与「全部工具」清单（由数据驱动，**不必改 Jinja 模板**）
- `/ai-video-generator/`、`/ai-image-generator/` 列表（见下方 `category`）

## 最小示例（新的视频模型落地页）

```yaml
pages:
  my-new-video-model:
    kind: studio
    mode: model          # 与现有「模型路线」同款表单；可换 video / image / music 等
    category: video      # 出现在 /ai-video-generator/；图像模型用 category: image
    title: 我的新模型
    desc: 一句话说明，用于 meta 与列表。
```

`mode` 决定左侧表单字段组合，可选值见 `routes.yaml` 顶部注释。

## 分区与聚合站式目录

- **`hub.sections`**：控制 `/ai-tools/` 上各区块标题与顺序；`show_path: true` 时在列表旁显示 URL。
- 默认按 **`mode`** 归入 `video` / `image` / `audio` / `models`（`model` 模式进「模型路线」）。
- **`hub_section`**：覆盖自动归类（例如希望某个 `mode: video` 的页只出现在某一区）。

## 与参考站 slug 对账

若新增 slug **不在** heyvid 英文 sitemap 中，CI 会报错时，在 `parity_allow_extra_slugs` 里加入该 slug：

```yaml
parity_allow_extra_slugs:
  - my-new-video-model
```

## 真正「接入视频生成」

本仓库只生成**静态壳**与表单占位。接 API 时建议：

1. 在 `public/app/` 或独立前端里实现调用；或
2. 在 `site/templates/partials/studio_form.html` 为特定 `mode` 增加 `data-model-id` / 隐藏字段，由你的 JS 读取并提交。
