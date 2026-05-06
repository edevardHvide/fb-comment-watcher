from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Status:
    state: str = "stopped"
    started_at: str | None = None
    last_poll_at: str | None = None
    polls: int = 0
    matches: int = 0
    sent: int = 0
    blocked: int = 0
    errors: int = 0
    last_error: str | None = None
    dry_run: bool = True
    pid: int | None = None

    def touch_poll(self) -> None:
        self.last_poll_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.polls += 1


def write(path: Path, status: Status) -> None:
    """Atomic write — temp file in same dir, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".status.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(status), f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def read(path: Path) -> Status | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    valid = {f for f in Status.__dataclass_fields__}
    clean = {k: v for k, v in data.items() if k in valid}
    return Status(**clean)
