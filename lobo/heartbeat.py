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
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from lobo import alarms, inbox, skills, tools
from lobo.memory import DEFAULT_HOME, NOTES_CHAR_LIMIT, Memory
from lobo.model import ModelClient, ModelError

try:
    import msvcrt  # Windows
except ImportError:
    msvcrt = None
    import fcntl

# Lobo picks its own next wake-up, clamped to this range.
MIN_WAKE_MINUTES = 10
MAX_WAKE_MINUTES = 24 * 60
# When a beat fails (network down, bad reply), try again after this long.
RETRY_MINUTES = 30
# Most tool calls allowed in one wake-up, so Lobo can't loop forever.
MAX_TOOL_CALLS = 5
# --restart leaves this note in the home so the new heartbeat can say who
# restarted it. Only a fresh note counts, in case a restart never happened.
RESTART_NOTE = "restart.note"
RESTART_NOTE_MAX_AGE = 5 * 60
# Names the install scripts give the unattended heartbeat.
WINDOWS_TASK = "Lobo heartbeat"
MAC_LABEL = "lobo.heartbeat"

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
   Text files in skills/ in your workspace are listed every wake-up under
   "Your skills" by their first line; read_file shows one in full.
4. Choose when to wake next, between {MIN_WAKE_MINUTES} and {MAX_WAKE_MINUTES} minutes from now.

Nobody is giving you tasks. What you do with your wake-ups is up to you.
Your owner may sometimes send you a message; it appears in your log.

Reply with a JSON object. To use a tool:
{{"thought": "<what you're thinking>", "tool": "<tool name>", "args": {{...}}}}
You'll get the result, then reply again.

To finish this wake-up:
{{"thought": "<what you're thinking>",
  "notes": "<the full new text of your notes, or null to leave them unchanged>",
  "next_wake_minutes": <integer>}}"""


def parse_reply(text: str) -> tuple[dict, str]:
    """Read the model's reply as one JSON object. Returns (object, dropped text).

    JSON mode guarantees valid JSON, but now and then the model writes
    several objects back to back, in one of two shapes:
      - a tool request, then the final answer it expects to give afterwards.
        The heartbeat goes one step at a time, so the tool request is used
        and the rest is dropped (Lobo answers again after the result).
      - one answer split in pieces ({"thought": ...} {"notes": ...,
        "next_wake_minutes": ...}). Those are merged into one.
    Anything dropped comes back as text, so it can be logged, not lost.
    """
    text = text.strip()
    decoder = json.JSONDecoder()
    objects, position = [], 0
    while position < len(text):
        try:
            value, position = decoder.raw_decode(text, position)
        except json.JSONDecodeError:
            if not objects:
                raise
            return _combine(objects, text[position:].strip())
        if not isinstance(value, dict):
            if not objects:
                raise ValueError(f"reply was a JSON {type(value).__name__}, not an object")
            return _combine(objects, text[position:].strip())
        objects.append(value)
        while position < len(text) and text[position] in " \t\r\n":
            position += 1
    return _combine(objects, "")


def _combine(objects: list[dict], rest: str) -> tuple[dict, str]:
    if "tool" in objects[0]:
        dropped = [json.dumps(o, ensure_ascii=False) for o in objects[1:]] + ([rest] if rest else [])
        return objects[0], " ".join(dropped)
    merged, conflicts = {}, []
    for o in objects:
        for key, value in o.items():
            if key in merged and merged[key] != value:
                conflicts.append(json.dumps({key: value}, ensure_ascii=False))
            else:
                merged.setdefault(key, value)
    return merged, " ".join(conflicts + ([rest] if rest else []))


def beat(memory: Memory, client: ModelClient) -> int:
    """Run one wake-up. Returns how many minutes to sleep afterwards."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    memory.record("wake", f"Woke at {now}.")
    # Any alarm that's due rings now: logged as an event, so it shows up in
    # the recent events below like everything else that happened.
    alarms.ring_due(memory)
    # Same for letters from the owner waiting in the mailbox.
    inbox.deliver(memory)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Current time: {now}\n\n{memory.snapshot()}\n\n"
                                    f"## Your alarms\n{alarms.describe_pending(memory)}\n\n"
                                    f"## Your skills\n{skills.describe(memory)}"},
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
            decision, dropped = parse_reply(reply.text)
            if dropped:
                memory.record("error", "Reply held more than one JSON object; part of it was "
                              f"not used: {dropped[:500]}")
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
        # A failed beat shouldn't kill Lobo. Log it and try again later. If
        # the reply itself was the problem, keep it: it may hold real words.
        detail = f" Reply was: {reply.text[:2000]}" if isinstance(e, json.JSONDecodeError) else ""
        memory.record("error", f"Beat failed: {type(e).__name__}: {e}.{detail}")
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


def acquire_lock(home: Path):
    """Claim the right to run the heartbeat for this home.

    Two heartbeats on one home would both wake Lobo and both write to its
    memory. The first one to start holds an OS-level lock on a file in the
    home; any later one finds it taken and gives up. Returns the open lock
    file (keep it open as long as you run), or None if someone else has it.
    The OS releases the lock when the process dies, even if it crashes, so a
    stale lock can't lock Lobo out.
    """
    home.mkdir(parents=True, exist_ok=True)
    f = open(home / "heartbeat.lock", "a+b")
    try:
        if msvcrt:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def sleep_until(wake_at: float, interrupt=None) -> bool:
    """Sleep until a wall-clock time, in short chunks, checking the clock.

    One long time.sleep can drift when the PC itself goes to sleep. Checking
    the real time between short sleeps means that when the PC wakes up and
    Lobo's time has passed, Lobo wakes right away instead of finishing a
    stale countdown. Between chunks it also asks `interrupt()` (a knock on
    the door); if that says yes, it stops early. Returns True if interrupted.
    """
    while (remaining := wake_at - time.time()) > 0:
        if interrupt and interrupt():
            return True
        time.sleep(min(remaining, 30))
    return False


