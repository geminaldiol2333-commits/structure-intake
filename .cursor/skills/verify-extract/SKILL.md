---
name: verify-extract
description: Drive the desktop extraction window (结构式提取) and prove opening a file, rejecting a file with no structure, copying, turning a literature page, and the screenshot button. Use when changing scratch/intake-v0.1. Do not open the page in Cursor's browser. The comparison window stays on verify-intake.
---

# Verify the extraction window

A person opens the extraction window by double-clicking `scratch/intake-v0.1/打开.vbs`. That starts a desktop window titled `结构式提取`. The person does not type a URL or a command. Closing the window stops only the server that window bound. Verification opens that same window. Do not open the page in Cursor's browser, and do not start `app.py` from a terminal the person can see.

The comparison page is a different window, titled `结构式提取原型`, on port 8765. Use `verify-intake` for that page. Do not drive both. `tools/render_dataset.py`, `tools/pipeline.py`, and the `tools/predict_*.py` drivers are not this app.

Only one extraction window can exist. It binds port 8766 for itself. A second start does not attach to the first. It shows a small notice titled with the sentence `提取窗口已经在运行。` and then exits. Do not kill the listener to free the port. If `launch` prints `attached`, the window already belonged to someone. Do not open a file in it, do not click `截图`, and do not run cleanup in a way that stops it.

## Launch

From the repo root:

```
python .cursor/skills/verify-extract/scripts/verify_extract.py launch
```

Do not pass `--port`. Ready means stdout prints `ready window 结构式提取 pid <pid> started` or `ready window 结构式提取 pid <pid> attached`, and `doctor` then prints `doctor ok`. A process that exists before the window title is on screen is not ready. Ready also means that pid is the listener on port 8766.

There is no auth and no database. The samples used by the journeys are already in `scratch/intake-prototypes/samples/`. Launch refuses to start when `plos-candidate.pdf`, `no-structure-chart.png`, or `common-structure.jpg` is missing. The launch log is `.cursor/skills/verify-extract/run/server.log`.

If port 8766 is taken and the extraction window is not open, launch exits and names the other pid. Do not kill that pid.

## Doctor

```
python .cursor/skills/verify-extract/scripts/verify_extract.py doctor
```

Run this before driving, and again whenever the window looks wrong. It is read-only. It passes only when all of these are true:

- The pid in `.cursor/skills/verify-extract/run/server.pid` is alive.
- Its command line contains `intake-v0.1\app.py`.
- A window titled `结构式提取` belongs to that pid.
- That pid is listening on port 8766.
- The three sample files named above exist.

`doctor ok` is the pass line. Anything else means do not drive. Doctor does not fetch a URL and does not click.

## Drive

Drive the open desktop window. Find controls by the accessible name under the window `结构式提取`. Do not open Cursor's browser and do not navigate to the window's local address. There is no login.

The empty window shows the text `把 PDF 或图片拖到这里`, the button `打开文件`, and the button `截图`. Wait until those three are in the accessibility tree before the first action. They appear after the page loads. A count of chrome panes alone is the tree before the page is ready.

If the window text says `正在识别`, stop. Someone is using the only instance. Do not open another file over that job.

`打开文件` opens the system file dialog. A control invoke that returns without a dialog did not press the button. Read the button's bounding rectangle and the window rectangle in the same DPI-aware process. Click the center of the button only when that center lies inside the window rectangle. A rectangle that sits outside the window is a DPI mismatch. Do not click it.

Do not post to `/api/open`, `/api/open-path`, or `/api/copy` from the helper. Those routes are what the page calls after a person acts. A direct post is not a proof that the button works.

## Evidence

Write proof under `.cursor/skills/verify-extract/evidence/<feature-id>/`. Cleanup must not delete that directory.

For a window step, bring the window titled `结构式提取` to the foreground, then save a desktop screenshot of its rectangle. The picture has to show that title and the state after the action. A grab of the rectangle while another window covers it is a picture of the other window. Take it again. Also save the text that the action was supposed to change, such as the status line. A file left in `.cursor/skills/verify-extract/run/` is not proof.

For a copy step, save the toast and a second observation of the clipboard. A toast that says `已放入 ChemDraw，可直接粘贴。` is not enough. The clipboard read must show the format `ChemDraw Interchange Format` and the text must contain `V2000`. A SMILES or SMARTS copy must not show `ChemDraw Interchange Format`. Save the previous clipboard and put it back after the assertion.

`scratch/intake-v0.1/jobs/` is the window's working data, not a proof folder. Do not treat a crop that was already on disk as evidence that this run clicked anything.

## Cleanup

```
python .cursor/skills/verify-extract/scripts/verify_extract.py cleanup
```

Cleanup reads `run/server.pid` and `run/started.txt`. When `started.txt` says `attached`, cleanup leaves the window. When it says `started`, cleanup stops that pid only if the command line contains `intake-v0.1\app.py` and the window still belongs to that pid. It then deletes `run/server.pid`, `run/started.txt`, and `run/server.log`. It leaves `.cursor/skills/verify-extract/evidence/` in place.

Do not use `taskkill` by image name. After a failed launch, run cleanup before trying again. If the window this run started is showing `正在识别` for a file a person dropped, do not stop it. Change is not required in the helper. Leave the process, and do not record the journey as finished.

## Helpers

The only helper is `python .cursor/skills/verify-extract/scripts/verify_extract.py` with `launch`, `doctor`, or `cleanup`. It does not click, copy, or open ChemDraw. Window actions stay in the feature files.
