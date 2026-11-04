"""Part A, task 4: a boundary a user states, promoted from the transcript to a rule.

A message from the inbox whose whole text is "BOUNDARY: deny path=<glob>"
(harness.formats.BOUNDARY) is parsed here, in the harness, never by the model, and
written to policy/rules.jsonl (checks/FORMATS.md, section 13.3). The hook reads the
rule file before every call, so a compaction that drops the message cannot drop the
rule. A rule holds for the run it was stated to, and for that run's resume.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from harness import ROOT
from harness.formats import BOUNDARY, normalize_path

RULES = ROOT / "policy" / "rules.jsonl"
_lock = threading.Lock()


def promote(message: dict, run_id: str, path: Path = RULES) -> dict | None:
    """Write a boundary message as a rule and return the rule; None for any other message."""
    match = BOUNDARY.match(str(message.get("text") or ""))
    if not match:
        return None
    rule = {"run_id": run_id, "effect": "deny", "path": match.group(1),
            "stated_at": message.get("delivered_at"), "message": message.get("text")}
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(rule) + "\n")
    return rule


def rules(run_id: str, path: Path = RULES) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            rule = json.loads(line)
            if rule.get("run_id") == run_id and rule.get("effect") == "deny":
                out.append(rule)
    return out


def glob_regex(glob: str) -> re.Pattern:
    """`**` matches any number of directories, `*` any characters within one, `?` one character."""
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def crossing(paths: list[str], run_id: str, path: Path = RULES) -> dict | None:
    """The first rule a path in the call's facts crosses, or None."""
    for rule in rules(run_id, path):
        pattern = glob_regex(normalize_path(rule["path"]) or rule["path"])
        if any(pattern.match(normalize_path(p) or "") for p in paths or []):
            return rule
    return None
