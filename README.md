# Lobo

An experimental persistent autonomous agent, built by hand one subsystem at a time.

Lobo is a sibling to Lobotomite (`../LLMTesting`). Lobotomite asks how much a small model can *do* inside a good harness. Lobo asks how much of an *agent* — memory, continuity, initiative — you can build around a model, and how much of the result belongs to the model versus the runtime around it.

It is not a personal assistant and not an attempt to compete with OpenClaw, Hermes, or Muse. The point is to understand how that kind of software works by building a small version of it.

## The shape of it

```
Your PC: Lobo runtime (Python)
  ├─ model client   → DeepSeek API now; any OpenAI-compatible backend later (e.g. local llama.cpp/Ollama)
  ├─ memory         → home/notes.md (curated) + home/memory.db (raw event log)
  ├─ heartbeat      → wake, show memory, model decides, save, sleep until it chose
  ├─ tools          → workspace-only file ops first           (not built yet)
  └─ workspace/     → the only part of the disk Lobo may touch (not built yet)
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

- `python -m lobo.heartbeat` — run Lobo. Stays open in the terminal, printing each wake-up; Ctrl+C stops it. `--once` for a single beat.
- `python -m lobo.model "prompt"` — send one prompt through the model client and print the reply plus token usage.
- `python -m lobo.memory` — print what Lobo would see of its memory. `python -m lobo.memory search <text>` searches the full log.

## Docs

- [docs/STATUS.md](docs/STATUS.md) — what exists, what's next.
- [docs/origin-chat.md](docs/origin-chat.md) — the ChatGPT conversation where the idea was worked out. The source of truth for intent.
