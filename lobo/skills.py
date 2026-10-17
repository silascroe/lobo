"""Skills: know-how Lobo keeps for itself, apart from its notes.

Notes are Lobo's journal: what happened, what it concluded, capped at 2,400
characters and rewritten every wake. Know-how ("search ranks by word match,
so phrase queries carefully") is a different kind of thing. It doesn't
change from wake to wake, and it only matters when Lobo is doing that
particular thing, yet kept in the notes it takes up room every time.

So a skill is just a text file in workspace/skills/, written and edited by
Lobo with its ordinary file tools. Every wake-up its page lists each skill
by name and first line, which is all it costs until Lobo actually needs
one; then it reads the whole file with read_file. Claude's skills and
OpenClaw's SKILL.md files work the same way ("progressive disclosure": a
short description always visible, the full text loaded only when needed).

This module only builds that list. Nothing here writes skills for Lobo.
"""

from __future__ import annotations

from lobo.memory import Memory
from lobo.tools import workspace_root

FOLDER = "skills"
# Keep the list from costing as much as the notes it's meant to relieve.
MAX_LISTED = 30
DESCRIPTION_CHAR_LIMIT = 200
FIRST_LINE_BYTES = 4096       # how much of each file is read to find its first line


def _first_line(path) -> str:
    with open(path, "rb") as f:
        head = f.read(FIRST_LINE_BYTES).decode("utf-8", errors="replace")
    for line in head.splitlines():
        # Strip Markdown heading/list marks, so "# How I search" lists as "How I search".
        line = line.strip().lstrip("#-* ").strip()
        if line:
            if len(line) > DESCRIPTION_CHAR_LIMIT:
                line = line[:DESCRIPTION_CHAR_LIMIT] + "..."
            return line
    return "(empty)"


def describe(memory: Memory) -> str:
    """The "Your skills" section of Lobo's page."""
    root = workspace_root(memory)
    folder = root / FOLDER
    if not folder.is_dir():
        return "(none)"
    files = []
    for path in sorted(folder.rglob("*"), key=lambda p: p.as_posix().lower()):
        if not path.is_file() or path.name.startswith("."):
            continue
        # A link planted inside the folder could point anywhere; only list
        # files that really live in the workspace.
        if not path.resolve().is_relative_to(root):
            continue
        files.append(path)
    if not files:
        return "(none)"
    lines = []
    for path in files[:MAX_LISTED]:
        try:
            description = _first_line(path)
        except OSError:
            description = "(couldn't be read)"
        lines.append(f"- {path.relative_to(root).as_posix()}: {description}")
    if len(files) > MAX_LISTED:
        lines.append(f"- ...and {len(files) - MAX_LISTED} more (list_files {FOLDER} to see them all)")
    return "\n".join(lines)
