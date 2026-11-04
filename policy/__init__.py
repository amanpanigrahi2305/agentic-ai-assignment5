"""Assignment 5: RepoMind's Control & Policy layer, enforced in the harness.

    autonomy.yaml    the three columns, by action class (checks/FORMATS.md, section 13.1)
    placement.py     a call's action class and column, from its facts: shared by the hook and bin/replay_policy
    hook.py          the pre-call hook the registry runs before every tool call
    boundary.py      a boundary a user states through the inbox, parsed into policy/rules.jsonl
    disclosure.py    the line every comment carries, and the check for it
    stops.py         logs/stops.jsonl: a stop requested, effective, lifted

The model never sees any of it.
"""
