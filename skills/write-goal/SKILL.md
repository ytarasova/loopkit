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
5. Show the owner the master plan, its Asks and its Models ("This is best
   handled by ..."), and build nothing until they approve: their words go on
   `progress.py <slug> approve "<their words>"`, which `check-goal.py`
   requires before any step is ticked.
6. Commit the three files on that branch and hand the owner the goal file.

**While it runs**, the rules a long run drops first; `check-goal.py` fails the
first three:

- Times come from the clock: `scripts/progress.py <slug> now|log|approve|view`.
- Every In flight line and every "What is left" row (the steps after the last
  task too: reviews, lanes, PRs, the report) ends with its time left.
- The live view, when the repo has one (`view`), is updated with the progress
  file, then stamped with `progress.py <slug> view`.
- An ask stated in chat goes into the master plan's Asks the same turn.
- After a compaction, re-read the goal and progress files and this lifecycle.
- A choice about people or their data is asked (§VIII.4), overriding
  `subagent-driven-development`'s "rulings, not stalls" for those choices.
- Look before you ask (§VI.8); never stop to ask whether to continue.
- An agent with no new output for twice its time left is checked, then
  restarted or stopped. Keep the machine under about 80% load; when CI runners
  back up, group work into fewer PRs. `max_parallel` is a ceiling, not a quota.
- Past about 200k tokens, bring the progress file current and hand off from it.
- Agents sharing a repo coordinate through the progress file.

**Before each dispatch, deploy or other step unsafe to run twice**: a line
under In flight, pushed. **At every state change** (a task merged, a gate
read, a deploy, a decision changed, a human step hit): update the progress
file, then commit and push it.

**Models.** The orchestrator and each step's subagent run on the models the
master plan names, chosen by [`models.md`](models.md): Opus 5.5 or Fable 5.2 to
orchestrate; haiku, sonnet or opus per step; reviewers on at least the
implementer's model; a step that fails twice moves up one model. Tell the
owner the orchestrator choice and its reason before the goal is handed over.

**The sequence.** Every task runs these steps in this order. A step starts
only when the one before it passed; a failure goes back to the step that
owns it, never forward. The orchestrator never skips, reorders or merges
two steps, and never takes a subagent's word for a step it can rerun.

| # | Step | Who | Passes when |
| --- | --- | --- | --- |
| 1 | Dispatch on the step's model: the task, its use cases, its files, its worktree and branch, its evidence file path, this sequence | orchestrator | the dispatch is under In flight and pushed |
| 2 | Build it test-first: a failing test per use case, then the code | implementer | each new test failed before the code and passes after |
| 3 | Assurance: every check in `assurance`, on the task's own commit | implementer | all green, output kept |
| 4 | Simplify: what the change can lose, applied | implementer | assurance still green |
| 5 | Evidence: each use case shown for its surface, written to the step's evidence file with steps 3 and 4 | implementer | `check-pr.py <file>` prints ok, except Review |
| 6 | Correctness review of the diff and the spec | reviewer, a context that did not write it, on at least the step's model | no open finding; fixes go back to step 2 |
| 7 | Quality, security and constitution review: input handling, authorization, data exposure, secrets, dependencies | reviewer, a second fresh context | no open finding; fixes go back to step 2 |
| 8 | UX review, for a UI use case: walked as a first-time user from the entry point | UX reviewer | passes; fixes go back to step 2 |
| 9 | Review lines written into the evidence file | reviewer | `check-pr.py <file>` prints ok |
| 10 | Verify: rerun the assurance and `check-pr.py` on the file, read the diff | orchestrator | its own run agrees with the file |
| 11 | Merge into the plan branch, tick the step with its file, push the progress file | orchestrator | `check-goal.py <slug>` ok |

At a plan's end, the same shape over the plan: the assurance on the plan
branch with its base merged in, a whole-branch review by a fresh context,
the PR opened with its plan's evidence, `check-pr.py <PR>` ok. At the goal's
end, the whole: `evidence/goal.md` on the top of the stack after the last
code commit, every use case again, then `check-goal.py <slug>` ok.

**What every subagent prompt carries**, because a subagent knows only its
prompt: the step numbers it owns and the sequence above; the task and the use
cases it proves, quoted from the master plan; its worktree, branch and files;
the commands for each check in `assurance`; its evidence file's path and the
`check-pr.py` command; and that its report is a claim the orchestrator will
rerun. A reviewer's prompt carries the diff range and the spec, never the
implementer's account of them.

**Every changeset is done only with its complete evidence** (constitution
§II.4 to §II.7): a task merged to its plan branch, a fix, and each PR. Nothing is ticked,
merged up or opened without it. Four sections, checked by
`python3 <base>/scripts/check-pr.py <PR number | evidence file>`:

- `## Assurance`: every check in `assurance` (tests, coverage, lint,
  typecheck, violations, security, by default), each with its command and the output it
  printed in a fenced block, naming the commit it ran on; on a PR,
  `check-pr.py <PR>` fails assurance that ran on anything but the PR's head.
  Counts are what ran, on the changeset's own commit
  (the reviewer checks this; the script cannot).
- `## Evidence`, told by use case: a `### UC<n> <who does what>` per use case
  from the master plan that the changeset proves, failure cases included, each
  with its proof for the surface the master plan gives it (check-goal passes
  the table; `--master <file>` does for a PR): UI, a screenshot per step taken after the
  last change to its screen; service, the curl request and the response it got;
  CLI, the command run and its output. Images go at an https URL a reviewer can
  open: commit them to an `evidence/<slug>` branch and link
  `https://github.com/<org>/<repo>/blob/evidence/<slug>/<file>?raw=true`. A
  path in a scratchpad, `/tmp` or a git-ignored folder renders for nobody. A
  report or doc link may follow; it never replaces the evidence.
- `## Signal`: a line starting `Success` and one starting `Failure`, each the
  metric, log line or alert to watch during the rollout, with a threshold and
  a window to read it over ("above 99% for 1 h", "0 5xx within 15 minutes of
  the deploy"); or `not-applicable` and why.
- `## Review`: a line each, `Simplify: <result>`, `Self-review, by <model> in
  a fresh context: <result>`, `Security review: <result>`, `Constitution:
  <result>`; the self-review by a context that did not write the change.

**Security, on every changeset.** Assurance includes `security`: a secret scan
of the diff (gitleaks or trufflehog), a dependency audit (the package
manager's audit), and static analysis where the repo has it (semgrep, bandit,
CodeQL), each with its output. The review (step 7) reads the diff for input
handling, authorization, data exposure and secrets; `security-review` runs it
on a branch, and the `security-guidance` hooks see each edit. `check-pr.py`
fails a body or evidence file that carries anything shaped like a credential:
blank tokens, keys, signed URLs and passwords in every curl exchange and CLI
run before it is written down. The failure names the line, never the value.

A UI changeset also carries `UX review: <result>`, and each UI use case shows
its flow, two screenshots or more, from where the person lands to what they
end up with. Use the skills already installed rather than writing new ones:

- building it: `frontend-design:frontend-design`, so the screen starts from a
  design, not from whatever renders;
- walking it: the `playwright` or `chrome-devtools-mcp` browser, driven like a
  person, with clicks from the entry point;
- reading it: `chrome-devtools-mcp:a11y-debugging` for contrast, sizes and
  names;
- judging it: the repo's UX reviewer agent when it has one, otherwise a fresh
  subagent given this list.

The reviewer gets the running app and the use cases, not the diff. It walks
each use case as a first-time user, from the app's entry point, never a deep
link, at the widths people use, and fails:

- navigation a person could not follow to the feature, or back out of;
- text that cannot be read: low contrast, too small, truncated, overlapping;
- a screen that breaks the patterns of the screens around it (layout, names,
  controls, where actions sit);
- a missing or unclear empty, loading, error or success state;
- an outcome the person cannot see, or copy that does not say what happened;
- a card or form judged in one state or for one option only: walk every state
  the change reaches (draft, tested, active, after a sync) and every option
  that shares the screen, not just the new one;
- the wrong count or place of actions: one Save per decision, a step's
  actions in one place, one primary button;
- a form that saves invalid input, or a thing that can be made but not
  renamed, moved or removed;
- the same thing looking or behaving differently on two screens (tables,
  buttons, sizes), or two words for one state;
- internal words on screen (ids, enum values, how the system works), or a
  dialog cut off at the viewport.

A fault on a shared screen that the change puts in front of people is in
scope; it is not "shared, unchanged".

Each failure is fixed and the walk taken again; its result goes on the line.
Screens that each work but do not add up to a usable flow are the failure this
review exists for.

What to show, and what not:

- Tag a use case `(ui)` only when its outcome is something new a person sees.
  A claim that something is unchanged is proven by the tests that pin it
  (`cli`), never by screens of the unchanged thing.
- Screens show only the app the change touches, web and terminal apart,
  nothing cut off.
- A step that proves no use case itself but enables one (a fake, a client,
  plumbing) writes `### Supports UC<n> <how>` with its tests' output.
- Adopting this kit mid-run, assurance cannot be re-run on old commits: run
  it on each plan branch's head and label it so.

The script checks shape, not truth: that a screenshot is newer than its
screen, that output came from the changeset's commit, and that failure cases
are among the use cases are the reviewer's to check.

The loop verifies itself piece by piece and as a whole. A step's file is
`<plans_dir>/<date>-<slug>-evidence/<plan>.<step>.md`, named
in parentheses on its ticked line; `check-goal.py` fails a ticked step without
one that passes. A PR body gathers its plan's steps: their assurance on the
PR's head, every use case the plan proves, the signal and the review. Run
`check-pr.py <PR>` after opening it; with the PR it also checks the changed
files against `surfaces`. Once every step is ticked, the whole:
`<plans_dir>/<date>-<slug>-evidence/goal.md`, taken on the top of the stack
after the last code commit, proves every use case in the master plan again
and passes the same check; `check-goal.py` fails without it. Showing the owner the evidence is the run's job,
never a human step: a run that ends "waiting for the owner to see the screens"
with the screens in its scratchpad has shown nothing.

**At the end**, in order:

1. The last gate read, `check-pr.py` passing on every PR, `check-goal.py` ok.
2. Every ask met, or dropped by the owner by name and date.
3. Clean up: the run's worktrees, merged branches, containers and processes
   are gone (`git worktree list`, `docker ps -a`).
4. When someone will operate what was built, a hand-off doc a sonnet-level
   agent can follow: setup, run, configuration, failure modes.
5. When asking the owner to look, open the app for them, signed in and seeded.
6. The retro: every correction the owner gave during the run is a row of the
   progress file's "Owner corrections", each with the kit change that encodes
   it, shipped as its own PR off main, never on a plan branch (`check-goal.py`
   fails a kit file changed on a feature branch, and a correction with no
   change). Then roll the kit change out to the repos that use it
   (`adopt/rollout.md`).
7. One short message: a row per plan (what shipped, its PR, each gate's
   commands and output); what is merged, deployed, green and verified live,
   each yes or no; what was skipped, removed or left out and why; then every
   ruling the run made.

**Landing the stack**, when the owner says to:
`python3 <base>/scripts/land-stack.py <bottom PR> ... <top PR>` prints the
plan; `--run` does one step and stops. It lands the lowest open PR only when
it is from this repo, based on main and holding it, its checks are complete
and green (`--allow-no-checks` for a repo without CI), `check-pr` passes,
nothing else is stacked on its branch, and the next PR holds all of it (a fix
made below and never merged up would otherwise be lost). It confirms GitHub
says MERGED (a merge queue only queues), retargets the next PR to main before
deleting the branch, merges main up into the next branch with a plain merge,
and stops on any conflict with nothing pushed. Then re-run the next PR's
assurance on its new head, update its body, and run it again; a landing cut
short is finished first. `--method rebase` keeps each commit's author.

**After the merge: watch.** Each PR's Success and Failure lines carry a
threshold and a window (`check-pr.py` fails them without). Once it deploys,
read each signal over its window, from the source it names, and write the
reading under the PR. A Failure reading rolls back first, then is fixed
(§III). When the run has ended by then, schedule the reading before it ends
(the `schedule` skill: one run at the end of the longest window).

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
| Asks | `| A<n> | <the owner's words> | <UC ids> |`: every ask, numbered, mapped to the use cases that prove it, or `dropped by <owner> <date>`. An ask stated in chat goes here the same turn. |
| Models | `Orchestrator: Opus 5.5` or `Fable 5.2`, and why, from [`models.md`](models.md), said to the owner as "This is best handled by ..."; the goal is scaffolded with `new-goal.py --orchestrator` to match. Every step ends `Model: haiku, sonnet or opus` with its reason. |
| Use cases | `UC<n>` rows: who does what, and what they end up with, failure cases included, and the surface (ui, service, cli). The spine of the evidence: every step names the use cases it proves (`Proves UC2.`), and a use case no step proves is a hole the checker fails. |
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

Every time in it is stamped by `scripts/progress.py`, never typed.

- **Now:** one line, `progress.py <slug> now "<text>"`, rewritten at each
  state change; `log` moves its time too.
- **Approved by:** the owner's words approving the master plan,
  `progress.py <slug> approve "<words>"`; no step is ticked before it.
- **Waiting on the owner:** every human step hit and open question, most
  blocking first, each with what it unblocks and the run's recommendation.
- **In flight:** each dispatched subagent and each step unsafe to run twice,
  written before it starts and removed when it lands: what, branch,
  worktree, command, its model, and last its time left ("40m").
- **What is left:** every step still to come, in order, the ones after the
  last task included, each with what it waits on and its time left.
- **Steps:** one checkbox per plan step and one per gate (`- [ ] G1 ...`).
  Each plan's steps are written here before its first step runs. Tick a step
  with its evidence file in parentheses,
  `(<plans_dir>/<date>-<slug>-evidence/<N>.<M>.md)`; a gate with the number
  it read and its commit.
- **Rulings:** each decision the run made alone, as `Ruling: <what>; <why>;
  <cost if wrong>`.
- **Log:** one line per state change, `progress.py <slug> log "<text>"`.

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
| A time is typed or reckoned | It lands ahead of the clock and the owner stops trusting every ETA. |
| A subagent runs `git add -f` on an ignored file | Reports and ledgers land in the PR; stage by path, never force. |
| A review agent reads the diff itself instead of running its skill's fan-out | Half the review never happens; check its report names the passes it ran. |
| A shell loop splits a variable (`for c in $C`) | zsh does not split it; use an array or `xargs`. |
| A kit fix is committed on the feature branch | It ships hidden in the feature's PR, and no other run or repo gets it; ship it off main. |
| A Self-review line does not say who reviewed | Nobody can tell the implementer from a fresh context; name the model and the context. |
