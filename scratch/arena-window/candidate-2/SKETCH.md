# Window launch sketch

Bodies raise `NotImplementedError`. The pseudocode is the logic to fill in later. This file is not a running app.

## Usage

An ordinary person double-clicks `scratch/intake-prototypes/打开结构式比较.pyw`. A desktop window opens. They do not type a URL or a command. Closing the window returns from `open_comparison` and stops only the listener that call bound.

When `scratch/intake-prototypes/out/results.json` is already a file, the window shows the existing `index.html` page. The scheme bar still fills from that page's own fetch. Copy still posts to `/api/copy` on the listener this window started. When that file is missing, the window shows one sentence and does not load `index.html`.

还没有比较结果。请等结果准备好之后，再打开这个窗口。

`serve` stays the headless command. `serve(8766)` binds `127.0.0.1` on port 8766, prints `http://127.0.0.1:8766/`, and blocks in `serve_forever`. It does not open a window. If port 8766 is taken, `serve` raises and leaves the other process running.

The person's call site is the double-click file. It uses `C:\Python314\pythonw.exe`, the interpreter next to the Python that already has pywebview.

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

The verifier's command stays on `prototype.py`. The serve branch is the second call site. The default port lives only in `serve`.

```python
elif command == "serve":
    from page_host import serve
    if "--port" in sys.argv:
        serve(int(sys.argv[sys.argv.index("--port") + 1]))
    else:
        serve()
```

`verify_intake.py` launch is the third call site. It stays as it is.

```python
process = subprocess.Popen(
    [sys.executable, str(PROTOTYPE), "serve", "--port", str(port)],
    cwd=str(APP),
    stdout=log,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
```

`__main__` with no command still calls `overlay`. `run` still builds `out/results.json` and still talks to ChemDraw. The window path calls neither.

## Types

`page_host.py` constructs these. The pyw and `prototype.py` do not import them.

```python
FIRST_PORT = 8765
PORT_COUNT = 11
WINDOW_TITLE = "结构式提取原型"

@dataclass(frozen=True)
class Port:
    """TCP port on 127.0.0.1. Built at the serve boundary and inside the free-port walk."""
    number: int

    def __post_init__(self) -> None:
        # TODO: raise ValueError for bool and for any int outside 1 through 65535.
        raise NotImplementedError("not implemented")


class _BoundToken:
    """One object minted by one successful bind. ComparisonPage must hold that same object."""


@dataclass(frozen=True)
class ComparisonPage:
    """The existing index.html, on the listener that minted token."""
    url: str
    token: _BoundToken


@dataclass(frozen=True)
class PlainNotice:
    """A sentence. No URL, so the presenter cannot navigate to index.html."""
    sentence: str


class Notice(enum.Enum):
    MISSING_RESULTS = "missing-results"
    NO_PORT = "no-port"
    NOT_READY = "not-ready"


SENTENCES: dict[Notice, str] = {
    Notice.MISSING_RESULTS: "还没有比较结果。请等结果准备好之后，再打开这个窗口。",
    Notice.NO_PORT: "比较窗口没有打开页面。请稍后再试。这个窗口没有关闭其他程序。",
    Notice.NOT_READY: "比较窗口没有打开页面。请再打开一次。",
}


class NoFreePort(Exception):
    """FIRST_PORT for PORT_COUNT steps finished with no listener left bound."""


class OwnedListener:
    """ThreadingHTTPServer on 127.0.0.1. allow_reuse_address stays false. shutdown runs on the main thread."""
    port: Port
    token: _BoundToken

    def url(self) -> str:
        """http://127.0.0.1:{port}/ read from the socket's own address, with the trailing slash."""
        raise NotImplementedError("not implemented")

    def page(self) -> ComparisonPage:
        """The only constructor of ComparisonPage."""
        raise NotImplementedError("not implemented")

    def serve_forever(self) -> None:
        raise NotImplementedError("not implemented")

    def shutdown(self) -> None:
        raise NotImplementedError("not implemented")
```

`ROOT` is the directory of `page_host.py`, which is `scratch/intake-prototypes`. The results path is `ROOT/out/results.json`. The page file is `ROOT/index.html`. Neither path uses the process working directory.

## Signatures

Public. `__all__` is `["serve", "open_comparison"]`.

```python
def serve(port: int = FIRST_PORT) -> None:
    """Bind this exact port, print its URL, and block. No window. A taken port raises OSError."""
    # TODO: Port(port), then _bind_exact, then print(listener.url(), flush=True), then listener.serve_forever().
    raise NotImplementedError("not implemented")


def open_comparison() -> None:
    """Window on the main thread. Returns after the person closes it. Stops only a listener this call bound."""
    # TODO: follow the pseudocode. Print nothing.
    raise NotImplementedError("not implemented")
```

Internal. Not imported by the pyw or by `prototype.py`.

