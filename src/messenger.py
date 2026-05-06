"""Send a Messenger DM to a given commenter via messenger.com."""
from __future__ import annotations

import logging
import random
import re
import time
from typing import Literal

from playwright.sync_api import Page, TimeoutError as PWTimeout

log = logging.getLogger(__name__)

SendResult = Literal["sent", "blocked", "error"]


def send(page: Page, commenter_id: str, message: str) -> SendResult:
    """Open messenger.com/t/<id> and send `message`. Returns outcome."""
    url = f"https://www.messenger.com/t/{commenter_id}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
    except PWTimeout:
        log.warning("messenger.com nav timed out for %s", commenter_id)
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
    blocked_patterns = [
        re.compile(r"isn'?t receiving messages", re.I),
        re.compile(r"can'?t reply to this conversation", re.I),
        re.compile(r"this person is unavailable", re.I),
    ]
    if any(p.search(body_text) for p in blocked_patterns):
        log.info("DM blocked by recipient privacy: %s", commenter_id)
        return "blocked"

    compose = page.get_by_role("textbox", name=re.compile(r"message", re.I)).first
    try:
        compose.wait_for(state="visible", timeout=8_000)
    except PWTimeout:
        log.warning("compose box not found for %s", commenter_id)
        return "error"

    time.sleep(random.uniform(2.0, 5.0))

    try:
        compose.click()
        compose.fill(message)
        time.sleep(random.uniform(0.4, 1.2))
        compose.press("Enter")
    except Exception as e:
        log.warning("send failed for %s: %s", commenter_id, e)
        return "error"

    page.wait_for_timeout(1500)
    log.info("DM sent to %s", commenter_id)
    return "sent"
