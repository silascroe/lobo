# Agent instructions for Lobo

Read `README.md`, then `docs/STATUS.md`. For the reasoning behind the project, `docs/origin-chat.md` is the source of truth.

## The one rule that matters

This project exists so the owner can learn how a persistent agent works, piece by piece. Therefore:

- **One new component per step.** Each part of the agent (client, memory, heartbeat, tools, etc.) is built and reviewed on its own. Don't land several new modules at once. Small supporting edits to existing files are fine; mention them.
- Explain what the new piece does and how it fits, in plain language, when you finish it.
- Don't build ahead. No "while I'm here" subsystems.

## Conventions

- Standard library only unless there's a strong reason; ask before adding a dependency.
- Model backend stays swappable: everything talks to an OpenAI-compatible chat-completions endpoint via `lobo/model.py`.
- Secrets come from environment variables, never files in the repo.
- Safety boundary: Lobo's file tools may only touch `<home>/workspace/`. Every path goes through `_resolve()` in `lobo/tools.py`; any new file-touching tool must use it. That fence is enough for text-file tools, not for a shell or browser: those need real isolation (VM/container) first.
- Never commit, push, or delete branches unless the owner asks.
- Update `docs/STATUS.md` when a piece lands.
