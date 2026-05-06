"""Two-step Facebook + Messenger login bootstrap.

Run with `uv run python -m src.auth` (or via the Auth page in the UI).

Flow:
  1. Open Chromium (re-using any existing saved session).
  2. Navigate to facebook.com — if not logged in, the user logs in manually.
     Detected automatically once the c_user cookie appears.
  3. Navigate to messenger.com — if not logged in, the user logs in manually.
     Detected automatically once the URL leaves /login.* on messenger.com.
  4. Save the combined storage_state covering both domains.

Designed to work whether stdin is a TTY or detached (run as a subprocess
from the Streamlit UI).
"""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from . import paths

FB_URL = "https://www.facebook.com/"
MESSENGER_URL = "https://www.messenger.com/"
POLL_INTERVAL_SEC = 1.5
TIMEOUT_SEC = 600  # 10 min per leg


def own_user_id() -> str | None:
    """Return the FB user id of the saved session, or None."""
    if not paths.AUTH_STATE.exists():
        return None
    try:
        data = json.loads(paths.AUTH_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for cookie in data.get("cookies", []):
        if cookie.get("name") == "c_user":
            return str(cookie.get("value") or "") or None
    return None


def _has_cookies_for(context, domain_substr: str, names: tuple[str, ...]) -> bool:
    try:
        cookies = context.cookies()
    except PWError:
        return False
    found = {c.get("name") for c in cookies if domain_substr in (c.get("domain") or "")}
    return any(n in found for n in names)


def _context_alive(context) -> bool:
    try:
        _ = context.pages
        return True
    except PWError:
        return False


def _wait_until(predicate, label: str) -> bool:
    deadline = time.monotonic() + TIMEOUT_SEC
    print(f"Waiting for {label}...", flush=True)
    while time.monotonic() < deadline:
        try:
            if predicate():
                print(f"  ✓ {label} detected", flush=True)
                return True
        except KeyboardInterrupt:
            return False
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)
    print(f"  ✗ timed out waiting for {label}", file=sys.stderr, flush=True)
    return False


def run() -> int:
    paths.AUTH_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 64, flush=True)
    print("Facebook + Messenger login", flush=True)
    print("Two windows of work: log in to Facebook AND to Messenger.", flush=True)
    print("Each is detected automatically once you complete it.", flush=True)
    print("=" * 64, flush=True)

    storage_state = (
        str(paths.AUTH_STATE) if paths.AUTH_STATE.exists() else None
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(storage_state=storage_state)
        page = context.new_page()

        # ---- Step 1: Facebook ----
        try:
            page.goto(FB_URL, wait_until="domcontentloaded", timeout=30_000)
        except PWError as e:
            print(f"Failed to open Facebook: {e}", file=sys.stderr, flush=True)
            browser.close()
            return 1

        fb_ok = _wait_until(
            lambda: _has_cookies_for(context, "facebook.com", ("c_user",)) and _context_alive(context),
            "Facebook login",
        )
        if not fb_ok:
            browser.close()
            return 1

        # ---- Step 2: Messenger ----
        print("Opening messenger.com — log in there too if prompted.", flush=True)
        try:
            page.goto(MESSENGER_URL, wait_until="domcontentloaded", timeout=30_000)
        except PWError as e:
            print(f"Failed to open Messenger: {e}", file=sys.stderr, flush=True)
            browser.close()
            return 1

        def messenger_ok() -> bool:
            if not _context_alive(context):
                return False
            url = page.url or ""
            if "login" in url.lower():
                return False
            # Either we're past login.php on messenger.com or we have a session cookie there.
            on_messenger = "messenger.com" in url
            has_session = _has_cookies_for(context, "messenger.com", ("xs", "c_user"))
            return on_messenger and has_session

        msg_ok = _wait_until(messenger_ok, "Messenger login")
        if not msg_ok:
            browser.close()
            return 1

        # ---- Save ----
        try:
            context.storage_state(path=str(paths.AUTH_STATE))
            paths.AUTH_STATE.chmod(0o600)
            print(f"Combined session saved to {paths.AUTH_STATE}", flush=True)
            data = json.loads(paths.AUTH_STATE.read_text())
            fb = sum(1 for c in data.get("cookies", []) if "facebook.com" in (c.get("domain") or ""))
            msg = sum(1 for c in data.get("cookies", []) if "messenger.com" in (c.get("domain") or ""))
            print(f"  facebook.com cookies: {fb}", flush=True)
            print(f"  messenger.com cookies: {msg}", flush=True)
        finally:
            time.sleep(0.5)
            try:
                browser.close()
            except PWError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
