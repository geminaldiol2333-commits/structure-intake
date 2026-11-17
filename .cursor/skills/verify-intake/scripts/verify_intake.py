"""Launch, check, and stop one intake comparison page.

The page is scratch/intake-prototypes. This script does not start ChemDraw,
does not run recognition, and does not post to /api/copy.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO = SKILL_DIR.parents[2]
APP = REPO / "scratch" / "intake-prototypes"
PAGE = APP / "comparison_page.py"
RESULTS = APP / "out" / "results.json"
RUN_DIR = SKILL_DIR / "run"
PID_FILE = RUN_DIR / "server.pid"
STARTED_FILE = RUN_DIR / "started.txt"
LOG_FILE = RUN_DIR / "server.log"
WINDOW_TITLE = "结构式提取原型"
PYTHONW = Path(sys.executable).with_name("pythonw.exe")

SCHEME_IDS = ("edgegrow", "molnextr")
SAMPLE_IDS = (
    "literature-pdf",
    "complex-screenshot",
    "common-image",
    "no-structure-pdf",
    "no-structure-image",
)
SCHEME_LABELS = {
    "edgegrow": "边外扩",
    "molnextr": "MolNexTR",
}


def listening_pid(port: int) -> int | None:
    output = subprocess.check_output(
        ["netstat", "-ano", "-p", "tcp"],
        text=True,
        errors="replace",
    )
    needle = f"127.0.0.1:{port}"
    for line in output.splitlines():
        if needle in line and "LISTENING" in line:
            return int(line.split()[-1])
    return None


def command_line(pid: int) -> str:
    output = subprocess.check_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
        ],
        text=True,
        errors="replace",
    )
    return output.strip()


def is_comparison_window(pid: int) -> bool:
    return "comparison_page.py" in command_line(pid)


def find_window() -> tuple[int, int] | None:
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, WINDOW_TITLE)
    if not hwnd:
        return None
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(hwnd), int(pid.value)


def read_run() -> tuple[int, str]:
    if not PID_FILE.is_file() or not STARTED_FILE.is_file():
        raise SystemExit("no comparison window recorded. run launch first.")
    return int(PID_FILE.read_text(encoding="utf-8").strip()), STARTED_FILE.read_text(encoding="utf-8").strip()


def record(pid: int, how: str) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid), encoding="utf-8")
    STARTED_FILE.write_text(how, encoding="utf-8")


def launch() -> None:
    if not PAGE.is_file():
        raise SystemExit(f"missing {PAGE}")
    if not PYTHONW.is_file():
        raise SystemExit(f"missing {PYTHONW}")
    if not RESULTS.is_file():
        raise SystemExit(
            "missing scratch/intake-prototypes/out/results.json. "
            "seed it with: python scratch/intake-prototypes/prototype.py run"
        )
    existing = find_window()
    if existing is not None:
        _hwnd, pid = existing
        if not is_comparison_window(pid):
            raise SystemExit(
                f"a window titled {WINDOW_TITLE} belongs to pid {pid}, "
                "which is not comparison_page.py. leave it alone."
            )
        record(pid, "attached")
        print(f"ready window {WINDOW_TITLE} pid {pid} attached")
        return
    owner = listening_pid(8765)
    if owner is not None:
        raise SystemExit(
            f"port 8765 is already listening (pid {owner}) and no comparison window is open. "
            "do not kill it."
        )
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_FILE, "w", encoding="utf-8")
    process = subprocess.Popen(
        [str(PYTHONW), str(PAGE)],
        cwd=str(APP),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    record(process.pid, "started")
    deadline = time.time() + 20
    while time.time() < deadline:
        if process.poll() is not None:
            raise SystemExit(f"window exited {process.returncode}. see {LOG_FILE}")
        found = find_window()
        if found is not None and found[1] == process.pid:
            print(f"ready window {WINDOW_TITLE} pid {process.pid} started")
            return
        time.sleep(0.3)
    raise SystemExit(f"window pid {process.pid} did not appear. see {LOG_FILE}")


def doctor() -> None:
    pid, how = read_run()
    failures: list[str] = []
    line = ""
    try:
        line = command_line(pid)
    except subprocess.CalledProcessError:
        failures.append(f"pid {pid} is not running")
    if line and not is_comparison_window(pid):
        failures.append(f"pid {pid} command line is not the comparison window: {line}")
    found = find_window()
    if found is None:
        failures.append(f"no window titled {WINDOW_TITLE}")
    elif found[1] != pid:
        failures.append(f"window pid is {found[1]}, expected {pid}")
    if not RESULTS.is_file():
        failures.append(f"missing {RESULTS}")
        payload = {}
    else:
        payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    schemes = (payload.get("schemes") or {}) if isinstance(payload, dict) else {}
    for scheme_id in SCHEME_IDS:
        if scheme_id not in schemes:
            failures.append(f"results missing scheme {scheme_id}")
            continue
        label = schemes[scheme_id].get("label")
        if label != SCHEME_LABELS[scheme_id]:
            failures.append(f"{scheme_id} label is {label!r}")
        found = {item.get("id") for item in schemes[scheme_id].get("samples") or []}
        missing = [sample_id for sample_id in SAMPLE_IDS if sample_id not in found]
        if missing:
            failures.append(f"{scheme_id} missing samples {missing}")
    print(f"window {WINDOW_TITLE}")
    print(f"pid {pid}")
    print(f"launch {how}")
    print(f"results {RESULTS}")
    print(f"schemes {','.join(SCHEME_IDS)}")
    if failures:
        print("doctor fail")
        for item in failures:
            print(f"- {item}")
        raise SystemExit(1)
    print("doctor ok")


def cleanup() -> None:
    if not PID_FILE.is_file():
        print("cleanup nothing-recorded")
        return
    pid, how = read_run()
    if how == "attached":
        print(f"cleanup left the existing window pid {pid}")
    else:
        found = find_window()
        if found is None:
            print("cleanup window already closed")
        elif found[1] != pid:
            print(f"cleanup refused: window pid is {found[1]}, not {pid}")
            raise SystemExit(1)
        elif not is_comparison_window(pid):
            print(f"cleanup refused: pid {pid} is not the comparison window")
            raise SystemExit(1)
        else:
            subprocess.check_call(["taskkill", "/PID", str(pid), "/T", "/F"])
            print(f"cleanup stopped pid {pid}")
    for path in (PID_FILE, STARTED_FILE, LOG_FILE):
        for _ in range(8):
            if not path.is_file():
                break
            try:
                path.unlink()
                break
            except PermissionError:
                time.sleep(0.15)
    print(f"cleanup kept {SKILL_DIR / 'evidence'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("launch", "doctor", "cleanup"))
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    if args.port is not None:
        raise SystemExit("verification opens the comparison window. do not pass --port.")
    if args.command == "launch":
        launch()
    elif args.command == "doctor":
        doctor()
    else:
        cleanup()


if __name__ == "__main__":
    main()
