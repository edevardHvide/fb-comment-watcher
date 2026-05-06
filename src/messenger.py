"""Send a Messenger DM to a given commenter via messenger.com."""
from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Literal

from playwright.sync_api import Page, TimeoutError as PWTimeout

from . import paths

log = logging.getLogger(__name__)

SendResult = Literal["sent", "blocked", "error"]

_BLOCKED_PATTERNS = [
    re.compile(r"isn'?t receiving messages", re.I),
    re.compile(r"can'?t reply to this conversation", re.I),
    re.compile(r"this person is unavailable", re.I),
    re.compile(r"this conversation isn'?t available", re.I),
]


def _save_messenger_debug(page: Page, reason: str, commenter_id: str) -> None:
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        debug_dir = paths.LOG_DIR / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        png = debug_dir / f"{ts}_msg_{reason}_{commenter_id}.png"
        html = debug_dir / f"{ts}_msg_{reason}_{commenter_id}.html"
        page.screenshot(path=str(png), full_page=False)
        try:
            full = page.evaluate("() => document.documentElement.outerHTML")
        except Exception:
            full = page.content()
        html.write_text(full, encoding="utf-8")
        log.info("messenger debug snapshot: %s", png.name)
    except Exception as e:
        log.debug("messenger debug failed: %s", e)


def _find_compose(page: Page, timeout_ms: int = 8_000):
    """Try several selectors. Return the first visible compose box, else None."""
    selectors = [
        'div[role="textbox"][aria-label*="message" i]',
        'div[role="textbox"][aria-label*="melding" i]',  # Norwegian: melding
        'div[role="textbox"][contenteditable="true"]',
        '[aria-label*="Aa" i][role="textbox"]',
    ]
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                if loc.is_visible(timeout=300):
                    return loc
            except Exception:
                continue
        time.sleep(0.4)
    return None


_messenger_session_ready = False


def _bootstrap_messenger(page: Page) -> bool:
    """Navigate to messenger.com root and confirm we're authenticated.

    The FB login session does not cover the messenger.com domain on its own;
    we need to visit messenger.com so it can SSO via the FB cookies and set
    its own session cookies on this domain. Returns True if authenticated.
    """
    global _messenger_session_ready
    if _messenger_session_ready:
        return True
    try:
        page.goto("https://www.messenger.com/", wait_until="domcontentloaded", timeout=20_000)
    except PWTimeout:
        return False
    try:
        page.wait_for_load_state("networkidle", timeout=8_000)
    except PWTimeout:
        pass
    if "login" in page.url:
        log.warning("messenger.com still redirecting to login: %s", page.url)
        return False
    _messenger_session_ready = True
    log.info("messenger.com session bootstrapped (url=%s)", page.url)
    return True


def send(page: Page, commenter_id: str, message: str) -> SendResult:
    """Open messenger.com/t/<id> and send `message`. Returns outcome."""
    if not _bootstrap_messenger(page):
        log.warning("messenger session not authenticated; cannot send")
        _save_messenger_debug(page, "not_authenticated", commenter_id)
        return "error"

    url = f"https://www.messenger.com/t/{commenter_id}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
    except PWTimeout:
        log.warning("messenger.com nav timed out for %s", commenter_id)
        _save_messenger_debug(page, "nav_timeout", commenter_id)
        return "error"

    try:
        page.wait_for_load_state("networkidle", timeout=6_000)
    except PWTimeout:
        pass

    body_text = ""
    try:
        body_text = page.inner_text("body", timeout=2_000)
    except Exception:
        pass
    if any(p.search(body_text) for p in _BLOCKED_PATTERNS):
        log.info("DM blocked by recipient privacy: %s", commenter_id)
        return "blocked"

    compose = _find_compose(page, timeout_ms=8_000)
    if compose is None:
        log.warning("compose box not found for %s (url=%s)", commenter_id, page.url)
        _save_messenger_debug(page, "no_compose", commenter_id)
        return "error"

    time.sleep(random.uniform(2.0, 5.0))

    try:
        compose.click()
        compose.fill(message)
        time.sleep(random.uniform(0.4, 1.2))
        compose.press("Enter")
    except Exception as e:
        log.warning("send failed for %s: %s", commenter_id, e)
        _save_messenger_debug(page, "send_failed", commenter_id)
        return "error"

    page.wait_for_timeout(1500)
    log.info("DM sent to %s", commenter_id)
    return "sent"
