"""Comment scraper. Opens a Facebook post and extracts visible comments."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page, TimeoutError as PWTimeout

from . import paths

log = logging.getLogger(__name__)


@dataclass
class Comment:
    commenter_id: str
    commenter_name: str
    profile_url: str
    text: str
    comment_id: str | None


_PROFILE_ID_PAT = re.compile(r"id=(\d+)")


def _commenter_id_from_url(url: str) -> str | None:
    """Extract a stable id from a profile URL.

    https://www.facebook.com/profile.php?id=12345         -> "12345"
    https://www.facebook.com/jane.doe                      -> "jane.doe"
    https://www.facebook.com/groups/<gid>/user/<uid>/      -> "<uid>"
    """
    if not url:
        return None
    parsed = urlparse(url)
    full = parsed.path + ("?" + parsed.query if parsed.query else "")
    if "profile.php" in full:
        m = _PROFILE_ID_PAT.search(parsed.query or url)
        if m:
            return m.group(1)
    path = parsed.path.strip("/")
    if not path:
        return None
    parts = path.split("/")
    first = parts[0]
    # Group user link: /groups/<gid>/user/<uid>/...
    if first == "groups" and len(parts) >= 4 and parts[2] == "user":
        return parts[3]
    if first in {"groups", "pages", "watch", "events", "marketplace", "share", "stories"}:
        return None
    return first or None


def _expand_more_buttons(page: Page, max_clicks: int = 30) -> None:
    """Click 'View more comments' / 'View N replies' / 'See more' buttons."""
    patterns = [
        re.compile(r"view\s+more\s+comments", re.I),
        re.compile(r"view\s+previous\s+comments", re.I),
        re.compile(r"view\s+\d+\s+more\s+comments?", re.I),
        re.compile(r"view\s+\d+\s+repl(y|ies)", re.I),
        re.compile(r"^see\s+more$", re.I),
    ]
    clicked = 0
    for _ in range(max_clicks):
        progressed = False
        for pat in patterns:
            try:
                button = page.get_by_role("button", name=pat).first
                if button and button.is_visible(timeout=400):
                    button.click(timeout=1500)
                    page.wait_for_timeout(500)
                    clicked += 1
                    progressed = True
                    break
            except (PWTimeout, Exception):
                continue
        if not progressed:
            break
    if clicked:
        log.debug("expanded %d sections", clicked)


def _scroll_to_load(page: Page, rounds: int = 4) -> None:
    """Wheel-scroll to trigger lazy comment rendering."""
    for _ in range(rounds):
        try:
            page.mouse.wheel(0, 700)
        except Exception:
            break
        page.wait_for_timeout(400)


_PROBE_PREFIXES = (
    # English
    "Comment by",
    # Norwegian
    "Kommentar av",
    # Swedish/Danish
    "Kommentar fra",
    # German
    "Kommentar von",
    # French
    "Commentaire de",
    # Spanish
    "Comentario de",
    # Italian
    "Commento di",
    # Portuguese
    "Comentário de",
    # Dutch
    "Reactie van",
)


def _save_debug(page: Page, reason: str) -> None:
    """Dump page HTML + screenshot + selector probe when scraping returns nothing."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        debug_dir = paths.LOG_DIR / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        html_path = debug_dir / f"{ts}_{reason}.html"
        png_path = debug_dir / f"{ts}_{reason}.png"
        probe_path = debug_dir / f"{ts}_{reason}.probe.txt"

        # Full DOM after JS render — no truncation.
        try:
            full = page.evaluate("() => document.documentElement.outerHTML")
        except Exception:
            full = page.content()
        html_path.write_text(full, encoding="utf-8")

        page.screenshot(path=str(png_path), full_page=False)

        lines = [
            f"url: {page.url}",
            f"title: {page.title()}",
            f"html_size: {len(full)}",
            "",
            "selector counts:",
            f"  [aria-label^='Comment by' i]                    -> {page.locator('[aria-label^=\"Comment by\" i]').count()}",
            f"  [aria-label^='Kommentar av' i]                  -> {page.locator('[aria-label^=\"Kommentar av\" i]').count()}",
            f"  [role='article']                                -> {page.locator('[role=\"article\"]').count()}",
            f"  [role='article'][aria-label]                    -> {page.locator('[role=\"article\"][aria-label]').count()}",
            f"  [role='dialog']                                 -> {page.locator('[role=\"dialog\"]').count()}",
            f"  a[role='link'][href*='/']                       -> {page.locator('a[role=\"link\"][href*=\"/\"]').count()}",
            "",
            "Comment-by elements (aria-label, first anchor href, snippet):",
        ]
        try:
            comment_dump = page.evaluate(
                """() => {
                    const sels = [
                        '[aria-label^="Comment by" i]',
                        '[aria-label^="Kommentar av" i]',
                        '[aria-label^="Kommentar fra" i]',
                        '[aria-label^="Kommentar von" i]',
                        '[aria-label^="Commentaire de" i]',
                        '[aria-label^="Comentario de" i]',
                        '[aria-label^="Commento di" i]',
                        '[aria-label^="Comentário de" i]',
                        '[aria-label^="Reactie van" i]',
                    ].join(',');
                    return Array.from(document.querySelectorAll(sels)).slice(0,20).map(el => {
                        const a = el.querySelector('a[href]');
                        return {
                            label: el.getAttribute('aria-label'),
                            href: a ? a.getAttribute('href') : null,
                            text: (el.innerText || '').slice(0,200),
                        };
                    });
                }"""
            )
            for c in comment_dump:
                lines.append(f"  label={c['label']!r}")
                lines.append(f"    href={c['href']!r}")
                lines.append(f"    text={c['text']!r}")
        except Exception as e:
            lines.append(f"  (probe failed: {e})")
        lines.append("")
        lines.append("All article[aria-label] elements:")
        try:
            arts = page.evaluate(
                """() => Array.from(document.querySelectorAll('[role="article"][aria-label]'))
                    .map(el => el.getAttribute('aria-label'))"""
            )
            for label in arts:
                lines.append(f"  {label!r}")
        except Exception as e:
            lines.append(f"  (probe failed: {e})")

        probe_path.write_text("\n".join(lines), encoding="utf-8")
        log.info("debug snapshot saved: %s", html_path.name)
    except Exception as e:
        log.debug("debug snapshot failed: %s", e)


