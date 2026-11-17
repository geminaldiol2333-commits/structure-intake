# Open a sample

Open a sample lets a person inspect one prepared file as 来源, 渲染, and 拒绝. The five samples stay available under every scheme.

## Sub-features

- `sample-literature` opens the literature PDF and shows structure cards.
- `sample-complex` opens the wide natural-product screenshot.
- `sample-common` opens the JPEG structure.
- `sample-columns` keeps 来源, 渲染, and 拒绝 visible together.

## How to get to it (user POV)

- Choose `文献 PDF`, `复杂结构截图`, or `常见图片` in the left column.
- The same names are available after choosing `边外扩` or `MolNexTR`.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the window `结构式提取原型` is open.
- `边外扩` is the selected scheme. Its summary starts with `在矢量框上把仍切到墨迹的边向外推`.

- **Literature.** Choose `文献 PDF`. The 渲染 column says `点左边的识别框，展开对应的渲染。` No `复制 MOL` is visible yet. Choose `识别框 1` on the first source page. One card appears with `复制 MOL`. The other frames stay closed.
- **Common image.** Choose `常见图片`. Click the picture. The 渲染 column shows one accepted card, and the card text includes `置信度 0.9`.
- **Complex screenshot.** Choose `复杂结构截图`. Click the picture. The card is marked `被拒绝` and includes `置信度 0.00，低于 0.45`.
- **Return.** Choose `文献 PDF` again. The literature columns return. `常见图片` is no longer the selected sample.
- **Proof.** On the common-image step, save a desktop screenshot to `.cursor/skills/verify-intake/evidence/open-sample/common.png`. It shows `结构式提取原型`, `常见图片`, and `来源`.

## Gotchas

- `复杂结构截图` was seeded with expect `structures`, but the page rejects it. The button can read `拒绝 · 与预期不符`. That mismatch is part of the observed state. Do not describe the screenshot as accepted in order to clear the pill.
- A scheme change rebuilds the left column. Re-select the sample after switching schemes before asserting its columns.
- `文献 PDF` has many frames. Assert the one open card, not a count of every structure.
- Under MolNexTR, `复杂结构截图` is accepted. This recipe stays on `边外扩`, where that sample is refused.
