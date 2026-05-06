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
1. Click **Launch FB login window**.
2. A Chromium window will open. Log in to Facebook normally (handles 2-factor codes).
3. Once you're logged in, the window saves your session and closes itself automatically.
4. Refresh this page to confirm the green ✅ appears.
"""
)

if paths.AUTH_STATE.exists():
    mtime = datetime.fromtimestamp(paths.AUTH_STATE.stat().st_mtime, tz=timezone.utc)
    st.success(f"Session present — saved {relative_time(mtime.isoformat())}")
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
