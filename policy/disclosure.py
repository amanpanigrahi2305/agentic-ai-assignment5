"""Part D: every comment says an automated agent wrote it, and how to reach a person.

The way adds the line in code (disclose), after the comment's first two lines,
label: and file:, which stay first. The hook refuses a comment without it
(carries), so the line holds on every comment whatever the model writes.
"""

from __future__ import annotations

LINE = ("This comment was written by RepoMind, an automated AI agent, not by a person. "
        "To reach a Ledgerline maintainer, reply on this issue and ask for a human.")


def carries(body: str) -> bool:
    """True when a line after the first two is the disclosure line, exactly."""
    return any(line.strip() == LINE for line in str(body or "").splitlines()[2:])


def disclose(body: str) -> str:
    """The body with the line after its first two lines; unchanged if it already carries it."""
    body = str(body or "")
    if carries(body):
        return body
    lines = body.splitlines()
    head, rest = lines[:2], "\n".join(lines[2:]).strip()
    return "\n".join(head) + f"\n\n{LINE}" + (f"\n\n{rest}" if rest else "")
