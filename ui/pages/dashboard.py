"""Dashboard: KPIs, controls, activity preview, log tail."""
from __future__ import annotations

import streamlit as st

from src import config as cfgmod
from src import paths, process, state, status
from ui.components import outcome_badge, relative_time, status_badge

st.title("💬 FB Comment Watcher")

cfg = cfgmod.load()
errs = cfg.validation_errors()
running = process.is_running()


@st.fragment(run_every="2s")
def live_panel() -> None:
    cur = status.read(paths.STATUS_FILE)
    is_running = process.is_running()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Status", "Running" if is_running else "Stopped")
        st.markdown(status_badge(is_running))
    with c2:
        st.metric("Polls", cur.polls if cur else 0)
    with c3:
        st.metric("DMs sent", cur.sent if cur else 0)
    with c4:
        try:
            with state.connect(paths.STATE_DB, read_only=True) as db:
                today = state.count_today(db)
        except Exception:
            today = 0
        st.metric("Matches today", today)

    cap_bits = []
    if cur:
        cap_bits.append(f"Mode: {'DRY-RUN' if cur.dry_run else 'LIVE'}")
        if cur.last_poll_at:
            cap_bits.append(f"Last poll: {relative_time(cur.last_poll_at)}")
        if cur.last_error:
            cap_bits.append(f"⚠️ {cur.last_error}")
    st.caption(" • ".join(cap_bits) if cap_bits else "No status yet.")

    st.divider()

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Recent matches")
        try:
            with state.connect(paths.STATE_DB, read_only=True) as db:
                rows = state.recent(db, limit=10)
        except Exception:
            rows = []
        if not rows:
            st.info("No matches yet.")
        else:
            for r in rows:
                with st.container(border=True):
                    head, badge = st.columns([4, 1])
                    head.markdown(f"**{r['commenter_name']}** · {relative_time(r['sent_at'])}")
                    badge.markdown(outcome_badge(r["status"]))
                    st.caption(f"keyword: `{r['keyword']}`")
                    txt = r["comment_text"] or ""
                    st.text(txt[:240] + ("…" if len(txt) > 240 else ""))

    with right:
        st.subheader("Live log")
        st.code(process.tail_log(50), language="log", height=380)


# --- Static section: controls + warnings (don't auto-rerun) ---

if errs:
    st.warning("Config incomplete: " + "; ".join(errs) + " — set up on the Config page.")

if not paths.AUTH_STATE.exists():
    st.error("No Facebook session. Visit the **Auth** page to log in first.")

ctrl_left, ctrl_right = st.columns([2, 1])
with ctrl_left:
    if running:
        if st.button("⏹ Stop watcher", type="secondary", use_container_width=True):
            process.stop()
            st.rerun()
    else:
        disabled = bool(errs) or not paths.AUTH_STATE.exists()
        live_label = "▶ Start watcher (LIVE — sends DMs)" if not cfg.dry_run else "▶ Start watcher (dry-run)"
        if st.button(live_label, type="primary", use_container_width=True, disabled=disabled):
            try:
                process.start(live=not cfg.dry_run)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start: {e}")
with ctrl_right:
    st.caption(f"Post: `{cfg.post_url or '(unset)'}`")
    st.caption(f"Keywords: `{', '.join(cfg.keywords) or '(none)'}`")

st.divider()
live_panel()
