# structure-intake 结构式提取

从文献 PDF / 截图 / 图片中框选结构式、识别为分子，并在 ChemDraw（ACS1996 样式）里重绘，
复制结果可直接粘贴回 ChemDraw。不经 SMILES 往返重排，坐标尽量来自原图。

这是 OCSR-complex benchmark 项目衍生出的独立工具（private）。

## 布局

| 路径 | 内容 |
|---|---|
| `scratch/intake-v0.1/` | 主程序（beta）。`app.py` 是服务 + 逻辑，`index.html` 是界面，双击 `打开.vbs` 启动桌面窗口（端口 8766）。 |
| `scratch/intake-prototypes/` | 原型与共用渲染层。`prototype.py` 里有 MolNexTR/MolScribe 封装、molblock 组装、ChemDraw 渲染；`comparison_page.py` + `比较页.vbs` 是早期对比窗口（端口 8765）。 |
| `scratch/intake-v0.1/boxes.py` | 页面墨迹框选（矢量页和位图页通用）：墨迹分组 + 笔画特征过滤。 |
| `scratch/intake-eval/` | 评测。`box_eval.py`（人工标注框选评测）、`bench_recognition.py`（benchmark 图识别率）、`ui_smoke.py`（无头端到端检查）、`gt.json`（229 个结构 / 20 页标注）。 |
| `.cursor/skills/verify-intake/` | 对比窗口的验收技能。 |
| `.cursor/skills/verify-extract/` | 提取窗口的验收技能（打开、拒绝、复制、翻页、截图、框选）。 |
| `scratch/arena-window/` | 窗口启动方案的综合记录。 |
| `scratch/_backup_2026-11-16/` | 改造前备份。 |

## 运行

双击 `scratch/intake-v0.1/打开.vbs`。第一次识别会加载 MolNexTR（CUDA）。

依赖（本机）：Python 3.14、PyMuPDF、OpenCV、RDKit、MolNexTR、MolScribe、pywebview、pywin32、ChemDraw COM。
模型检查点路径写死在 `scratch/intake-prototypes/prototype.py` 顶部
（`MOLSCRIBE_CKPT`、`MOLNEXTR_CKPT`），换机器需要改。

## 评测命令

```bash
# 框选评测（对 gt.json 的 20 个标注页；--method ink 为当前检测器，current 为旧矢量管线）
python scratch/intake-eval/box_eval.py --method ink

# benchmark 识别率（ACS1996 726 张 v0 图；graph=窗口实际产出，model=MolNexTR 自带 SMILES）
python scratch/intake-eval/bench_recognition.py --variants v0_orig --out scratch/intake-eval/out/bench

# 无头端到端检查（不弹窗口，不碰剪贴板）
python scratch/intake-eval/ui_smoke.py <pdf 或图片>
```

标注（`gt.json`）由 `gt_raw.jsonl` 生成：`python scratch/intake-eval/build_gt.py`。
`gt_raw.jsonl` 里的 `inkpick` 引用当前检测器的框编号，改了检测器后标注可能需要重对。

## 已知限制

- 纯位图 PDF（整页扫描 / 位图 SI）整份拒绝，需要接位图页检测模型。
- 反应机理简图会出框（由识别门槛兜底）。
- 折线图图片会被 MolNexTR 收下（置信度虚高）。
- 图片输入仍是整张交给模型；一图多结构需用「框选」手动框。
