"""Streamlit entry point. Multi-page navigation."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="FB Comment Watcher",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

dashboard = st.Page("ui/pages/dashboard.py", title="Dashboard", icon="🏠", default=True)
activity = st.Page("ui/pages/activity.py", title="Activity", icon="📋")
config_page = st.Page("ui/pages/config.py", title="Config", icon="⚙️")
auth_page = st.Page("ui/pages/auth.py", title="Auth", icon="🔐")

nav = st.navigation(
    {
        "Operate": [dashboard, activity],
        "Setup": [config_page, auth_page],
    }
)
nav.run()
