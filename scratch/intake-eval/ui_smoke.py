"""Headless check of the extraction page: open a PDF, draw a box, read the result.

Starts the app's own HTTP handler on a spare port (no webview window, no
clipboard), loads index.html in headless Chromium, and drives it the way the
page drives itself after the file dialog: POST /api/open-path, then the
「框选」 toggle and a mouse drag on the source sheet.

    python scratch/intake-eval/ui_smoke.py <pdf> [--out DIR]
"""
import argparse
import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "intake-v0.1"))
import app  # noqa: E402

PORT = 8799


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "ui_smoke"))
    ap.add_argument("--page", type=int, default=0, help="view page index to draw on")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    app.start_sta()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), app.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1500, "height": 950})
            page.goto(f"http://127.0.0.1:{PORT}/")
            page.wait_for_selector("text=把 PDF 或图片拖到这里")
            # what the 打开文件 button does after the dialog returns a path
            page.evaluate("""async (path) => {
                busy = true;
                working(path.split(/[/\\\\]/).pop(), "");
                const response = await fetch("/api/open-path", {method: "POST",
                    headers: {"Content-Type": "application/json"}, body: JSON.stringify({path})});
                await take(response, "x");
            }""", args.pdf)
            page.wait_for_function("job !== null && !busy", timeout=600000)
            page.wait_for_timeout(300)
            if page.locator(".frame").count() == 0:
                print("status:", page.inner_text(".status") if page.locator(".status").count() else page.inner_text("#main"))
                page.screenshot(path=os.path.join(args.out, "1-opened.png"))
                browser.close()
                return
            status = page.inner_text(".status")
            frames = page.locator(".frame").count()
            pending = page.locator(".frame.pending").count()
            page.screenshot(path=os.path.join(args.out, "1-opened.png"))
            print("status:", status)
            print("frames on first page:", frames, "pending:", pending)
            if args.page:
                page.evaluate("(i) => { lit = i; result(); }", args.page)
            # open the first frame
            page.locator(".frame").first.click()
            page.wait_for_selector(".panel .render img, .panel .hint")
            page.screenshot(path=os.path.join(args.out, "2-frame-open.png"))
            # draw around frame 1 with a margin: it should replace that frame
            page.click("#draw")
            box = page.locator(".frame").first.bounding_box()
            limit = page.locator(".sheet").first.bounding_box()
            x0, y0 = max(box["x"] - 6, limit["x"] + 1), max(box["y"] - 6, limit["y"] + 1)
            x1 = min(box["x"] + box["width"] + 6, limit["x"] + limit["width"] - 1)
            y1 = min(box["y"] + box["height"] + 6, limit["y"] + limit["height"] - 1)
            before = page.evaluate("job.pages[lit].frames.length")
            page.mouse.move(x0, y0)
            page.mouse.down()
            page.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=5)
            page.mouse.move(x1, y1, steps=5)
            page.mouse.up()
            page.wait_for_function("!busy && job.focus", timeout=300000)
            after = page.evaluate("job.pages[lit].frames.length")
            focus = page.evaluate("job.focus")
            frame = page.evaluate("job.pages[lit].frames[job.focus.frame]")
            structure = page.evaluate("job.pages[lit].structures[job.pages[lit].frames[job.focus.frame].structure]")
            page.screenshot(path=os.path.join(args.out, "3-drawn.png"))
            print("frames before/after drawing over frame 1:", before, after)
            print("focus:", focus, "manual:", frame.get("manual"))
            print("drawn structure ok:", structure.get("ok"), "atoms:", structure.get("n_atoms"),
                  "reason:", structure.get("reason"))
            print("render shown:", page.locator(".panel .render img").count() > 0)
            # draw a fresh box in an empty corner: too small -> toast, no request
            page.click("#draw")
            sheet = page.locator(".sheet").first.bounding_box()
            page.mouse.move(sheet["x"] + 3, sheet["y"] + 3)
            page.mouse.down()
            page.mouse.move(sheet["x"] + 5, sheet["y"] + 5)
            page.mouse.up()
            page.wait_for_timeout(300)
            print("tiny box toast:", page.inner_text("#toast"))
            json.dump({"status": status, "frames": frames, "pending": pending, "before": before,
                       "after": after, "structure": structure}, open(os.path.join(args.out, "result.json"), "w",
                                                                      encoding="utf-8"), ensure_ascii=False, indent=1)
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
