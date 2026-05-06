# fb-comment-watcher

Local Facebook post comment watcher with auto-Messenger DM and a Streamlit control panel.

> ⚠️ Automating a personal Facebook account violates Meta's Terms of Service. Use at your own risk. Account suspension is possible. Always start in dry-run mode.

## Setup

```bash
cd /Users/edevard/projects/fb-comment-watcher
uv sync
uv run playwright install chromium
```

## Run the UI

```bash
uv run streamlit run streamlit_app.py
```

Open http://localhost:8501.

## First-time login (two-step)

The watcher needs an authenticated session on **both** `facebook.com` (to read comments) **and** `messenger.com` (to send DMs). Cross-domain SSO is not reliable, so we explicitly log in to both.

1. Go to the **Auth** page in the dashboard.
2. Click **"Launch FB login window"** — a Chromium window opens.
3. **Step 1 — Facebook:** the window navigates to facebook.com. Log in manually (handles 2FA / captchas). Once you reach your feed, the auth tool detects the `c_user` cookie and continues automatically.
4. **Step 2 — Messenger:** the same Chromium window navigates to messenger.com. If you're not auto-signed-in (typical on first run), log in there too. The tool detects messenger session cookies and saves the combined state.
5. The window closes itself when both legs are complete. Session is saved to `.auth/storage_state.json`.

Refresh the **Auth** page in the dashboard — it should show ✅ session present.

## Configure

On the **Config** page:
- Paste the URL of the post to monitor.
- Add keywords (one per line). A comment containing any keyword (case-insensitive) triggers a DM.
- Set the message template.
- Keep **dry-run** ON for the first day until you trust the matcher.

## Run the watcher

On the **Dashboard** page:
- Click ▶ Start watcher.
- Watch KPIs and the live log tail.
- Comments + outcomes appear on the **Activity** page.

## Stop / restart

- Click ⏹ Stop watcher in the UI.
- The Streamlit app and the watcher are independent — closing the browser does not kill the watcher.

## Files

- `state.db` — SQLite, dedup of (post, commenter).
- `status.json` — watcher heartbeat, written every poll.
- `logs/watcher.log` — rotating log file.
- `runtime/watcher.pid` — PID of running watcher.
- `.auth/storage_state.json` — Playwright session cookies (chmod 600).

## Tests

```bash
uv run pytest
```
