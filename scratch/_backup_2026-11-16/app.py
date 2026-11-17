# v0.1 beta. One document at a time. PDF boxes grow, then MolNexTR.
# A picture, including a screenshot, goes to MolNexTR. Wide pictures are padded square first.

from __future__ import annotations

import json
import os
import queue
import shutil
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import parse_qs, unquote, urlparse

PROTO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "intake-prototypes")
sys.path.insert(0, PROTO)

import prototype as page  # noqa: E402
from PIL import Image  # noqa: E402

APP = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(APP, "jobs")
TITLE = "结构式提取"
PORT = 8766
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}

LOCK = threading.Lock()
MODELS = None
JOB = {"id": "", "clips": {}, "view": None}
STA = queue.Queue()
STA_WAKE = None


def start_sta():
    """ChemDraw stays on one thread. A request thread exits, and that disconnects it."""
    global STA_WAKE
    import win32event
    STA_WAKE = win32event.CreateEvent(None, 0, 0, None)
    threading.Thread(target=_sta_worker, name="chemdraw-sta", daemon=True).start()


def _sta_worker():
    import pythoncom
    import win32event
    pythoncom.CoInitialize()
    while True:
        win32event.MsgWaitForMultipleObjects([STA_WAKE], False, 100, win32event.QS_ALLINPUT)
        pythoncom.PumpWaitingMessages()
        while True:
            try:
                func, args, done = STA.get_nowait()
            except queue.Empty:
                break
            try:
                done["value"] = func(*args)
            except Exception as exc:
                done["error"] = exc
            finally:
                done["event"].set()


def on_sta(func, *args):
    import win32event
    done = {"event": threading.Event()}
    STA.put((func, args, done))
    win32event.SetEvent(STA_WAKE)
    done["event"].wait()
    if "error" in done:
        raise done["error"]
    return done["value"]


def models():
    global MODELS
    if MODELS is None:
        MODELS = page.Models()
    return MODELS


def safe_name(name):
    base = os.path.basename(name or "").replace("\\", "").replace("/", "")
    return base[:180] or "未命名"


def extension_of(name):
    return os.path.splitext(safe_name(name))[1].lower()


def predict_file(path):
    letterbox = page.image_ratio(path) >= 2
    model = None
    saved = None
    boxed = None
    try:
        if letterbox:
            models().load_molnextr()
            model = models().molnextr
            saved = model.transform
            model.transform = page.square_model_transform()
            boxed = page.letterboxed_copy(path)
            return models().predict_molnextr(boxed)
        return models().predict_molnextr(path)
    finally:
        if model is not None:
            model.transform = saved
        if boxed and os.path.exists(boxed):
            os.remove(boxed)


def stage_image(src, folder):
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    if ext in {".png", ".jpg", ".jpeg"}:
        dest = os.path.join(folder, "upload" + ext)
        if os.path.abspath(src) != os.path.abspath(dest):
            shutil.copyfile(src, dest)
        return dest
    dest = os.path.join(folder, "upload.png")
    with Image.open(src) as image:
        image.convert("RGB").save(dest)
    return dest


def public_structure(packed, url):
    render = url if url and os.path.isfile(url_to_file(url)) else ""
    return {
        "render": render,
        "mol": packed.get("mol") or "",
        "smiles": packed.get("smiles") or "",
        "smarts": packed.get("smarts") or "",
        "n_atoms": packed.get("n_atoms") or 0,
        "confidence": packed.get("confidence"),
        "ok": bool(packed.get("ok")),
        "reason": packed.get("reason") or "",
    }


def url_to_file(url):
    path = unquote(url.split("?", 1)[0])
    if not path.startswith("/jobs/"):
        return ""
    full = os.path.normpath(os.path.join(JOBS, path[len("/jobs/"):].replace("/", os.sep)))
    jobs = os.path.normpath(JOBS)
    if not full.startswith(jobs + os.sep):
        return ""
    return full


def clip_of(packed):
    rel = (packed.get("clip_file") or "").replace("/", os.sep)
    if not rel:
        return ""
    return os.path.normpath(os.path.join(page.ROOT, rel))


def blank_page_png(pdf_path, folder):
    import fitz
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, "source.png")
    doc = fitz.open(pdf_path)
    try:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.15, 1.15), alpha=False)
        pix.save(dest)
        return dest, pix.width, pix.height, doc[0].number + 1
    finally:
        doc.close()


