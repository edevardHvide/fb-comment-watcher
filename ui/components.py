"""Shared UI helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def relative_time(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return iso_ts
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - ts
    s = int(delta.total_seconds())
    if s < 0:
        return "just now"
    if s < 60:
        return f"{s}s ago"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


def status_badge(running: bool) -> str:
    if running:
        return ":green-badge[● Running]"
    return ":gray-badge[● Stopped]"


def outcome_badge(status: str) -> str:
    return {
        "sent": ":green-badge[Sent]",
        "dry_run": ":blue-badge[Dry-run]",
        "blocked": ":orange-badge[Blocked]",
        "error": ":red-badge[Error]",
    }.get(status, f":gray-badge[{status}]")
