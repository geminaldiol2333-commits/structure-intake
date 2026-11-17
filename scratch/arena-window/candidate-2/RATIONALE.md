# Window launch rationale

## Problem

An ordinary person should get the existing comparison page in a desktop window. Today the only arrival is `scratch/intake-prototypes/prototype.py serve`. That command defaults the port to 8765, binds `ThreadingHTTPServer` to `127.0.0.1`, prints `http://127.0.0.1:<port>/`, and blocks in `serve_forever`. The URL returns `index.html`. The title is `结构式提取原型`. The scheme bar stays empty until the page fetches `out/results.json`. `run` builds that file and talks to ChemDraw. `serve` does not. `overlay` does not open the page. Copy remains `POST /api/copy`. The verifier starts `prototype.py serve --port <port>` with no window, refuses to kill a listener it does not own, and its doctor check requires the command line to contain `prototype.py`, `serve`, and `--port` plus that port. Closing the person's window must stop only the server that window started. A taken port stays with the process that already has it. A missing results file must be a plain sentence in the window. The launch must not start ChemDraw.

## Usage (caller's view)

Double-click `scratch/intake-prototypes/打开结构式比较.pyw`. A desktop window opens. The person types neither a URL nor a command. Closing the window returns from `open_comparison` and stops only the listener that call bound.

When `out/results.json` is already a file, the window shows the existing page. Copy still posts to `/api/copy` on that listener. When the file is missing, the window shows this sentence.

还没有比较结果。请等结果准备好之后，再打开这个窗口。

`serve(8766)` binds that exact port, prints `http://127.0.0.1:8766/`, and blocks with no window. A taken port raises `OSError` and leaves the other process running.

The double-click file is the person's call site. It re-executes itself with `C:\Python314\pythonw.exe` when the current interpreter is different, then calls `open_comparison`. If that interpreter is missing, or `page_host` fails to import, or `open_comparison` raises, a native message box shows `比较窗口打不开。页面程序没有加载成功。` The file does not bind a port.

```python
PYTHONW = r"C:\Python314\pythonw.exe"
LOAD_SENTENCE = "比较窗口打不开。页面程序没有加载成功。"

def main() -> None:
    """No console. Call open_comparison on C:\\Python314\\pythonw.exe."""
    # TODO: if sys.executable is not PYTHONW and PYTHONW exists, replace this process with PYTHONW on this same file.
    # TODO: if PYTHONW is missing, show LOAD_SENTENCE in a native message box and return.
    # TODO: import open_comparison and call it. On any exception, show LOAD_SENTENCE in a native message box.
    # TODO: this file does not bind a port and does not import page_host from the failure path.
    raise NotImplementedError("not implemented")

if __name__ == "__main__":
    main()
```

The serve branch in `prototype.py` is the second call site. The default port lives only in `serve`.

```python
elif command == "serve":
    from page_host import serve
    if "--port" in sys.argv:
        serve(int(sys.argv[sys.argv.index("--port") + 1]))
    else:
        serve()
```

The third call site is `verify_intake.py` launch, unchanged.

```python
process = subprocess.Popen(
    [sys.executable, str(PROTOTYPE), "serve", "--port", str(port)],
    cwd=str(APP),
    stdout=log,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
```

`__main__` with no command still calls `overlay`.

## Shape

The window shows a `ComparisonPage` or a `PlainNotice`. `ComparisonPage` exists only after this process has bound a listener and `results.json` is a file. It holds the URL read back from that socket and a token minted by that `OwnedListener`. `PlainNotice` holds one sentence from `SENTENCES` and has no URL. A missing file, a full port walk, a bind error, or a server that never accepts builds a `PlainNotice` only. per model-the-domain. per type-system-discipline.

`OwnedListener` is the bound `ThreadingHTTPServer` on `127.0.0.1`. `url()` reads the socket's own address. `page()` is the only constructor of `ComparisonPage`. `_present` navigates only when `document.token is listener.token`. per encode-lessons-in-structure.

`serve(port: int = FIRST_PORT)` parses `port` into `Port`, binds that exact port, prints the URL, and blocks. `open_comparison()` takes no arguments. The person calls that function. The verifier calls `serve` with the port it chose. per encode-lessons-in-structure. A bad number raises `ValueError` inside `Port`. A taken exact port raises `OSError` from `serve`. The human walk treats `EADDRINUSE` and Windows error 10048 as taken, skips that port, and leaves the other process running. Any other bind error becomes the not-ready sentence. per boundary-discipline.

