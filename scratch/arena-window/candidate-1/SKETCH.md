# Comparison window

The person double-clicks one file and gets one desktop window. The page inside it is the existing `index.html`. This file is the contract. Bodies stay unimplemented.

## Usage

An ordinary person double-clicks `scratch/intake-prototypes/比较页.vbs`. A window titled `结构式提取原型` opens. When `out/results.json` can paint at least one scheme label, the window loads the existing comparison page from the server this process just bound. The person types no URL and no command. Closing the window stops that server. A second double-click finds the port taken, shows a short notice, and leaves the first window running.

When the results file is missing, unreadable, or has no scheme label, the window shows a plain sentence. `index.html` stays unloaded, so the empty scheme bar stays unpainted.

Verification keeps the command it already runs.

```text
python scratch/intake-prototypes/prototype.py serve --port 8766
```

That process prints `http://127.0.0.1:8766/` and blocks in `serve_forever`. It opens no window.

Three call sites.

The launcher pins the interpreter that has pywebview. Window style 0 hides the host. The script waits for nothing, so the host process is gone while the window still owns the server.

```vbs
Set shell = CreateObject("Wscript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
exe = "C:\Python314\pythonw.exe"
script = folder & "\comparison_page.py"
shell.Run """" & exe & """ """ & script & """", 0, False
```

`comparison_page.py` has one main. It ignores `sys.argv`.

```python
if __name__ == "__main__":
    open_comparison()
```

`prototype.py` keeps `overlay` and `run`. The `serve` branch stays headless. Omitting `--port` uses `serve`'s default, which is `PAGE_PORT`.

```python
elif command == "serve":
    from comparison_page import serve
    if "--port" in sys.argv:
        serve(int(sys.argv[sys.argv.index("--port") + 1]))
    else:
        serve()
```

`verify_intake.py` stays as it is. `launch` already spawns the command above.

## Module map

`scratch/intake-prototypes/比较页.vbs` is the human launch file. The interpreter path appears only here.

`scratch/intake-prototypes/comparison_page.py` is the new module. It owns the notices, the bind, the clipboard handler, and the WebView2 window. `__all__` is `open_comparison` and `serve`.

`scratch/intake-prototypes/prototype.py` keeps recognition. The `serve` function moves into `comparison_page.py`. The `serve` command stays, so a verification command line still contains `prototype.py`, `serve`, and `--port <port>`.

`index.html` stays the page. `tools/` stays untouched. Recognition schemes stay untouched.

`prototype.py` may import `comparison_page`. `comparison_page.py` imports the standard library at module level, `win32clipboard` inside `_bind_page` before the bind, and `webview` inside `_show`. The window process leaves rdkit, fitz, and `run` unloaded.

## Types and signatures

