# Setup Guide — For Total Beginners

Hi! 👋 This guide gets you from a brand-new Mac with **nothing installed** to a working Facebook Comment Watcher with a clean dashboard you can click around in.

You don't need to be technical. You just need to follow each step in order. If something looks scary, don't worry — Claude will do most of the work.

**You'll need:**
- A Mac (anything from the last few years)
- Your Claude account (the one you used to sign up at claude.com)
- Your Facebook login (email/phone + password, plus your phone if you have 2-factor auth)
- About 30 minutes for the first-time setup
- An internet connection (to download things during setup)

That's it. The project itself is open-source and lives on GitHub at **https://github.com/edevardHvide/fb-comment-watcher** — Claude will download it for you in Part 1.

> ⚠️ **Important honest warning before you start.** Facebook does not officially allow tools like this one. In rare cases, accounts that automate actions can get a warning, get temporarily locked, or get banned. The safest way to use this is in **Dry-run mode** at first, which we'll set up below — Dry-run mode watches comments but does **not** send any messages.

---

## Part 1 — Install the tools we need (one time only)

We need three small things installed on your Mac. The easiest way is to let **Claude Code** do it for you. Claude Code is like having a friendly developer sitting next to you — you tell it what you want in plain English, and it makes it happen.

### Step 1.1 — Install Claude Code

1. Open the **Safari** browser (or Chrome, whichever you use).
2. Go to: **https://claude.com/download**
3. Click **Download for Mac**.
4. When the file finishes downloading, double-click it to install Claude Code.
5. Open Claude Code from your Applications folder. The first time you open it, sign in with your Claude account (the same one you use at claude.com).

If your Mac says "Claude can't be opened because it's from an unidentified developer", right-click (or Control-click) the app and choose **Open** — that bypasses the warning.

### Step 1.2 — Open Claude Code in any folder

The first time you launch Claude Code, you'll be asked to pick a folder to "open". Pick your **Desktop** (or any folder you like — it doesn't matter for now, Claude will create the project folder inside it in the next step).

From here on, **the chat box at the bottom of Claude Code is where you talk to Claude**. You type in plain English and press Enter.

### Step 1.3 — Let Claude download and set up the project

Copy the entire block below. Paste it into the Claude Code chat box and press Enter:

> Please set up the fb-comment-watcher project on my Mac for the first time. I'm not technical. I need you to:
> 1. Install Homebrew if it isn't installed.
> 2. Install `git` and `uv` using Homebrew.
> 3. Clone the repository **https://github.com/edevardHvide/fb-comment-watcher** into the current folder.
> 4. Move into the cloned `fb-comment-watcher` folder.
> 5. Run `uv sync` to install all the Python packages.
> 6. Run `uv run playwright install chromium` to install the browser the watcher uses.
> 7. When you're done, tell me whether everything succeeded and where the project folder ended up.
>
> If macOS asks for my password during Homebrew installation, I'll type it in — that's normal. Please pause and tell me what to type when needed.

Claude will work for a few minutes. It might:
- Ask permission to run commands → click **Allow**.
- Ask you to type your Mac password into the Terminal window → that's normal, the same password you use to log into your Mac.
- Show a lot of text scrolling by → that's also normal, Claude is just installing things.

When Claude says **"everything succeeded"** or similar, you're done with Part 1. 🎉

> 💡 **Where did the project go?** Whatever folder you opened Claude Code in (e.g. Desktop), there should now be a `fb-comment-watcher` folder inside it. That's your project. Claude will continue working from there for the rest of this guide — you don't need to do anything special.

### Step 1.4 — Make sure Claude is "in" the project folder

Tell Claude:

> From now on, work inside the `fb-comment-watcher` folder we just downloaded. Always run commands from there.

