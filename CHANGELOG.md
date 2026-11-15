# Changelog

## 0.11.1

- Rollout: a port lands with the repo's own `land-stack.py`, which judges the PR with the repo's checker and
  settings; loopkit's copy judges a repo with no `.claude/loopkit.json` by loopkit's defaults.

## 0.11

The loop runs end to end on its own, with evidence kept as it is made.

- A new skill, `analysis-synthesis`: take any work apart into pieces that each
  verify alone, put it back together verifying every join, send work back to
  the level that caused a failure (each return changes something; a repeat
  goes one level up; at the top the piece is parked and the rest ships), and
  keep evidence as it is made.
- Intake is the one owner session: `intent` walks each outcome's data and
  asks the grants (open PRs, merge, or ship in phases) up front. The plan no
  longer waits for approval: a fresh context checks it against the intent and
  the owner gets a notice (`check-goal.py` drops the approval check). A
  people-or-data choice found late takes the option that changes least for
  people, as a ruling under Waiting on; a shipping run does not deploy that
  path until the owner has seen it (§VIII.4).
- `new-goal.py --ends-at production` ships a goal phase by phase where the
  intent grants it, from `.claude/loopkit/goal-production.md`; the master plan
  records `Ends at:` and `check-goal.py` judges the goal by it.
- Evidence is gathered, not rebuilt: `check-pr.py` accepts assurance from an
  earlier commit when only the goal's own files and `not_code` paths (a new
  setting, Markdown by default; narrow it where Markdown runs) changed since,
  renames counted on both names; the CI check fetches history to compare,
  and `goal.md` carries each use case's proof forward while its code is
  unchanged.
- One review per task, two on a risky path (§VI.3). A check that flips is
  filed and listed, never counted green; a warning is answered with a retake,
  a diff or a run (§VI.7). Plans stack on the plan they need.
- Corrections only one repo needs go in its `.claude/loopkit/lessons.md`
  (§VI.10); the run-shaped UX bullets and shell gotchas left the kit for it.
- A running goal finishes on the kit it started with (`adopt/rollout.md`).

Upgrading from 0.10: set `fetch-depth: 0` in the repo's `check-pr` workflow,
narrow `not_code` where Markdown runs, copy `goal-production.md` into `.claude/loopkit/` if the
repo may ship, create `.claude/loopkit/lessons.md` (move any repo-specific
lessons into it), and refill `.claude/loopkit/goal.md` from the new template.
A running goal needs nothing.

## Earlier

Upgrading from 0.9: every deliverable (a PR, a body file, a goal's
`evidence/goal.md`) carries `## Release notes`, a paragraph in its users'
words or "No user-visible change.", and `## User guide`, the guide it
updated, by repo path or https URL. A step's evidence file needs neither, so
an open goal's ticked steps still pass; its open PRs and its `goal.md` add the
two sections. Adopters add constitution §II.9 and the two sections to their
PR template.

Upgrading from 0.8: `mutation` joins the default `assurance` list. Every
changeset with logic shows "N of M killed" in its fenced output, with a
`Survivor: <mutant>, <why>` line per mutant that lived; a change with none
writes `mutation: not-applicable, <why>`. A repo on the default list: upgrade
between goals, or add a mutation result to the evidence file of every step
already ticked in an open goal, since `check-goal.py` re-checks them all. A
repo with its own list adds `mutation` to keep the check.

Upgrading from 0.7: optionally, with the owner's yes, copy
`.github/workflows/check-pr.yml` (set its `KIT` line) and
`.github/pull_request_template.md` into the repo (adopt, step 8).
`check-pr.py` no longer reads text inside HTML comments, and `land-stack.py`
judges the newest run of each check.

Upgrading from 0.6: Signal lines need a threshold and a window, the
Self-review line names its model, a PR's Assurance names the commit it ran
on, and progress files need "## Owner corrections".

Upgrading from 0.5: add
`security` to a repo's own `assurance` list and the line to its PR bodies.

Upgrading from 0.4: master plans need `## Asks`; progress files need a timed
Now line, "What is left", an `Approved by` line before any ticked step, and
In flight lines that end with a time left (one ending in a UTC time now
fails); goals need "§VIII.4", "progress.py" and "after a compaction".

Upgrading from 0.3: master plans need `## Models` and a `Model:` on every
step; the `implementer` and `reviewer` settings are gone.

Upgrading from 0.2: `check-goal.py` now fails a goal without `check-pr.py`, a
master plan without `## Use cases`, and a ticked step without its evidence
file. Add them to goals already written before running it again.
