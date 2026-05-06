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
- **Keywords** (one per line). A comment containing any keyword (case-insensitive substring) triggers a DM.
- **Exclude keywords** (one per line). If a comment contains any of these, it's skipped — even if it matches a keyword.
- **Message template** — text sent verbatim as the Messenger DM.
- **Public reply** (optional, opt-in toggle) — when ON, the watcher also posts a public reply to the matching comment, attempting to @-tag the commenter. Use `{name}` in the reply template; it's substituted with the commenter's name when the @-tag autocomplete doesn't appear.
- Keep **dry-run** ON for the first day until you trust the matcher.

## How matching works

For every poll the watcher compares each visible comment against the rules above and acts on it once. There's a **baseline** captured the moment the watcher starts: every comment already on the post is recorded as `pre_existing` and will never be DM'd, even if it matches a keyword. Only comments that arrive **after** start are eligible.

A commenter is also dedup'd permanently after any send attempt — `sent`, `blocked`, or `error` all block future retries to the same person on the same post. Only `dry_run` rows leave a person eligible for a real send later (so flipping dry-run off works).

## Run the watcher

On the **Dashboard** page:
- Click ▶ Start watcher.
- Watch KPIs and the live log tail.
- Comments + outcomes appear on the **Activity** page.

Per-poll log lines tell you exactly what happened to each comment:
- `no-match: <name> (<id>) text=...` — keyword didn't match (or was excluded)
- `skip: <name> (<id>) — already in db status=...` — already DM'd / pre-existing
- `match: <name> (<id>) — kw=...` — about to send

## Stop / restart

- Click ⏹ Stop watcher in the UI.
- The Streamlit app and the watcher are independent — closing the browser does not kill the watcher.

## Re-testing against yourself

Sending a DM to yourself is allowed (no self-skip), but after it succeeds your row becomes `sent` and you'll be permanently dedup'd on that post. To re-test:

```bash
sqlite3 state.db "DELETE FROM messaged WHERE commenter_id='<your_fb_user_id>'"
```

Then restart the watcher and post a fresh matching comment.

## Files

- `state.db` — SQLite, dedup of (post, commenter).
- `status.json` — watcher heartbeat, written every poll.
- `logs/watcher.log` — rotating log file.
- `logs/debug/` — PNG + HTML snapshots whenever the scraper, sender, or replier hits an unexpected DOM state.
- `runtime/watcher.pid` — PID of running watcher.
- `.auth/storage_state.json` — Playwright session cookies, chmod 600.

## Tests

```bash
uv run pytest
```
