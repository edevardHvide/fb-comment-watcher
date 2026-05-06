"""One-time Facebook login bootstrap. Saves Playwright storage_state.

Run with `uv run python -m src.auth` (or via the Auth page in the UI).
Opens a headed Chromium window, lets the user log in manually, and saves
.auth/storage_state.json automatically once Facebook sets the logged-in
cookie (c_user). Also handles the case where the user closes the window.

Designed to work whether stdin is a TTY (run from terminal) or detached
(run as a subprocess from the Streamlit UI).
"""
from __future__ import annotations

import sys
import time

from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from . import paths

LOGIN_URL = "https://www.facebook.com/"
POLL_INTERVAL_SEC = 2.0
TIMEOUT_SEC = 600  # 10 min


def _is_logged_in(context) -> bool:
    """Facebook sets a c_user cookie containing the numeric user id on login."""
    try:
        for c in context.cookies():
            if c.get("name") == "c_user" and c.get("value"):
                return True
    except PWError:
        pass
    return False


def _context_alive(context) -> bool:
    try:
        _ = context.pages
        return True
    except PWError:
        return False


def run() -> int:
    paths.AUTH_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60, flush=True)
    print("Opening Chromium. Log in to Facebook in the new window.", flush=True)
    print("This will save your session automatically.", flush=True)
    print("(Close the window or press Ctrl+C to abort.)", flush=True)
    print("=" * 60, flush=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
        except PWError as e:
            print(f"Failed to open Facebook: {e}", file=sys.stderr, flush=True)
            browser.close()
            return 1

        deadline = time.monotonic() + TIMEOUT_SEC
        try:
            while time.monotonic() < deadline:
                if not _context_alive(context):
                    print("Window closed before login completed.", file=sys.stderr, flush=True)
                    return 1
                if _is_logged_in(context):
                    print("Login detected. Saving session...", flush=True)
                    context.storage_state(path=str(paths.AUTH_STATE))
                    paths.AUTH_STATE.chmod(0o600)
                    print(f"Session saved to {paths.AUTH_STATE}", flush=True)
                    time.sleep(1.0)
                    browser.close()
                    return 0
                time.sleep(POLL_INTERVAL_SEC)
        except KeyboardInterrupt:
            print("\nAborted.", file=sys.stderr, flush=True)
            try:
                browser.close()
            except PWError:
                pass
            return 1

        print("Timed out waiting for login.", file=sys.stderr, flush=True)
        try:
            browser.close()
        except PWError:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
