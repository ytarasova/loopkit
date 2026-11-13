# loopkit

How to run multi-day, unattended Claude Code sessions in a repo: a
constitution, an intent interview, and `/goal` files with a checker. The
skills are generic; `adopt` fits them to each repo.

| Skill | Does |
| --- | --- |
| `loopkit:adopt` | Reads the repo, asks what it cannot read, writes `CONSTITUTION.md`, `.claude/loopkit.json` and `.claude/loopkit/goal.md`. |
| `loopkit:intent` | Interviews you about a problem and writes the intent: problem, outcome, constraints, proof, open questions. |
| `loopkit:write-goal` | Turns an intent or spec into three files (goal, master plan, progress) and checks them before you run `/goal`. |

## Install

Needs the `superpowers` plugin (`subagent-driven-development`, `writing-plans`)
and Python 3.

```
/plugin marketplace add ytarasova/loopkit
/plugin install loopkit@loopkit
```

## The loop

1. `/loopkit:adopt` once per repo.
2. `/loopkit:intent <a sentence>`: the interview, then the intent file.
3. A spec or plan, when the design is open.
4. `/loopkit:write-goal`: baselines measured, master plan and progress file
   written, `check-goal.py` prints `ok`.
5. `/goal <contents of the goal file>`. The run orchestrates on
   `orchestrator`, fans out up to `max_parallel` `implementer` subagents in
   their own worktrees, has each change reviewed by a `reviewer` subagent that
   did not write it, ships each plan as a PR stacked on the one before,
   records each dispatch before it starts, and writes every state change to the progress file, so it can
   resume after compaction or a restart.
6. The run ends when the gates hold, or when it hits a step only you can
   take: then it records it under "Waiting on", pushes and stops. Read
   "Waiting on" and "Rulings" in the progress file.

## Customizing

- Per repo: edit `.claude/loopkit.json` (models, reviewer, subagent count, runner,
  rules the checker must see in every goal) or `.claude/loopkit/goal.md`.
- `.claude/loopkit/master.md` or `progress.md` in a repo replace this kit's
  templates for that repo.
- For everyone: edit the templates in `skills/write-goal/templates/` and the
  core clauses in `skills/adopt/CONSTITUTION.md`.

From this repo, `python3 skills/write-goal/scripts/test_goal_kit.py` checks the
scripts.

The intent skill credits Matt Pocock's `grilling` and Switch Dimension's
`molten-validate`, both MIT.