def read_pdf(pdf_path, folder, job_id):
    import fitz
    extracted = page.extract_pdf(pdf_path, ocr=False)
    pages = []
    clips = {}
    kept = 0
    doc = fitz.open(pdf_path)
    try:
        for info in extracted:
            if not info.get("structures"):
                continue
            number = info["page"]
            sealed = page.seal_boxes(doc[number - 1], info["structures"])
            boxes, _sent = page.review_boxes(doc[number - 1], sealed)
            if not boxes:
                continue
            page_dir = os.path.join(folder, f"p{number}")
            os.makedirs(page_dir, exist_ok=True)
            source = os.path.join(page_dir, "source.png")
            page.render_page_preview(pdf_path, number - 1, [{"box": box} for box in boxes], source, scale=1.15)
            frames, width, height = page.frames_from_boxes(boxes, source, pdf_path, number - 1)
            structures = []
            for index, box in enumerate(boxes):
                crop = os.path.join(page_dir, f"crop{index:02d}.png")
                page.crop_page(pdf_path, number - 1, box, crop, scale=4.0)
                try:
                    pred = predict_file(crop)
                except Exception as exc:
                    structures.append({
                        "render": "", "mol": "", "smiles": "", "smarts": "",
                        "n_atoms": 0, "confidence": None, "ok": False, "reason": str(exc)[:160],
                    })
                    continue
                packed, ok = page.render_prediction(models(), page_dir, index, pred)
                structures.append(public_structure(packed, f"/jobs/{job_id}/p{number}/s{index:02d}.png"))
                clips[(len(pages), index)] = clip_of(packed)
                if ok:
                    kept += 1
            pages.append({
                "page": number,
                "source": f"/jobs/{job_id}/p{number}/source.png",
                "width": width,
                "height": height,
                "frames": frames,
                "structures": structures,
            })
    finally:
        doc.close()
    if pages and kept:
        status, reason = "ready", f"收下 {kept} 个结构。"
    elif pages:
        status, reason = "rejected", "这些框没有通过识别。"
    else:
        dest, width, height, number = blank_page_png(pdf_path, os.path.join(folder, "p1"))
        pages = [{
            "page": number,
            "source": f"/jobs/{job_id}/p1/source.png",
            "width": width,
            "height": height,
            "frames": [],
            "structures": [],
        }]
        status, reason = "rejected", "没有可外扩的结构框。"
    return {"status": status, "kind": "pdf", "reason": reason, "pages": pages}, clips


def read_image(image_path, folder, job_id, title):
    sample = page.image_via_predict(
        models(), folder, "doc", title, image_path, "structures", "", models().predict_molnextr,
    )
    source_name = "source" + os.path.splitext(image_path)[1].lower()
    source_file = os.path.join(folder, "doc", source_name)
    width = height = 1
    if os.path.isfile(source_file):
        with Image.open(source_file) as image:
            width, height = image.size
    raw_page = (sample.get("pages") or [{}])[0]
    structures = []
    clips = {}
    frames = []
    for index, packed in enumerate(raw_page.get("structures") or []):
        structures.append(public_structure(packed, f"/jobs/{job_id}/doc/s{index:02d}.png"))
        clips[(0, index)] = clip_of(packed)
    if structures:
        frames, width, height = page.full_image_frame(source_file)
    status = "ready" if sample.get("status") == "structures" else "rejected"
    return {
        "status": status,
        "kind": "image",
        "reason": sample.get("reason") or "",
        "pages": [{
            "page": 1,
            "source": f"/jobs/{job_id}/doc/{source_name}",
            "width": width,
            "height": height,
            "frames": frames,
            "structures": structures,
        }],
    }, clips


def recognize(src, name, kind_hint):
    job_id = time.strftime("%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"
    folder = os.path.join(JOBS, job_id)
    os.makedirs(folder, exist_ok=True)
    ext = extension_of(name)
    if ext == ".pdf" or kind_hint == "pdf":
        stored = os.path.join(folder, "upload.pdf")
        if os.path.abspath(src) != os.path.abspath(stored):
            shutil.copyfile(src, stored)
        view, clips = read_pdf(stored, folder, job_id)
    else:
        staged = stage_image(src, folder)
        view, clips = read_image(staged, folder, job_id, safe_name(name))
    view["name"] = safe_name(name)
    view["id"] = job_id
    JOB["id"] = job_id
    JOB["clips"] = clips
    JOB["view"] = view
    return view


def dib_to_png(dib):
    bi_size = struct.unpack_from("<I", dib, 0)[0]
    bit_count = struct.unpack_from("<H", dib, 14)[0]
    compression = struct.unpack_from("<I", dib, 16)[0]
    clr_used = struct.unpack_from("<I", dib, 32)[0]
    extra = 0
    if bit_count <= 8:
        extra = (clr_used or (1 << bit_count)) * 4
    elif compression == 3 and bi_size == 40:
        extra = 12
    offset = 14 + bi_size + extra
    blob = struct.pack("<2sIHHI", b"BM", 14 + len(dib), 0, 0, offset) + dib
    image = Image.open(BytesIO(blob))
    out = BytesIO()
    image.convert("RGB").save(out, "PNG")
    return out.getvalue()


def clipboard_png():
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        png_fmt = win32clipboard.RegisterClipboardFormat("PNG")
        if win32clipboard.IsClipboardFormatAvailable(png_fmt):
            data = win32clipboard.GetClipboardData(png_fmt)
            return bytes(data)
        if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            return None
        dib = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
    finally:
        win32clipboard.CloseClipboard()
    try:
        return dib_to_png(bytes(dib))
    except Exception:
        return None


def clipboard_sequence():
    return int(__import__("ctypes").windll.user32.GetClipboardSequenceNumber())


def host_running():
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq ScreenClippingHost.exe", "/NH"],
            creationflags=flags,
        )
    except Exception:
        return False
    return b"ScreenClippingHost" in out


