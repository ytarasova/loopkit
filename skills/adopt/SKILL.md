---
name: adopt
description: Use when setting up loopkit in a repo, or on "adopt loopkit", "set up goals here", "add a constitution", "make write-goal work in this repo", when new-goal.py says to run adopt first, or when the owner changes how their runs work (orchestrator model, implementer model, how many subagents, what is hands-off).
---

# Adopt loopkit in a repo

loopkit's skills are generic; the repo supplies the facts. This skill reads
the repo, asks the owner only what the repo cannot say, and writes four
things:

| File | Holds | Read by |
| --- | --- | --- |
| `CONSTITUTION.md` | How work is done here: the core clauses plus the repo's own. | every session, `write-goal`'s goal text |
| `.claude/loopkit.json` | The knobs below. | `new-goal.py`, `check-goal.py`, `intent` |
| `.claude/loopkit/goal.md` | The goal template with this repo's commands written in. | `new-goal.py` |
| `CLAUDE.md` | A link to the constitution, and where gate baselines are read. | every session |

## The knobs

```json
{
  "owner": "Sam",
  "plans_dir": "docs/plans",
  "intent_dir": "docs/specs",
  "ends_at": "pr",
  "orchestrator": "Opus 5.5",
  "implementer": "sonnet",
  "reviewer": "sonnet",
  "max_parallel": 5,
  "runner": "make",
  "bypass": ["npx", "npm run", "pytest"],
  "goal_rules": { "one tier at a time": "test tiers share a database" },
  "assurance": ["tests", "coverage", "lint", "typecheck", "violations"],
  "surfaces": { "ui": ["^web/src/"], "service": ["^api/"], "cli": ["^cli/"] },
  "rollback_pattern": "",
  "ban_em_dash": true
}
```

| Key | Means |
| --- | --- |
| `owner` | Who the run hands questions and the PR to. |
| `ends_at` | `pr`: the goal ends at an open PR the owner merges. `production`: it ships and ends on gates read after deploy, and gates need a window. |
| `orchestrator`, `implementer`, `max_parallel` | Written into every goal: one orchestrator session, up to `max_parallel` implementer subagents at once, each in its own worktree. |
| `reviewer` | The model for both review stages, each run by a subagent that did not write the change. |
| `runner` | The one entry point for commands (`make`, `rake`, `just`, `./bin/dev`). Empty when the repo has none; then drop the runner sentence from the goal template. |
| `bypass` | Backticked commands that skip the runner. The checker fails a goal or master plan that uses one. |
| `goal_rules` | `{"text": "rule"}`: text every goal must keep, for rules a run here cannot do without. |
| `assurance` | The technical checks every changeset shows run, by the name its evidence uses: tests, coverage, lint, typecheck, violations (static analysis, security, fitness). |
| `surfaces` | Which changed files are a UI, a service or a CLI. `check-pr.py` then asks the PR for use-case screenshots, a curl request and response, or the command's run. |
| `rollback_pattern` | A regex every plan's Rollback must match, e.g. `[a-z-]+-production:\d+` for a task definition revision. |
| `ban_em_dash` | Fail any goal file with an em-dash. |

Changing a model or the subagent count later is an edit to
`.claude/loopkit.json` alone; the next `new-goal.py` picks it up. Changing
`ends_at` also means re-copying and refilling `.claude/loopkit/goal.md` (step
5), because the repo's copy is made from one template or the other.

Paths below are relative to this skill's base directory, shown when the skill
loads; `write-goal` is its sibling, `<base>/../write-goal`. Resolve them to
absolute paths before running anything from the target repo.

## Steps

1. **Read before asking.** `CLAUDE.md`, any `CONSTITUTION.md`, the runner
   (`Makefile`, `Rakefile`, `justfile`, `package.json` scripts), the CI
   workflows (which checks are required, which run on main after merge), the
   deploy path and its rollback, how tests share state (which suites can run
   at once in separate worktrees), what makes a fresh worktree runnable
   (dependencies, `.env`, ports), and the last 30 commits for fixes that taught a lesson. State what you found.
2. **Ask the frontier in one round,** numbered, each with your recommended
   answer: `owner`; `ends_at`; the four model knobs (recommend the defaults
   above); what is hands-off beyond the constitution's list (paid calls,
   deployed environments, another team's repo); who merges what. Nothing a
   grep could answer.
3. **Write `.claude/loopkit.json`.** Only keys that differ from the defaults
   in `write-goal/scripts/config.py` need to be there; write them all anyway,
   so the owner sees every knob.
4. **The constitution.**
   - None yet: copy `<base>/CONSTITUTION.md` and fill every
     `{{PROJECT: ...}}`. A project clause goes in only if a real mistake or a
     real constraint earned it; delete a line that has neither.
   - One exists: keep it, and its numbering. Add only the core clauses it
     lacks: fresh-context review with "PASS is a claim" (template §VI.3),
     "Ask before anything you cannot take back" with the reversibility test
     (§VIII.2), causes before symptoms (§III), no pre-existing failures
     (§V.2), pass-or-fail verification (§VI.7), stacked PRs (§VII.7). Then note the
     repo's own numbers for those six; step 5 needs them.
5. **The goal template.** Copy `<base>/../write-goal/templates/goal-<ends_at>.md`
   to `.claude/loopkit/goal.md`. Fill each `{{PROJECT: ...}}` with this
   repo's exact commands, read from the runner and CI, not guessed. Rewrite
   the `§` cites to the constitution's real numbers. Leave `{{FILL: ...}}`
   and the `{{UPPERCASE}}` names alone; they are per goal. Add a line for
   any skill the repo uses to open PRs or review, and drop any line naming a
   plugin that is not installed, except `superpowers`, which loopkit needs.
   A filled goal should stay near 3,000 characters (`check-goal.py` warns
   over 3,000, fails over 4,000): cut project lines before rules.
6. **`CLAUDE.md`.** Subagents load `CLAUDE.md`, not the goal or linked
   files, and it is what survives compaction, so it carries what every
   context must see, and nothing else:
   - a link to `CONSTITUTION.md` near the top;
   - the hands-off list in one sentence (§VIII.2 plus step 2's answers);
   - "During a /goal run, state is the newest `<plans_dir>/*-progress.md`;
     read it before acting.";
   - where gate baselines are read (CI runs, deploy status, logs, metrics),
     only if the code does not show it.
7. **Prove it.** Run `<base>/../write-goal/scripts/test_goal_kit.py`. Then scaffold
   a goal with `new-goal.py --slug adopt-smoke --title "Adopt smoke"`,
   confirm it writes three files with no `{{PROJECT:` and the knobs filled
   in, run `check-goal.py adopt-smoke` (it must fail only on unfilled placeholders
   and the unfilled `Done means:` line), and delete the three files it wrote.
8. **Land it the repo's way:** a branch and a PR per the constitution's
   merge rules, stacked on any open loopkit PR in the repo. Report the knobs you set and every answer you
   chose for the owner, so they can change one.

## Common mistakes

| Mistake | What happens |
| --- | --- |
| Replacing an existing constitution with the template | The repo's earned clauses and their numbers are lost, and every cite to them breaks. |
| Guessing a gate command | The run's first gate fails on a typo, or passes on a command that tests nothing. |
| Copying another repo's project clauses | Rules with no mistake behind them here; the run follows them anyway. |
| Leaving `{{PROJECT: ...}}` in the goal template | `new-goal.py` refuses to run. |
| Putting preferences in the goal template | They drift per repo. Models and counts live in `.claude/loopkit.json`. |
