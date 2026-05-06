from pathlib import Path

from src import config as cfgmod


def test_save_and_load_roundtrip(tmp_path: Path):
    p = tmp_path / "config.yaml"
    cfg = cfgmod.Config(
        post_url="https://www.facebook.com/post/1",
        keywords=["interested", "info"],
        message_template="hi",
        poll_seconds=30,
        poll_jitter_seconds=5,
        dry_run=False,
    )
    cfgmod.save(cfg, p)
    loaded = cfgmod.load(p)
    assert loaded == cfg


def test_validation_empty():
    errs = cfgmod.Config().validation_errors()
    assert "post_url is empty" in errs
    assert "at least one keyword required" in errs


def test_validation_https_required():
    cfg = cfgmod.Config(
        post_url="ftp://x", keywords=["a"], message_template="m"
    )
    assert "post_url must start with https://" in cfg.validation_errors()