```python
from __future__ import annotations

import errno
import html
import json
import threading
from dataclasses import dataclass
from enum import Enum
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Callable, assert_never

APP_DIR = Path(__file__).resolve().parent
RESULTS_PATH = APP_DIR / "out" / "results.json"
LOOPBACK = "127.0.0.1"
PAGE_PORT = 8765
WINDOW_TITLE = "结构式提取原型"

__all__ = ["open_comparison", "serve"]


class NoticeKind(Enum):
    NO_RESULTS = "no_results"
    PORT_TAKEN = "port_taken"
    PORT_FAILED = "port_failed"


@dataclass(frozen=True)
class PlainNotice:
    """One sentence for one window. The NOTICE table is the only builder."""

    kind: NoticeKind
    heading: str
    body: str


@dataclass(frozen=True)
class ReadyPage:
    """The scheme bar would show at least one label.

    Carries no JSON. index.html fetches out/results.json itself.
    """


class PortTaken(Exception):
    """The person's port already has a listener. That listener stays with the other process."""

    def __init__(self, port: int) -> None:
        super().__init__(port)
        self.port = port


NOTICE: dict[NoticeKind, PlainNotice] = {
    NoticeKind.NO_RESULTS: PlainNotice(
        NoticeKind.NO_RESULTS,
        "还没有比较结果",
        "还没有可以比较的结果。请先完成结构式提取，等结果准备好后再双击打开这个窗口。",
    ),
    NoticeKind.PORT_TAKEN: PlainNotice(
        NoticeKind.PORT_TAKEN,
        "比较页已经在运行",
        "这个窗口没有再打开页面，也没有关闭正在运行的程序。请回到已经打开的比较页。",
    ),
    NoticeKind.PORT_FAILED: PlainNotice(
        NoticeKind.PORT_FAILED,
        "比较页没有打开",
        "这个窗口没有关闭别的程序。请稍后再双击一次。",
    ),
}


class _OwnedPageServer:
    """The listening socket this window bound. stop() touches only this object."""

    def __init__(self, server: ThreadingHTTPServer) -> None:
        self._server = server
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stopped = False

    def bound_address(self) -> tuple[str, int]:
        """Host and port read from the socket this object bound."""
        raise NotImplementedError("not implemented")

    def serve_in_background(self) -> None:
        """Start serve_forever on a non-daemon thread. Call once."""
        raise NotImplementedError("not implemented")

    def stop(self) -> None:
        """Idempotent. shutdown, server_close, then join this server's thread.

        The window-closed hook and the finally block both call this. The lock
        makes the later call wait, see _stopped, and return.
        """
        raise NotImplementedError("not implemented")


@dataclass(frozen=True)
class _PageTarget:
    """URL for a server this process bound, plus the close hook that stops it."""

    url: str
    on_closed: Callable[[], None]

    @staticmethod
    def from_owned(owned: _OwnedPageServer) -> _PageTarget:
        host, port = owned.bound_address()
        return _PageTarget(_page_url(host, port), owned.stop)


@dataclass(frozen=True)
class _NoticeTarget:
    """The notice document."""

    html_text: str
```

`Handler` is nested inside `_bind_page`. `from comparison_page import Handler` has no such name. There is no `LaunchMode`. `open_comparison` takes no port.

## Flow

