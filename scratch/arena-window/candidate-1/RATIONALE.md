# Comparison window

## Problem

The comparison page is `scratch/intake-prototypes/index.html`. A person reaches it by running `prototype.py serve`. That command binds `ThreadingHTTPServer` to `127.0.0.1`, prints `http://127.0.0.1:<port>/`, and blocks in `serve_forever`. The serve branch defaults the port to 8765. With no arguments, `__main__` runs `overlay`, and the comparison page stays unstarted. `run` writes `out/results.json` and talks to ChemDraw. The scheme bar stays empty until `main()` fetches that file and builds a button per scheme. The ordinary person gets a desktop window without typing a URL or a command. Closing the window stops only the server that window started. `verify_intake.py launch` still starts `prototype.py serve --port <port>` as a headless process. `doctor` still requires that command line to contain `prototype.py`, `serve`, and `--port <port>`. Cleanup still kills only the recorded pid. A taken port stays owned by whoever already bound it. A missing `out/results.json` becomes a plain sentence, because loading `index.html` then leaves `#schemes` empty. The window leaves ChemDraw unstarted, and it leaves `tools/` and the recognition schemes unchanged. pywebview is installed for `C:\Python314\python.exe`. WebView2 157.0.4314.42 is installed.

## Usage (caller's view)

Double-click `scratch/intake-prototypes/比较页.vbs`. The script starts `C:\Python314\pythonw.exe` on `comparison_page.py` and exits. A window titled `结构式提取原型` opens on the existing comparison page. Close it and that page's server stops. A second double-click shows `比较页已经在运行` and leaves the first window alone.

If `out/results.json` is missing, the window shows `还没有比较结果` and the sentence under it in the sketch. The comparison page stays unloaded.

Verification calls the same command it calls today.

```text
python scratch/intake-prototypes/prototype.py serve --port 8766
```

`comparison_page.py` loads the window with `open_comparison()`. `prototype.py` loads the headless server with `serve(port)` from the `serve` branch. Those are the only two callers. The signatures are `open_comparison() -> None` and `serve(port: int = PAGE_PORT) -> None`.

## Shape

One module, `comparison_page.py`, owns the headed session and the page server. The human entry is `open_comparison()`. The verification entry is `serve()`. The vbs file only pins `pythonw.exe`.

The result of the file check is `ReadyPage` or `PlainNotice`. `ReadyPage` exists when `schemes` contains at least one object with a non-empty `label`, which is the condition `index.html` uses to append a button. It carries no JSON. The page reads the file again through the existing fetch. `PlainNotice` values live in the `NOTICE` table, one row per `NoticeKind`, and the HTML is escaped from that row. Per type-system-discipline, a notice target has HTML and a page target has a URL. One function cannot be given the other shape.

The listening socket's owner is `_OwnedPageServer`. `stop()` calls `shutdown` and `server_close` on that object and joins its thread. Per separate-before-serializing-shared-state, the window process and the verification process each bind their own socket. The operating system gives the port to whichever bind runs first. The loser leaves the winner's pid untouched. Per make-operations-idempotent, `stop()` can run twice, from the closed hook and from `finally`, and the second call returns. A crash ends the process, which releases an in-process socket, so the next double-click can bind again. The server thread stays non-daemon, so the process waits until `stop()` has joined it.

`_page_url` is the only formatter. `serve()` prints the bound socket's address through it. The page target loads that same string. Per encode-lessons-in-structure, `PAGE_PORT` is the only `8765`. `__main__` calls `open_comparison` and nothing else. `Handler` is nested inside `_bind_page`, so an outside `import Handler` fails.

Validation sits at the edges. `_inspect_results` parses the file. `_start_owned` turns address-in-use into `PortTaken` and lets any other `OSError` out for `open_comparison` to show as `PORT_FAILED`. `serve()` lets address-in-use propagate and opens no notice window. Per boundary-discipline, the clipboard rules stay inside the nested `Handler` and move unchanged. MOL still writes ChemDraw Interchange Format plus format 13. SMILES and SMARTS still write format 13 only.

