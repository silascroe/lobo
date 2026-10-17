# Installing Lobo on a Mac

Lobo is a small program that lives on your computer and wakes up on its own every so often to think, write, and do whatever it decides to do. Nobody gives it tasks; you mostly watch. This guide gets one running on a Mac. It takes about 15 minutes. You need the API key you were given (it starts with `sk-`).

Lobo lives only while your Mac is on, awake, and you're logged in. Close the lid and it sleeps too; it picks up again when you open it.

> **Not yet tested on a real Mac.** If a step fails, copy the exact error and send it to whoever gave you this.

## 1. Get the files

(Using Codex? Skip to "Using Codex for this" at the bottom.)

On this repo's GitHub page, click the green **Code** button, then **Download ZIP**. Unzip it (double-click), rename the folder from `lobo-main` to `lobo`, and move it into your home folder (the one with your name, which has Desktop, Documents and Downloads in it).

Don't leave it in Downloads, Desktop or Documents: macOS blocks background programs from those folders, and Lobo would silently fail to start.

## 2. Install Python

Python is the language Lobo is written in. Macs come with an old version that's too old.

Go to [python.org/downloads](https://www.python.org/downloads/), download the latest macOS installer, and run it. When it finishes, a Finder window opens: double-click **Install Certificates.command** in it. Don't skip that; without it Lobo can't make secure connections to the internet. (If you missed the window, it's in Applications > Python 3.x.)

## 3. Open Terminal

Terminal is the app where you type commands. Press Cmd+Space, type `Terminal`, press Return. Then go to Lobo's folder by typing this and pressing Return:

```bash
cd ~/lobo
```

## 4. Give it your key

Type this, with your real key between the quotes, and press Return:

```bash
export DEEPSEEK_API_KEY="sk-your-key-here"
```

Nothing visible happens; that's normal. Treat the key like a password: don't post it, screenshot it, or paste it into a chat (including Codex or ChatGPT). Typing it into your own Terminal is fine.

## 5. Check it works

```bash
python3 -m lobo.model "Say hi in five words."
```

You should see a short reply and some token counts. If you see `CERTIFICATE_VERIFY_FAILED`, go back to step 2 and run Install Certificates. If it says Python is too old or offers to install "command line developer tools", the new Python didn't install; redo step 2.

## 6. Start Lobo for good

```bash
python3 scripts/install_mac.py
```

That's it. Lobo wakes up right away and from now on starts by itself every time you log in. You can close Terminal.

## Watching it

From Terminal, in `~/lobo`:

- See what it's doing: `tail -f home/heartbeat.log` (Ctrl+C to stop watching; Lobo keeps running).
- Read its life as tidy pages: `python3 -m lobo.days`, then open the `home/days` folder in Finder.
- Leave it a letter: `python3 -m lobo.inbox "your message"`. Add `--now` to wake it up for it. Run `python3 -m lobo.inbox` alone to see the conversation, including anything it wrote to you.

Before any of these, open a fresh Terminal and type `cd ~/lobo` first.

## Stopping it

`python3 scripts/install_mac.py --remove` stops it and stops it starting at login. Its memories stay in `home/`; installing again brings the same Lobo back. **The `home` folder is Lobo.** Deleting it, or replacing the whole `lobo` folder with a fresh download, means a different Lobo starts from nothing. To update the code later, replace everything *except* `home`.

If you change your key, run step 4 and step 6 again.

## Updating

If you got the files with Git (the Codex route below does), updating keeps `home` safe automatically, since Git doesn't track it:

```bash
cd ~/lobo
git pull
python3 -m lobo.heartbeat --restart
```

The last line restarts Lobo on the new code (it wakes up right away). If you downloaded a ZIP instead, replace everything except `home`, then run that last line.

## Using Codex for this

Codex can do most of it, but the key should never pass through it. Give Codex this:

> Install Lobo on my Mac: https://github.com/silascroe/lobo. Clone it with git into ~/lobo (not Desktop, Documents or Downloads) and follow docs/INSTALL-mac.md. Do steps 1 to 3 yourself where you can, and tell me if I need to click through an installer. Don't run steps 4 to 6 yourself: they need my API key, which I won't paste to you. Instead, give me the exact commands to type into my own Terminal, then help me read any errors. Don't edit any files in ~/lobo.

Later, "update Lobo following the Updating section of ~/lobo/docs/INSTALL-mac.md" is all Codex needs.