```python
def _inspect_results(path: Path) -> ReadyPage | PlainNotice:
    """Pure gate. No socket and no window.

    ReadyPage when the file parses as an object whose schemes map contains at
    least one object with a non-empty string label. That is the condition under
    which index.html would append a scheme button. Every other outcome returns
    NOTICE[NoticeKind.NO_RESULTS]. Sample ids stay unchecked. The parsed object
    is discarded.
    """
    # TODO: missing file, OSError, UnicodeError, JSONDecodeError, non-dict,
    # missing schemes, empty schemes, and no usable label all return the notice.
    raise NotImplementedError("not implemented")


def _notice_html(notice: PlainNotice) -> str:
    # TODO: one zh-CN document. html.escape on heading and body.
    # Visible words are notice.heading and notice.body. The title element is WINDOW_TITLE.
    raise NotImplementedError("not implemented")


def _page_url(host: str, port: int) -> str:
    """The one URL string. serve() prints it. The page target loads it."""
    # TODO: return f"http://{host}:{port}/"
    raise NotImplementedError("not implemented")


def _bind_page(port: int) -> ThreadingHTTPServer:
    """Bind LOOPBACK on this port. allow_reuse_address stays false. Return before serve_forever.

    Import win32clipboard before the bind. Nest Handler in this function and move
    do_GET and do_POST unchanged from prototype.py. GET still serves files under
    APP_DIR only. POST /api/copy still empties the clipboard. kind mol with a
    clip file still writes ChemDraw Interchange Format and format 13. Every
    other kind still writes format 13 only. log_message stays silent.
    """
    raise NotImplementedError("not implemented")


def _is_addr_in_use(error: OSError) -> bool:
    # TODO: True when winerror is 10048 or errno is errno.EADDRINUSE or 10048.
    raise NotImplementedError("not implemented")


def _start_owned(port: int) -> _OwnedPageServer:
    # TODO: bind. Address-in-use raises PortTaken(port) and leaves the existing
    # listener running. Any other OSError propagates.
    # On success, serve_in_background and return.
    # If the thread fails to start, server_close and reraise.
    raise NotImplementedError("not implemented")


def open_comparison() -> None:
    """Open the one human window and block until it closes.

    Ignores sys.argv. Leaves ChemDraw unstarted. Leaves every other process
    running. Prints nothing.
    """
    # TODO:
    # verdict = _inspect_results(RESULTS_PATH)
    # match verdict:
    #     case PlainNotice() as notice:
    #         _show(_NoticeTarget(_notice_html(notice)))
    #         return
    #     case ReadyPage():
    #         pass
    #     case unreachable:
    #         assert_never(unreachable)
    # try:
    #     owned = _start_owned(PAGE_PORT)
    # except PortTaken:
    #     _show(_NoticeTarget(_notice_html(NOTICE[NoticeKind.PORT_TAKEN])))
    #     return
    # except OSError:
    #     _show(_NoticeTarget(_notice_html(NOTICE[NoticeKind.PORT_FAILED])))
    #     return
    # try:
    #     _show(_PageTarget.from_owned(owned))
    # finally:
    #     owned.stop()
    raise NotImplementedError("not implemented")


def _show(target: _PageTarget | _NoticeTarget) -> None:
    """Block on the main thread until the person closes the window.

    Import webview in this function. Call webview.start with gui="edgechromium"
    and leave every other start argument at its default. The installed
    signature defaults http_server to false. server and http_port would start
    pywebview's Bottle server and skip Handler.do_POST.
    """
    # TODO:
    # match target:
    #     case _PageTarget(url=url, on_closed=on_closed):
    #         window = webview.create_window(
    #             WINDOW_TITLE, url=url, width=1280, height=860, text_select=True,
    #         )
    #         window.events.closed += on_closed
    #     case _NoticeTarget(html_text=html_text):
    #         window = webview.create_window(
    #             WINDOW_TITLE, html=html_text, width=720, height=420,
    #         )
    #     case unreachable:
    #         assert_never(unreachable)
    # if window is None:
    #     raise RuntimeError("pywebview returned no window")
    # webview.start(gui="edgechromium")
    raise NotImplementedError("not implemented")


def serve(port: int = PAGE_PORT) -> None:
    """Headless page for verification.

    Binds, prints _page_url of the bound socket, and blocks in serve_forever
    on this thread. This path leaves webview unimported and leaves ChemDraw
    unstarted. Address-in-use raises OSError. The existing listener keeps the port.
    """
    # TODO:
    # server = _bind_page(port)
    # host, bound_port = server.server_address
    # print(_page_url(host, bound_port), flush=True)
    # server.serve_forever()
    raise NotImplementedError("not implemented")
```

`_OwnedPageServer.stop` holds its lock across shutdown, `server_close`, and the join. pywebview runs `events.closed` on a side thread and swallows exceptions from that hook. The `finally` in `open_comparison` is the stop that still runs after `webview.start` returns.

`serve` keeps `serve_forever` on the calling thread. The human path uses a background thread because `webview.start` occupies the main thread.

## Invariants

`_PageTarget.from_owned` and `serve` both format the URL with `_page_url` and the socket's own address.

A notice window has no server. Closing it stops nothing.

`stop` searches for no listener. A failed bind creates no `_OwnedPageServer`.

The window writes no pid file. Verification's `server.pid` stays the only pid record. This module neither reads it nor writes it.

`comparison_page.py` `__main__` calls `open_comparison` only. Headless serving stays the `prototype.py serve` command.

A missing results file leaves `run` uncalled. The window leaves ChemDraw unstarted.
