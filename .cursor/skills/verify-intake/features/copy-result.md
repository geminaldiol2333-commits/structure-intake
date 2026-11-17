# Copy MOL, SMILES, and SMARTS

Copy lets a person put one accepted structure on the clipboard in one format at a time. MOL is the ChemDraw paste payload. SMILES and SMARTS are plain text and do not ride along with the MOL format.

## Sub-features

- `copy-mol` places ChemDraw Interchange Format and the mol text.
- `copy-smiles` places only the SMILES text.
- `copy-smarts` places only the SMARTS text.
- `copy-paste` pastes the MOL payload into a new ChemDraw document.

## How to get to it (user POV)

- Choose `边外扩`, then `常见图片`, then click the picture.
- On the opened card, choose `复制 MOL`, `复制 SMILES`, or `复制 SMARTS`.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the window `结构式提取原型` is open.
- `常见图片` under `边外扩` shows one picture. Clicking it opens one card with `复制 MOL`.
- The previous clipboard text and format list have been saved so they can be restored.
- No person is using this machine's clipboard during the recipe.

- **MOL.** Choose `复制 MOL`. A toast appears with `已放入 ChemDraw Interchange Format，可在 ChemDraw 里粘贴。` A clipboard read after the toast shows format `ChemDraw Interchange Format` and format 13. The text contains `V2000` and `32 38`.
- **Paste.** In a ChemDraw document created for this check, paste with `Document.Paste`, read the atom count and bond count, then close that document. The document has 32 atoms and 38 bonds. Close it without saving.
- **SMILES.** Choose `复制 SMILES`. The toast says `已复制文本。` The clipboard text is the SMILES string and the format list does not include `ChemDraw Interchange Format`.
- **SMARTS.** Choose `复制 SMARTS`. The toast says `已复制文本。` The clipboard text starts with `[#6]` and the format list does not include `ChemDraw Interchange Format`.
- **Restore.** Put the saved clipboard back.
- **Proof.** Save the three clipboard listings and the paste atom count to `.cursor/skills/verify-intake/evidence/copy-result/clipboard.txt`. Save `.cursor/skills/verify-intake/evidence/copy-result/common.png` while the MOL toast or the accepted card is visible, with `结构式提取原型` in frame.

## Gotchas

- `复制 MOL` replaces the Windows clipboard for every application. Restore it even when an assertion fails.
- The toast is not the proof. Read the clipboard after the toast, then paste MOL in ChemDraw when the claim is that ChemDraw can receive it.
- SMILES and SMARTS must be copied by their own buttons. Copying MOL and then reading a SMILES field from the page does not prove the text copy.
- `复杂结构截图` has no `复制 MOL` button because it is rejected. Do not switch to it to avoid the paste check.
- The helper never posts to `/api/copy`. Click the button.
