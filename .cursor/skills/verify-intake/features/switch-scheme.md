# Switch scheme

Switch scheme lets a person compare the same samples under 边外扩 and MolNexTR. The summary sentence changes with the scheme. The selected sample stays put.

## Sub-features

- `scheme-edgegrow` shows the edge-growth summary.
- `scheme-molnextr` shows the MolNexTR summary.
- `scheme-keys` selects the same two schemes from the keyboard.

## How to get to it (user POV)

- Choose `边外扩` or `MolNexTR` in the top bar.
- Press `1` or `2` while the window has focus.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the window `结构式提取原型` is open.
- The button `文献 PDF` is visible.

- **Open on edge growth.** Look at the open window. The summary starts with `在矢量框上把仍切到墨迹的边向外推`. The button `边外扩` is the selected scheme button. The literature preview is one fixed-height page with a slider labeled `文献页`.
- **MolNexTR.** Choose `MolNexTR`. The summary starts with `外扩后的裁图交给 MolNexTR`. `文献 PDF` remains selected.
- **Edge growth again.** Choose `边外扩`. The summary returns to text that starts with `在矢量框上把仍切到墨迹的边向外推`.
- **Keys.** Focus the window and press `2`, then `1`. The summary matches MolNexTR, then edge growth. A key proof does not replace the button proof.
- **Proof.** After the MolNexTR step, save a desktop screenshot to `.cursor/skills/verify-intake/evidence/switch-scheme/molnextr.png`. It shows `结构式提取原型` and the MolNexTR summary.

## Gotchas

- The top bar is empty until `out/results.json` loads. A missing `边外扩` button means the page is not ready.
- `矢量坐标`, `栅格坐标`, `SMILES 重画`, and `墨迹框` are not buttons. Do not go looking for them.
- The selected state is the summary sentence. Button color alone is not the proof.
- Keys `1` and `2` do nothing useful while another application has focus. Click the window first.
- Do not click `复制 MOL` during this recipe. That replaces the Windows clipboard.
