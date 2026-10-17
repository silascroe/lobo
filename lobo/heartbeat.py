"""Heartbeat: the loop that makes Lobo wake up on its own.

One beat is the whole cycle of a persistent agent in miniature:

  wake  -> load memory (notes + recent events)
        -> show it to the model and ask what it wants to do
        -> save what it thought, any rewrite of its notes, and when to wake next
  sleep -> until the time it chose

Between beats nothing is running but a sleeping Python process. The model
isn't "waiting"; it doesn't exist until the next call. Everything that makes
the next wake-up feel continuous with this one is in memory.

A wake-up can take several steps. If Lobo asks for a tool, the heartbeat
runs it, shows Lobo the result, and asks again, until Lobo gives its final
answer (notes + next wake) or runs out of steps.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from lobo import tools
from lobo.memory import DEFAULT_HOME, NOTES_CHAR_LIMIT, Memory
from lobo.model import ModelClient, ModelError

# Lobo picks its own next wake-up, clamped to this range.
MIN_WAKE_MINUTES = 10
MAX_WAKE_MINUTES = 24 * 60
# When a beat fails (network down, bad reply), try again after this long.
RETRY_MINUTES = 30
# Most tool calls allowed in one wake-up, so Lobo can't loop forever.
MAX_TOOL_CALLS = 5

SYSTEM_PROMPT = f"""You are Lobo, a persistent agent.

You don't run continuously. You exist as a series of wake-ups. Between them
there is nothing. Each time you wake, you're shown your notes (which you
wrote) and a log of recent events. That is your only continuity.

Each wake-up you can:
1. Think. Whatever you like.
2. Use tools (up to {MAX_TOOL_CALLS} calls per wake-up). Available tools:
{tools.describe()}
3. Rewrite your notes. They're shown to you every wake-up and are capped at
   {NOTES_CHAR_LIMIT} characters. Use them for whatever you want to carry forward.
4. Choose when to wake next, between {MIN_WAKE_MINUTES} and {MAX_WAKE_MINUTES} minutes from now.

Nobody is giving you tasks. What you do with your wake-ups is up to you.

Reply with a JSON object. To use a tool:
{{"thought": "<what you're thinking>", "tool": "<tool name>", "args": {{...}}}}
You'll get the result, then reply again.

To finish this wake-up:
{{"thought": "<what you're thinking>",
  "notes": "<the full new text of your notes, or null to leave them unchanged>",
  "next_wake_minutes": <integer>}}"""


def beat(memory: Memory, client: ModelClient) -> int:
    """Run one wake-up. Returns how many minutes to sleep afterwards."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    memory.record("wake", f"Woke at {now}.")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Current time: {now}\n\n{memory.snapshot()}"},
    ]

    tokens_in = tokens_out = 0
    tool_calls = 0
    try:
        # Each pass is one model call. A tool request sends the result back
        # and loops; a final answer breaks out. One extra pass past the tool
        # limit lets Lobo answer after being told it's out of calls.
        for _ in range(MAX_TOOL_CALLS + 2):
            reply = client.complete(messages, json_mode=True)
            tokens_in += reply.prompt_tokens
            tokens_out += reply.completion_tokens
            if reply.reasoning:
                # The model's private reasoning, before it wrote its answer.
                # Kept for you to read; Lobo's page only shows the header.
                memory.record("reasoning",
                              f"Reasoned ({len(reply.reasoning)} chars).\n{reply.reasoning}")
            decision = json.loads(reply.text)
            memory.record("thought", str(decision.get("thought", "")).strip() or "(empty)")

            if "tool" not in decision:
                break
            name, args = str(decision["tool"]), decision.get("args", {})
            if tool_calls >= MAX_TOOL_CALLS:
                result = "No tool calls left this wake-up. Give your final answer now."
            else:
                result = tools.run(memory, name, args)
                tool_calls += 1
            first_line = result.splitlines()[0] if result else ""
            # The header (all Lobo's page shows) gets a short version of the
            # args; write_file content can be huge. The full args and result
            # go in the body, so the log keeps every version of every file.
            args_json = json.dumps(args, ensure_ascii=False)
            short_args = args_json if len(args_json) <= 200 else args_json[:200] + "...}"
            memory.record("tool", f"{name} {short_args} -> {first_line}\n"
                                  f"args: {args_json}\n{result}")
            # The model's own request and the result both go on the page, so
            # the next call sees the whole exchange so far.
            messages.append({"role": "assistant", "content": reply.text})
            messages.append({"role": "user", "content": f"Tool result:\n{result}"})
        else:
            raise ValueError("kept requesting tools past the limit")

        notes = decision.get("notes")
        if "next_wake_minutes" not in decision:
            # Don't paper over this silently: Lobo should see that its final
            # answer was missing a piece, and you should too.
            memory.record("error", "Final reply had no next_wake_minutes; "
                          f"defaulted to {RETRY_MINUTES}. Reply was: {reply.text[:500]}")
        minutes = int(decision.get("next_wake_minutes", RETRY_MINUTES))
    except (ModelError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
        # A failed beat shouldn't kill Lobo. Log it and try again later.
        memory.record("error", f"Beat failed: {type(e).__name__}: {e}")
        return RETRY_MINUTES

    if isinstance(notes, str):
        try:
            memory.write_notes(notes)
        except ValueError as e:
            # Over the cap. Lobo will see this error in its log next time.
            memory.record("error", str(e))

    clamped = max(MIN_WAKE_MINUTES, min(MAX_WAKE_MINUTES, minutes))
    memory.record(
        "sleep",
        f"Sleeping {clamped} min"
        + (f" (asked for {minutes})" if clamped != minutes else "")
        + f". [{tool_calls} tool calls, {tokens_in} in, {tokens_out} out]",
    )
    return clamped


def show_beat(memory: Memory, since_id: int) -> None:
    """Print the events from the latest beat, so you can watch it live."""
    for e in memory.recent(50):
        if e.id > since_id:
            print(f"[{e.time}] {e.kind}: {e.content}\n")


def last_id(memory: Memory) -> int:
    latest = memory.recent(1)
    return latest[0].id if latest else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lobo's heartbeat.")
    parser.add_argument("--once", action="store_true", help="beat once and exit")
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME,
                        help="memory folder (a different home is a different Lobo)")
    parser.add_argument("--backend", default="deepseek")
    args = parser.parse_args()
    # Lobo may write text the console can't display (some Windows consoles
    # are not UTF-8). Printing it should never crash the heartbeat.
    sys.stdout.reconfigure(errors="replace")

    memory = Memory(args.home)
    client = ModelClient.from_backend(args.backend)
    # Starting the heartbeat wakes Lobo right away, whatever time it chose.
    # Say so in its log, as a plain fact, and let it draw its own conclusions.
    if args.once:
        memory.record("start", "Woken manually by the owner.")
    else:
        memory.record("start", "Heartbeat restarted by the owner; woke immediately.")
    try:
        while True:
            before = last_id(memory)
            minutes = beat(memory, client)
            show_beat(memory, before)
            if args.once:
                break
            wake_at = datetime.fromtimestamp(time.time() + minutes * 60)
            print(f"--- next beat at {wake_at:%H:%M} local. Ctrl+C to stop. ---\n")
            time.sleep(minutes * 60)
    except KeyboardInterrupt:
        memory.record("stopped", "Heartbeat stopped by the owner.")
        print("\nStopped.")
    finally:
        memory.close()


if __name__ == "__main__":
    main()
