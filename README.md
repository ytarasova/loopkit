# loopkit

How to run multi-day, unattended Claude Code sessions in a repo: a
constitution, an intent interview, and `/goal` files with a checker. The
skills are generic; `adopt` fits them to each repo.

| Skill | Does |
| --- | --- |
| `loopkit:adopt` | Reads the repo, asks what it cannot read, writes `CONSTITUTION.md`, `.claude/loopkit.json`, `.claude/loopkit/goal.md` (and `goal-production.md` where a goal may ship) and `.claude/loopkit/lessons.md`. |
| `loopkit:intent` | Interviews you about a problem and writes the intent: problem, outcome, constraints, proof, open questions. |
| `loopkit:write-goal` | Turns an intent or spec into three files (goal, master plan, progress) and checks them before you run `/goal`. |
| `loopkit:analysis-synthesis` | Takes any big piece of work apart into pieces that each verify alone, and puts it back together verifying every join, with a lead per subtree when one context is not enough. |
| `loopkit:optimize` | Sets up a score over many of a system's users' tasks and the loop that raises it, with evo doing the search: cases, a scorer, gates against a false gain, and one PR per run. |

## Install

Needs the `superpowers` plugin (`subagent-driven-development`, `writing-plans`)
and Python 3.10 or newer (macOS's own `/usr/bin/python3` is 3.9 and fails). Repos with a UI also use `frontend-design`, `playwright` and
`chrome-devtools-mcp` (its `a11y-debugging`) for the UX review.

```
/plugin marketplace add ytarasova/loopkit
/plugin install loopkit@loopkit
```

## The loop

1. `/loopkit:adopt` once per repo.
2. `/loopkit:intent <a sentence>`: the interview, then the intent file. It is
   the one session you give the work: it walks the data, asks the choices
   about people and their data, and records your grants (open PRs, merge, or
   ship in phases).
3. A spec or plan, when the design is open.
4. `/loopkit:write-goal`: baselines measured, master plan and progress file
   written, `check-goal.py` prints `ok`.
5. `/goal <contents of the goal file>`. The run orchestrates on
   `orchestrator`, fans out up to `max_parallel` `implementer` subagents in
   their own worktrees, has each change reviewed by a `reviewer` subagent that
   did not write it, ships each plan as a PR stacked on the plan it needs,
   sends work back to the level that caused a failure,
   records each dispatch before it starts, and writes every state change to the progress file, so it can
   resume after compaction or a restart.
6. The run ends when the gates hold (merged or shipped, when granted), or
   when it hits a step only you can take: then it records it under "Waiting
   on", pushes and stops. Read
   "Waiting on" and "Rulings" in the progress file. No part is done without
   its complete evidence in its PR: tests and their output; screenshots
   (UI), curl request and response (service) or the command's run (CLI);
   success and failure signals for the rollout; simplify, self-review and
   the constitution cross-checked. `check-pr.py <PR>` checks it, and CI runs it on every PR.

Lessons from the owner's corrections across runs are built in: asks tracked
from the intent to the final message, choices about people and their data
asked at intake, times
stamped from the clock (`progress.py`), a time left on every open item, a
fuller UX walk, and an ending that cleans up and says what shipped.

Security is part of every changeset's proof: `security` is in the default
`assurance` (a secret scan, a dependency audit, static analysis), the Review
needs a `Security review:` line, and `check-pr.py` fails a body or evidence
file carrying anything shaped like a credential. The loop closes after the PRs too: `land-stack.py` lands a stack in order
(retarget first, merge up, stop before a fix is lost), each Signal line
carries a threshold and a window to watch after the deploy, evidence is
written once and gathered rather than rebuilt, and every owner correction ends
as a kit change, or a lesson in the repo, shipped off main.

Work with no finished state, only a score to raise across many user tasks, runs as an optimize loop instead of
steps 3 to 6: `/loopkit:optimize` writes the cases, the scorer and the gates, measures the baseline, and hands the
search to evo (github.com/evo-hq/evo, installed only on the owner's word). Each run ends as one PR with its
evidence, or with a report that nothing valid was found. The parts that must be exact: `skills/optimize/contract.md`.

Rolling a loopkit change out to repos that adopted it: `skills/adopt/rollout.md`.

Models: the intent says which orchestrator the work needs ("This is best
handled by Fable 5.2, because ..." or Opus 5.5), and the master plan names a
model per step (haiku, sonnet or opus), from `write-goal/models.md`.

What changed in each version, and how to upgrade: [`CHANGELOG.md`](CHANGELOG.md).

## Customizing

- Per repo: edit `.claude/loopkit.json` (models, reviewer, subagent count, runner,
  rules the checker must see in every goal) or `.claude/loopkit/goal.md`.
- `.claude/loopkit/master.md` or `progress.md` in a repo replace this kit's
  templates for that repo.
- For everyone: edit the templates in `skills/write-goal/templates/` and the
  core clauses in `skills/adopt/CONSTITUTION.md`.
- The kit stays generic: no domain or product concepts (tenants, one product's
  nouns, a particular stack). What is specific to one system lives in that
  system's repo, in its adoption.

From this repo, `python3 skills/write-goal/scripts/test_goal_kit.py` checks the
scripts; CI runs it on Python 3.10 and 3.14 on every PR and push to main, and gitleaks over each PR's commits and each push to main.

The intent skill credits Matt Pocock's `grilling` and Switch Dimension's
`molten-validate`, both MIT.
