# Copy MOL, SMILES, and SMARTS

Copy lets a person put one accepted structure on the clipboard. MOL is the ChemDraw paste. SMILES and SMARTS are text. The manual editor stays closed.

## Sub-features

- `copy-mol` places ChemDraw interchange data and a molfile.
- `copy-smiles` places only text.
- `copy-smarts` places only text.
- `edit-closed` leaves `人工编辑` disabled.

## How to get to it (user POV)

- Open `scratch/intake-prototypes/samples/common-structure.jpg`.
- Choose a frame labeled `识别框 1` when the picture has a frame. A single picture uses one frame that covers the picture.
- Choose `复制 MOL`, `复制 SMILES`, or `复制 SMARTS` in the result column.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the launch line says `started`.
- `common-structure.jpg` has finished. The status line contains `收下` and `复制 MOL` is enabled.
- Save the current clipboard before the first copy, and put it back after the last assertion.

- **Show the card.** Choose `识别框 1`. The result column shows `复制 MOL`, `复制 SMILES`, `复制 SMARTS`, and a disabled `人工编辑`.
- **MOL.** Choose `复制 MOL`. The toast says `已放入 ChemDraw，可直接粘贴。` A later clipboard read shows `ChemDraw Interchange Format` and text that contains `V2000`.
- **SMILES.** Choose `复制 SMILES`. The toast says `已复制文本。` The clipboard has text and does not have `ChemDraw Interchange Format`.
- **SMARTS.** Choose `复制 SMARTS`. The toast says `已复制文本。` The clipboard has text and does not have `ChemDraw Interchange Format`.
- **Proof.** Save the three toasts and the three clipboard reads under `.cursor/skills/verify-extract/evidence/copy-result/`. Save a desktop screenshot `card.png` that shows `结构式提取`, `复制 MOL`, and the disabled `人工编辑`.

## Gotchas

- A toast is not the clipboard. Read the clipboard after the toast.
- Do not post to `/api/copy` from outside the window.
- `人工编辑` is disabled on purpose. Do not enable it to complete this journey.
- Restoring the previous clipboard is part of the journey. Leaving ChemDraw data on the clipboard fails the cleanup of this step.