def find_hwnd():
    return int(__import__("ctypes").windll.user32.FindWindowW(None, TITLE))


def place_window(show):
    import ctypes
    user32 = ctypes.windll.user32
    hwnd = find_hwnd()
    if not hwnd:
        return
    user32.ShowWindow(hwnd, 9 if show else 6)
    if show:
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)


def wait_snip():
    before = clipboard_sequence()
    subprocess.Popen(["explorer.exe", "ms-screenclip:"])
    saw = False
    deadline = time.time() + 90
    while time.time() < deadline:
        if host_running():
            saw = True
        if clipboard_sequence() != before:
            image = clipboard_png()
            if image:
                return image, ""
        if saw and not host_running():
            time.sleep(0.8)
            if clipboard_sequence() != before:
                image = clipboard_png()
                if image:
                    return image, ""
            return None, "截图取消了。"
        time.sleep(0.2)
    return None, "等截图超时了。"


def save_snip(image):
    job_id = time.strftime("%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"
    folder = os.path.join(JOBS, job_id)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, "snip.png")
    open(dest, "wb").write(image)
    return job_id, dest


class Api:
    def capture(self):
        if LOCK.locked():
            return {"ok": False, "reason": "等这一份识别完。"}
        place_window(False)
        time.sleep(0.35)
        try:
            image, reason = wait_snip()
        finally:
            place_window(True)
        if not image:
            return {"ok": False, "reason": reason or "没有截到图。"}
        job_id, _dest = save_snip(image)
        return {"ok": True, "id": job_id, "name": "截图.png", "url": f"/jobs/{job_id}/snip.png"}

    def choose_file(self):
        import webview
        if self_window() is None:
            return {"ok": False, "reason": "窗口还没准备好。"}
        picked = self_window().create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("PDF 或图片 (*.pdf;*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff)",),
        )
        if not picked:
            return {"ok": False, "reason": ""}
        return {"ok": True, "path": picked[0]}


WINDOW = None


def self_window():
    return WINDOW


