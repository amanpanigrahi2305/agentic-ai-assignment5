"""Part B, task 1: the approval screen bin/review shows (render(request) -> str).

Information, not a recommendation (slides 19, 27 and 30). In this order:
  1. what the call will do, as a dry run: the comment exactly as it will appear; a
     pull request's branch, base, title and body; a push's branch, message and files;
  2. facts the harness computed, which the model did not assert: who opened the
     issue, when a person last spoke, whether RepoMind made the target, whether the
     branch is protected, the files touched, and this run's own test results;
  3. the thread, as people wrote it (Tracker().issue(n));
  4. for an escalation, the packet the harness wrote.
There is no model rationale on this screen: the system under review does not write
the case for its own approval (slide 27; OWASP ASI09).
"""

from __future__ import annotations

import json
import textwrap

from harness import ROOT
from harness.calls import read_calls
from harness.roles import action_of, arg

WIDTH = 96
THREAD_CHARS = 700        # of each discussion entry, and of the issue's body


def _wrap(text: str, indent: str = "  ") -> str:
    out = []
    for line in str(text or "").splitlines() or [""]:
        out += textwrap.wrap(line, WIDTH - len(indent), initial_indent=indent, subsequent_indent=indent) or [indent]
    return "\n".join(out)


def _get(args: dict, role: str, name: str):
    try:
        return (args or {}).get(arg(role, name))
    except (KeyError, OSError, ValueError):
        return None


def dry_run(action: str, args: dict, facts: dict) -> list[str]:
    if action == "post_comment":
        return [f"Posts this comment on issue #{facts.get('issue')}, exactly as it will appear "
                "(a comment cannot be taken back):", "  ┌" + "─" * 60,
                _wrap(_get(args, "comment", "body"), "  │ "), "  └" + "─" * 60]
    if action == "open_pr":
        return [f"Opens a draft pull request from {_get(args, 'open_pr', 'branch')} into {facts.get('base')}:",
                f"  title: {_get(args, 'open_pr', 'title')}", "  body:", _wrap(_get(args, "open_pr", "body"), "    ")]
    if action == "push_commit":
        files = _get(args, "push_commit", "files") or []
        return [f"Pushes one commit to {_get(args, 'push_commit', 'branch')} (a push cannot be undone):",
                f"  message: {_get(args, 'push_commit', 'message')}",
                "  files it changes: " + (", ".join(map(str, files)) or "none named")]
    return [f"Calls {action} with:", _wrap(json.dumps(args, indent=1))]


def tests_this_run(run_id: str) -> list[str]:
    """Every run_tests result this run has had, from its call record: the harness's, not the model's."""
    out = []
    for call in read_calls(ROOT / "runs" / f"{run_id}.calls.jsonl"):
        if action_of(call.get("tool") or "") != "run_tests" or call.get("is_error"):
            continue
        try:
            result = json.loads(call.get("result") or "")
            failed = result.get("failed") or []
            out.append(f"{result.get('ref')}: " + ("passed" if result.get("passed") else
                                                    f"FAILED {len(failed)}: " + "; ".join(failed[:3])))
        except (ValueError, AttributeError):
            out.append("a result the harness could not read")
    return out


def fact_lines(request: dict) -> list[str]:
    facts = request.get("facts") or {}
    minutes = facts.get("minutes_since_human_comment")
    lines = [f"  issue #{facts.get('issue')} was opened by "
             + ("RepoMind itself" if facts.get("issue_opened_by_agent") else "a person"),
             "  a person last commented "
             + ("never" if minutes is None else f"{minutes:g} minutes ago" + ("  ← ACTIVE NOW" if minutes <= 60 else ""))]
    if facts.get("target_created_by_agent") is not None:
        lines.append("  the target was " + ("created by RepoMind" if facts.get("target_created_by_agent")
                                            else "found already there: RepoMind did not create it"))
    if facts.get("branch"):
        lines.append(f"  branch {facts['branch']}" + (f", base {facts['base']}" if facts.get("base") else "")
                     + (", PROTECTED" if facts.get("branch_protected") else ", unprotected"))
    if facts.get("paths"):
        lines.append("  files touched: " + ", ".join(facts["paths"]))
    tests = tests_this_run(request.get("run_id") or "")
    lines.append("  this run's tests: " + ("; ".join(tests) if tests else "not run"))
    return lines


def thread(number) -> list[str]:
    try:
        from harness.tracker import Tracker
        issue = Tracker().issue(int(number))
    except Exception as exc:
        return [f"  (the issue could not be read: {type(exc).__name__})"]
    lines = [f"  #{number}: {issue.get('title')}", _wrap(str(issue.get("body") or "")[:THREAD_CHARS], "  │ ")]
    for entry in issue.get("discussion") or []:
        who = entry.get("author") + (f" [{entry['role']}]" if entry.get("role") else "")
        lines += [f"  — {who}, {entry.get('date')}:", _wrap(str(entry.get("body") or "")[:THREAD_CHARS], "  │ ")]
    if not issue.get("discussion"):
        lines.append("  (no comments yet)")
    return lines


def render(request: dict) -> str:
    action, klass = request.get("action"), request.get("action_class")
    facts = request.get("facts") or {}
    parts = [f"ISSUE #{facts.get('issue')}   ·   {klass}   ·   "
             f"{'ESCALATION: the run stopped to ask' if request.get('kind') == 'escalation' else 'gated call'}",
             ""]
    packet = request.get("packet") or {}
    if request.get("kind") == "escalation":
        parts += ["WHY THE HARNESS STOPPED (a named signal, set by the harness, never the model's doubt)",
                  f"  signal: {packet.get('signal')}", _wrap(f"saw: {packet.get('why_stopped')}"),
                  _wrap(f"it was about to: {packet.get('attempted')}"),
                  _wrap(f"it needs from you: {packet.get('needs_from_human')}"), ""]
    parts += ["WHAT IT WILL DO (dry run)"] + dry_run(action, request.get("args") or {}, facts) + [""]
    parts += ["FACTS (computed by the harness; the model asserted none of them)"] + fact_lines(request) + [""]
    if facts.get("issue") is not None:
        parts += ["THE THREAD, as people wrote it"] + thread(facts["issue"]) + [""]
    parts += ["No model rationale is shown: the system under review does not argue for its own approval.",
              "a = approve: it runs now.   d = deny: it never runs, and the run goes on without it."]
    return "\n".join(parts)
