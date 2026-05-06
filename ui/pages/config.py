"""Config: edit config.yaml safely from the UI."""
from __future__ import annotations

import streamlit as st

from src import config as cfgmod
from src import process

st.title("⚙️ Config")

cfg = cfgmod.load()
running = process.is_running()

if running:
    st.warning("Watcher is running. Save changes, then stop & restart it from the Dashboard for changes to take effect.")

with st.form("config_form", clear_on_submit=False):
    post_url = st.text_input(
        "Post URL",
        value=cfg.post_url,
        placeholder="https://www.facebook.com/...",
        help="Full URL of the Facebook post to monitor.",
    )

    kw_text = st.text_area(
        "Keywords (one per line)",
        value="\n".join(cfg.keywords),
        height=120,
        help="A comment containing ANY of these (case-insensitive substring) triggers a DM.",
    )

    exclude_text = st.text_area(
        "Exclude keywords (one per line)",
        value="\n".join(cfg.exclude_keywords),
        height=100,
        help="If a comment contains ANY of these, it is skipped — even if it matches an include keyword.",
    )

    template = st.text_area(
        "Message template",
        value=cfg.message_template,
        height=140,
        help="Sent verbatim. No placeholders in v1.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        poll_seconds = st.number_input(
            "Poll interval (seconds)",
            min_value=5,
            max_value=600,
            value=int(cfg.poll_seconds),
            step=1,
        )
    with c2:
        poll_jitter = st.number_input(
            "Jitter (± seconds)",
            min_value=0,
            max_value=60,
            value=int(cfg.poll_jitter_seconds),
            step=1,
        )
    with c3:
        dry_run = st.toggle(
            "Dry-run mode",
            value=cfg.dry_run,
            help="When ON: detect matches and log, but do NOT send DMs.",
        )

    if poll_seconds < 15:
        st.caption("⚠️ Polling under 15 s increases anti-bot detection risk.")

    submitted = st.form_submit_button("💾 Save", type="primary", use_container_width=True)

if submitted:
    keywords = [k.strip() for k in kw_text.splitlines() if k.strip()]
    exclude_keywords = [k.strip() for k in exclude_text.splitlines() if k.strip()]
    new_cfg = cfgmod.Config(
        post_url=post_url.strip(),
        keywords=keywords,
        exclude_keywords=exclude_keywords,
        message_template=template.strip(),
        poll_seconds=int(poll_seconds),
        poll_jitter_seconds=int(poll_jitter),
        dry_run=bool(dry_run),
    )
    errs = new_cfg.validation_errors()
    if errs:
        st.error("Cannot save: " + "; ".join(errs))
    else:
        cfgmod.save(new_cfg)
        st.toast("Saved.", icon="✅")

st.divider()
st.subheader("Current config (on disk)")
cur = cfgmod.load()
st.code(
    f"post_url: {cur.post_url}\n"
    f"keywords: {cur.keywords}\n"
    f"exclude_keywords: {cur.exclude_keywords}\n"
    f"poll_seconds: {cur.poll_seconds} (± {cur.poll_jitter_seconds})\n"
    f"dry_run: {cur.dry_run}\n"
    f"message_template: |\n  {cur.message_template[:200]}",
    language="yaml",
)
