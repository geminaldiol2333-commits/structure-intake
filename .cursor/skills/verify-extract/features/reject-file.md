# Reject a file with no structure

Reject a file lets a person see that a PDF or a picture with no chemical structure is refused. The reason is the status line. No enabled `复制 MOL` button appears.

## Sub-features

- `reject-pdf` refuses the economics PDF.
- `reject-image` refuses the line chart.

## How to get to it (user POV)

- Drop `scratch/intake-prototypes/samples/plos-candidate.pdf` on the dashed area.
- Choose `打开文件` and pick that same PDF.
- Drop `scratch/intake-prototypes/samples/no-structure-chart.png`, or pick it with `打开文件`.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the launch line says `started`.
- The window is on the empty drop page. It does not say `正在识别`.

- **Economics PDF.** Choose `打开文件` and confirm `scratch/intake-prototypes/samples/plos-candidate.pdf`. The status line contains `没有找到结构式`. There is no enabled `复制 MOL` button.
- **Chart.** From the empty page, drop `scratch/intake-prototypes/samples/no-structure-chart.png`. The expected status is a refusal. There is no enabled `复制 MOL` button.
- **Proof.** On the PDF step, save a desktop screenshot to `.cursor/skills/verify-extract/evidence/reject-file/pdf.png`. It shows `结构式提取` and `没有找到结构式`.

## Gotchas

- The chart journey is a refusal. MolNexTR currently accepts `无结构图片`. When the status says `收下`, record the failure with the status text. Do not change the expected sentence to acceptance, and do not lower the recognition gate to make the journey pass.
- The file dialog can take about two seconds after `打开文件`. A second click in that gap opens nothing new and looks like a miss.
- The economics PDF does not load the picture model. A long wait on that file is a hung window, not the model.
- If the source area says nothing and the status line is empty, record that as a failure. Do not switch to a file that contains a structure to make the recipe pass.
