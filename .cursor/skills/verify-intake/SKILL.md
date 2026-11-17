---
name: verify-intake
description: Drive the desktop comparison window (结构式提取原型) and prove scheme switching, sample review, rejection, and copy. Use when changing scratch/intake-prototypes or checking that the comparison window still behaves. Do not open the page in Cursor's browser.
---

# Verify the intake comparison page

A person opens the comparison page by double-clicking `scratch/intake-prototypes/比较页.vbs`. That starts a desktop window titled `结构式提取原型`. The person does not type a URL or a command. Closing the window stops only the server that window bound. Verification opens that same window. Do not open the page in Cursor's browser, and do not start `prototype.py serve`. The manual edit button stays disabled.

The rest of this repo is a batch benchmark. `tools/render_dataset.py`, `tools/pipeline.py`, and the `tools/predict_*.py` drivers are not this app. Do not start them from this skill. They use ChemDraw and can run for a long time.

The window binds port 8765 for itself. Verification does not open that address. The page also writes the Windows clipboard when someone copies. If the window is already open, launch records it and cleanup leaves it. If launch starts the window, cleanup stops only that pid.

## Launch

From the repo root:

```
python .cursor/skills/verify-intake/scripts/verify_intake.py launch
```

Do not pass `--port`. Ready means stdout prints `ready window 结构式提取原型 pid <pid> started` or `ready window 结构式提取原型 pid <pid> attached`, and `doctor` then prints `doctor ok`. A process that exists before the window title is on screen is not ready. The helper refuses to launch when `out/results.json` is missing.

Seed, only when `scratch/intake-prototypes/out/results.json` is absent:

```
python scratch/intake-prototypes/prototype.py run
```

That command is not isolated. It loads MolScribe, opens ChemDraw, and its paste proof replaces the Windows clipboard. After it finishes, `out/results.json` scheme keys, in this order, must be `vector`, `raster`, `roundtrip`, `edgegrow`, `molnextr`, `inkpage`. Each scheme must contain samples `literature-pdf`, `complex-screenshot`, `common-image`, `no-structure-pdf`, and `no-structure-image`. Then launch.

There is no auth and no database. The launch log is `.cursor/skills/verify-intake/run/server.log`.

If port 8765 is taken and the comparison window is not open, launch exits and names the other pid. Do not kill that pid.

## Doctor

```
python .cursor/skills/verify-intake/scripts/verify_intake.py doctor
```

Run this before driving, and again whenever the page looks wrong. It is read-only. It passes only when all of these are true:

- The pid in `.cursor/skills/verify-intake/run/server.pid` is alive.
- Its command line contains `comparison_page.py`.
- A window titled `结构式提取原型` belongs to that pid.
- `scratch/intake-prototypes/out/results.json` on disk contains `edgegrow` labeled `边外扩` and `molnextr` labeled `MolNexTR`. Each has the five sample ids above. The window shows only those two, in that order. Keys `1` and `2` follow that order. Older schemes may remain in the file and are not buttons. Doctor reads the file. It does not fetch a URL.

`doctor ok` is the pass line. Anything else means do not drive.

## Drive

Drive the open desktop window. Click its buttons by the visible label. Do not open Cursor's browser and do not navigate to the window's local address. There is no login.

Wait until the button `文献 PDF` is visible in the window before the first click. The buttons appear after the window loads the results file.

Scheme buttons, in the top bar:

- `边外扩` selects edgegrow. The summary starts with `在矢量框上把仍切到墨迹的边向外推`.
- `MolNexTR` selects molnextr. The summary starts with `外扩后的裁图交给 MolNexTR`.

Keys `1` and `2` select those schemes in that order when the window has focus. There is no text field. Do not treat a key proof as a click proof.

Literature PDF shows one page in a fixed-height preview. A slider labeled `文献页` changes the page. The label reads `第 N 页`. Other samples do not use that slider.

Sample buttons, in the left column:

- `文献 PDF`
- `复杂结构截图`
- `常见图片`
- `无结构 PDF`
- `无结构图片`

Each sample button also exposes `有结构` or `拒绝`. On an accepted structure card the actions are `复制 MOL`, `复制 SMILES`, `复制 SMARTS`, and a disabled `人工编辑`.

Copy posts to the page's own `/api/copy`. Drive it by clicking the button. Do not call that route from the helper. A MOL copy must be followed by a separate read of the clipboard formats and, when the claim is ChemDraw paste, by `Document.Paste` into a new ChemDraw document that the run then closes. SMILES and SMARTS copies must leave only text formats. Save the previous clipboard and put it back after the assertion.

## Evidence

Write proof under `.cursor/skills/verify-intake/evidence/<feature-id>/`. Cleanup must not delete that directory.

For a window step, save a desktop screenshot that shows the title `结构式提取原型` and the state after the action. Also save the text that the action was supposed to change, such as the scheme summary or the reject reason. Copy the screenshot into `evidence/<feature-id>/` before cleanup. A file left in a temp directory is not proof.

For a copy step, save the request outcome shown in the toast and a second observation of the clipboard. A toast that says `已放入 ChemDraw Interchange Format` is not enough. The clipboard read must show the format `ChemDraw Interchange Format` plus CF_UNICODETEXT 13, and the text must contain `V2000`. A SMILES or SMARTS copy must not show `ChemDraw Interchange Format`.

`scratch/intake-prototypes/out/` is the prepared comparison data, not a proof folder. Do not treat a render PNG that was already on disk as evidence that this run clicked anything.

## Cleanup

```
python .cursor/skills/verify-intake/scripts/verify_intake.py cleanup
```

Cleanup reads `run/server.pid` and `run/started.txt`. When `started.txt` says `attached`, cleanup leaves the window. When it says `started`, cleanup stops that pid only if the command line contains `comparison_page.py` and the window still belongs to that pid. It then deletes `run/server.pid`, `run/started.txt`, and `run/server.log`. It leaves `.cursor/skills/verify-intake/evidence/` in place.

Do not use `taskkill` by image name. After a failed launch, run cleanup before trying again.

## Helpers

The only helper is `python .cursor/skills/verify-intake/scripts/verify_intake.py` with `launch`, `doctor`, or `cleanup`. It does not click, copy, or open ChemDraw. Window clicks stay in the feature files.
