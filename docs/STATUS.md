# Status

## Built

1. **Model client** — `lobo/model.py`. Sends a conversation to any OpenAI-compatible chat endpoint (DeepSeek by default) and returns the reply plus token counts. Standard library only.

2. **Memory** — `lobo/memory.py`. Two layers, after Hermes/OpenClaw: `home/notes.md` (curated, capped at 2,400 chars, shown to the model every wake) and `home/memory.db` (append-only SQLite event log; recent events shown, the rest searchable).

## Next, in order (one file each)

3. **Heartbeat** — loop that wakes on a schedule, loads memory, asks the model what to do, saves the result. After this, Lobo is no longer a chatbot.
4. **Budget** — spending cap based on the token counts the client already returns.
5. **Workspace file tools** — read/write/list confined to `workspace/`.

Later, each gated on isolation and owner approval: shell, GitHub API, email, browser. Model comparison runs (DeepSeek vs local Qwen on the GTX 1070 via the same client).
