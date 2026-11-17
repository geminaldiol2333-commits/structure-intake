# Take a screenshot

Take a screenshot lets a person snip the screen. The extraction window gets out of the way, then comes back and recognizes the snip.

## Sub-features

- `snip-start` minimizes the window and opens the system snip tool.
- `snip-cancel` restores the window when the snip is cancelled.
- `snip-paste` recognizes a finished snip without a second paste from the person.

## How to get to it (user POV)

- Choose `截图` on the empty page, or after a finished file.
- Draw a region in the system snipping tool, or cancel it.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the launch line says `started`.
- The window does not say `正在识别`.
- No other journey needs the window to stay visible. This action minimizes it.

- **Cancel.** Choose `截图`. The window minimizes and the system snip tool opens. Cancel the snip. The window returns. A toast says `截图取消了。` The drop text `把 PDF 或图片拖到这里` is back when the page was empty.
- **Proof.** Save a desktop screenshot to `.cursor/skills/verify-extract/evidence/snip/cancelled.png` after the window returns. It shows `结构式提取` and the drop text. Record the toast text in `cancelled.txt`.

## Gotchas

- Do not start this journey while a file is recognizing. The button toasts `等这一份识别完。` and the snip tool does not open.
- A finished snip is a picture and goes through MolNexTR. Cancel is the journey that does not require a model.
- The snip tool is the Windows one. Do not drive a region snip unless the person asked for that journey. A cancel is not proof of recognition.
- If the window does not return, record the failure. Do not kill `ScreenClippingHost.exe` by image name. Close the snip UI, then look at the extraction window again.
