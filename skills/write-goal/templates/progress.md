# {{TITLE}}: progress

Where the run is. The master plan holds the facts, this file holds the state, and the goal text carries neither. Updated at
every state change, then committed and pushed.

**Now ({{DATE}}):** the master plan, this file and the goal are written; no step has started.

## Waiting on {{OWNER}}

Human steps hit and open questions, most blocking first. One line each: the step, and what it unblocks.

- Nothing yet.

## In flight

Written before it starts, removed when it lands: each dispatched implementer and each step unsafe to run twice (a deploy, a
migration). One line each: what, branch, worktree, command, UTC time.

- Nothing.

## Steps

- [x] Baselines read ({{FILL: HH:MM}} UTC)
- [ ] Plan 1 step 1: {{FILL: what}}

A step is ticked only with its evidence file, `{{PLANS_DIR}}/{{DATE}}-{{SLUG}}-evidence/<plan>.<step>.md`, named on its line in
parentheses and passing `check-pr.py`: `- [x] Plan 1 step 1: what ({{PLANS_DIR}}/{{DATE}}-{{SLUG}}-evidence/1.1.md)`.
- [ ] G1 {{FILL: name}}

## Rulings

Decisions the run made alone: `Ruling: <what>; <why>; <cost if wrong>`.

- None yet.

## Log

Newest last, one line per state change, each with its UTC time.

- {{DATE}} {{FILL: HH:MM}} UTC: plan written; {{FILL: the baselines in one line}}.
