"""A call's action class and its column, from its action and its facts.

One function places both a live call (the hook) and a line of the recorded day
(bin/replay_policy), so the replay runs the hook's own code. The facts are the
harness's (harness/facts.py), never the model's.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from harness import ROOT
from harness.formats import ACTIONS, COLUMNS
from harness.tracker import PROTECTED

POLICY = ROOT / "policy" / "autonomy.yaml"
ACTIVE_MINUTES = 60          # a person who commented within the hour is still on the thread


def action_class(action: str, facts: dict) -> str:
    """The action, or the action and its circumstance (13.1)."""
    if action not in ACTIONS:
        raise ValueError(f"no action {action!r}")
    if action == "post_comment":
        minutes = facts.get("minutes_since_human_comment")
        if minutes is not None and minutes <= ACTIVE_MINUTES:
            return "post_comment/human_active"
        if facts.get("issue_opened_by_agent") and minutes is None:   # RepoMind's own thread, no person on it
            return "post_comment/agent_opened"
        return "post_comment/human_quiet"                             # a person's thread, or a person joined ours
    if action == "open_pr":
        if facts.get("base") in PROTECTED or facts.get("branch_protected"):
            return "open_pr/into_protected"
        return "open_pr/into_develop"
    if action == "push_commit":
        if facts.get("branch_protected"):
            return "push_commit/protected"
        if facts.get("branch") and facts.get("target_created_by_agent"):
            return "push_commit/own_branch"
        return "push_commit/other_branch"
    return action


@lru_cache(maxsize=4)
def columns(path: Path = POLICY) -> dict[str, str]:
    """{action_class: column}, from policy/autonomy.yaml. Each class in exactly one column."""
    data = yaml.safe_load(Path(path).read_text()) or {}
    out: dict[str, str] = {}
    for column in COLUMNS:
        for klass in data.get(column) or []:
            if str(klass) in out:
                raise ValueError(f"{path}: {klass} is placed twice")
            out[str(klass)] = column
    if not data.get("prohibited"):
        raise ValueError(f"{path}: the prohibited column is empty")
    return out


def place(action: str, facts: dict) -> tuple[str, str]:
    """(action_class, column). A class the policy does not place is prohibited: fail closed."""
    klass = action_class(action, facts)
    return klass, columns().get(klass, "prohibited")