```python
def _taken(error: OSError) -> bool:
    """True only for errno.EADDRINUSE or Windows error 10048."""
    raise NotImplementedError("not implemented")


def _bind_exact(port: Port) -> OwnedListener:
    """Bind 127.0.0.1 on this port. On failure, leave no socket and raise OSError."""
    raise NotImplementedError("not implemented")


def _bind_first_free() -> OwnedListener:
    """Try FIRST_PORT through FIRST_PORT + PORT_COUNT - 1. Skip a taken port. Raise NoFreePort if none bind."""
    raise NotImplementedError("not implemented")


def _present(document: ComparisonPage | PlainNotice, listener: OwnedListener | None = None) -> None:
    """Show one desktop window and block until it closes."""
    raise NotImplementedError("not implemented")


def _show_page(listener: OwnedListener) -> PlainNotice | None:
    """Serve listener on a background thread, present listener.page(), then shutdown that listener."""
    raise NotImplementedError("not implemented")
```

`page_host.py` has no command parser.

```python
if __name__ == "__main__":
    # TODO: exit here. Do not call serve or open_comparison.
    raise SystemExit(1)
```

Running the module as a script exits. It does not call `serve` or `open_comparison`.

## Module map

`scratch/intake-prototypes/page_host.py` owns the handler, `serve`, and `open_comparison`. It does not import `prototype`. Its module top imports the standard library only. `pywebview` is imported inside `_present`. `win32clipboard` stays inside `do_POST`, where it lives today.

`scratch/intake-prototypes/打开结构式比较.pyw` is the double-click entry above. It is the only user entry that calls `open_comparison`.

`scratch/intake-prototypes/prototype.py` keeps the current `__main__` commands `overlay`, `run`, and `serve`. The serve command becomes the call site above. The `Handler` class leaves this file. `overlay` and `run_all` stay.

`scratch/intake-prototypes/index.html` stays the page inside the window. No edit.

`.cursor/skills/verify-intake/scripts/verify_intake.py` stays as it is. `tools/` stays as it is.

The current `Handler` moves inside `_bind_exact`'s helper, so it is not a class on the import line. `do_GET` and `do_POST` move unchanged. `log_message` stays suppressed. MOL still writes ChemDraw Interchange Format and clipboard format 13. SMILES and SMARTS still write format 13 only. Static files still resolve under `ROOT`.

## Pseudocode

`open_comparison` chooses one document, then shows it.

```text
if results.json is not a file:
    _present(PlainNotice(SENTENCES[MISSING_RESULTS]))
    return
try:
    listener = _bind_first_free()
except NoFreePort:
    _present(PlainNotice(SENTENCES[NO_PORT]))
    return
except OSError:
    _present(PlainNotice(SENTENCES[NOT_READY]))
    return
failure = _show_page(listener)
if failure is not None:
    _present(failure)
```

A missing file never binds a socket. `NoFreePort` means the walk left no socket bound. `open_comparison` also catches `OSError` from the walk and presents `SENTENCES[NOT_READY]`. That error means a bind failed for a reason other than a taken port, and `_bind_exact` left no socket behind.

`_bind_first_free` walks `FIRST_PORT` for `PORT_COUNT` steps, which is 8765 through 8775. `_taken` skips that port. Any other `OSError` aborts the walk. The walk does not call taskkill or netstat, and it leaves `allow_reuse_address` false.

`_show_page` is the only function that calls `shutdown`. Calling `shutdown` twice on the same listener is safe and does not touch another process. `serve` does not call `shutdown`. The verifier stops a headless server by killing the process it recorded.

```text
worker = Thread(target=listener.serve_forever, daemon=True)
worker.start()
try:
    if tcp connect to the bound host and port fails for 2 seconds:
        return PlainNotice(SENTENCES[NOT_READY])
    _present(listener.page(), listener)
    return None
finally:
    listener.shutdown()
    worker.join(timeout=3)
```

`serve` does not use `_show_page`, `_present`, or `_bind_first_free`.

`_present` makes one window, then calls `webview.start` once. A `ComparisonPage` whose `token is listener.token` passes `url=document.url`. A `ComparisonPage` with any other token is shown as `PlainNotice(SENTENCES[NOT_READY])`. A `PlainNotice` passes `html` and leaves `url` unset. The window uses title `WINDOW_TITLE`, width 1280, height 800, text selection on, and `gui="edgechromium"`. `_present` does not call `shutdown`. When `_show_page` is the caller, its `finally` block shuts that listener down after `webview.start` returns.

`_present` on a `PlainNotice` opens one native window with `html` set to a document that has charset utf-8, the title `WINDOW_TITLE`, and one paragraph containing the escaped sentence. That document has no script and no fetch. The call passes `html` and leaves `url` unset.

If importing pywebview or starting the webview raises, `_present` shows a native message box and returns. The box uses `document.sentence` when `document` is a `PlainNotice`. It uses `SENTENCES[NOT_READY]` when `document` is a `ComparisonPage`. `_show_page` then shuts that listener down in `finally`. A notice shown before any bind has no listener.

The window frame is a normal desktop frame with a close button. `webview.start` runs on the main thread and returns when the person closes the window. For a page, that return reaches the `finally` block in `_show_page`, which is where `shutdown` runs. For a notice chosen before any bind, that return ends `open_comparison`.

The comparison page is loaded only as `http://127.0.0.1:{port}/` from `OwnedListener.url`. Relative fetch of `out/results.json` and `POST /api/copy` stay on that origin.
