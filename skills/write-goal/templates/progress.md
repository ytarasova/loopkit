# {{TITLE}}: progress

Where the run is. The master plan holds the facts, this file holds the state, and the goal text carries neither. Updated at
every state change, then committed and pushed.

**Now ({{DATE}} {{FILL: HH:MM}} UTC):** the master plan, this file and the goal are written; no step has started.

Times in this file come from the clock, never typed: `python3 <write-goal>/scripts/progress.py {{SLUG}} now "<text>"` rewrites
this line, `log "<text>"` adds a Log line, and `view` stamps the live view's update (when the repo has one).

Approved by {{OWNER}} {{FILL: YYYY-MM-DD HH:MM}} UTC: {{FILL: their words approving the master plan; no code before this line}}

## Waiting on {{OWNER}}

Human steps hit and open questions, most blocking first. One line each: the step, and what it unblocks.

- Nothing yet.

## In flight

Written before it starts, removed when it lands: each dispatched implementer and each step unsafe to run twice (a deploy, a
migration). One line each: what, branch, worktree, command, its model, and the time left ("40m").

- Nothing.

## What is left

Every step still to come, in order, including the ones after the last task (reviews, lanes, PRs, the report). Each with the
time left, read again at every state change.

| Step | Waits on | Time left |
| --- | --- | --- |
| {{FILL: the first step}} | nothing | {{FILL: e.g. 2h 30m}} |

## Steps

A step is ticked only with its evidence file, `{{PLANS_DIR}}/{{DATE}}-{{SLUG}}-evidence/<plan>.<step>.md`, named on its line in
parentheses and passing `check-pr.py`: `- [x] Plan 1 step 1: what ({{PLANS_DIR}}/{{DATE}}-{{SLUG}}-evidence/1.1.md)`. Once every
box is ticked, `{{PLANS_DIR}}/{{DATE}}-{{SLUG}}-evidence/goal.md` proves every use case again on the final code.

- [x] Baselines read ({{FILL: HH:MM}} UTC)
- [ ] Plan 1 step 1: {{FILL: what}}
- [ ] G1 {{FILL: name}}

## Rulings

Decisions the run made alone: `Ruling: <what>; <why>; <cost if wrong>`.

- None yet.

## Log

Newest last, one line per state change, each with its UTC time.

- {{DATE}} {{FILL: HH:MM}} UTC: plan written; {{FILL: the baselines in one line}}.
