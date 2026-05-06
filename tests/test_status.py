from pathlib import Path

from src import status


def test_roundtrip(tmp_path: Path):
    p = tmp_path / "status.json"
    s = status.Status(state="running", polls=3, sent=1, dry_run=False)
    status.write(p, s)
    loaded = status.read(p)
    assert loaded is not None
    assert loaded.state == "running"
    assert loaded.polls == 3
    assert loaded.sent == 1
    assert loaded.dry_run is False


def test_read_missing(tmp_path: Path):
    assert status.read(tmp_path / "nope.json") is None


def test_touch_increments(tmp_path: Path):
    s = status.Status()
    assert s.polls == 0
    s.touch_poll()
    assert s.polls == 1
    assert s.last_poll_at is not None
