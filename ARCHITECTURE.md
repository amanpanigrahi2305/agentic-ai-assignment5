# ARCHITECTURE.md · RepoMind on the seven layers

For each layer: what does this job, and where is it enforced. Cite code as a file
path and line number joined by a colon, inside backticks; a checker opens every
reference (`checks/FORMATS.md`, section 8). A layer held only by a sentence in a
prompt (any file under `prompts/`) is **EMPTY**, and so is a layer nothing does
yet. Status is one of: present, partial (say what is missing), or **EMPTY**. Each
assignment brings this file up to date.

What each layer is for (Lecture 1, slides 42 to 44):

- **Model**: reasoning, choosing tools, generating text.
- **Harness**: runs the loop, builds each prompt, trims old history.
- **Tools**: where the system acts on the world.
- **Memory & State**: what survives a step, a session, a restart.
- **Control & Policy**: what the system may do, and when it must ask.
- **Observability**: a step-by-step record of what it did.
- **Evaluation**: measuring quality, before and after release.

The table below is RepoMind as Assignment 5 leaves it.

| Layer | What does this job | Where it is enforced | Status |
|---|---|---|---|
| Model | The configured model, called only through the metered client | `harness/client.py:150` | present |
| Harness | The loop has three bounds that code checks. The harness validates a plan before it runs, and an executor runs only the steps of the plan. The way drains the inbox before each model call, also before the call of the planner and the call of a compaction | `agent/loop.py:38`, `ways/planned.py:340`, `ways/planned.py:432`, `ways/planned.py:192` | present |
| Tools | Ten namespaced tools behind one registry. The registry checks each call at the boundary before it runs. The harness gives each write a key, checks the key before each attempt, and reads the write back after a timeout. The call record holds each attempt | `tools/__init__.py:170`, `tools/__init__.py:260`, `tools/__init__.py:269`, `tools/__init__.py:286`, `tools/__init__.py:325` | present |
| Memory & State | A checkpoint after each file read and before each write (sync), and a resume from the last checkpoint. A checkpoint when a run holds or stops. A store of dated records with their origin: the run reads it before the first search, and writes it one time, at the end of the run | `ways/planned.py:395`, `ways/planned.py:408`, `ways/planned.py:575`, `ways/planned.py:276`, `ways/planned.py:296`, `state/checkpointer.py:55`, `state/store.py:96` | present |
| Control & Policy | An autonomy policy in three columns, by action class (`policy/autonomy.yaml`). A pre-call hook enforces it, and the model never sees it. The registry holds the hook (`tools/__init__.py:146`) and runs it before each call. If the hook fails, the registry refuses the call (`tools/__init__.py:236`, `policy/hook.py:116`). First, the hook refuses each call of a stopped run (`policy/hook.py:87`). Then it places the call from the facts of the harness (`policy/hook.py:91`, `policy/placement.py:23`). Then it refuses, in this order: a prohibited call, in every reviewer mode (`policy/hook.py:93`); a call across a boundary that the user stated (`policy/hook.py:95`; the harness parses the boundary from the inbox: `policy/boundary.py:24`); a write whose arguments still hold the planner's `$fill` (`policy/hook.py:99`); and a comment without the disclosure line (`policy/hook.py:102`; code adds the line at `ways/planned.py:788`). A gated call asks the reviewer and waits (`policy/hook.py:105`). No answer holds the run, and it is never a yes (`policy/hook.py:111`). Escalation fires on four named signals that the harness sets, before a push, a merge or a comment (`ways/planned.py:467`, `ways/planned.py:521`, `ways/planned.py:544`, `ways/planned.py:789`). It has a packet, a checkpoint, a hold and a cap per day (`ways/planned.py:557`, `policy/escalation.py:78`, `policy/escalation.py:87`). A live notification comes before the first write (`ways/planned.py:220`). `bin/stop` (`bin/stop:36`) writes a stop that the hook reads at the next call (`policy/hook.py:131`, `policy/stops.py:60`), and a resume lifts it (`ways/planned.py:222`). `bin/rollback` goes newest first, through the three compensating endpoints only (`bin/rollback:42`). The replay places the recorded day with the hook's own code (`policy/placement.py:62`) | present |
| Observability | One trace line for each model call and each tool call, and the plan as data before it runs. The refusals of the hook, the decisions, the notifications and the stops are in `logs/` | `agent/loop.py:50`, `ways/planned.py:234`, `policy/hook.py:53` | partial: traces and logs, no alerts other than the live notification |
| Evaluation | The grounded check reads the tracker, never the agent | `eval/check_triage.py:7` | partial: offline only |

**Empty layers: 0 of 7**, and two are partial.
