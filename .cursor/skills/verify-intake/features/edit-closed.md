# Leave manual edit closed

Leave manual edit closed keeps an edit control on each accepted card without letting it change the structure. The control is visible and disabled.

## Sub-features

- `edit-visible` shows `人工编辑` on an accepted card.
- `edit-disabled` does not open an editor and does not copy.
- `edit-absent-on-reject` does not offer the control for a refused file.

## How to get to it (user POV)

- Choose `边外扩`, then `常见图片`, click the picture, and look at the card actions.
- Choose `无结构 PDF` and look at the 渲染 column.

## Driving it with the window

Preconditions:

- `doctor` printed `doctor ok` and the window `结构式提取原型` is open.

- **Accepted card.** Choose `边外扩`, then `常见图片`, then click the picture. The card shows a button named `人工编辑`. Its disabled state is true. Its title is `人工编辑通道先留着，这一版不开放`.
- **Click.** Activate `人工编辑`. The window stays on the same sample, no toast appears, and the clipboard is unchanged.
- **Rejected file.** Choose `无结构 PDF`. The page has no `人工编辑` button.
- **Proof.** Save a desktop screenshot to `.cursor/skills/verify-intake/evidence/edit-closed/disabled.png` from the accepted-card step. It shows `结构式提取原型`, `人工编辑`, and that the button is disabled.

## Gotchas

- A disabled button can still be exposed to accessibility tools. Assert the disabled state, not the absence of the name, on the accepted card.
- The refused PDF has no edit button because it has no accepted card. That is a different check from the disabled button.
- Do not remove the button to make the click easier to automate.
