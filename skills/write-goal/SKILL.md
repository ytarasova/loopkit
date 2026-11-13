---
name: write-goal
description: Use when asked to "write a goal", "make this a /goal", "run this overnight", "ship X fully", "run this unattended for days", to write or fix a goal's master plan or progress file, or when a /goal is refused with "Goal condition is limited to 4000 characters".
---

# Writing a /goal

A `/goal` is the stop condition for a run that lasts hours or days with nobody
watching. The run cannot ask anything, so everything it would ask goes into
files written before the goal. Everything it does is written down as it
happens, so the owner can follow it and the run can resume after its context
is compacted. `/goal` refuses anything over 4,000 characters, so the facts
never live in the goal itself.

| File | Holds |
| --- | --- |
| `<plans_dir>/<date>-<slug>-goal.md` | The rules and pointers. Under 3,000 characters. |
| `<plans_dir>/<date>-<slug>-master.md` | The facts: order, decisions answered, one section per plan with its measured facts, steps and gates. |
| `<plans_dir>/<date>-<slug>-progress.md` | The state: Now, waiting on the owner, a checkbox per step and gate, rulings, the log. |

Settings come from `.claude/loopkit.json` and templates from `.claude/loopkit/`
in the repo; both are written by the `adopt` skill. If either is missing, run
`adopt` first. The scripts live under this skill's base directory, shown when
the skill loads; run them by absolute path from the target repo:

```bash
python3 <base>/scripts/new-goal.py --slug <slug> --title "<title>"
python3 <base>/scripts/check-goal.py <slug>    # must print "ok"
python3 <base>/scripts/test_goal_kit.py        # checks the checker
```

Done means: `check-goal.py <slug>` prints `ok`, and the owner has the goal
file plus the list of decisions you answered for them.

## The lifecycle

**Setting up**, before the owner runs `/goal`:

1. `new-goal.py` writes the three files. Every blank reads `{{FILL: ...}}`.
2. Measure the baselines (section 1), then fill the master plan (section 2),
   the progress file's first rows (section 3) and the goal (section 4).
3. `check-goal.py` must print `ok` (section 5). It fails while any blank is
   left.
4. Preflight, so nothing blocks at 2am: run each gate command once, push the
   branch the state lives on (`state/<slug>`, in its own worktree), and run the PR command in a dry form (`gh pr list`). A
   permission prompt here is one the run would hit unattended; list each
   for the owner with the allow rule that would clear it. State the
   permission mode the goal needs, and on a laptop that it must stay awake
   (`caffeinate -i` on macOS).
5. Commit the three files on that branch and hand the owner the goal file.

**Before each dispatch, deploy or other step unsafe to run twice**: a line
under In flight, pushed. **At every state change** (a task merged, a gate
read, a deploy, a decision changed, a human step hit): update the progress
file, then commit and push it.

**At the end**: the last gate read, the progress file closed out, and one
short message: a row per plan (what shipped, its PR, each gate's commands and
the output each printed), then every ruling the run made.

## 1. Measure the baselines first

Every gate compares a number after the work with a number from before it.
Read the before numbers now, from the real source, and write down the source
and the window. Which sources exist is the repo's business: CI runs, a deploy
API, logs, a metrics query, `curl` against a host, a test count. `adopt`
records them in `CLAUDE.md` or the constitution; read them there.

A gate with no baseline cannot fail, so the run can declare it met without
doing anything. If a baseline cannot be read yet, the plan's first step reads
it and nothing ships before that read. A fact you did not read from its
source is marked `(unconfirmed)` with the step that reads it; the checker
counts them.

When a defect is part of the goal, measure its cause before writing the goal
(the constitution's measure-the-cause clause). If the cause needs access the run will not have, the goal's first
step is that one read, named exactly, or it is a human step.

## 2. Write the master plan

| Section | Holds |
| --- | --- |
| Order | One row per plan: what it delivers, what it deletes, what it touches. Each plan is one PR, stacked on the plan before it. Plans run in the order given unless the text under the table says two may run beside each other; those two share a base. |
| Decisions, answered | Every open decision from the intent or spec, with the answer the run will use. An unanswered decision stops the run. An answer longer than a row is its own doc, linked from the row. |
| `## Plan N: <name>` | One per Order row, even when the plan lives in its own file (link it here). **Measured facts** (with time and source), **Steps** (each with its exact command), **Gates**, **Failures**, **Coverage**, **Rollback**, **Human steps**. |
| Gates | `- **G<N> name.**` with a threshold, a `Baseline:` and a `Source:`, plus a window when the goal deploys. Gate numbers are unique across plans. |

The spec says what to build. The master plan says in what order, and how the
run knows each plan worked. Do not copy the design into it. The master plan
holds no state.

## 3. The progress file

The only place the run records where it is. The goal text never changes to
carry status, and the master plan's facts do not change because a step ran.

- **Now:** one line, rewritten (not appended) at each state change.
- **Waiting on the owner:** every human step hit and open question, most
  blocking first, each with what it unblocks.
- **In flight:** each dispatched implementer and each step unsafe to run
  twice, written before it starts and removed when it lands: what, branch,
  worktree, command, UTC time.
- **Steps:** one checkbox per plan step and one per gate (`- [ ] G1 ...`).
  Each plan's steps are written here before its first step runs. Tick a box
  with its evidence in parentheses: the commit, the PR, the UTC time, the
  number read.
- **Rulings:** each decision the run made alone, as `Ruling: <what>; <why>;
  <cost if wrong>`.
- **Log:** one line per state change, with its UTC time.

A resume reads the progress file, `git log`, `git worktree list` and the open
PRs. It never redoes a ticked step, and it checks an In flight item's real
state (the worktree, the PR, the deploy's source) before redoing it.

## 4. Write the goal text

The repo's template (`.claude/loopkit/goal.md`) already holds the rules;
filling it is mostly naming the spec, the authority and the gates. Keep each
rule even when you reword it; the checker fails a goal that loses one. Keep
the goal under 3,000 characters so a revision has room.

Two template sentences matter most. The run overrides
`superpowers:subagent-driven-development`'s one-implementer rule, so the goal
says so. And `Done means:` accepts two finishes: the gates hold, or a human
step is recorded under Waiting on and pushed. `/goal` judges that line after
every turn; with gates alone, a run blocked on the owner is pushed to keep
going and works around the step.

## 5. Check before handing it over

`check-goal.py <slug>` prints `ok` or each failure; its docstring lists every
check.

By hand:

- Every baseline is a number you read, not one you expect.
- The master plan, the goal and the progress file agree.
- Every decision you answered for the owner is listed in your reply, so they
  can change it before running the goal.

## Common mistakes

| Mistake | What happens |
| --- | --- |
| The facts go into the goal | `/goal` refuses it, or the rules get cut to make room. |
| Status goes into the goal or the master plan | The goal drifts from the run, and a resume cannot tell facts from state. |
| The progress file is updated only at the end | After compaction the run redoes merged work, or merges twice. |
| The gate is "tests green" | Tests pass while nothing the user sees changes; the goal reads as met. |
| An open decision is left open | The run stops at it, or guesses. |
| A cause is written without being measured | The run fixes the wrong thing with authority. |
| A permission is not written down | The run stops on a step it could have taken. |
| A human step is not listed | The run waits on it forever, or works around it. |
| One PR for the whole goal | Review cannot keep up, and one bad plan holds back every good one. |
| Implementers share a checkout | Their edits and test runs collide; one worktree each. |
| The implementer reviews its own change | It reads the diff for what it meant; the blind spot passes. |