The walk is `8765` through `8775`, from `FIRST_PORT` and `PORT_COUNT`. `allow_reuse_address` stays false, so a second process cannot steal a bound port. A second double-click gets the next free port in that list, or the no-port sentence. Close calls `OwnedListener.shutdown` on the listener `_show_page` started. `serve` does not call `shutdown`. The verifier still kills only the pid it recorded. The window process is `pythonw.exe` on the pyw file, so the doctor check does not match it. per separate-before-serializing-shared-state. per make-operations-idempotent.

No lock file is left behind. A crash drops the socket with the process. The next double-click binds a free port or shows the no-port sentence. `shutdown` on the same listener is safe to repeat and does not search for another pid.

`page_host.py` holds the handler, `serve`, and `open_comparison`. It does not import `prototype`, so the window does not load rdkit, fitz, or ChemDraw. `prototype.py` keeps `overlay` as the no-argument command and calls `page_host.serve` from the serve command. The handler moves once, with `do_POST` unchanged. per redesign-from-first-principles. per laziness-protocol. per foundational-thinking.

`open_comparison` hides the walk, the thread, WebView2, the three sentences, and the shutdown pairing. `serve` hides the handler, the clipboard formats, and the files under `ROOT`. Each caller imports one function. The pyw adds the no-console process and the load-failure sentence, which `page_host` cannot show when its import fails. per minimize-reader-load. per experience-first.

The window is 1280 by 800, with a normal frame, title `结构式提取原型`, and `gui="edgechromium"`. `_present` calls `webview.start` once. The page loads only as `http://127.0.0.1:{port}/` from that listener, because `fetch("out/results.json")` and `POST /api/copy` need that origin. A notice document is the sentence in one paragraph, with no script. If pywebview cannot start, the same function shows a native message box with the notice sentence, or with the not-ready sentence when the document was a page. When `_show_page` was the caller, it still shuts that listener down afterward.

The design leaves `index.html`, `verify_intake.py`, `tools/`, and the recognition schemes alone. It does not start `run` or `overlay`.

## Synthesis decision

Placeholder. The orchestrator fills this section after comparing candidates.

## Tradeoffs accepted

- We accept a serve branch in `prototype.py` that parses `--port` and calls `page_host.serve` in exchange for the doctor check still seeing `prototype.py`, `serve`, and `--port` on the command line.
- We accept a second copy of the title `结构式提取原型` in `WINDOW_TITLE` in exchange for leaving `index.html` unread by the launcher.
- We accept a second window on the next free port when the person double-clicks twice in exchange for no pid scan and no lock file.
- We accept two of those windows racing on the Windows clipboard in exchange for keeping clipboard writes inside the existing `do_POST`.
- We accept the pyw hiding a traceback from a double-click in exchange for the load-failure sentence on a window with no console.
- We accept Python still importing underscore names from `page_host` in exchange for not adding a loader that only pretends to hide them. `__all__` lists `serve` and `open_comparison`.
- We accept double-clicking `prototype.py` still running `overlay` in exchange for the window path never starting ChemDraw.
- We accept the human port list including 8766 in exchange for the window code not mentioning the verifier's port.

## Alternatives considered

A `--window` flag on `serve` lost. Callers would pass a port and a mode on the same command the person would have to type. The hidden part is only the webview call. The verifier command and the person command would share one signature, so one default picks the wrong process for the other caller. per experience-first.

A child process running `prototype.py serve` under the window lost. Callers would manage a pid and a second stop path, and that child's command line matches the doctor check. The hidden part is the handler, reused by process. `OwnedListener.shutdown` and the verifier's taskkill could both claim that process. per separate-before-serializing-shared-state.

Loading `index.html` as a file URL and skipping the server lost. Callers would avoid ports, and the hidden part is the bind. The page's fetch and copy button would have no origin, so the scheme bar would stay empty and `do_POST` would never run.

Teaching `index.html` to draw the missing-file sentence lost. Callers would still need a URL, and the hidden part is one fetch error. The existing header and empty scheme bar would remain around the sentence. The launch would no longer own the choice between `ComparisonPage` and `PlainNotice`. per model-the-domain.

## Open questions and risks

If `out/results.json` is present but empty or the wrong shape, this design loads the existing page. Should that file use the same plain sentence as a missing file?

The human walk covers 8765 through 8775. Is eleven ports the limit you want when several old windows are still open?

If the webview fails after a successful bind, `_show_page` still shuts that listener down after the message box. Is closing and opening again the retry you want?

## Next implementation step

Move the current `Handler` into `page_host.serve`, point the `prototype.py` serve command at it, and run `verify_intake.py launch --port 8766` then `doctor` before filling in `open_comparison`.
