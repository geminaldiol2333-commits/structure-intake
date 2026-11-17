# Intake comparison verification map

This directory is the maintained source for verifying the user-facing behavior of the intake comparison page. Read the index before driving the page, then use the matching feature file as the recipe.

## Baseline preconditions

- Launch with `python .cursor/skills/verify-intake/scripts/verify_intake.py launch` from the repo root. That opens the desktop window. Do not open the page in Cursor's browser.
- Require `scratch/intake-prototypes/out/results.json` to already contain the five samples. Do not regenerate it during an ordinary drive.
- Run `python .cursor/skills/verify-intake/scripts/verify_intake.py doctor` and require `doctor ok` and the recorded pid.
- Drive the window that doctor named. Do not navigate to a local address.
- Never drive a listener that this verification run did not start. Port 8765 is the usual interactive session.

## Driving conventions

- Start every recipe from the baseline page unless its preconditions say otherwise.
- Prefer the button's accessible name over coordinates or tab order.
- Wait until `文献 PDF` is visible. The sample list appears only after the results file loads.
- Treat the commands in each feature file as literal.
- Record the feature id and the entry point used with every artifact.
- Report an unreachable path with the attempted action and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- UI proof includes a desktop screenshot with `结构式提取原型` visible.
- Copy proof includes the toast and a later clipboard read. MOL paste proof includes the atom count from a ChemDraw document opened for that check and then closed.
- Keep proof files under `.cursor/skills/verify-intake/evidence/`. Cleanup must not remove them.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with the window` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact action and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Switch scheme](./switch-scheme.md) covers the six scheme buttons and the number keys.
- [Open a sample](./open-sample.md) covers the five sample buttons and the three columns.
- [Reject a file with no structure](./reject-file.md) covers the economics PDF and the chart image.
- [Copy MOL, SMILES, and SMARTS](./copy-result.md) covers separate copy actions for one accepted structure.
- [Leave manual edit closed](./edit-closed.md) covers the disabled edit control.