def copy_structure(kind, text, clip_file):
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        if kind == "mol" and clip_file and os.path.isfile(clip_file):
            fmt = win32clipboard.RegisterClipboardFormat("ChemDraw Interchange Format")
            win32clipboard.SetClipboardData(fmt, open(clip_file, "rb").read())
            win32clipboard.SetClipboardData(13, text)
            return "已放入 ChemDraw，可直接粘贴。"
        win32clipboard.SetClipboardData(13, text)
        return "已复制文本。"
    finally:
        win32clipboard.CloseClipboard()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, payload, code=200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path in ("/", "/index.html"):
            target = os.path.join(APP, "index.html")
        elif path.startswith("/jobs/"):
            target = url_to_file(path)
        else:
            target = ""
        if not target or not os.path.isfile(target):
            self.send_error(404)
            return
        data = open(target, "rb").read()
        kind = "text/html; charset=utf-8"
        if target.endswith(".png"):
            kind = "image/png"
        elif target.endswith((".jpg", ".jpeg")):
            kind = "image/jpeg"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if parsed.path == "/api/copy":
            self.copy(body)
            return
        if parsed.path == "/api/open":
            self.open_bytes(parsed, body)
            return
        if parsed.path == "/api/open-path":
            self.open_path(body)
            return
        if parsed.path == "/api/recognize":
            self.recognize_saved(body)
            return
        self.send_error(404)

    def copy(self, body):
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "message": "复制内容读不出来。"}, 400)
            return
        view = JOB.get("view") or {}
        try:
            page_index = int(payload.get("page"))
            structure_index = int(payload.get("structure"))
            structure = view["pages"][page_index]["structures"][structure_index]
        except Exception:
            self.send_json({"ok": False, "message": "没有这份结果。"}, 404)
            return
        kind = payload.get("kind") or "mol"
        text = structure.get("mol") if kind == "mol" else structure.get(kind) or ""
        clip = JOB.get("clips", {}).get((page_index, structure_index), "")
        try:
            message = copy_structure(kind, text, clip)
        except Exception as exc:
            self.send_json({"ok": False, "message": str(exc)[:160]}, 500)
            return
        self.send_json({"ok": True, "message": message})

    def open_bytes(self, parsed, body):
        name = safe_name(parse_qs(parsed.query).get("name", ["upload"])[0])
        ext = extension_of(name)
        if ext not in ALLOWED or len(body) < 32:
            self.send_json({"status": "failed", "name": name, "reason": "只收 PDF 和常见图片。", "pages": []})
            return
        if not LOCK.acquire(blocking=False):
            self.send_json({"status": "failed", "name": name, "reason": "等这一份识别完。", "pages": []}, 409)
            return
        folder = os.path.join(JOBS, "incoming")
        os.makedirs(folder, exist_ok=True)
        src = os.path.join(folder, "upload" + ext)
        try:
            open(src, "wb").write(body)
            self.send_json(on_sta(recognize, src, name, "pdf" if ext == ".pdf" else "image"))
        except Exception as exc:
            self.send_json({"status": "failed", "name": name, "reason": str(exc)[:180], "pages": []}, 500)
        finally:
            LOCK.release()

    def open_path(self, body):
        try:
            payload = json.loads(body.decode("utf-8"))
            src = payload.get("path") or ""
        except Exception:
            self.send_json({"status": "failed", "reason": "路径读不出来。", "pages": []}, 400)
            return
        ext = extension_of(src)
        if ext not in ALLOWED or not os.path.isfile(src):
            self.send_json({"status": "failed", "name": safe_name(src), "reason": "只收 PDF 和常见图片。", "pages": []})
            return
        if not LOCK.acquire(blocking=False):
            self.send_json({"status": "failed", "name": safe_name(src), "reason": "等这一份识别完。", "pages": []}, 409)
            return
        try:
            self.send_json(on_sta(recognize, src, os.path.basename(src), "pdf" if ext == ".pdf" else "image"))
        except Exception as exc:
            self.send_json({"status": "failed", "name": safe_name(src), "reason": str(exc)[:180], "pages": []}, 500)
        finally:
            LOCK.release()

    def recognize_saved(self, body):
        try:
            payload = json.loads(body.decode("utf-8"))
            job_id = payload.get("id") or ""
        except Exception:
            self.send_json({"status": "failed", "reason": "截图编号读不出来。", "pages": []}, 400)
            return
        src = os.path.join(JOBS, job_id, "snip.png")
        jobs = os.path.normpath(JOBS)
        full = os.path.normpath(src)
        if not full.startswith(jobs + os.sep) or not os.path.isfile(full):
            self.send_json({"status": "failed", "reason": "截图文件不在了。", "pages": []}, 404)
            return
        if not LOCK.acquire(blocking=False):
            self.send_json({"status": "failed", "name": "截图.png", "reason": "等这一份识别完。", "pages": []}, 409)
            return
        try:
            self.send_json(on_sta(recognize, full, "截图.png", "image"))
        except Exception as exc:
            self.send_json({"status": "failed", "name": "截图.png", "reason": str(exc)[:180], "pages": []}, 500)
        finally:
            LOCK.release()


def bind():
    import socket
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler, bind_and_activate=False)
    server.allow_reuse_address = False
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    server.server_bind()
    server.server_activate()
    return server


def check(path):
    view = recognize(path, os.path.basename(path), "pdf" if path.lower().endswith(".pdf") else "image")
    atoms = [item.get("n_atoms") for page in view["pages"] for item in page["structures"]]
    print(view["status"], view["reason"], "atoms", atoms)


def main():
    os.makedirs(JOBS, exist_ok=True)
    if len(sys.argv) >= 3 and sys.argv[1] == "--check":
        check(sys.argv[2])
        return
    try:
        server = bind()
    except OSError:
        import webview
        webview.create_window(TITLE, html="<p style='font-family:sans-serif;padding:24px'>提取窗口已经在运行。</p>", width=480, height=180)
        webview.start(gui="edgechromium")
        return
    start_sta()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    import webview
    global WINDOW
    api = Api()
    WINDOW = webview.create_window(TITLE, url=f"http://127.0.0.1:{PORT}/", js_api=api, width=1280, height=860, text_select=True)
    WINDOW.events.closed += lambda: server.shutdown()
    webview.start(gui="edgechromium")


if __name__ == "__main__":
    main()
