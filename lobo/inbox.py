"""Inbox: letters between the owner and Lobo.

The owner isn't Lobo's boss and doesn't hand it tasks; think neighbor
leaving notes, not ticket queue. A message from the owner waits in a mailbox
(a `messages` table in memory.db) until Lobo's next wake, when it's delivered
as a `message` event, right in the recent log Lobo reads. A message sent with
--now is a knock instead: the sleeping heartbeat notices within ~30 seconds
and wakes Lobo early.

Lobo writes back with the message_owner tool, if it wants to. Both directions
are also logged as `message` events, so Lobo can recall its conversations.

  python -m lobo.inbox "hello"          leave a letter (read at next wake)
  python -m lobo.inbox --now "hello"    knock: wake Lobo to read it
  python -m lobo.inbox                  show the conversation; marks Lobo's
                                        replies as read by you
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from lobo.memory import DEFAULT_HOME, Memory

MESSAGE_CHAR_LIMIT = 4000


def _table(memory: Memory) -> None:
    memory.db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            time      TEXT NOT NULL,
            sender    TEXT NOT NULL,      -- 'owner' or 'lobo'
            text      TEXT NOT NULL,
            knock     INTEGER NOT NULL DEFAULT 0,
            read_at   TEXT                -- when the other side saw it
        )
    """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _check(text: str) -> str:
    text = str(text).strip()
    if not text:
        raise ValueError("A message can't be empty.")
    if len(text) > MESSAGE_CHAR_LIMIT:
        raise ValueError(f"Message is {len(text)} chars; the limit is {MESSAGE_CHAR_LIMIT}.")
    return text


# --- owner side --------------------------------------------------------------

def owner_sends(memory: Memory, text: str, knock: bool = False) -> int:
    """Put a letter in Lobo's mailbox. Nothing is logged until Lobo reads it."""
    _table(memory)
    cur = memory.db.execute(
        "INSERT INTO messages (time, sender, text, knock) VALUES (?, 'owner', ?, ?)",
        (_now(), _check(text), int(knock)),
    )
    memory.db.commit()
    return cur.lastrowid


def conversation(memory: Memory, limit: int = 20) -> list[tuple]:
    """(id, time, sender, text, read_at), oldest first."""
    _table(memory)
    rows = memory.db.execute(
        "SELECT id, time, sender, text, read_at FROM messages ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return list(reversed(rows))


def owner_reads(memory: Memory) -> None:
    _table(memory)
    memory.db.execute(
        "UPDATE messages SET read_at = ? WHERE sender = 'lobo' AND read_at IS NULL", (_now(),))
    memory.db.commit()


# --- Lobo side ---------------------------------------------------------------

def deliver(memory: Memory) -> int:
    """At wake-up: log every unread owner message as an event, mark it read."""
    _table(memory)
    unread = memory.db.execute(
        "SELECT id, time, text FROM messages WHERE sender = 'owner' AND read_at IS NULL "
        "ORDER BY id"
    ).fetchall()
    for msg_id, sent, text in unread:
        memory.record("message", f"From the owner (sent {sent}):\n{text}")
        memory.db.execute("UPDATE messages SET read_at = ? WHERE id = ?", (_now(), msg_id))
        memory.db.commit()
    return len(unread)


def knocked(memory: Memory) -> bool:
    """Is there an unread knock? Checked by the sleeping heartbeat."""
    _table(memory)
    return memory.db.execute(
        "SELECT 1 FROM messages WHERE sender = 'owner' AND knock = 1 AND read_at IS NULL"
    ).fetchone() is not None


def lobo_sends(memory: Memory, text: str) -> str:
    _table(memory)
    text = _check(text)
    memory.db.execute(
        "INSERT INTO messages (time, sender, text) VALUES (?, 'lobo', ?)", (_now(), text))
    memory.db.commit()
    memory.record("message", f"To the owner:\n{text}")
    return "Sent. The owner will see it whenever they next check."


# --- the owner's command line ------------------------------------------------

def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Write to Lobo, or read the conversation.")
    parser.add_argument("text", nargs="*", help="your message (omit to read)")
    parser.add_argument("--now", action="store_true", help="knock: wake Lobo to read it")
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    args = parser.parse_args()

    memory = Memory(args.home)
    try:
        if args.text:
            try:
                owner_sends(memory, " ".join(args.text), knock=args.now)
            except ValueError as e:
                print(e)
                sys.exit(1)
            print("Knocked. Lobo wakes within a minute to read it." if args.now
                  else "Left in the mailbox. Lobo reads it at its next wake.")
            return
        rows = conversation(memory)
        if not rows:
            print("No messages yet.")
        for _, when, sender, text, read_at in rows:
            local = datetime.fromisoformat(when).astimezone()
            who = "You" if sender == "owner" else "Lobo"
            status = "" if sender == "lobo" else ("  (read)" if read_at else "  (not read yet)")
            new = "  [new]" if sender == "lobo" and not read_at else ""
            print(f"--- {who}, {local:%a %H:%M}{status}{new}\n{text}\n")
        owner_reads(memory)
    finally:
        memory.close()


if __name__ == "__main__":
    main()
