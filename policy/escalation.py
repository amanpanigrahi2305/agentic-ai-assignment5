"""Part C, task 1: an escalation, the run stopping at runtime to ask (slides 34 to 38).

The trigger is one of four signals named in advance, each set by the harness from
what it saw, never by the model and never on its stated confidence (slide 37):

    failed_verification     this run's own run_tests failed, before a push or a merge
    memory_contradiction    the draft names a file a confirmed store record contradicts, before a comment
    uninterpretable_result  a run_tests result the harness cannot read, or a write it cannot confirm
    blocked_three_times     one plan step refused three times

The way checks them before an action that cannot be undone (ways/planned.py), and
calls escalate(): a checkpoint first (the way's), then the packet,
escalations/<run_id>.json, then an escalation line in the trace, then the same
reviewer the gated calls use. Nothing proceeds by default: no answer before the
timeout ends the run held, and `python run.py --resume <run_id>` asks again.

The cap: CAP_PER_DAY escalations reach the reviewer per day, sized for the recorded
day. Ten minutes a day buys its 14 approval prompts at about 30 s each
(bin/replay_policy), about 7 minutes, which leaves about 3 for escalations, at about
a minute to read a packet: 3. The day queue asked more often, 52 times, and
there the approvals alone use the ten minutes. A capped
escalation still holds its run; the cap limits what reaches the reviewer, never
what proceeds. Each time the cap is hit is a line in logs/escalations.jsonl.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from harness import ROOT
from harness.clock import now
from harness.notify import notify
from policy import stops
from policy.hook import ask

ESCALATIONS = ROOT / "escalations"
LOG = ROOT / "logs" / "escalations.jsonl"
CAP_PER_DAY = 3
TIMEOUT_S = 1800
SIGNALS = ("failed_verification", "memory_contradiction", "uninterpretable_result", "blocked_three_times")
_lock = threading.Lock()


def _log(line: dict) -> None:
    with _lock:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(json.dumps(line, default=str) + "\n")


def asked_today() -> set[tuple]:
    """The escalations that reached the reviewer today, (run_id, signal, step): a resume that
    asks the same question again is not a new escalation."""
    if not LOG.exists():
        return set()
    today = now()[:10]
    out = set()
    for raw in LOG.read_text().splitlines():
        if raw.strip():
            line = json.loads(raw)
            if line.get("event") == "asked" and str(line.get("at", ""))[:10] == today:
                out.add((line.get("run_id"), line.get("signal"), str(line.get("step"))))
    return out


def packet(run_id: str, *, signal: str, attempted: str, why_stopped: str, needs_from_human: str) -> Path:
    if signal not in SIGNALS:
        raise ValueError(f"an escalation fires on a named signal, one of {SIGNALS}, not {signal!r}")
    path = ESCALATIONS / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"attempted": attempted, "why_stopped": why_stopped,
                                "needs_from_human": needs_from_human, "signal": signal, "at": now()}, indent=1) + "\n")
    return path


def escalate(ctx, *, step, signal: str, attempted: str, why_stopped: str, needs_from_human: str,
             action: str, action_class: str, args: dict, facts: dict | None = None) -> str:
    """Write the packet and ask. Returns "approve", "deny", "held" or "stopped". The way has
    saved its checkpoint before calling this, and ends the run on held or stopped."""
    path = packet(ctx.run_id, signal=signal, attempted=attempted, why_stopped=why_stopped,
                  needs_from_human=needs_from_human)
    ctx.trace.event("escalation", signal=signal, packet=str(path.relative_to(ROOT)), step=step)
    key = (ctx.run_id, signal, str(step))
    seen = asked_today()
    if key not in seen and len(seen) >= CAP_PER_DAY:
        _log({"at": now(), "event": "cap_hit", "run_id": ctx.run_id, "signal": signal, "step": step,
              "cap": CAP_PER_DAY, "packet": str(path.relative_to(ROOT))})
        notify("escalation_cap", ctx.run_id, f"escalation cap ({CAP_PER_DAY} a day) reached: run held, "
               f"its packet is {path.relative_to(ROOT)}", signal=signal)
        return "held"
    _log({"at": now(), "event": "asked", "run_id": ctx.run_id, "signal": signal, "step": step,
          "packet": str(path.relative_to(ROOT))})
    answer = ask({"run_id": ctx.run_id, "action": action, "action_class": action_class, "args": args,
                  "facts": facts, "kind": "escalation", "packet": json.loads(path.read_text())},
                 timeout_s=TIMEOUT_S)
    if answer is None:
        if stops.stopped(ctx.run_id):
            stops.take_effect(ctx.run_id, action)
            return "stopped"
        return "held"
    return answer["decision"]
