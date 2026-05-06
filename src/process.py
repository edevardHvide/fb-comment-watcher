"""Manage the watcher subprocess from the Streamlit UI."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import paths


def _read_pid() -> int | None:
    if not paths.PID_FILE.exists():
        return None
    try:
        return int(paths.PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def is_running() -> bool:
    pid = _read_pid()
    if pid is None:
        return False
    if _alive(pid):
        return True
    try:
        paths.PID_FILE.unlink()
    except FileNotFoundError:
        pass
    return False


def start(live: bool) -> int:
    if is_running():
        raise RuntimeError("watcher already running")
    paths.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "src.main"]
    if live:
        cmd.append("--live")
    proc = subprocess.Popen(
        cmd,
        cwd=str(paths.ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    paths.PID_FILE.write_text(str(proc.pid))
    return proc.pid


def stop(timeout: float = 10.0) -> bool:
    pid = _read_pid()
    if pid is None or not _alive(pid):
        if paths.PID_FILE.exists():
            paths.PID_FILE.unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        paths.PID_FILE.unlink(missing_ok=True)
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid):
            paths.PID_FILE.unlink(missing_ok=True)
            return True
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    paths.PID_FILE.unlink(missing_ok=True)
    return True


def tail_log(n: int = 50, log_path: Path = paths.LOG_FILE) -> str:
    if not log_path.exists():
        return "(no log yet)"
    try:
        with log_path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 32_768)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="replace")
    except OSError as e:
        return f"(log read error: {e})"
    lines = data.splitlines()[-n:]
    return "\n".join(lines)