The public surface is two functions. Behind them sit the results gate, the bind, the thread, the notice copy, the WebView2 startup, and the rule that a foreign listener is left alone. Callers pass nothing. Per laziness-protocol, the `prototype.py` serve branch parses `--port` and calls the moved `serve`, which keeps the command line `doctor` already checks. Per minimize-reader-load, the human path is the vbs plus `open_comparison`, and the verification path is the existing command plus `serve`. Per model-the-domain, the session is the owned server or a notice. Per experience-first, the person gets a window with Chinese sentences and no command prompt, because the vbs starts `pythonw` at window style 0. Per redesign-from-first-principles, the page server leaves the recognition module, so a double-click leaves `run` unloaded. Per foundational-thinking, `ReadyPage` and `_OwnedPageServer` come before the webview calls.

`webview.start` stays on the main thread with `gui="edgechromium"` and `http_server` left false. Passing pywebview's `server` or `http_port` would start its Bottle server and skip `POST /api/copy`. The page window sets `text_select` so strings on the existing page can be selected.

## Synthesis decision

The orchestrator fills this section after comparing candidates. It records which candidate became the base and why, what was adapted from the others, and what was rejected and why.

## Tradeoffs accepted

- We accept a hardcoded `C:\Python314\pythonw.exe` in the vbs in exchange for the interpreter that already has pywebview.
- We accept a shared module for `serve` and `open_comparison` in exchange for one clipboard handler and a window process that leaves `prototype.py` unloaded. `webview` stays inside `_show`, so the verification import of `serve` leaves pywebview unloaded.
- We accept that Python can still import a leading-underscore name in exchange for a module a reader can scan. The clipboard class is the one name that must fail an outside import, and it is nested so that name does not exist.
- We accept one sentence for a missing file, a broken file, and a file with no scheme label in exchange for a gate that asks only whether the scheme bar would stay empty.
- We accept that a second double-click shows a notice instead of focusing the first window in exchange for never attaching to a socket this process did not bind.
- We accept a plain notice with no error code when the bind fails for a reason other than address-in-use, in exchange for a window that a person with no console can read.
- We accept that `stop()` can wait while `OpenClipboard` is held by another application, in exchange for closing the server only after the active `POST /api/copy` finishes.

## Alternatives considered

A `--window` flag on `prototype.py serve` lost. The caller would pass a mode, a port, and a URL policy, and the verification command would be one flag away from opening a window. The flag hides almost nothing. `open_comparison()` hides the port, the thread, and the notices.

Opening the system browser on the printed URL lost. The person would see an address bar, and closing the browser would leave `serve_forever` running. The browser hides no server lifetime.

Spawning `prototype.py serve` as a child and killing that pid on close lost. A crash would orphan a listener, and the next double-click is forbidden to kill a process it did not record. In-process `serve_forever` releases the port when the process dies. The child design also puts `prototype.py serve --port` on a second process, which is the command line `doctor` treats as its own server.

Adopting whatever already listens on 8765 lost. The window would display a server it does not own, and close would have to know someone else's lifetime. `PortTaken` makes that state unrepresentable.

Splitting `desk.py` from `page_server.py` lost. The extra file would forward the same bind into the window and would give agents two modules in which to copy `Handler`. One module keeps the handler nested in `_bind_page`.

## Open questions and risks

Should the port-taken sentence keep telling the person to return to an open window when the occupant is a headless `serve` on 8765? Verification's default port is 8766. Is that enough distance to keep this copy?

Is the double-click file in `scratch/intake-prototypes` enough for the ordinary person, or do they need the same vbs path placed on the desktop as the one launch file?

pywebview runs the closed hook on a side thread and swallows exceptions from it. Should `stop()` wait without a timeout when another application holds the clipboard, given that this wait also blocks process exit?

## Next implementation step

Add `comparison_page.py` and `比较页.vbs`, move `serve` into that module, and point the `prototype.py` serve branch at `serve()`.
