# Status

## Built

1. **Model client** — `lobo/model.py`. Sends a conversation to any OpenAI-compatible chat endpoint (DeepSeek by default) and returns the reply plus token counts. Standard library only.

2. **Memory** — `lobo/memory.py`. Two layers, after Hermes/OpenClaw: `home/notes.md` (curated, capped at 2,400 chars, shown to the model every wake) and `home/memory.db` (append-only SQLite event log; recent events shown, the rest searchable).

3. **Heartbeat** — `lobo/heartbeat.py`. Wake, show the model its memory, save its thought / notes rewrite / chosen next wake (clamped 10 min to 24 h), sleep. Replies use DeepSeek JSON mode (`json_mode` option added to `model.py`). Failed beats are logged and retried in 30 min. Runs as a watchable terminal loop; `--once` for a single beat, `--home` for a separate Lobo.

4. **Tools + recall** — `lobo/tools.py`. A wake-up can now take several steps: Lobo replies with a tool request in JSON, the heartbeat runs it and sends back the result, up to 5 calls per wake. First tool is `recall`, a read-only search of Lobo's full event log (skips past tool results so searches don't echo each other). Plain-JSON protocol, not native function calling, so every step is readable in the log.

## Known gaps

- Restarting the heartbeat wakes Lobo immediately, ignoring the wake time it chose. (In testing, Lobo noticed and logged this as an anomaly.) Fix: on start, honor the last `sleep` event.

## Next, in order (one component each)

5. **Budget** — spending cap based on the token counts the client already returns.
6. **Workspace file tools** — read/write/list confined to `workspace/`, added to `tools.py`.

Later, each gated on isolation and owner approval: shell, GitHub API, email, browser. Model comparison runs (DeepSeek vs local Qwen on the GTX 1070 via the same client).
