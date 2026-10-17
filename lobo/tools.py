"""Tools: things Lobo can do besides think.

A tool is just a Python function plus a description the model reads. The
model can't run code. It can only ask, in its reply, for a tool to be run
("tool": "recall", "args": {"query": "rats"}). The heartbeat sees that, runs
the function, and hands the result back to the model as a new message. The
model then keeps thinking with the result in front of it.

That round trip (model asks, Python runs, result goes back) is how every
tool-using agent works, Codex and Claude Code included. Theirs use a fancier
built-in API for the asking part; Lobo uses plain JSON so you can read every
step in its log.

First tool: recall, a search over Lobo's own permanent event log. Read-only,
touches nothing but its own memory.
"""

from __future__ import annotations

from lobo.memory import Memory

# Long log entries (old notes, long thoughts) get cut to this in results,
# so one search can't flood the model's page.
RESULT_CHAR_LIMIT = 500


def recall(memory: Memory, query: str, limit: int = 10) -> str:
    query = str(query).strip()
    if not query:
        return "recall needs a non-empty query."
    # Skip past tool results: they contain old search results, so including
    # them would make every search echo the ones before it.
    hits = memory.search(query, limit=int(limit), exclude_kinds=("tool",))
    if not hits:
        return f"No events contain {query!r}."
    lines = [f"{len(hits)} event(s) containing {query!r}, newest first:"]
    for e in hits:
        text = e.content
        if len(text) > RESULT_CHAR_LIMIT:
            text = text[:RESULT_CHAR_LIMIT] + " [...]"
        lines.append(f"[{e.time}] {e.kind}: {text}")
    return "\n".join(lines)


# name -> (function, description shown to the model)
TOOLS = {
    "recall": (
        recall,
        'Search your entire permanent log (every past wake, thought, and notes '
        'version, not just the recent ones you see). Matches text exactly, '
        'case-insensitive, so search one distinctive word or short phrase. '
        'Args: {"query": "<text>"}',
    ),
}


def describe() -> str:
    """Tool list, formatted for the system prompt."""
    return "\n".join(f"- {name}: {desc}" for name, (_, desc) in TOOLS.items())


def run(memory: Memory, name: str, args: dict) -> str:
    """Run a tool by name. Mistakes come back as text the model can read,
    not as crashes: a bad tool call is something Lobo should learn from."""
    if name not in TOOLS:
        return f"Unknown tool {name!r}. Available: {', '.join(TOOLS)}."
    if not isinstance(args, dict):
        return f"args for {name} must be a JSON object."
    function, _ = TOOLS[name]
    try:
        return function(memory, **args)
    except (TypeError, ValueError) as e:
        return f"Bad args for {name}: {e}"