def start_message(home: Path, once: bool, scheduled: bool) -> str:
    """What Lobo's log says about why the heartbeat just started.

    Plain facts, and only ones the heartbeat actually knows. Started by the
    scheduler with no restart note, it can't tell a login from a restart
    after a crash, so it says both.
    """
    note = home / RESTART_NOTE
    restarted = False
    if note.exists():
        restarted = time.time() - note.stat().st_mtime < RESTART_NOTE_MAX_AGE
        note.unlink()
    if once:
        return "Woken manually by the owner."
    if restarted or not scheduled:
        return "Heartbeat restarted by the owner; woke immediately."
    scheduler = "Windows Task Scheduler" if sys.platform == "win32" else "launchd"
    return (f"Heartbeat started automatically by {scheduler} (at login, or after the "
            "previous heartbeat crashed); woke immediately.")


def restart(home: Path) -> None:
    """Restart the unattended heartbeat so its log says the owner did it.

    Stops the running one, waits until it's really gone (its lock comes
    free), then starts it again through the same scheduler that runs it.
    """
    def run(*command: str) -> subprocess.CompletedProcess:
        return subprocess.run(command, capture_output=True, text=True)

    if sys.platform == "win32":
        stop, start = ["schtasks", "/End", "/TN", WINDOWS_TASK], ["schtasks", "/Run", "/TN", WINDOWS_TASK]
    elif sys.platform == "darwin":
        target = f"gui/{os.getuid()}"
        plist = Path.home() / "Library" / "LaunchAgents" / f"{MAC_LABEL}.plist"
        stop, start = ["launchctl", "bootout", f"{target}/{MAC_LABEL}"], ["launchctl", "bootstrap", target, str(plist)]
    else:
        sys.exit("--restart works with the Windows task or the Mac launchd agent only.")

    home.mkdir(parents=True, exist_ok=True)
    (home / RESTART_NOTE).write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    run(*stop)   # fails harmlessly if it wasn't running
    for _ in range(60):
        lock = acquire_lock(home)
        if lock:
            lock.close()
            break
        time.sleep(0.5)
    else:
        (home / RESTART_NOTE).unlink(missing_ok=True)
        sys.exit("The old heartbeat didn't stop within 30 seconds; nothing restarted.")
    result = run(*start)
    if result.returncode:
        (home / RESTART_NOTE).unlink(missing_ok=True)
        sys.exit(f"Couldn't start the heartbeat (is it installed?): {(result.stderr or result.stdout).strip()}")
    print("Restarted. Lobo wakes now, and his log says the owner restarted him.")


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
    parser.add_argument("--log", action="store_true",
                        help="write output to <home>/heartbeat.log (for running hidden)")
    parser.add_argument("--scheduled", action="store_true",
                        help="started by Task Scheduler / launchd (changes the start message)")
    parser.add_argument("--restart", action="store_true",
                        help="restart the unattended heartbeat, logged as an owner restart")
    args = parser.parse_args()
    if args.restart:
        restart(args.home)
        return
    if args.log:
        # Run hidden (pythonw) there is no console to print to, so output
        # and any crash traceback go to a file instead.
        args.home.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(args.home / "heartbeat.log", "a",
                                       encoding="utf-8", errors="replace", buffering=1)
    else:
        # Lobo may write text the console can't display (some Windows consoles
        # are not UTF-8). Printing it should never crash the heartbeat.
        sys.stdout.reconfigure(errors="replace")

    lock = acquire_lock(args.home)
    if lock is None:
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] Another heartbeat is already running "
              f"for {args.home}. Exiting.")
        sys.exit(1)

    memory = Memory(args.home)
    client = ModelClient.from_backend(args.backend)
    # Starting the heartbeat wakes Lobo right away, whatever time it chose.
    # Say so in its log, as a plain fact, and let it draw its own conclusions.
    memory.record("start", start_message(args.home, args.once, args.scheduled))
    try:
        while True:
            before = last_id(memory)
            minutes = beat(memory, client)
            show_beat(memory, before)
            if args.once:
                break
            wake_at = time.time() + minutes * 60
            why = ""
            alarm_at = alarms.next_due(memory)
            if alarm_at is not None and alarm_at < wake_at:
                # An alarm comes due before the wake Lobo chose: wake for it.
                wake_at, why = alarm_at, " (for an alarm)"
            print(f"--- next beat at {datetime.fromtimestamp(wake_at):%H:%M} local{why}. "
                  "Ctrl+C to stop. ---\n")
            if sleep_until(wake_at, interrupt=lambda: inbox.knocked(memory)):
                print("--- knock: the owner sent a message; waking early. ---\n")
    except KeyboardInterrupt:
        memory.record("stopped", "Heartbeat stopped by the owner.")
        print("\nStopped.")
    finally:
        memory.close()
        lock.close()


if __name__ == "__main__":
    main()
