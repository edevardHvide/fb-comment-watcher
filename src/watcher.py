"""Comment scraper. Opens a Facebook post and extracts visible comments."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError as PWTimeout

log = logging.getLogger(__name__)


@dataclass
class Comment:
    commenter_id: str
    commenter_name: str
    profile_url: str
    text: str
    comment_id: str | None


_PROFILE_ID_PAT = re.compile(r"(?:profile\.php\?id=|/)([\w.\-]+?)(?:[/?]|$)")


def _commenter_id_from_url(url: str) -> str | None:
    """Extract a stable id from a profile URL.

    Examples:
        https://www.facebook.com/profile.php?id=12345 -> "12345"
        https://www.facebook.com/jane.doe              -> "jane.doe"
        https://www.facebook.com/jane.doe/             -> "jane.doe"
    """
    if not url:
        return None
    parsed = urlparse(url)
    if "profile.php" in parsed.path or "profile.php" in url:
        m = re.search(r"id=(\d+)", parsed.query or "")
        if m:
            return m.group(1)
    path = parsed.path.strip("/")
    if not path:
        return None
    first = path.split("/")[0]
    if first in {"groups", "pages", "watch", "events", "marketplace"}:
        return None
    return first or None


def _expand_more_buttons(page: Page, max_clicks: int = 30) -> None:
    """Click 'View more comments' / 'View N replies' / 'See more' buttons."""
    patterns = [
        re.compile(r"view\s+more\s+comments", re.I),
        re.compile(r"view\s+previous\s+comments", re.I),
        re.compile(r"view\s+\d+\s+more\s+comments?", re.I),
        re.compile(r"view\s+\d+\s+repl(y|ies)", re.I),
        re.compile(r"see\s+more$", re.I),
    ]
    clicked = 0
    for _ in range(max_clicks):
        progressed = False
        for pat in patterns:
            try:
                button = page.get_by_role("button", name=pat).first
                if button and button.is_visible(timeout=500):
                    button.click(timeout=1500)
                    page.wait_for_timeout(600)
                    clicked += 1
                    progressed = True
                    break
            except (PWTimeout, Exception):
                continue
        if not progressed:
            break
    if clicked:
        log.debug("expanded %d comment/reply sections", clicked)


def scrape(page: Page, post_url: str, *, expand: bool = True) -> list[Comment]:
    """Open the post and return all visible comments.

    Selectors target ARIA roles. Facebook regularly rotates DOM; this is the
    most stable strategy short of a private API. Adjust as needed.
    """
    page.goto(post_url, wait_until="domcontentloaded", timeout=30_000)
    try:
        page.wait_for_load_state("networkidle", timeout=8_000)
    except PWTimeout:
        pass

    if expand:
        _expand_more_buttons(page)

    comments: list[Comment] = []
    seen_ids: set[str] = set()

    articles = page.get_by_role("article").all()
    for art in articles:
        try:
            html_id = art.get_attribute("aria-labelledby") or art.get_attribute("id")
            text = (art.inner_text(timeout=1500) or "").strip()
            if not text:
                continue
            anchor = art.locator("a[href*='facebook.com'], a[href^='/']").first
            href = anchor.get_attribute("href", timeout=500) if anchor else None
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.facebook.com" + href
            cid = _commenter_id_from_url(href)
            if not cid:
                continue
            name_text = ""
            try:
                name_text = (anchor.inner_text(timeout=500) or "").strip().splitlines()[0]
            except Exception:
                pass
            body = text
            if name_text and body.startswith(name_text):
                body = body[len(name_text):].strip()
            dedup_key = f"{cid}::{body[:80]}"
            if dedup_key in seen_ids:
                continue
            seen_ids.add(dedup_key)
            comments.append(
                Comment(
                    commenter_id=cid,
                    commenter_name=name_text or cid,
                    profile_url=href.split("?")[0],
                    text=body,
                    comment_id=html_id,
                )
            )
        except Exception as e:
            log.debug("skip article: %s", e)
            continue

    log.info("scraped %d candidate comments", len(comments))
    return comments
