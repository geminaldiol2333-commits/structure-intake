# Window launch synthesis

## Pick

Base is candidate 1. `comparison_page.py` plus `比较页.vbs`.

The cross-judge did not run. The pool names `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. This parent is Grok, so the judge had to be Claude. That slug is not available here. No other family sits in the pool. The pick below is the orchestrator's alone.

## Rubric

1. A person gets one window and types no URL and no command.
2. Closing that window stops only the server that window bound.
3. `prototype.py serve --port` stays headless, and the doctor command line still matches.
4. A taken port is not killed. A missing or unusable results file is a sentence, not the empty scheme bar.
5. One human way to open the page.
6. Copy, schemes, and ChemDraw-on-`run` stay as they are.

Candidate 1 meets all six. Candidate 2 meets 1, 2, 3, and 6. It fails 4 and 5 because a second double-click binds the next port from 8765 through 8775, including the verifier's 8766, and opens another copy. A bad results file still loads `index.html`.

## Grafts from candidate 2

Keep candidate 1's fixed port, `ReadyPage` gate, nested handler, and in-process non-daemon server.

Add two notices candidate 2 had and candidate 1 lacked.

- If `C:\Python314\pythonw.exe` is missing, `比较页.vbs` shows `比较窗口打不开。页面程序没有加载成功。` and starts nothing.
- If importing pywebview or starting the window raises, `comparison_page.py` shows that same sentence with `MessageBoxW` and then stops an owned server if one exists.

Rejected from candidate 2.

- The port walk. A second window is a second clipboard writer, and it can land on the verifier's port.
- The bind token. Candidate 1 already builds the page URL only from the socket it bound.
- Treating any existing `results.json` as ready. The scheme-label gate stays.

## Implementation contract

Add `scratch/intake-prototypes/comparison_page.py` and `scratch/intake-prototypes/比较页.vbs` as candidate 1's sketch specifies, plus the two grafts above.

Move `serve` out of `prototype.py`. The `serve` command in `prototype.py` imports `serve` from `comparison_page` and passes `--port` when present. `overlay` and `run` stay. `index.html`, `tools/`, and `verify_intake.py` stay.

Do not kill a listener. Do not start ChemDraw. Do not call `open_comparison` from the implementation turn. The parent verifies the window.