_NAME_FROM_ARIA = re.compile(
    r"^(?:Comment by|Kommentar av|Kommentar fra|Kommentar von|Commentaire de|Comentario de|Commento di|Comentário de|Reactie van)\s+(.+?)(?:\s+\d+\s+\S.*)?$",
    re.I,
)

# Trailing UI meta lines to strip from comment text:
# "17m", "2h", "Like", "Reply", "Like  Reply", "Edited", "5d ago", "Share", etc.
_META_LINE = re.compile(
    r"^(?:\d+\s*[smhdwy]\s*(?:ago)?|like|reply|share|edit(?:ed)?|like\s+reply|see translation)$",
    re.I,
)


_EXTRACT_JS = """
(el) => {
    const anchors = Array.from(el.querySelectorAll('a[href]'));
    let href = null;
    for (const a of anchors) {
        const h = a.getAttribute('href');
        if (!h) continue;
        if (h.startsWith('#') || h.startsWith('javascript:')) continue;
        // Skip in-page like/reply/comment-anchor links.
        if (h.startsWith('/groups/') && h.includes('/permalink/')) continue;
        if (h.includes('comment_id=')) continue;
        href = h;
        break;
    }
    return {
        label: el.getAttribute('aria-label') || '',
        href: href,
        text: el.innerText || '',
        id: el.getAttribute('id') || null,
    };
}
"""


