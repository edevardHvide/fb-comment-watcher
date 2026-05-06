from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal

Status = Literal["sent", "dry_run", "blocked", "error"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS messaged (
    post_url      TEXT NOT NULL,
    commenter_id  TEXT NOT NULL,
    commenter_name TEXT,
    comment_id    TEXT,
    comment_text  TEXT,
    profile_url   TEXT,
    keyword       TEXT,
    sent_at       TEXT NOT NULL,
    status        TEXT NOT NULL,
    PRIMARY KEY (post_url, commenter_id)
);
CREATE INDEX IF NOT EXISTS idx_messaged_sent_at ON messaged(sent_at);
"""


def _connect(db_path: Path, read_only: bool = False) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if read_only:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    else:
        conn = sqlite3.connect(db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect(db_path: Path, read_only: bool = False) -> Iterator[sqlite3.Connection]:
    conn = _connect(db_path, read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()


def was_messaged(conn: sqlite3.Connection, post_url: str, commenter_id: str) -> bool:
    """True if we have already sent (live) a DM to this commenter for this post."""
    row = conn.execute(
        "SELECT status FROM messaged WHERE post_url = ? AND commenter_id = ?",
        (post_url, commenter_id),
    ).fetchone()
    if row is None:
        return False
    return row["status"] == "sent"


def mark(
    conn: sqlite3.Connection,
    *,
    post_url: str,
    commenter_id: str,
    commenter_name: str,
    comment_id: str | None,
    comment_text: str,
    profile_url: str,
    keyword: str,
    status: Status,
) -> None:
    conn.execute(
        """
        INSERT INTO messaged
            (post_url, commenter_id, commenter_name, comment_id, comment_text,
             profile_url, keyword, sent_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_url, commenter_id) DO UPDATE SET
            commenter_name = excluded.commenter_name,
            comment_id     = excluded.comment_id,
            comment_text   = excluded.comment_text,
            profile_url    = excluded.profile_url,
            keyword        = excluded.keyword,
            sent_at        = excluded.sent_at,
            status         = excluded.status
        """,
        (
            post_url,
            commenter_id,
            commenter_name,
            comment_id,
            comment_text,
            profile_url,
            keyword,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            status,
        ),
    )


def recent(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM messaged ORDER BY sent_at DESC LIMIT ?", (limit,)
        ).fetchall()
    )


def count_today(conn: sqlite3.Connection) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM messaged WHERE sent_at LIKE ?",
        (f"{today}%",),
    ).fetchone()
    return int(row["n"])
