"""Desktop comparison window and the headless page server."""

from __future__ import annotations

import ctypes
import errno
import html
import json
import os
import socket
import threading
from dataclasses import dataclass
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, assert_never

APP_DIR = Path(__file__).resolve().parent
RESULTS_PATH = APP_DIR / "out" / "results.json"
LOOPBACK = "127.0.0.1"
PAGE_PORT = 8765
WINDOW_TITLE = "结构式提取原型"
LOAD_FAILED = "比较窗口打不开。页面程序没有加载成功。"
_PAGE_ROOT = os.path.normpath(str(APP_DIR))

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
        return _socket_address(self._server)

    def serve_in_background(self) -> None:
        """Start serve_forever on a non-daemon thread. Call once."""
        thread = threading.Thread(target=self._server.serve_forever, daemon=False)
        thread.start()
        self._thread = thread

    def stop(self) -> None:
        """Idempotent. shutdown, server_close, then join this server's thread.

        The window-closed hook and the finally block both call this. The lock
        makes the later call wait, see _stopped, and return.
        """
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            self._server.shutdown()
            self._server.server_close()
            thread = self._thread
            # Joining this thread from itself never returns.
            if thread is not None and thread is not threading.current_thread():
                thread.join()


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


def _inspect_results(path: Path) -> ReadyPage | PlainNotice:
    """Pure gate. No socket and no window.

    ReadyPage when the file parses as an object whose schemes map contains at
    least one object with a non-empty string label. That is the condition under
    which index.html would append a scheme button. Every other outcome returns
    NOTICE[NoticeKind.NO_RESULTS]. Sample ids stay unchecked. The parsed object
    is discarded.
    """
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return NOTICE[NoticeKind.NO_RESULTS]
    if not isinstance(parsed, dict):
        return NOTICE[NoticeKind.NO_RESULTS]
    schemes = parsed.get("schemes")
    if not isinstance(schemes, dict):
        return NOTICE[NoticeKind.NO_RESULTS]
    for scheme in schemes.values():
        if not isinstance(scheme, dict):
            continue
        label = scheme.get("label")
        if isinstance(label, str) and label != "":
            return ReadyPage()
    return NOTICE[NoticeKind.NO_RESULTS]


def _notice_html(notice: PlainNotice) -> str:
    heading = html.escape(notice.heading)
    body = html.escape(notice.body)
    return (
        "<!DOCTYPE html>"
        '<html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>{WINDOW_TITLE}</title></head>"
        f"<body><h1>{heading}</h1><p>{body}</p></body></html>"
    )


def _page_url(host: str, port: int) -> str:
    """The one URL string. serve() prints it. The page target loads it."""
    return f"http://{host}:{port}/"


def _socket_address(server: ThreadingHTTPServer) -> tuple[str, int]:
    host, bound_port = server.socket.getsockname()[:2]
    return str(host), int(bound_port)


