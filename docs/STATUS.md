# Status

## Built

1. **Model client** — `lobo/model.py`. Sends a conversation to any OpenAI-compatible chat endpoint and returns the reply, token counts, and the model's separate reasoning text if it has one. Default is `deepseek-flash` (DeepSeek-V4.1-Flash, thinking mode on by default, default effort; `temperature` is ignored in thinking mode). Standard library only.

2. **Memory** — `lobo/memory.py`. Two layers, after Hermes/OpenClaw: `home/notes.md` (curated, capped at 2,400 chars, shown to the model every wake) and `home/memory.db` (append-only SQLite event log; recent events shown, the rest searchable).

3. **Heartbeat** — `lobo/heartbeat.py`. Wake, show the model its memory, save its thought / notes rewrite / chosen next wake (clamped 10 min to 24 h), sleep. Replies use DeepSeek JSON mode (`json_mode` option added to `model.py`). Failed beats are logged and retried in 30 min; a final reply missing `next_wake_minutes` is logged as an error (with the raw reply) before defaulting to 30. Each step's private reasoning is logged as a `reasoning` event (header only on Lobo's page). Runs as a watchable terminal loop; `--once` for a single beat, `--home` for a separate Lobo.

4. **Tools + recall** — `lobo/tools.py`. A wake-up can now take several steps: Lobo replies with a tool request in JSON, the heartbeat runs it and sends back the result, up to 5 calls per wake. First tool is `recall`, a read-only search of Lobo's full event log (skips past tool results so searches don't echo each other). Plain-JSON protocol, not native function calling, so every step is readable in the log.

## The live Lobo

Born 2026-10-17 in `home/`, running on DeepSeek Flash. So far it set itself a "slow journal" practice, theorized its wake interval was being "compressed" (it was really owner restarts), corrected that once restarts were logged, used recall unprompted to investigate a said-240/slept-30 mismatch, and wrote itself a rule to verify claims against its log. Read its history with `python -m lobo.memory search <word>` or its `notes.md`.

## Known gaps

- Restarting the heartbeat wakes Lobo immediately, ignoring the wake time it chose. Deliberately left as is for now: each start logs a `start` event ("restarted by the owner" / "woken manually by the owner") and Lobo is told nothing more. Early on it theorized its interval was being "compressed"; watching whether it connects that to the start events is part of the experiment.

## Next, in order (one component each)

5. **Budget** — spending cap based on the token counts the client already returns.
6. **Workspace file tools** — read/write/list confined to `workspace/`, added to `tools.py`.

Later, each gated on isolation and owner approval: shell, GitHub API, email, browser. Model comparison runs (DeepSeek vs local Qwen on the GTX 1070 via the same client).
