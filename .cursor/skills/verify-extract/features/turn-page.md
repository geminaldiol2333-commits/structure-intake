# Turn a literature page

Turn a page lets a person move through a multi-page PDF one page at a time. The preview stays in a fixed stage. The slider is the control.

## Sub-features

- `page-slider` changes which page is on screen.
- `page-label` shows the page number from the PDF and the position in the strip.
- `page-resets` clears the open frame when the page changes.

## How to get to it (user POV)

- Open `scratch/intake-prototypes/samples/bjoc-19-142.pdf` with `打开文件` or by dropping it.
- Use the slider labeled `文献页` under the preview.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the launch line says `started`.
- The PDF has finished. The status line contains `收下`. The slider `文献页` is visible. A one-page file has no slider. If this PDF produces one page of frames, record that as a failure of this journey.

- **Read the first page.** The label reads `第 N 页` and the strip reads `1 /` followed by the page count. Frames on the page are buttons named `识别框 1` and upward.
- **Move the slider.** Set `文献页` to the next page. The label's page number changes. The strip reads `2 /`. An open render from the previous page is gone. The hint says `点左边的识别框，展开对应的渲染。`
- **Proof.** Save two desktop screenshots to `.cursor/skills/verify-extract/evidence/turn-page/page-1.png` and `page-2.png`. Each shows `结构式提取` and a different `第 N 页`.

## Gotchas

- This file has many structures. The first run in a process loads the model. Wait for `收下` or for a failure status. Do not judge the slider while `正在识别` is showing.
- A file outside the repo is not this journey. Use `bjoc-19-142.pdf`.
- Overlapping frames cycle on a repeated click. That is the frame journey, not the page journey. Changing the page must clear the open frame.