def _bind_page(port: int) -> ThreadingHTTPServer:
    """Bind LOOPBACK on this port. allow_reuse_address stays false. Return before serve_forever.

    Import win32clipboard before the bind. Nest Handler in this function and move
    do_GET and do_POST unchanged from prototype.py. GET still serves files under
    APP_DIR only. POST /api/copy still empties the clipboard. kind mol with a
    clip file still writes ChemDraw Interchange Format and format 13. Every
    other kind still writes format 13 only. log_message stays silent.
    """
    # A missing clipboard module must fail before this process holds the port.
    import win32clipboard

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                target = os.path.join(_PAGE_ROOT, "index.html")
            else:
                target = os.path.normpath(os.path.join(_PAGE_ROOT, path.lstrip("/")))
            if not target.startswith(_PAGE_ROOT) or not os.path.isfile(target):
                self.send_error(404)
                return
            data = open(target, "rb").read()
            kind = "text/html"
            if target.endswith(".json"):
                kind = "application/json"
            elif target.endswith(".png"):
                kind = "image/png"
            elif target.endswith(".jpg") or target.endswith(".jpeg"):
                kind = "image/jpeg"
            elif target.endswith(".css"):
                kind = "text/css"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/api/copy":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            kind = body.get("kind")
            text = body.get("text") or ""
            clip_file = body.get("clip") or ""
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                if kind == "mol" and clip_file:
                    fmt = win32clipboard.RegisterClipboardFormat("ChemDraw Interchange Format")
                    data = open(os.path.join(_PAGE_ROOT, clip_file), "rb").read()
                    win32clipboard.SetClipboardData(fmt, data)
                    win32clipboard.SetClipboardData(13, text)
                    message = "已放入 ChemDraw Interchange Format，可在 ChemDraw 里粘贴。"
                else:
                    win32clipboard.SetClipboardData(13, text)
                    message = "已复制文本。"
            finally:
                win32clipboard.CloseClipboard()
            raw = json.dumps({"ok": True, "message": message}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    # HTTPServer sets allow_reuse_address True. On Windows that option lets a
    # second bind succeed, so a taken port would not raise.
    server = ThreadingHTTPServer((LOOPBACK, port), Handler, bind_and_activate=False)
    server.allow_reuse_address = False
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        server.server_bind()
        server.server_activate()
    except BaseException:
        server.server_close()
        raise
    return server


def _is_addr_in_use(error: OSError) -> bool:
    winerror = getattr(error, "winerror", None)
    return winerror == 10048 or error.errno in (errno.EADDRINUSE, 10048)


def _start_owned(port: int) -> _OwnedPageServer:
    try:
        server = _bind_page(port)
    except OSError as error:
        if _is_addr_in_use(error):
            raise PortTaken(port) from error
        raise
    owned = _OwnedPageServer(server)
    try:
        owned.serve_in_background()
    except BaseException:
        server.server_close()
        raise
    return owned


def _tell_load_failed() -> None:
    message_box = ctypes.windll.user32.MessageBoxW
    # Without wchar argtypes, ctypes can hand the Chinese sentence over as a narrow pointer.
    message_box.argtypes = (
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
    )
    message_box.restype = ctypes.c_int
    message_box(None, LOAD_FAILED, WINDOW_TITLE, 0)


def open_comparison() -> None:
    """Open the one human window and block until it closes.

    Ignores sys.argv. Leaves ChemDraw unstarted. Leaves every other process
    running. Prints nothing.
    """
    verdict = _inspect_results(RESULTS_PATH)
    match verdict:
        case PlainNotice() as notice:
            _show(_NoticeTarget(_notice_html(notice)))
            return
        case ReadyPage():
            pass
        case unreachable:
            assert_never(unreachable)
    try:
        owned = _start_owned(PAGE_PORT)
    except PortTaken:
        _show(_NoticeTarget(_notice_html(NOTICE[NoticeKind.PORT_TAKEN])))
        return
    except OSError:
        _show(_NoticeTarget(_notice_html(NOTICE[NoticeKind.PORT_FAILED])))
        return
    try:
        _show(_PageTarget.from_owned(owned))
    finally:
        owned.stop()


def _show(target: _PageTarget | _NoticeTarget) -> None:
    """Block on the main thread until the person closes the window.

    Import webview in this function. Call webview.start with gui="edgechromium"
    and leave every other start argument at its default. The installed
    signature defaults http_server to false. server and http_port would start
    pywebview's Bottle server and skip Handler.do_POST.
    """
    try:
        # Module-level import would load webview into `prototype.py serve`.
        import webview

        match target:
            case _PageTarget(url=url, on_closed=on_closed):
                window = webview.create_window(
                    WINDOW_TITLE,
                    url=url,
                    width=1280,
                    height=860,
                    text_select=True,
                )
                hook = on_closed
            case _NoticeTarget(html_text=html_text):
                window = webview.create_window(
                    WINDOW_TITLE,
                    html=html_text,
                    width=720,
                    height=420,
                )
                hook = None
            case unreachable:
                assert_never(unreachable)
        if window is None:
            raise RuntimeError("pywebview returned no window")
        if hook is not None:
            window.events.closed += hook
        webview.start(gui="edgechromium")
    except Exception as error:
        # assert_never marks a missed session shape. That is a bug, not a failed window.
        if isinstance(error, AssertionError):
            raise
        _tell_load_failed()


def serve(port: int = PAGE_PORT) -> None:
    """Headless page for verification.

    Binds, prints _page_url of the bound socket, and blocks in serve_forever
    on this thread. This path leaves webview unimported and leaves ChemDraw
    unstarted. Address-in-use raises OSError. The existing listener keeps the port.
    """
    server = _bind_page(port)
    host, bound_port = _socket_address(server)
    print(_page_url(host, bound_port), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    open_comparison()
