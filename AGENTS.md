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
- Safety boundary: once tools exist, Lobo may only touch `workspace/`. Path checks live in code. Real isolation (VM/container) is required before Lobo gets a shell or browser.
- Never commit, push, or delete branches unless the owner asks.
- Update `docs/STATUS.md` when a piece lands.