def _extract_from_node(node: Locator) -> Comment | None:
    """Pull commenter id/name/text from a comment element via single JS round-trip."""
    try:
        data = node.evaluate(_EXTRACT_JS)
    except Exception as e:
        log.debug("evaluate failed: %s", e)
        return None
    if not data:
        return None

    aria = data.get("label") or ""
    m = _NAME_FROM_ARIA.match(aria)
    name_from_aria = m.group(1).strip() if m else ""

    href = data.get("href")
    if not href:
        log.info("extract: no usable href in node (aria=%r)", aria[:80])
        return None
    if href.startswith("/"):
        href = "https://www.facebook.com" + href
    cid = _commenter_id_from_url(href)
    if not cid:
        log.info("extract: cid not parseable from href=%r", href)
        return None

    full_text = (data.get("text") or "").strip()
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    # Strip a leading author-name line.
    if lines and name_from_aria and lines[0] == name_from_aria:
        lines = lines[1:]
    # Strip trailing UI meta lines (timestamp, Like, Reply, Share, Edited, …).
    while lines and _META_LINE.match(lines[-1]):
        lines.pop()
    body = "\n".join(lines).strip()

    if not body:
        log.info("extract: empty body after stripping (aria=%r, text=%r)",
                 aria[:80], full_text[:120])
        return None

    return Comment(
        commenter_id=cid,
        commenter_name=name_from_aria or cid,
        profile_url=href.split("?")[0] if "profile.php" not in href else href,
        text=body,
        comment_id=data.get("id"),
    )


def _comment_nodes(page: Page) -> list[Locator]:
    """Try several selector strategies. Return the first that yields nodes."""
    # Build a multilingual prefix-match selector.
    prefix_sel = ", ".join(f'[aria-label^="{p}" i]' for p in _PROBE_PREFIXES)
    strategies = [
        ("multilingual aria-label prefix", prefix_sel),
        ("article + aria-label (any lang)", 'div[role="article"][aria-label]:not([aria-label=""])'),
    ]
    for label, sel in strategies:
        nodes = page.locator(sel).all()
        if nodes:
            log.info("comment selector hit: %s -> %d", label, len(nodes))
            return nodes

    arts = page.get_by_role("article").all()
    log.info("fallback to role=article -> %d nodes", len(arts))
    return arts[1:] if len(arts) > 1 else []


_COMMENT_MARKER_SEL = ", ".join(
    f'[aria-label^="{p}" i]' for p in _PROBE_PREFIXES
)


def _wait_for_comments(page: Page, timeout_ms: int = 15_000) -> bool:
    """Wait until at least one comment-marked element exists in the DOM."""
    try:
        page.wait_for_selector(_COMMENT_MARKER_SEL, timeout=timeout_ms, state="attached")
        return True
    except PWTimeout:
        return False


def scrape(page: Page, post_url: str, *, expand: bool = True) -> list[Comment]:
    """Open the post and return all visible comments."""
    page.goto(post_url, wait_until="domcontentloaded", timeout=30_000)

    # First-pass wait for any post/dialog shell.
    try:
        page.wait_for_selector(
            '[role="article"], [role="dialog"]',
            timeout=10_000,
            state="attached",
        )
    except PWTimeout:
        pass

    try:
        page.wait_for_load_state("networkidle", timeout=4_000)
    except PWTimeout:
        pass

    # Scroll to encourage lazy comment render.
    _scroll_to_load(page, rounds=3)

    if expand:
        _expand_more_buttons(page)
        _scroll_to_load(page, rounds=2)

    # Now wait specifically for at least one comment marker. Retry across a
    # few scroll/expand rounds if FB hasn't rendered them yet.
    for attempt in range(3):
        if _wait_for_comments(page, timeout_ms=8_000):
            break
        log.info("no comment markers yet (attempt %d), scrolling more", attempt + 1)
        _scroll_to_load(page, rounds=3)
        _expand_more_buttons(page)

    nodes = _comment_nodes(page)
    comments: list[Comment] = []
    seen: set[str] = set()
    for node in nodes:
        c = _extract_from_node(node)
        if c is None:
            continue
        key = f"{c.commenter_id}::{c.text[:80]}"
        if key in seen:
            continue
        seen.add(key)
        comments.append(c)

    if not comments:
        _save_debug(page, "no_comments")
    log.info("scraped %d candidate comments", len(comments))
    return comments
