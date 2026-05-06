"""Activity: filterable table of all matches and DM outcomes."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import paths, state

st.title("📋 Activity")

try:
    with state.connect(paths.STATE_DB, read_only=True) as db:
        rows = state.recent(db, limit=10_000)
except Exception as e:
    st.warning(f"State DB not available: {e}")
    rows = []

if not rows:
    st.info("No comments processed yet. Start the watcher from the Dashboard.")
    st.stop()

df = pd.DataFrame([dict(r) for r in rows])
df["sent_at"] = pd.to_datetime(df["sent_at"], utc=True, errors="coerce")

with st.sidebar:
    st.markdown("### Filters")
    statuses = sorted(df["status"].dropna().unique().tolist())
    sel_status = st.multiselect("Status", statuses, default=statuses)
    keyword_q = st.text_input("Search comment text")

filtered = df[df["status"].isin(sel_status)]
if keyword_q:
    filtered = filtered[filtered["comment_text"].str.contains(keyword_q, case=False, na=False)]

st.caption(f"{len(filtered)} of {len(df)} rows")

st.dataframe(
    filtered[
        [
            "sent_at",
            "commenter_name",
            "comment_text",
            "keyword",
            "status",
            "profile_url",
        ]
    ],
    use_container_width=True,
    hide_index=True,
    column_config={
        "sent_at": st.column_config.DatetimeColumn("When", format="YYYY-MM-DD HH:mm"),
        "commenter_name": "Commenter",
        "comment_text": st.column_config.TextColumn("Comment", width="large"),
        "keyword": "Keyword",
        "status": "Status",
        "profile_url": st.column_config.LinkColumn("Profile", display_text="open"),
    },
)
