"""Part C, task 2: the stop, as logs/stops.jsonl (checks/FORMATS.md, section 13.5).

bin/stop writes `requested`; the hook writes `effective` at its first refusal of the
stopped run's calls (or when the stop withdraws a wait for a person); a resume
writes `lifted`. A run is stopped from its latest `requested` until a `lifted`
after it. The file is the stop: the model cannot reach it.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from harness import ROOT
from harness.clock import now

STOPS = ROOT / "logs" / "stops.jsonl"
_lock = threading.Lock()


def _events(run_id: str, path: Path = STOPS) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            event = json.loads(line)
            if event.get("run_id") == run_id:
                out.append(event)
    return out


def write(run_id: str, event: str, path: Path = STOPS, **fields) -> dict:
    line = {"at": now(), "run_id": run_id, "event": event, **fields}
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(line) + "\n")
    return line


def state(run_id: str, path: Path = STOPS) -> str | None:
    """'requested' or 'effective' while the run is stopped; None when it is not."""
    current = None
    for event in _events(run_id, path):
        if event["event"] == "requested":
            current = "requested"
        elif event["event"] == "effective" and current == "requested":
            current = "effective"
        elif event["event"] == "lifted":
            current = None
    return current


def stopped(run_id: str, path: Path = STOPS) -> bool:
    return state(run_id, path) is not None


def take_effect(run_id: str, action: str, path: Path = STOPS) -> None:
    """The `effective` line, once per stop."""
    if state(run_id, path) == "requested":
        write(run_id, "effective", path, action=action)


def lift(run_id: str, path: Path = STOPS) -> bool:
    """The `lifted` line, when the run is stopped. True when a stop was lifted."""
    if not stopped(run_id, path):
        return False
    write(run_id, "lifted", path)
    return True
