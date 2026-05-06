"""Auth: bootstrap or refresh the Facebook session."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone

import streamlit as st

from src import paths
from ui.components import relative_time

st.title("🔐 Auth")

st.markdown(
    """
The watcher needs sessions for **both** Facebook (to read comments) and Messenger (to send DMs).
The launch button opens one Chromium window that walks you through both logins:

1. Click **Launch FB login window**.
2. **Step 1 — Facebook**: log in normally (handles 2-factor codes).
3. **Step 2 — Messenger**: the same window navigates to messenger.com. Log in there too if prompted.
4. The window saves your session and closes itself automatically.
5. Refresh this page to confirm the green ✅ appears.
"""
)

def _cookie_summary() -> tuple[int, int]:
    import json
    try:
        data = json.loads(paths.AUTH_STATE.read_text())
    except Exception:
        return (0, 0)
    cookies = data.get("cookies", [])
    fb = sum(1 for c in cookies if "facebook.com" in (c.get("domain") or ""))
    msg = sum(1 for c in cookies if "messenger.com" in (c.get("domain") or ""))
    return (fb, msg)


if paths.AUTH_STATE.exists():
    mtime = datetime.fromtimestamp(paths.AUTH_STATE.stat().st_mtime, tz=timezone.utc)
    fb_n, msg_n = _cookie_summary()
    if fb_n > 0 and msg_n > 0:
        st.success(
            f"Session present — saved {relative_time(mtime.isoformat())} "
            f"· facebook.com cookies: {fb_n} · messenger.com cookies: {msg_n}"
        )
    elif fb_n > 0:
        st.warning(
            f"Facebook session OK ({fb_n} cookies), but **no Messenger session** "
            f"({msg_n} cookies). Re-run the login flow — the watcher cannot send DMs without it."
        )
    else:
        st.warning("Session file exists but has no Facebook cookies. Re-run the login flow.")
else:
    st.warning("No session saved yet.")

st.caption(f"Session file: `{paths.AUTH_STATE}`")

st.divider()

AUTH_LOG = paths.LOG_DIR / "auth.log"

if st.button("🚀 Launch FB login window", type="primary", use_container_width=True):
    try:
        paths.LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_handle = AUTH_LOG.open("w")
        subprocess.Popen(
            [sys.executable, "-m", "src.auth"],
            cwd=str(paths.ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        st.info(
            "Chromium is launching. Log in to Facebook in the new window. "
            "It saves and closes automatically once you're logged in."
        )
    except Exception as e:
        st.error(f"Failed to launch: {e}")

if AUTH_LOG.exists():
    st.subheader("Auth log")
    st.code(AUTH_LOG.read_text()[-2_000:], language="log")

if paths.AUTH_STATE.exists():
    st.divider()
    if st.button("🗑 Delete saved session", type="secondary"):
        paths.AUTH_STATE.unlink()
        st.toast("Session deleted.", icon="🗑")
        st.rerun()
