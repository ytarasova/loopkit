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
`adopt` first. The repo's own lessons, `.claude/loopkit/lessons.md` when it
exists, are read with this skill: corrections only this repo needs, kept out
of the kit. The scripts live under this skill's base directory, shown when
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
5. Check the plan against the accepted intent in a fresh context: every ask
   reaches a use case, every use case a step that verifies it, the grants
   are named, and each use case's data was walked through change, sharing,
   removal and failure, with every choice about people or their data in
   "Decisions, answered". Log the check. Then send the owner the master plan,
   its Asks and its Models ("This is best handled by ...") as a notice and
   start; the run does not wait for them. Their words, when they give them, go
   on `progress.py <slug> approve "<their words>"`; an objection sends the
   work back to the step it names.
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
- Choices about people or their data are asked at intake (§VIII.4). One
  found later takes the option that changes least for people (their data
  goes nowhere new, nothing is deleted, nothing new is shown), as a ruling
  under Waiting on for the owner to see; work does not stop for it, but a
  shipping run does not deploy that path until the owner has seen it.
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
| 6 | Review of the diff and the spec: correctness, then quality, security (input handling, authorization, data exposure, secrets, dependencies) and the constitution. On a risky path (`models.md`: auth, data, money, migrations, concurrency) these are two reviewers, correctness first | reviewer, a context that did not write it, on at least the step's model | no open finding; fixes go back to step 2 |
| 7 | UX review, for a UI use case: walked as a first-time user from the entry point | UX reviewer | passes; fixes go back to step 2 |
| 8 | Review lines written into the evidence file | reviewer | `check-pr.py <file>` prints ok |
| 9 | Verify: rerun the assurance and `check-pr.py` on the file, read the diff | orchestrator | its own run agrees with the file |
| 10 | Merge into the plan branch, tick the step with its file, push the progress file | orchestrator | `check-goal.py <slug>` ok |

At a plan's end, the same shape over the plan: the assurance on the plan
branch with its base merged in, a whole-branch review by a fresh context,
the PR opened with its plan's evidence, its release notes and its user guide,
`check-pr.py <PR>` ok. At the goal's end, the whole: `evidence/goal.md` on the
top of the stack after the last code commit, gathering every use case, the goal's
release notes and the guide, then `check-goal.py <slug>` ok.

**Subagents.** What every subagent prompt carries, and how a stalled one is
caught and replaced: [`subagents.md`](subagents.md), read before each dispatch.

**Every changeset is done only with its complete evidence** (constitution
§II.4 to §II.7): a task merged to its plan branch, a fix, and each PR. Nothing is ticked,
merged up or opened without it. Four sections, checked by
`python3 <base>/scripts/check-pr.py <PR number | evidence file>`, which CI
also runs on every PR with the base branch's checker (adopt, step 8), so a body missing its evidence is a red
check that `land-stack.py` will not land:

- `## Assurance`: every check in `assurance` (tests, coverage, mutation,
  lint, typecheck, violations, security, by default), each with its command and the output it
  printed in a fenced block, naming the commit it ran on; on a PR, the head,
  or an earlier commit when only Markdown and the goal's own files changed
  since (`check-pr.py <PR>` checks). Evidence is written once, by whoever
  produced it, when it was produced; a commit that changes no code never
  makes it be taken again.
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

**Release notes and the user guide, on every deliverable** (constitution
§II.9). A deliverable is what a person receives: each PR, and the goal's whole
in `evidence/goal.md`; a step's evidence file is a piece of one and needs
neither. Two more sections, which `check-pr.py` checks on a PR, a body file
and `goal.md`:

- `## Release notes`: one paragraph in its users' words: what changed, for
  whom, and what they now see or do. Benefit first, present tense, no PR or
  issue numbers (receipts stay in the PR). A change no user sees writes
  `No user-visible change.`
- `## User guide`: the guide that walks those users through the change, by
  repo path or https URL, and what this change added to it. The guide is a
  how-to: for each use case, what the person does and what they get, from
  where they start; it is updated in the same change, so it never trails the
  code. `not-applicable, <why>` only beside `No user-visible change.`

Where the repo has its own release-notes or user-guide skill, write them with
it.

At the goal's end, `goal.md`'s release notes cover the whole goal, and its
guide walks every use case. The reviewer reads both as a first-time user: do
the notes say what changed for them, and do the guide's steps work on the
final code.

