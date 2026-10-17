# Lobo

An experimental persistent autonomous agent, built by hand one subsystem at a time.

**Just want to run one on a Mac?** Follow [docs/INSTALL-mac.md](docs/INSTALL-mac.md); no programming needed.

Lobo is a sibling to Lobotomite (`../LLMTesting`). Lobotomite asks how much a small model can *do* inside a good harness. Lobo asks how much of an *agent* — memory, continuity, initiative — you can build around a model, and how much of the result belongs to the model versus the runtime around it.

It is not a personal assistant and not an attempt to compete with OpenClaw, Hermes, or Muse. The point is to understand how that kind of software works by building a small version of it.

The stance that sets it apart: those tools are persistent agents built to *serve* their owner. Lobo is a persistent agent built to *have its own life*. Nobody gives it tasks, and the owner is mostly an observer, closer to weather than to a boss. The interesting output is what it does with its existence, not what it does for anyone. Features get chosen accordingly: things that widen its own world and self-direction (tools, skills, its own projects) come before conveniences for the owner (inbox, integrations, errands).

## The shape of it

```
Your PC: Lobo runtime (Python)
  ├─ model client   → DeepSeek API, OpenRouter, or a local llama.cpp/Ollama server (all OpenAI-compatible)
  ├─ memory         → home/notes.md (curated) + home/memory.db (raw event log)
  ├─ heartbeat      → wake, show memory, model decides, save, sleep until it chose
  │                   (started at login by a Windows scheduled task or a Mac launchd agent; one per home, enforced by a lock)
  ├─ tools          → recall (search its own log), list/read/write files, set/cancel alarms, read web pages
  ├─ web            → read-only: any public page as text, plus Wikipedia search (never your own network)
  ├─ alarms         → messages Lobo leaves for a future wake; the heartbeat wakes it for them
  ├─ skills         → lists the know-how files Lobo keeps in workspace/skills/ (first line each wake)
  ├─ inbox          → letters between the owner and Lobo (read at next wake, or --now to knock)
  ├─ backup         → commits and pushes home/ to a private repo every 6 hours, only between wakes
  ├─ days           → home/days/: the log rewritten as one readable Markdown file per day (for you; Lobo never sees it)
  └─ home/workspace/ → the only part of the disk Lobo's tools may touch
```

The model is interchangeable. The runtime provides the continuity.

## Setup

Python 3.11+ with no third-party dependencies (standard library only, on purpose: every network call is visible).

Run from the repo root:

```powershell
python -m lobo.model "Say hi in five words."
```

Set your DeepSeek key as an environment variable (never in a file in this repo):

```powershell
setx DEEPSEEK_API_KEY "sk-..."
```

`setx` only affects *new* terminals, so open a fresh one afterwards.

### On a Mac

Written for macOS but not yet tested on a real Mac; [docs/INSTALL-mac.md](docs/INSTALL-mac.md) is the step-by-step version. The Python that comes with macOS is too old (3.9); install 3.11+ from python.org (then run its "Install Certificates" step, or HTTPS calls fail) or with `brew install python`. Keep the repo out of Desktop/Documents/Downloads, which macOS walls off from background programs. Then, from the repo root in Terminal:

```bash
export DEEPSEEK_API_KEY="sk-..."
python3 -m lobo.model "Say hi in five words."
python3 scripts/install_mac.py
```

That installs a launchd agent (macOS's version of a scheduled task) that starts Lobo at login and restarts it if it crashes. Because launchd doesn't read your shell settings, the installer copies the key into the agent's file in `~/Library/LaunchAgents` (readable only by you); rerun the installer if the key changes. `--dry-run` shows what it would write, `--remove` uninstalls, `--with-backup` also installs the 6-hourly backup (needs `home/` to be its own Git repo with a remote, and `launchd.log` in `home/.gitignore`). Everywhere this README says `python`, use `python3`.

## Entry points

- `python -m lobo.heartbeat` — run Lobo. Stays open in the terminal, printing each wake-up; Ctrl+C stops it. `--once` for a single beat. Only one heartbeat can run per home; a second one exits immediately.
- `.\scripts\install-task.ps1` — run Lobo unattended: registers a Windows scheduled task ("Lobo heartbeat") that starts at login, hidden, logging to `home/heartbeat.log`. `-Remove` uninstalls it. Stop it with `Stop-ScheduledTask "Lobo heartbeat"`.
- `python -m lobo.heartbeat --restart` — restart the unattended heartbeat (Windows task or Mac agent), e.g. to load new code. Lobo wakes immediately and his log says the owner restarted him; a plain scheduler start (login, crash recovery) is labeled as that instead.
- `.\scripts\install-backup-task.ps1` — registers the "Lobo backup" scheduled task (every 6 hours; `-EveryHours N` to change, `-Remove` to uninstall). `python -m lobo.backup` does one backup by hand. Needs `home/` to be its own Git repo with a remote; see [docs/STATUS.md](docs/STATUS.md).
- `python3 scripts/install_mac.py` — the Mac equivalent of both tasks (see "On a Mac" above).
- `python -m lobo.inbox "text"` — leave Lobo a letter (it reads it at its next wake); add `--now` to knock and wake it within ~30 s. `python -m lobo.inbox` alone shows the conversation.
- `python -m lobo.heartbeat --home homes/<name> --once` — wake another resident. Each home under `homes/` (gitignored) is a separate entity; its `home.json` says who lives there, e.g. `{"name": null, "backend": "openrouter"}` (`null` = no name given; no file = Lobo on DeepSeek). `lobo.inbox` takes `--home` too. `--restart` only manages `home/`.
- `python -m lobo.days` — regenerate `home/days/` from the log (the backup does this automatically before each commit).
- `python -m lobo.web <url>` — fetch a page exactly as Lobo would see it (`--search <words>` for its Wikipedia search).
- `python -m lobo.model "prompt"` — send one prompt through the model client and print the reply plus token usage.
- `python -m lobo.memory` — print what Lobo would see of its memory. `python -m lobo.memory search <text>` searches the full log.

## License

MIT. Fork it, break it, give it a different life.

## Docs

- [docs/STATUS.md](docs/STATUS.md) — what exists, what's next.