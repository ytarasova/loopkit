# {{TITLE}}: master plan

Written {{DATE}} {{FILL: HH:MM}} UTC. Spec: {{FILL: the spec, the decision doc, or the owner's words}}.
State lives in [{{DATE}}-{{SLUG}}-progress.md]({{DATE}}-{{SLUG}}-progress.md); the goal text is
[{{DATE}}-{{SLUG}}-goal.md]({{DATE}}-{{SLUG}}-goal.md). Baselines below were read at the time above. A fact not read from its
source is marked `(unconfirmed)`, and a step reads it before anything depends on it.

## Order

| # | Plan | Delivers | Deletes | Touches |
| --- | --- | --- | --- | --- |
| 1 | {{FILL: name; a long plan may live in its own file, linked from its Plan N section}} | {{FILL: what ships}} | {{FILL: what goes, or "nothing"}} | {{FILL: apps, packages or services}} |

Each plan is one PR, stacked on the plan before it. {{FILL: "Plans run in this order." or which two may run beside each other, on the same base}}

## Decisions, answered

An unanswered decision stops the run. An answer longer than a row is a decision doc, linked here.

| Decision | Answer the run uses |
| --- | --- |
| {{FILL: decision}} | {{FILL: answer, and whose it is}} |

## Plan 1: {{FILL: name}}

**Measured facts ({{FILL: HH:MM}} UTC, source in parentheses)**

- {{FILL: what runs now and the rollback target (release, revision or commit), when the goal deploys}}
- {{FILL: every number a gate compares against, with its source and window}}

**Steps**

1. {{FILL: step, with the exact command}}

**Gates**

- **G1 {{FILL: name}}.** {{FILL: threshold}} within {{FILL: window, e.g. "10 min of the deploy completing" or "the last code commit"}}. Baseline: {{FILL: the number, and when it was read}}. Source: {{FILL: the command, dashboard, log or API that reads it}}.

**Failures.** {{FILL: what each likely red means and what the run does about it}}

**Coverage.** {{FILL: the tests that pin the change, or why existing suites cover it}}

**Rollback.** {{FILL: the exact command and target, migrations, data written, any one-way door; or "Revert the PR" when nothing deploys}}

**Human steps.** {{FILL: each one and what it unblocks, or "None expected."}}