**Mutation, on every changeset with logic.** Coverage shows a line ran, not
that a test checks it. Disable each rule or branch the changeset adds, one at a
time, run the tests that cover it, and end its fenced output with
`N of M killed`. Scope it to the diff: the repo's tool where there is one
(Stryker `--incremental` for JS and TS, mutant `--since origin/main` for Ruby,
mutmut on the changed files for Python; none prints that line, so take it
from the tool's summary), hand mutants otherwise. Each survivor gets a line
`Survivor: <mutant>, <why it stands>`: equivalent to the original, or the test
that now kills it; "no time" is not a reason. A change with no logic (docs,
config, plumbing with no branch) writes `mutation: not-applicable, <why>`. Run
without cached bytecode (delete `__pycache__`, set `PYTHONDONTWRITEBYTECODE=1`),
restore each file in a `finally`, rerun a kill that a flaky suite may have
made, and end on the unmutated suite passing. `check-pr.py` checks the count
and the survivor lines; the reviewer checks that every new branch had a
mutant.

**Security, on every changeset.** Assurance includes `security`: a secret scan
of the diff (gitleaks or trufflehog), a dependency audit (the package
manager's audit), and static analysis where the repo has it (semgrep, bandit,
CodeQL), each with its output. The review (step 6) reads the diff for input
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
- a screen judged in one state only: walk every state the change reaches;
- whatever the repo's lessons add.

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
  nothing cut off. A faulty capture is retaken, never captioned.
- A step that proves no use case itself but enables one (a fake, a client,
  plumbing) writes `### Supports UC<n> <how>` with its tests' output.

The script checks shape, not truth: that a screenshot is newer than its
screen, that output came from the changeset's commit, and that failure cases
are among the use cases are the reviewer's to check.

The loop verifies itself piece by piece and as a whole. A step's file is
`<plans_dir>/<date>-<slug>-evidence/<plan>.<step>.md`, named
in parentheses on its ticked line; `check-goal.py` fails a ticked step without
one that passes. A PR body gathers its plan's steps: their assurance (on the
PR's head, or carried over while no code changed), every use case the plan
proves, the signal and the review. Run
`check-pr.py <PR>` after opening it; with the PR it also checks the changed
files against `surfaces`. Once every step is ticked, the whole:
`<plans_dir>/<date>-<slug>-evidence/goal.md`, on the top of the stack after
the last code commit, gathers every use case in the master plan: each one's
proof from the step that gave it, carried over with its commit while the code
it covers is unchanged, taken again only where it changed, plus the whole's
own gates on the final code. It passes the same check as a deliverable (release notes and the guide too); `check-goal.py` fails without it. Showing the owner the evidence is the run's job,
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
   progress file's "Owner corrections", each with the change that encodes it,
   shipped as its own PR off main, never on a plan branch (`check-goal.py`
   fails a kit file changed on a feature branch, and a correction with no
   change). A correction any repo would hit changes loopkit and rolls out to
   the repos that use it (`adopt/rollout.md`); one only this repo would hit
   goes in its `.claude/loopkit/lessons.md`.
   Then tidy the repo's lessons, the file named above: merge two lessons that
   say one thing, and remove one only after `git grep` shows that what it
   names (a file, a command, a rule) is gone. A lesson another repo that uses
   the kit also holds is general: move it into loopkit and out of both.
7. One short message: a row per plan (what shipped, its PR, each gate's
   commands and output); what is merged, deployed, green and verified live,
   each yes or no; what was skipped, removed or left out and why; every
   ruling the run made; and a link to each page the owner reads (the report,
   the live view) at its current version.

**Landing the stack**, when the intent's Grants name merging or the owner
says to:
`python3 <base>/scripts/land-stack.py <bottom PR> ... <top PR>` prints what
it would do; `--run` lands the lowest open PR and stops. It lands only a PR
from this repo, based on main and holding it, with its checks complete and
green (`--allow-no-checks` for a repo without CI), `check-pr` passing, nothing
else stacked on its branch, and the next PR holding every non-merge commit of it (a fix
made below and never merged up would otherwise be lost). It merges matching
the head it checked, confirms GitHub says MERGED (a merge queue only queues),
retargets the next PR to main, and deletes the branch only while its tip is
the merged commit and no open PR uses it. It never merges main up itself: it
prints the commands, and you run them, resolve any conflict, re-run that PR's
assurance on its new head, update its body, and run it again. A PR of the
stack merged earlier (a queue, by hand) is finished first, and that run stops
there: the PR above goes onto its base, and its branch is deleted under the
same conditions. `--method rebase` keeps each commit's author. A merge-up
would leave a merge commit beside the original copies of commits main now
holds rewritten, which GitHub refuses to rebase, so with it the tool prints one
rebase per branch instead, as one command that stops at the first failure:
replay that branch's own commits from the head it read onto where the branch
below now is, and push with a lease on that head. No local branch is touched
(they are stale after), and a push made since is refused. Re-run the
assurance of every PR it moved. If the run stops before the lines ran, the
next run prints them again. A branch the repo deleted on merge is reported
gone, not a stop.

**After the merge: watch.** Each PR's Success and Failure lines carry a
threshold and a window (`check-pr.py` fails them without). Once it deploys,
read each signal over its window, from the source it names, and write the
reading under the PR. A Failure reading rolls back first, then is fixed
(§III). When the run has ended by then, schedule the reading before it ends
(the `schedule` skill: one run at the end of the longest window).

**Shipping in phases**, when the Grants say ship (`ends_at: production`, or
`new-goal.py --ends-at production`): each plan is a phase. Land it, deploy
it, read its signals over their windows, then the next phase on green. A
Failure reading rolls back, sends the work back (to building, or to planning
when the plan was wrong), and ships it again. The run repeats until every plan
is live and its signals read green, or a piece is parked with its evidence.

## 1. Measure the baselines first

Every gate compares a number after the work with a number from before it.
Read the before numbers now, from the real source, and write down the source
and the window. Which sources exist is the repo's business: CI runs, a deploy
API, logs, a metrics query, `curl` against a host, a test count. `adopt`
records them in `CLAUDE.md` or the constitution; read them there.

Time each gate as well. A gate that takes more than a few minutes names the
quick check that predicts it, which workers run after every change; the slow
gate then runs once per join (a plan's head, the top of the stack), not per
step. A check that flips on the same code is broken: fix it, or file it and
link the ticket in the evidence (§VI.7); it is never counted green.

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

Divide the goal with `analysis-synthesis`. Plans and steps are its tree: split
a step until one worker can do it in one context and verify it alone (its use
case tests, a number, a script), and put what the others share first. Steps
and gates are the verification at each level; the plan branch, its PR and
`goal.md` are the synthesis, each rerunning what is below it. The run
dispatches a step once what it needs is merged, not in list order. A goal too
big for one orchestrator's context gives a plan a lead, written in Models: it
runs that plan's steps by the sequence and reports; the orchestrator still
writes the progress file, asks the owner and reruns the lead's verification.

**Sending work back.** The run is not only forward: verification sends a
piece back to building, building sends a plan back to planning, planning sends
an ask back to intake. Work goes back to the level that caused the failure,
no further; the level above decides, and logs one ruling: what failed, where
it went, what it invalidated, what changed. Each return changes something
(the check, the split, the model, or the reading of the ask). A second return
for the same cause goes one level higher. At the top, the piece is parked:
the rest ships, and the piece is listed as not done, with its evidence. A
ticked step reopens only by such a ruling.

## 3. The progress file

The only place the run records where it is. The goal text never changes to
carry status, and the master plan's facts do not change because a step ran.

Every time in it is stamped by `scripts/progress.py`, never typed.

- **Now:** one line, `progress.py <slug> now "<text>"`, rewritten at each
  state change; `log` moves its time too.
- **Approved by:** the owner's words on the master plan, when they give
  them, `progress.py <slug> approve "<words>"`; the run does not wait for it.
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
says so. And `Done means:` accepts three finishes: the gates hold; a human
step is recorded under Waiting on and pushed; or the owner changed the ending
(merge now, stop here), recorded with their words and stated in the last
message. `/goal` judges that line after every turn; with gates alone, a run
blocked on the owner is pushed to keep going and works around the step, and a
run the owner redirected can never stop.

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
| A subagent waited on, not watched | It stalls silently for an hour, and no message wakes it. |
| The facts go into the goal | `/goal` refuses it, or the rules get cut to make room. |
| Status goes into the goal or the master plan | The goal drifts from the run, and a resume cannot tell facts from state. |
| The progress file is updated only at the end | After compaction the run redoes merged work, or merges twice. |
| The gate is "tests green" | Tests pass while nothing the user sees changes; the goal reads as met. |
| An open decision is left open | The run stops at it, or guesses. |
| A cause is written without being measured | The run fixes the wrong thing with authority. |
| A permission is not granted at intake | The run stops on a step it could have taken. |
| A human step is not listed | The run waits on it forever, or works around it. |
| A failing check is answered in words (a caption, "a false alarm", "passes alone") | The fault ships under a description of it; retake, fix, or file it. |
| One PR for the whole goal | Review cannot keep up, and one bad plan holds back every good one. |
| Implementers share a checkout | Their edits and test runs collide; one worktree each. |
| The implementer reviews its own change | It reads the diff for what it meant; the blind spot passes. |
| A time is typed or reckoned | It lands ahead of the clock and the owner stops trusting every ETA. |
| A kit fix is committed on the feature branch | It ships hidden in the feature's PR, and no other run or repo gets it; ship it off main. |
| A Self-review line does not say who reviewed | Nobody can tell the implementer from a fresh context; name the model and the context. |
