"""Post a reply to a Facebook comment, optionally @-tagging the commenter."""
from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Literal

from playwright.sync_api import Locator, Page, TimeoutError as PWTimeout

from . import paths

log = logging.getLogger(__name__)

ReplyResult = Literal["sent", "error"]

# Reply button visible labels across FB locales we support.
_REPLY_LABELS = (
    "Reply", "Svar", "Antworten", "Répondre",
    "Responder", "Rispondi", "Beantwoorden",
)

# Suggestion popup shows up as a listbox / role=combobox container.
_SUGGESTION_SEL = (
    'ul[role="listbox"] [role="option"], '
    'div[role="listbox"] [role="option"], '
    '[role="combobox"] [role="option"]'
)


def _save_reply_debug(page: Page, reason: str, commenter_id: str) -> None:
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        debug_dir = paths.LOG_DIR / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        png = debug_dir / f"{ts}_reply_{reason}_{commenter_id}.png"
        html = debug_dir / f"{ts}_reply_{reason}_{commenter_id}.html"
        page.screenshot(path=str(png), full_page=False)
        try:
            full = page.evaluate("() => document.documentElement.outerHTML")
        except Exception:
            full = page.content()
        html.write_text(full, encoding="utf-8")
        log.info("reply debug snapshot: %s", png.name)
    except Exception as e:
        log.debug("reply debug failed: %s", e)


def _find_comment_article(page: Page, commenter_id: str) -> Locator | None:
    """Locate the article element whose anchors point at this commenter."""
    js = """
    (id) => {
        const arts = Array.from(document.querySelectorAll('[role="article"][aria-label]'));
        for (let i = 0; i < arts.length; i++) {
            const a = arts[i];
            const links = Array.from(a.querySelectorAll('a[href]'));
            for (const l of links) {
                const h = l.getAttribute('href') || '';
                if (h.includes(id) && !h.includes('comment_id=')) {
                    a.setAttribute('data-fbcw-target', '1');
                    return true;
                }
            }
        }
        return false;
    }
    """
    try:
        hit = page.evaluate(js, commenter_id)
    except Exception as e:
        log.debug("find_comment_article evaluate failed: %s", e)
        return None
    if not hit:
        return None
    return page.locator('[data-fbcw-target="1"]').first


def _click_reply_button(article: Locator) -> bool:
    """Click the Reply/Svar/etc button inside this comment article."""
    for label in _REPLY_LABELS:
        # role=button with exact text match (FB sometimes wraps in span).
        btn = article.get_by_role("button", name=re.compile(rf"^{re.escape(label)}$", re.I)).first
        try:
            if btn.is_visible(timeout=400):
                btn.click()
                return True
        except Exception:
            continue
    # Fallback: any button containing the text.
    for label in _REPLY_LABELS:
        try:
            btn = article.locator(f'[role="button"]:has-text("{label}")').first
            if btn.is_visible(timeout=400):
                btn.click()
                return True
        except Exception:
            continue
    return False


def _find_reply_textbox(page: Page, timeout_ms: int = 6_000) -> Locator | None:
    """After clicking Reply, find the newly-revealed contenteditable input."""
    selectors = [
        'div[role="textbox"][aria-label*="reply" i]',
        'div[role="textbox"][aria-label*="svar" i]',
        'div[role="textbox"][aria-label*="comment" i]',
        'div[role="textbox"][aria-label*="kommentar" i]',
        'div[role="textbox"][contenteditable="true"]',
    ]
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for sel in selectors:
            loc = page.locator(sel).last  # newest one is the just-opened reply box
            try:
                if loc.is_visible(timeout=300):
                    return loc
            except Exception:
                continue
        time.sleep(0.3)
    return None


def _try_at_mention(page: Page, box: Locator, name: str) -> bool:
    """Type @ + first part of name, wait for suggestion popup, click first option.

    Returns True if a tag was inserted, False otherwise.
    """
    short = name.split()[0] if name else ""
    if not short:
        return False
    try:
        box.click()
        # Type "@" then a few characters slowly so FB can fire its query.
        box.type("@", delay=80)
        for ch in short[:6]:
            box.type(ch, delay=90)
        # Wait briefly for suggestion list.
        try:
            page.wait_for_selector(_SUGGESTION_SEL, timeout=2_500, state="visible")
        except PWTimeout:
            return False
        first = page.locator(_SUGGESTION_SEL).first
        if not first.is_visible(timeout=400):
            return False
        first.click()
        return True
    except Exception as e:
        log.debug("@-mention attempt failed: %s", e)
        return False


def _clear_box(box: Locator) -> None:
    try:
        box.click()
        box.press("Control+A")
        box.press("Delete")
    except Exception:
        pass


def reply(
    page: Page,
    post_url: str,
    commenter_id: str,
    commenter_name: str,
    template: str,
) -> ReplyResult:
    """Reply to the comment from `commenter_id` on `post_url`.

    `template` may include `{name}` — replaced with the commenter name when
    real @-tagging fails so the person is at least addressed by name.
    """
    log.info("reply: open post for %s (%s)", commenter_name, commenter_id)
    try:
        page.goto(post_url, wait_until="domcontentloaded", timeout=30_000)
    except PWTimeout:
        log.warning("reply: nav timeout")
        return "error"
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PWTimeout:
        pass

    # Comments may be lazy-loaded — give it a small scroll nudge.
    try:
        page.evaluate("() => window.scrollTo(0, 800)")
    except Exception:
        pass
    time.sleep(1.0)

    article = _find_comment_article(page, commenter_id)
    if article is None:
        log.warning("reply: comment article not found for %s", commenter_id)
        _save_reply_debug(page, "no_article", commenter_id)
        return "error"

    if not _click_reply_button(article):
        log.warning("reply: Reply button not found in article for %s", commenter_id)
        _save_reply_debug(page, "no_reply_btn", commenter_id)
        return "error"

    box = _find_reply_textbox(page, timeout_ms=8_000)
    if box is None:
        log.warning("reply: textbox didn't appear after clicking Reply")
        _save_reply_debug(page, "no_textbox", commenter_id)
        return "error"

    # Random pre-type pause to look human.
    time.sleep(random.uniform(1.5, 3.0))

    tagged = _try_at_mention(page, box, commenter_name)
    if not tagged:
        log.info("reply: @-mention unavailable, falling back to plain name for %s", commenter_id)
        _clear_box(box)

    # Fill in the rest of the message. {name} only consumed by the fallback.
    if tagged:
        rest = template.replace("{name}", "").strip()
        # Keep a leading space between the tag and the rest of the message.
        rest = (" " + rest) if rest and not rest.startswith((" ", ",", "!", ".")) else rest
    else:
        rest = template.replace("{name}", commenter_name or "")

    try:
        box.type(rest, delay=20)
        time.sleep(random.uniform(0.4, 1.0))
        box.press("Enter")
    except Exception as e:
        log.warning("reply: type/send failed: %s", e)
        _save_reply_debug(page, "send_failed", commenter_id)
        return "error"

    # Brief settle so the reply gets posted before we navigate away.
    page.wait_for_timeout(1500)
    log.info("reply posted to %s (tagged=%s)", commenter_id, tagged)
    return "sent"
