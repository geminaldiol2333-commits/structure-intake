# Draw a box and recognize it

A person can draw a rectangle on the source preview and have that region recognized. This covers structures the automatic frames missed, frames held as pending, and a picture that holds more than one structure. Automatic frames come in three looks: blue is accepted, orange with `!` is accepted but needs review, dashed brown with `?` is pending and was not recognized. A drawn frame is green.

## Sub-features

- `draw-toggle` is the `框选` button in the source panel header. It turns drawing on and off. `Esc` turns it off.
- `draw-replace` replaces an existing frame when the drawn box covers most of it, and keeps the frame number.
- `draw-add` adds a new frame when the drawn box overlaps no frame.
- `draw-too-small` refuses a box under 8 preview pixels on a side with the toast `框太小了，再框大一点。`, and sends no request.
- `pending-frame` names a frame `识别框 N 待确认` when the structure touches an arrow, bracket, frame line or caption. Its card says why and has no enabled copy button.
- `review-frame` names a frame `识别框 N 需复核` when the recognized graph has a valence error, a radical, several pieces, or one bond far longer than the rest. Copy stays enabled. The card text starts with `需复核：`.

## How to get to it (user POV)

- Open any PDF or picture with `打开文件`, by dropping it, or with `截图`.
- After the result shows, choose `框选` above the source preview, then drag on the preview.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the launch line says `started`.
- `C:\Users\ycc\Documents\出题人\仿生合成\X-1.pdf` has finished. The status line contains `收下` and `待确认`.

- **Find a pending frame.** On page 1 a frame named `识别框 6 待确认` is visible. Choose it. The render column says `结构在` and `没有送去识别`.
- **Turn drawing on.** Choose `框选`. The button is pressed and the hint `在页面上拖出一个框` appears.
- **Redraw that frame.** Drag a rectangle a little larger than the pending frame. The toast `正在识别这一块……` appears, then `这一块已识别。` or a reason. The frame keeps its number, turns green, and is open. The render column shows a picture. Drawing is off again.
- **Too small.** Choose `框选` and click once without dragging. The toast reads `框太小了，再框大一点。`. No frame is added.
- **Proof.** Save desktop screenshots to `.cursor/skills/verify-extract/evidence/draw-box/pending.png`, `redrawn.png` and `too-small.png`, each with `结构式提取` in front, plus the status line text.

## Gotchas

- While drawing is on, clicks on frames do not open them. Turn drawing off to inspect a frame.
- A drawn region goes to MolNexTR without the pending check. A box that cuts through a neighbour is the person's choice.
- The first drawn box after launch can be slow if the model is not loaded yet. The window stays busy until the toast changes.
- Frame numbers follow reading order on the page. A redraw keeps the number. A new box gets the next number.
- A headless check of the same flow is `python scratch/intake-eval/ui_smoke.py <file>`. It uses the app's handler on port 8799 and is not a proof of the desktop window.