(This is just to make sure Claude doesn't accidentally run things in the wrong place later.)

---

## Part 2 — Start the dashboard

The dashboard is the friendly window where you control everything. You don't need the command line again after this — you'll do everything by clicking buttons.

### Step 2.1 — Ask Claude to start the dashboard

In the Claude Code chat box, type:

> Please start the Streamlit dashboard for this project.

Claude will run a command and tell you the dashboard is ready. A web browser tab should open automatically at **http://localhost:8501**. If it doesn't, open Safari/Chrome yourself and type that address into the URL bar.

You should see a page titled **💬 FB Comment Watcher** with a sidebar on the left (Dashboard, Activity, Config, Auth).

> 💡 **Tip:** The dashboard runs as long as the Terminal window stays open. If you close it, the dashboard stops. To restart it later, just ask Claude again: *"Please start the Streamlit dashboard."*

---

## Part 3 — Log in to Facebook (one time)

The watcher uses your real Facebook session. We'll save it once so you don't have to log in again every time.

### Step 3.1 — Open the Auth page

In the dashboard sidebar, click **🔐 Auth**.

### Step 3.2 — Launch the login window

Click the big blue button **🚀 Launch FB login window**.

A new Chromium browser window will open showing facebook.com.

### Step 3.3 — Log in normally

1. Type your Facebook email/phone and password.
2. If Facebook asks for a 2-factor code, enter it from your phone.
3. Wait until you see your Facebook home feed.

The window will **close itself automatically** once it detects you're logged in. You don't need to do anything else.

### Step 3.4 — Confirm

Refresh the **🔐 Auth** page in your dashboard browser. It should now show ✅ **Session present**.

You're logged in. You won't have to do this again unless your Facebook session expires (usually weeks or months from now).

---

## Part 4 — Tell the watcher what to look for

### Step 4.1 — Open the Config page

In the dashboard sidebar, click **⚙️ Config**.

### Step 4.2 — Paste the post URL

1. Open Facebook in your normal browser.
2. Find the post you want to watch.
3. Click the post's date/time (e.g. "2 hours ago") to open it on its own page.
4. Copy the URL from the address bar.
5. Paste it into the **Post URL** field on the Config page.

### Step 4.3 — Add keywords

In the **Keywords** box, type the words/phrases that should trigger a message. Put **one per line**. For example:

```
interested
send info
yes please
```

A comment will trigger a DM if it contains **any** of these (case doesn't matter — "Interested" matches "interested").

### Step 4.4 — Write your message

In the **Message template** box, type the message you want to send. Example:

```
Hi! Thanks for your comment — here's the info you asked about:

[your details here]

Talk soon!
```

### Step 4.5 — Important: leave Dry-run ON for the first day

Make sure the **Dry-run mode** toggle is **ON** (blue). In Dry-run mode, the watcher pretends it sent messages and logs everything, but **doesn't actually send any DMs**. This lets you confirm the keywords work as expected before any real messages go out.

### Step 4.6 — Save

Click the blue **💾 Save** button. You should see a small "Saved" notification.

---

## Part 5 — Run it!

### Step 5.1 — Start the watcher

In the dashboard sidebar, click **🏠 Dashboard**.

You'll see four cards at the top: **Status**, **Polls**, **DMs sent**, **Matches today**.

Click the big button **▶ Start watcher (dry-run)**.

A new Chromium window will pop up. **Don't close this window!** This is the watcher actually browsing Facebook for you. Move it to a corner of your screen if it's in the way, but leave it open.

Within a few seconds, the dashboard will switch to **● Running** and the **Polls** counter will start ticking up.

### Step 5.2 — Test it (recommended)

Ask a friend to leave a comment on your post containing one of your keywords. Or use a second Facebook account if you have one. Within ~30 seconds:

- The **Matches today** counter goes up.
- The **Recent matches** section shows the comment.
- Because we're in Dry-run mode, the **status badge** says "Dry-run" — no message was actually sent.

Click **📋 Activity** in the sidebar to see the full list of what the watcher noticed.

### Step 5.3 — Switch to live mode (when you're confident)

Once you've seen Dry-run work correctly with a real test:

1. Go to **🏠 Dashboard**, click **⏹ Stop watcher**.
2. Go to **⚙️ Config**, switch **Dry-run mode** to **OFF**, click **Save**.
3. Go back to **🏠 Dashboard**, click the now-red button **▶ Start watcher (LIVE — sends DMs)**.

It's now live. New matching comments will trigger real Messenger DMs.

> 💡 **You can switch back to Dry-run any time** by stopping, toggling off Live in Config, and starting again.

---

## Part 6 — Daily use (after first-time setup)

Each time you want to use it:

1. **Start the dashboard.** In Claude Code, type: *"Please start the Streamlit dashboard."*
2. **Browser opens** at http://localhost:8501. (If not, open it yourself.)
3. **Click ▶ Start watcher.** That's it.

To stop:
- Click **⏹ Stop watcher** in the dashboard.
- Close the Terminal window (this also stops the dashboard).

Your config, your Facebook login, and your activity history are all saved between sessions. You don't reconfigure anything.

---

## Common problems

### "I don't see the dashboard / browser tab didn't open"
Open Safari/Chrome and go to **http://localhost:8501** manually.

### "Status says Stopped even though I clicked Start"
Wait 5 seconds and refresh the dashboard. If still stopped, check the **Live log** section — it will show the error. Ask Claude: *"The watcher won't start. Here's what the log says: [paste log]. Help me fix it."*

### "Watcher keeps saying 'no session'"
Your Facebook login expired. Go to **🔐 Auth** and click "Launch FB login window" again. Repeat Part 3.

### "I'm getting blocked / Facebook is asking for verification"
**Stop the watcher right away.** Increase the Poll interval in Config to 60 seconds or more. Wait a day. Don't run it at high speed for a while.

### "I want to monitor a different post"
Go to **⚙️ Config**, paste the new URL, click Save. Stop and restart the watcher.

### "I want to delete everything and start over"
Ask Claude: *"Please reset this project — delete state.db, status.json, .auth/, logs/, and runtime/."*

### "Something else broke"
The first thing to try with anything you don't understand: **just paste the error into the Claude Code chat and ask Claude to fix it**. Claude knows this whole project and can usually figure things out.

---

## Things to know

- **The watcher keeps running even if you close things.** Once you click Start, the watcher runs in the background. Closing the dashboard tab doesn't stop it. Closing the Terminal where Claude is running doesn't stop it either. **The only way to stop it is to click ⏹ Stop watcher in the dashboard** (reopen http://localhost:8501 if you closed the tab).
- **The Chromium window must stay open** while the watcher runs. It's the window the watcher uses to read Facebook. Don't close it until you've stopped the watcher.
- **Your Mac must stay awake.** If your Mac sleeps, the watcher pauses. Either turn off sleep in System Settings → Battery (while plugged in), or accept that the watcher only runs when your Mac is awake.
- **Don't use the watcher's Chromium for anything else.** It's controlled by the program — clicking around in it manually will confuse the watcher. Use a different browser for your normal browsing.
- **If you ever lose track, ask Claude:** *"Is the watcher running right now?"* — Claude can check and stop it if needed.

---

## Glossary (if you want to know what's going on)

- **Terminal** — a window that lets programs print text and accept commands. You don't need to type into it for normal use.
- **Claude Code** — an app that lets you tell Claude what you want and it runs commands on your Mac for you.
- **Homebrew** — a tool that installs other tools on Mac. Like an app store for developer programs.
- **Python** — the programming language this project is written in. You don't need to learn it.
- **uv** — a tool that manages Python and its packages. Faster than the default.
- **Playwright** — the library that lets the watcher control a browser automatically.
- **Chromium** — the open-source browser that Playwright drives. It's basically Chrome.
- **Streamlit** — the framework that powers the friendly dashboard you click around in.
- **Dashboard / localhost:8501** — the local web page running on your own Mac. "localhost" means "this computer" — nothing on the public internet, only you can see it.
- **Dry-run** — practice mode. Detects matches but does not send anything.
- **Live mode** — real mode. Actually sends messages.

---

## Need help?

Open Claude Code, make sure the `fb-comment-watcher` folder is open, and ask Claude in plain English. For example:

> "The watcher started but I'm not seeing matches even though I commented one of my keywords. Can you check what's wrong?"

Claude can read all the project files, look at the logs, and walk you through fixing it.

Good luck! 🍀
