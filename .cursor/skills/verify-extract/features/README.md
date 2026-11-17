# Extraction window verification map

This directory is the maintained source for verifying the user-facing behavior of the extraction window. Read the index before driving the window, then use the matching feature file as the recipe.

## Baseline preconditions

- Launch with `python .cursor/skills/verify-extract/scripts/verify_extract.py launch` from the repo root. That opens the desktop window titled `结构式提取`. Do not open the page in Cursor's browser.
- Run `python .cursor/skills/verify-extract/scripts/verify_extract.py doctor` and require `doctor ok`.
- Drive the window that doctor named. Do not navigate to a local address.
- Never drive a window this run attached to. Port 8766 belongs to one instance. A second start is a notice, not another session.
- If the window says `正在识别`, stop. Do not open a file over that job.

## Driving conventions

- Start every recipe from the empty drop page unless its preconditions say otherwise.
- Prefer the control's accessible name over coordinates or tab order.
- Wait until `把 PDF 或图片拖到这里` is visible. The page is not ready before that text exists.
- Treat the actions in each feature file as literal.
- Record the feature id and the entry point used with every artifact.
- Report an unreachable path with the attempted action and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- UI proof includes a desktop screenshot with `结构式提取` visible and the window in front.
- Copy proof includes the toast and a later clipboard read.
- Keep proof files under `.cursor/skills/verify-extract/evidence/`. Cleanup must not remove them.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with the window` starts with `Preconditions:` and uses labeled bullets that pair each user action with an observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Open a file](./open-file.md) covers the drop target and the file button.
- [Reject a file with no structure](./reject-file.md) covers the economics PDF and the chart image.
- [Copy MOL, SMILES, and SMARTS](./copy-result.md) covers separate copy actions and the closed editor.
- [Turn a literature page](./turn-page.md) covers the page slider on a multi-page PDF.
- [Take a screenshot](./snip.md) covers the screenshot button, including cancel.
- [Draw a box and recognize it](./draw-box.md) covers 框选, redrawing a pending frame, and the pending and review frame states.
