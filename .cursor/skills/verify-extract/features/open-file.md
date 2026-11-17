# Open a file

Open a file lets a person put a PDF or a picture into the window. The window then shows that file and a status line. The empty window is the drop target.

## Sub-features

- `open-drop` accepts a file dropped on the dashed area.
- `open-button` accepts a file chosen with `打开文件`.
- `open-busy` refuses a second file while the first is still running.

## How to get to it (user POV)

- Drop a PDF or a picture onto the area labeled `把 PDF 或图片拖到这里`.
- Choose `打开文件` and pick a file in the system dialog.
- The accepted types are pdf, png, jpg, jpeg, webp, bmp, tif, tiff, and gif.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the launch line says `started`.
- The text `把 PDF 或图片拖到这里` is visible.
- The window does not say `正在识别`.

- **Drop.** Drop `scratch/intake-prototypes/samples/common-structure.jpg` on the dashed area. The window shows `正在识别` and the file name, then a status line that contains `收下` and a button `复制 MOL`.
- **File button.** From the empty page, choose `打开文件`. In the system dialog, choose `scratch/intake-prototypes/samples/plos-candidate.pdf` and confirm. The status line contains `没有找到结构式`.
- **Busy.** While `正在识别` is on screen, choose `打开文件` again. A toast says `等这一份识别完。` The status line keeps the first file name.
- **Proof.** Save a desktop screenshot of the drop result to `.cursor/skills/verify-extract/evidence/open-file/dropped.png`. It shows `结构式提取`, the file name, and `复制 MOL`.

## Gotchas

- A proof that uses only `打开文件` does not prove the drop target. Record the entry point that was actually used.
- The file dialog can take about two seconds after `打开文件`. Wait before clicking the button again.
- Posting the file to `/api/open` from outside the window skips both entry points. Do not do that.
- The first picture in a new process loads the model. Wait for the status line. Do not start a second file because the first one is slow.
- `人工编辑` stays disabled. A disabled button is the expected state, not a failed click.
