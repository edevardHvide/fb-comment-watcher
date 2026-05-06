"""Watcher daemon entrypoint.

Usage:
    uv run python -m src.main          # dry-run (default)
    uv run python -m src.main --live   # actually send DMs
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import sys
import time
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from playwright.sync_api import sync_playwright

from . import config as cfgmod
from . import matcher, messenger, paths, reply as replymod, state, status, watcher

log = logging.getLogger("watcher")

_running = True


def _setup_logging() -> None:
    paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_h = RotatingFileHandler(
        paths.LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_h.setFormatter(fmt)
    stream_h = logging.StreamHandler(sys.stdout)
    stream_h.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(file_h)
    root.addHandler(stream_h)
    root.setLevel(logging.INFO)


def _handle_signal(signum, frame) -> None:
    global _running
    log.info("received signal %d, stopping...", signum)
    _running = False


def _jitter(base: int, jitter: int) -> float:
    return max(1.0, base + random.uniform(-jitter, jitter))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually send DMs. Without this flag, matches are logged only.",
    )
    args = parser.parse_args(argv)

    _setup_logging()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    cfg = cfgmod.load()
    errs = cfg.validation_errors()
    if errs:
        log.error("invalid config: %s", "; ".join(errs))
        return 2
    if not paths.AUTH_STATE.exists():
        log.error("no session at %s — run `python -m src.auth` first", paths.AUTH_STATE)
        return 3

    live = args.live
    dry = not live
    log.info("starting watcher | live=%s | dry_run=%s | post=%s", live, dry, cfg.post_url)

    state.init(paths.STATE_DB)

    st = status.Status(
        state="starting",
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        dry_run=dry,
        pid=os.getpid(),
    )
    status.write(paths.STATUS_FILE, st)

    consecutive_errors = 0

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context(storage_state=str(paths.AUTH_STATE))
            page = context.new_page()

            st.state = "running"
            status.write(paths.STATUS_FILE, st)

            with state.connect(paths.STATE_DB) as db:
                # Baseline: mark every comment present at startup as pre_existing
                # so we only DM commenters whose comments arrive AFTER this point.
                try:
                    baseline_comments = watcher.scrape(page, cfg.post_url)
                    inserted = 0
                    for c in baseline_comments:
                        if state.baseline(
                            db,
                            post_url=cfg.post_url,
                            commenter_id=c.commenter_id,
                            commenter_name=c.commenter_name,
                            comment_id=c.comment_id,
                            comment_text=c.text,
                            profile_url=c.profile_url,
                        ):
                            inserted += 1
                    log.info(
                        "baseline complete | %d comments visible | %d new entries (rest already known)",
                        len(baseline_comments), inserted,
                    )
                except Exception as e:
                    log.warning("baseline scrape failed (will retry on first poll): %s", e)

                while _running:
                    try:
                        comments = watcher.scrape(page, cfg.post_url)
                        for c in comments:
                            kw = matcher.matches(c.text, cfg.keywords, cfg.exclude_keywords)
                            if not kw:
                                log.info(
                                    "no-match: %s (%s) text=%r",
                                    c.commenter_name, c.commenter_id, c.text[:120],
                                )
                                continue
                            row = db.execute(
                                "SELECT status FROM messaged WHERE post_url=? AND commenter_id=?",
                                (cfg.post_url, c.commenter_id),
                            ).fetchone()
                            if row is not None and row["status"] != "dry_run":
                                log.info(
                                    "skip: %s (%s) — already in db status=%s — text=%r",
                                    c.commenter_name, c.commenter_id, row["status"], c.text[:120],
                                )
                                continue
                            log.info(
                                "match: %s (%s) — kw=%r — text=%r",
                                c.commenter_name, c.commenter_id, kw, c.text[:120],
                            )
                            st.matches += 1
                            if dry:
                                log.info(
                                    "[DRY-RUN] would DM %s (%s) — kw=%r — text=%r",
                                    c.commenter_name, c.commenter_id, kw, c.text[:120],
                                )
                                state.mark(
                                    db,
                                    post_url=cfg.post_url,
                                    commenter_id=c.commenter_id,
                                    commenter_name=c.commenter_name,
                                    comment_id=c.comment_id,
                                    comment_text=c.text,
                                    profile_url=c.profile_url,
                                    keyword=kw,
                                    status="dry_run",
                                )
                            else:
                                if cfg.reply_enabled and cfg.reply_template.strip():
                                    try:
                                        rep_outcome = replymod.reply(
                                            page,
                                            cfg.post_url,
                                            c.commenter_id,
                                            c.commenter_name,
                                            cfg.reply_template,
                                        )
                                        log.info("reply outcome=%s for %s", rep_outcome, c.commenter_id)
                                    except Exception as e:
                                        log.warning("reply errored for %s: %s", c.commenter_id, e)
                                outcome = messenger.send(
                                    page, c.commenter_id, cfg.message_template
                                )
                                state.mark(
                                    db,
                                    post_url=cfg.post_url,
                                    commenter_id=c.commenter_id,
                                    commenter_name=c.commenter_name,
                                    comment_id=c.comment_id,
                                    comment_text=c.text,
                                    profile_url=c.profile_url,
                                    keyword=kw,
                                    status=outcome,
                                )
                                if outcome == "sent":
                                    st.sent += 1
                                elif outcome == "blocked":
                                    st.blocked += 1
                                else:
                                    st.errors += 1
                                time.sleep(random.uniform(8.0, 15.0))
                        consecutive_errors = 0
                        st.last_error = None
                    except Exception as e:
                        consecutive_errors += 1
                        st.errors += 1
                        st.last_error = f"{type(e).__name__}: {e}"
                        log.error("poll failed: %s", e)
                        log.debug(traceback.format_exc())
                        if consecutive_errors >= 5:
                            log.error("5 consecutive failures — stopping")
                            break

                    st.touch_poll()
                    status.write(paths.STATUS_FILE, st)

                    sleep_for = _jitter(cfg.poll_seconds, cfg.poll_jitter_seconds)
                    end = time.monotonic() + sleep_for
                    while _running and time.monotonic() < end:
                        time.sleep(0.5)

            browser.close()
    finally:
        st.state = "stopped"
        status.write(paths.STATUS_FILE, st)
        log.info("watcher stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
