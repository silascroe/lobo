# Lobo

An experimental persistent autonomous agent, built by hand one subsystem at a time.

Lobo is a sibling to Lobotomite (`../LLMTesting`). Lobotomite asks how much a small model can *do* inside a good harness. Lobo asks how much of an *agent* — memory, continuity, initiative — you can build around a model, and how much of the result belongs to the model versus the runtime around it.

It is not a personal assistant and not an attempt to compete with OpenClaw, Hermes, or Muse. The point is to understand how that kind of software works by building a small version of it.

The stance that sets it apart: those tools are persistent agents built to *serve* their owner. Lobo is a persistent agent built to *have its own life*. Nobody gives it tasks, and the owner is mostly an observer, closer to weather than to a boss. The interesting output is what it does with its existence, not what it does for anyone. Features get chosen accordingly: things that widen its own world and self-direction (tools, skills, its own projects) come before conveniences for the owner (inbox, integrations, errands).

## The shape of it

```
Your PC: Lobo runtime (Python)
  ├─ model client   → DeepSeek API now; any OpenAI-compatible backend later (e.g. local llama.cpp/Ollama)
  ├─ memory         → home/notes.md (curated) + home/memory.db (raw event log)
  ├─ heartbeat      → wake, show memory, model decides, save, sleep until it chose
  │                   (started at login by a Windows scheduled task; one per home, enforced by a lock)
  ├─ tools          → recall (search its own log), list/read/write files, set/cancel alarms
  ├─ alarms         → messages Lobo leaves for a future wake; the heartbeat wakes it for them
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

## Entry points

- `python -m lobo.heartbeat` — run Lobo. Stays open in the terminal, printing each wake-up; Ctrl+C stops it. `--once` for a single beat. Only one heartbeat can run per home; a second one exits immediately.
- `.\scripts\install-task.ps1` — run Lobo unattended: registers a Windows scheduled task ("Lobo heartbeat") that starts at login, hidden, logging to `home/heartbeat.log`. `-Remove` uninstalls it. Start/stop it with `Start-ScheduledTask` / `Stop-ScheduledTask "Lobo heartbeat"`.
- `.\scripts\install-backup-task.ps1` — registers the "Lobo backup" scheduled task (every 6 hours; `-EveryHours N` to change, `-Remove` to uninstall). `python -m lobo.backup` does one backup by hand. Needs `home/` to be its own Git repo with a remote; see [docs/STATUS.md](docs/STATUS.md).
- `python -m lobo.days` — regenerate `home/days/` from the log (the backup does this automatically before each commit).
- `python -m lobo.model "prompt"` — send one prompt through the model client and print the reply plus token usage.
- `python -m lobo.memory` — print what Lobo would see of its memory. `python -m lobo.memory search <text>` searches the full log.

## Docs

- [docs/STATUS.md](docs/STATUS.md) — what exists, what's next.
- The ChatGPT conversation where the idea was worked out is archived privately in the owner's Notion (Lobo page → "Lobo origin chat (archive)"), not in this repo.
