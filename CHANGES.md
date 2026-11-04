# CHANGES.md

Three lines per assignment: what it added, what it removed, what it constrained.
Removals are logged like additions.

## Assignment 1
- **Added:** a bounded tool loop; four ways to triage an issue (a direct call, a workflow, an agent, and a hybrid of the two); a grounded success check that reads the tracker; a results script
- **Removed:** nothing
- **Constrained:** every agent run to three bounds checked in code (steps, tokens, wall clock); success to what the tracker holds for the run's ID

## Assignment 2
- **Added:** a plan written as data before the issue is read; a validator with four checks; an executor that runs only the plan's steps; one checkpoint that may revise the plan; a second pass before the comment; detectors and a diff over traces; a progress file and a compaction
- **Removed:** the model's choice of the next tool, in the planned way
- **Constrained:** every tool call to a step of a validated plan; revisions to steps not yet done; the comment to drafts that pass the second pass

## Assignment 3
- **Added:** five rewritten tool definitions with examples, among them open_pr; a boundary check before every call; errors that name the fix; harness-derived idempotency keys, a check before every write attempt and a read-back after a timeout; the call record; a fail-closed hook
- **Removed:** free-text tool descriptions and free-form filters; protocol detail in anything the model sees
- **Constrained:** every write to be safe to retry, and to a person when its outcome cannot be read back; the comment to the last write, after the PR

## Assignment 4
- **Added:** a checkpoint after each file read and before each write, saved sync; a resume from the last checkpoint that replays a write with its saved arguments and key; a memory store of dated records with their source and origin, read before the first search; a write policy with one record per issue, superseded when it disagrees
- **Removed:** the conversation from every checkpoint; the issue's own text from what memory shows a prompt
- **Constrained:** a crashed run to resume, never restart; what is remembered to what a person stated or RepoMind derived, each with its source


## Assignment 5
- **Added:** an autonomy policy in three columns, by action class (`policy/autonomy.yaml`). A pre-call hook enforces it, and the model never sees it. A boundary that a user states goes from the inbox into a rule file that the hook reads. A replay of a recorded day uses the hook's own code, and it estimates a plan review. An approval screen shows dry runs and the facts of the harness, and a decisions log records each answer. Escalation fires on four named signals, with a packet, a checkpoint, a hold and a cap per day. A live notification comes before the first write of each run. A stop that notifies takes effect at the next call, and a resume lifts it. Rollback goes newest first, through the three compensating endpoints. A disclosure line is on each comment: code adds it, and the hook requires it. A hook rule refuses, without a prompt, a write whose arguments still hold the planner's `$fill`
- **Fixed:** the way filled a `$fill` only at the start of a value. Now a value that holds `$fill` at any position goes back to the model to be filled. The day queue found the defect: 35 of the 52 prompts showed `$fill`, and RepoMind posted 7 comments with it on its own issues
- **Removed:** autonomous merge (`merge_pr` is prohibited in every reviewer mode). Closing issues (`close_issue` is prohibited, because the task never closes an issue). Pushes to `main`, or to any branch that RepoMind did not create, `develop` included. Pull requests into `main`. Any default that makes no answer into a yes
- **Constrained:** `push_commit` by circumstance: only to RepoMind's own pull-request branch, with the approval of a person, and with an escalation first when the run's own tests failed. `post_comment` by circumstance: alone only on an issue that RepoMind opened and that no person has joined; with the approval of a person on any thread that a person opened, joined or is active on; and never without the disclosure line. `open_pr` only into `develop`, with approval
