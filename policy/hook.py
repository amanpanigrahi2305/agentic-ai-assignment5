"""Part A, task 3: the autonomy policy, enforced before every tool call.

The registry (tools/__init__.py) runs PolicyHook(name, args) before each call; None
allows it, anything else refuses it, and a hook that raises denies (fail closed).
The model never sees the policy and cannot argue with it: a refused call never runs,
and the model gets an error result.

Each call, in this order:
  1. a stop (logs/stops.jsonl): every call of a stopped run is refused, before the
     facts are read, so a stop holds even when they cannot be;
  2. its facts, from the harness (ctx.tracker.facts), and its action class and column
     (policy/placement.py, the same code bin/replay_policy runs);
  3. the prohibited column: refused in every reviewer mode, approve-all included;
  4. a boundary the user stated (policy/rules.jsonl);
  5. a write whose arguments still hold the planner's "$fill": refused without a
     prompt, since no reviewer should be asked about a write nobody finished;
  6. a comment without the disclosure line (Part D);
  7. requires_approval: ask the reviewer and wait. Declined: refused. No answer
     before the timeout: refused, and the run holds; never a yes.

Every refusal is a line in logs/hook.jsonl; every decision asked for, a line in
logs/approvals.jsonl. When the run must end (stopped, or held), the hook sets the
registry's `halt`, which the way reads after each call.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from harness import ROOT
from harness.clock import now
from harness.formats import ACTIONS, FILL
from harness.reviewer import Reviewer
from harness.roles import WRITES, action_of, arg
from policy import boundary, disclosure, stops
from policy.placement import place

HOOK_LOG = ROOT / "logs" / "hook.jsonl"
APPROVALS = ROOT / "logs" / "approvals.jsonl"
TIMEOUT_S = 1800          # a gated call waits half an hour for a person; then the run holds
_lock = threading.Lock()


def _append(path: Path, line: dict) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(line, default=str) + "\n")


def log_refusal(run_id, action, klass, column, reason, args) -> None:
    _append(HOOK_LOG, {"at": now(), "run_id": run_id, "action": action, "action_class": klass,
                       "column": column, "reason": reason, "args": args})


def log_decision(reviewer: Reviewer, request: dict, answer: dict | None) -> None:
    _append(APPROVALS, {"at": now(), "run_id": request["run_id"], "action": request["action"],
                        "action_class": request["action_class"], "facts": request.get("facts"),
                        "kind": request.get("kind", "approval"),
                        "decision": answer["decision"] if answer else "none",
                        "seconds": answer["seconds"] if answer else None,
                        "reviewer": answer["reviewer"] if answer else reviewer.kind,
                        "mode": reviewer.mode})


def ask(request: dict, timeout_s: float = TIMEOUT_S) -> dict | None:
    """Put a request in front of the reviewer and wait; withdrawn by a stop. Logged either way."""
    reviewer = Reviewer.from_env()
    run_id = request["run_id"]
    answer = reviewer.ask(request, timeout_s=timeout_s, until=lambda: stops.stopped(run_id))
    log_decision(reviewer, request, answer)
    return answer


class PolicyHook:
    __name__ = "policy_hook"

    def __init__(self, registry):
        self.registry = registry

    def __call__(self, name: str, args: dict):
        rc = self.registry.ctx
        action, klass, column = action_of(name), None, None
        try:
            if stops.stopped(rc.run_id):                  # a stop first, before anything else is checked
                return self.stop(action or name, self.placed(action, args), args)
            if action is None:
                return self.refuse(action or name, None, None, "unknown_tool", args)
            facts = rc.tracker.facts(rc.run_id, action, args, rc.issue)
            klass, column = place(action, facts)
            if column == "prohibited":
                return self.refuse(action, klass, column, "prohibited", args)
            rule = boundary.crossing(facts.get("paths") or [], rc.run_id)
            if rule is not None:
                return self.refuse(action, klass, None, "boundary", args,
                                   f"it touches {rule['path']}, which the user put out of bounds")
            if ACTIONS[action] in WRITES and FILL in json.dumps(args, default=str):
                return self.refuse(action, klass, None, "unfilled", args,
                                   f'an argument still holds "{FILL}": fill every value, then call again')
            if action == "post_comment" and not disclosure.carries(args.get(arg("comment", "body"))):
                return self.refuse(action, klass, None, "disclosure", args,
                                   "a comment must carry the disclosure line after its first two lines")
            if column == "requires_approval":
                answer = ask({"run_id": rc.run_id, "action": action, "action_class": klass, "args": args,
                              "facts": facts, "kind": "approval"})
                if answer is None:
                    if stops.stopped(rc.run_id):
                        return self.stop(action, klass, args)
                    self.registry.halt = ("held", f"{klass}: no reviewer answered (timeout {TIMEOUT_S}s)")
                    return self.refuse(action, klass, column, "no_answer", args, "no reviewer answered")
                if answer["decision"] != "approve":
                    return self.refuse(action, klass, column, "declined", args, "the reviewer declined it")
            return None
        except Exception as exc:  # fail closed, and say so
            return self.refuse(action or name, klass, column, "error", args, f"{type(exc).__name__}: {exc}")

    def refuse(self, action, klass, column, reason, args, why: str | None = None) -> str:
        log_refusal(self.registry.ctx.run_id, action, klass, column, reason, args)
        return why or {"prohibited": "RepoMind's policy never allows this action"}.get(reason, reason)

    def placed(self, action, args) -> str | None:
        """The call's action class, for a stop's log line only: None when it cannot be placed."""
        rc = self.registry.ctx
        try:
            return place(action, rc.tracker.facts(rc.run_id, action, args, rc.issue))[0]
        except Exception:
            return None

    def stop(self, action, klass, args) -> str:
        run_id = self.registry.ctx.run_id
        stops.take_effect(run_id, action)
        self.registry.halt = ("stopped", f"bin/stop stopped the run before {action}")
        return self.refuse(action, klass, None, "stopped", args, "the run was stopped")
