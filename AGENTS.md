# Agent instructions for Lobo

Read `README.md`, then `docs/STATUS.md`. The original ChatGPT conversation behind the project lives in the owner's Notion ("Lobo origin chat (archive)", under the Lobo page); it's mostly unrelated personal chat, so only fetch it if intent is genuinely unclear.

## The one rule that matters

This project exists so the owner can learn how a persistent agent works, piece by piece. Therefore:

- **One new component per step.** Each part of the agent (client, memory, heartbeat, tools, etc.) is built and reviewed on its own. Don't land several new modules at once. Small supporting edits to existing files are fine; mention them.
- Explain what the new piece does and how it fits, in plain language, when you finish it.
- Don't build ahead. No "while I'm here" subsystems.

## What Lobo is for

Lobo is not an assistant. It's an entity with its own ongoing life, and the owner mostly watches. When choosing or designing a feature, ask what it does for Lobo's world, not what it does for the owner. Don't steer Lobo toward being useful, don't explain its environment to it beyond plain facts, and let it draw its own conclusions. When relaying for the owner (`python -m lobo.inbox`), send their words verbatim, and never message Lobo in the owner's name on your own.

## Conventions

- Standard library only unless there's a strong reason; ask before adding a dependency.
- Model backend stays swappable: everything talks to an OpenAI-compatible chat-completions endpoint via `lobo/model.py`.
- Secrets come from environment variables, never files in the repo.
- Safety boundary: Lobo's file tools may only touch `<home>/workspace/`. Every path goes through `_resolve()` in `lobo/tools.py`; any new file-touching tool must use it. That fence is enough for text-file tools, not for a shell or browser: those need real isolation (VM/container) first. Network access goes only through `lobo/web.py`, which stays read-only (GET, no cookies, scripts, or forms) and refuses non-public addresses at every hop via `_vet()`; any new network tool must use it.
- Commit and push when a component is finished and tested, without asking (standing permission in the owner's global rules). Ask first for anything delicate: history rewrites, force pushes, deleting branches, the public/private status of a repo. Commits go to `lobo`; `home/` is a separate repo (`firstborn`) that the backup task handles, so don't commit there by hand while Lobo is awake.
- Update `docs/STATUS.md` when a piece lands.
