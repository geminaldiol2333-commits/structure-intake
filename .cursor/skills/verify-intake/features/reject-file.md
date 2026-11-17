# Reject a file with no structure

Reject a file lets a person see that a PDF or image with no chemical structure is refused. The reason is written in the 拒绝 column. No accepted structure card appears.

## Sub-features

- `reject-pdf` refuses the economics PDF.
- `reject-image` refuses the line chart.
- `reject-edgegrow` keeps both refusals on 边外扩.

## How to get to it (user POV)

- Choose `无结构 PDF` or `无结构图片` in the left column.
- Choose `边外扩` before those two buttons. MolNexTR is a different check.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the window `结构式提取原型` is open.
- The button `无结构 PDF` is visible.

- **PDF on edge growth.** Choose `边外扩`, then `无结构 PDF`. The left button shows `拒绝`. The 拒绝 column includes `没有可外扩的结构框`. There is no `复制 MOL` button.
- **Chart on edge growth.** Choose `无结构图片`. The left button shows `拒绝`. The 拒绝 column includes `置信度 0.43，低于 0.45`. Any drawing in 渲染 is marked `被拒绝` and has no `复制 MOL` button.
- **Proof.** On the PDF step, save a desktop screenshot to `.cursor/skills/verify-intake/evidence/reject-file/pdf.png`. It shows `结构式提取原型`, `无结构 PDF`, and the refuse sentence.

## Gotchas

- The chart can still display an unaccepted drawing. A picture in 渲染 is not acceptance. Acceptance requires a `复制 MOL` button.
- If the 来源 column says `没有预览`, record that as a failure of this journey. Do not switch to another sample to make the recipe pass.
- MolNexTR accepts `无结构图片` and `复杂结构截图`. Keep this recipe on `边外扩`. Do not move a failing step onto MolNexTR and then drop the refusal check.
