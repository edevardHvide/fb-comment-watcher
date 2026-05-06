from pathlib import Path

from src import state


def _common(**overrides):
    base = dict(
        post_url="https://fb.com/p/1",
        commenter_id="alice",
        commenter_name="Alice",
        comment_id="c1",
        comment_text="interested",
        profile_url="https://fb.com/alice",
        keyword="interested",
        status="sent",
    )
    base.update(overrides)
    return base


def test_init_and_dedup(tmp_path: Path):
    db = tmp_path / "state.db"
    state.init(db)
    with state.connect(db) as conn:
        assert state.was_messaged(conn, "https://fb.com/p/1", "alice") is False
        state.mark(conn, **_common())
        assert state.was_messaged(conn, "https://fb.com/p/1", "alice") is True


def test_dry_run_does_not_block_future_send(tmp_path: Path):
    db = tmp_path / "state.db"
    state.init(db)
    with state.connect(db) as conn:
        state.mark(conn, **_common(status="dry_run"))
        assert state.was_messaged(conn, "https://fb.com/p/1", "alice") is False
        state.mark(conn, **_common(status="sent"))
        assert state.was_messaged(conn, "https://fb.com/p/1", "alice") is True


def test_recent_orders_desc(tmp_path: Path):
    db = tmp_path / "state.db"
    state.init(db)
    with state.connect(db) as conn:
        state.mark(conn, **_common(commenter_id="a"))
        state.mark(conn, **_common(commenter_id="b"))
        rows = state.recent(conn, limit=10)
        assert len(rows) == 2
        assert rows[0]["sent_at"] >= rows[1]["sent_at"]
