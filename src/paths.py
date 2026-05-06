"""Centralized filesystem paths for the project."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = ROOT / "config.yaml"
STATE_DB = ROOT / "state.db"
STATUS_FILE = ROOT / "status.json"
LOG_FILE = ROOT / "logs" / "watcher.log"
PID_FILE = ROOT / "runtime" / "watcher.pid"
AUTH_STATE = ROOT / ".auth" / "storage_state.json"
AUTH_DIR = ROOT / ".auth"
LOG_DIR = ROOT / "logs"
RUNTIME_DIR = ROOT / "runtime"
