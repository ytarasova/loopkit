---
name: optimize
description: Use when asked for an optimization loop, an autoresearch loop, a loop "with criteria", an evo loop over a system's use cases, or when a system should get measurably better across many of its users' tasks at once, such as "make our MCP easier for Claude to build with", "improve the platform until these use cases are fully achievable", "raise the score across these cases", or when handed an optimize intake file. Not for one feature with a known end (write-goal), and not for tuning the solver or its prompts.
---

# Optimize

Some work has no finished state, only a number that should rise: how much of
what its users ask a system gets done. This skill sets up that number, the
loop that climbs it, and the checks that tell a real gain from a false one.

The search is evo's (github.com/evo-hq/evo): hypotheses, experiments in
worktrees, keep or discard, a frontier, a dashboard. loopkit adds what evo
leaves to its user: the cases, a score that can be trusted, the gates, and
the landing. This is a method, not a form: use as much as the system needs.
The exact parts (a case's files, what the scorer must do, the gate commands,
the evo commands) are in [`contract.md`](contract.md).

## The pieces

| Piece | What it is |
| --- | --- |
| The system | What gets improved: a product, an API, an MCP server, a library, a prompt set, a pipeline. |
| A case | One task, stated the way its user would state it, the desired outcome, and checks on the result. |
| The solver | Whoever attempts each case, often a fresh Claude given the task and only the system's public surface: a headless `claude -p` in the same harness (`contract.md`). Set at adoption, fixed for a run. |
| A clean start | The state a case begins from. The adopting repo defines it, and the scorer resets to it before every try. |
| The scorer | One command: for each case, reset, run the solver, run the checks, report the score and the trace. |
| The gates | Commands that fail an experiment whose score rose for the wrong reason. |
| The loop | evo's `/evo:optimize`. |
| The landing | The run's best valid experiment as one PR with its evidence, by this repo's loopkit rules. |

Two made-up systems, to show the same shape in different places:

| | Larder, an inventory product with an MCP server | tidewater, a date-parsing library |
| --- | --- | --- |
| A case | "Warn me when any item drops under ten." | "Read the dates out of these supplier invoices." |
| The solver | Claude with the task and Larder's MCP server | Claude with the task, the package and its docs |
| A clean start | An empty account with the sample stock | A fresh directory holding the invoices |
| A check | An alert rule exists and fires at nine | The output matches the expected dates |
| What changes | Larder and its MCP server | tidewater and its docs |

What changes is always the system. The solver, the cases and the checks hold
still, so a gain can only have come from the system.

## A gain that is not one

The loop will raise the number any way it is allowed to. Each of these is a
failure even when the score rises, and each has its guard below:

- the cases, the checks or the scorer changed;
- the score rose on the cases the loop saw and not on the ones held out,
  when the run holds cases out (Held-out cases);
- a change fits one case instead of improving the system (a tool, a branch
  or a doc page named after the case);
- the solver got there around the system, not through its public surface;
- a kept change broke the system's own tests.

## Cases

A case comes from a real user: a conversation, a ticket, a request. Use
`intent` to capture it in their words, and keep the source beside the case.
State the task as that user would, with no names from inside the system and
no hint at how to do it. A task that waits on its user ("check this with me
first") gets that user's answers, written beforehand (`contract.md`).
A solver may also stop to ask when its task did not say it would. Intake
decides what it hears then, the same for every case: a standing reply,
added to each case's replies after its own, or the try ends there and
scores what was built before the question.
Write the outcome as plain sentences, one per thing
the user would notice, and one check per sentence. A check reads what the
solver left behind and passes or fails. It meets the rules for a
verification in `analysis-synthesis`: quick, fixed before the work, steady,
close to what matters.

The outcome covers the result in use, not only that it exists: its main
path, what it must refuse, and the edge cases the task implies. A check that
a thing was made is not a check that it works. When people use the result
through screens, the checks read what a person can do there, not only what
was stored: reach it from where its user starts, pick each choice, open a
listed row, save. Stored data and rules behind a screen nobody can finish
score as working.

What only a reader can decide (it fits the purpose, the names make sense)
goes in the case's judged part, with its rubric. It is reported beside the
score and never added to it, so nothing raises the number by pleasing a
judge. It is read twice a run, on the baseline and on the winner.

Fewer than ten cases for the loop to see is a thin suite: evo's own advice
is ten to twenty at the least.

## Held-out cases

Holding cases out is a choice the owner makes at intake, never a default.
The loop never sees a held-out case, so a gain that fits only the cases it
saw shows as a training score that rose and a held-out score that did not.
That is worth its cost when there are real cases to spare and the loop runs
with no person between rounds. It is worth little when the cases are few,
or drafted rather than taken from users: a few held-out tries are noisy, and
a floor taken from a baseline near zero only catches a system that broke.
Three choices:

- **None.** Every case trains. Nothing measured then catches a gain that
  fits the cases: the case-shaped gate judges each experiment, and the
  walkthroughs and the owner judge the winner. So the landing PR waits for
  the owner even under a merge grant.
- **At the landing**, the cheaper way to hold cases out. They are scored in
  the baseline and on the cut-down winner, and nowhere else. The leak gate
  still runs on every experiment, at no solver session. A winner below the
  floor does not land: the next best valid experiment is cut down instead.
- **Every experiment.** The held-out floor is a gate as well, at (held-out
  cases) x `k` solver sessions an experiment.

When cases are held out, they are about a third, picked at random, never by whether they
pass. Intake records the choice, its cost in sessions and whose it is. When
the baseline's floor comes out near zero, tell the owner before the loop:
that floor guards little, and the choice can still change before round one.

A held-out case is spent once its build or transcript is studied, by the
loop or by a later goal fixing what it found. The next check that the
system works beyond its cases needs fresh ones, written by a context that
has not seen the work.

## The scorer

For each case, `k` times (default 3): reset to the clean start, run a fresh
solver with the task and the system's public surface and nothing else (no
repo, no shell into it, no way around), run the checks. A try scores checks
passed over checks. The scorer reports each case to evo with its transcript
and every check's result. The transcript is not optional: evo finds the gap
that cuts across cases by reading them (the solver guessed a field name five
times; nothing lists the valid ones). Without it the loop is blind.

**Frozen for a run:** the scorer, the cases, their checks, the code that
runs the checks, and whatever defines the clean start. They run from the
run's baseline, whatever an experiment changed. Otherwise an experiment
could change how a check is judged, or start a case already solved, without
touching a case file.

## Noise

A sampled solver scores differently on the same system twice. evo compares
scores directly and keeps whatever scored higher, with no threshold and no
averaging across runs, so a lucky run would pass as a gain. The scorer
answers for it:

- each case reports its mean over the tries minus its spread across them, a
  lower bound, and the run's score is the mean of those;
- before the loop, run the scorer on the baseline `n` times (default 3)
  yourself and compare the lower bounds. If they differ by more than a gain
  you would believe, raise `k` or fix the unsteady cases first;
- a case that swings across its whole range on the baseline is fixed or set
  aside before the loop, never counted.

## Gates

Each is a command that exits non-zero, registered once on evo's root so
every experiment inherits it. Those marked pre run before the scorer, so a
failure spends no solver sessions.

- **Suite unchanged (pre).** The frozen files match the baseline.
- **The system's own tests (pre).** The repo's fast suite.
- **No held-out leak (pre)**, when cases are held out. evo's advice is that held-out cases cannot be
  hidden from agents in the same repo, only caught: the experiment carries
  no distinctive string of a held-out case.
- **No case-shaped change (pre).** A fixed-prompt model call reads the
  experiment's diff beside the case titles and fails a change that fits one
  case instead of improving the system. It costs a call per experiment, so
  its cost is stated at intake.
- **Held-out floor (post)**, only when intake chose every experiment. The
  held-out cases, scored only here, do not fall below the lowest score they
  got across the baseline runs. When intake chose the landing, it runs once
  there, by hand (`contract.md`).

## Gaps

The loop is there to close the system's gaps, not only to find them. A gap
is something users' tasks need that the public surface lacks or gets wrong:
a missing capability, a missing rule, a name the solver keeps guessing.
After the baseline, each gap the transcripts and walkthroughs show gets a
row in the run's gap ledger (its progress file, when the run is a goal): the
evidence, the checks it fails across cases, the fix proposed, and its state.

An experiment may be as large as its gap: a whole missing capability, with
its migration, tests and docs, is a fair experiment, not a reason to stop.
Say so in `.evo/project.md`, with the open gaps worst first (most checks
failed across cases). Such a change passes the case-shaped gate only
when its users would want it without the case. A gap is closed when the
checks it failed pass and every gate holds, not when a change for it exists.

## Cost and stopping

One experiment costs (training cases, plus held-out cases when their floor
runs every experiment) x `k` solver sessions, and a round up to `subagents` x `budget` experiments, each retried
up to evo's `max-attempts`. State that number before the first round. evo
runs until the score stalls, which on a noisy score can be long, so intake
sets the caps: evo takes the width (`subagents`), the depth per branch
(`budget`) and the stall limit (`stall`); the round limit and the ceiling on
solver sessions are the run's own, since evo has neither (`contract.md`).
evo's own agents spend too, every round; the round limit is what bounds
them.

## Running it

1. **Intake**, with the owner (`intent`): the cases' sources, the solver,
   the caps, what a solver's unplanned question hears (Cases), whether
   cases are held out and where they are scored (Held-out cases), and the
   grants. Installing evo is one of them, per repo: it
   adds hooks to the host and sends anonymous telemetry unless turned off.
   Never install it unasked. A session loads evo only if it started after
   the install, so start the run's session then, with `EVO_TELEMETRY=0`.
   A case runs somewhere it can be thrown away;
   running one anywhere a mistake cannot be undone is a grant like any other
   (`write-goal`, constitution §VIII.2). The intake ends as a file in the
   repo: the cases' sources in their users' words, each decision with whose
   it is, and what is left to Discover.
2. **Discover**, before any case is written: read the system, and write
   down what the suite will stand on. Ask the owner only what the system
   cannot say.
   - Its public surface: what a user, and so the solver, reaches it
     through, and what that surface lets them do.
   - A clean start: how one is made and reset, how long it takes, and
     whether several can run side by side (that sets the caps).
   - What can check a result: the system's own tests, check formats and
     read-back calls. A case's checks use these before anything new.
   - The gate suite: the fastest of the system's own tests that a broken
     change fails.
   - For each case, what the surface already offers and what it lacks.
     This is the first map of the gaps, before any score.
3. **The suite**, landed by its own PR before any run: cases, any held-out
   cases, the scorer, the gates. A run then has a baseline to freeze.
4. **The baseline**: the `n` runs above, on the training and any held-out
   cases, the judged part read once, each case's result walked (Landing),
   the gap ledger started (Gaps), the cost of a round stated.
5. **The loop**: evo's discover, which finds the scorer already built
   (`contract.md`), then `/evo:optimize` with the caps. An unattended run
   is a goal (`write-goal`): its master plan holds the caps, the
   held-out choice and the baseline, its progress file each round's best score and the gap
   ledger.
6. **The landing**, below. A run that finds no valid gain ends with its
   report and no PR. Either way it leaves nothing running (`contract.md`).

Given an intake file (`/optimize <file>`), start at Discover and go on
without asking again. The prompt names the run and nothing else: the grants,
caps and solver are in the file, the exact commands in `contract.md`, and the
repo's own limits (how many subagents, what must not be touched) in its
constitution and `.claude/loopkit.json`. Steps 3 to 6 run as one goal
(`write-goal`, ending at the run's PR): plan 1 the suite, plan 2 the
baseline and the run. A grant the file lacks goes under "Waiting on".

## Landing

evo searches; loopkit lands. evo's own `/evo:ship` stops for the owner twice
and writes its own PR body, so an unattended run does not use it. One run
lands as one PR: the best valid experiment, cut down to the smallest diff
that keeps its score, on a branch from the run's baseline. The winner's own
score is the best of many noisy runs, so it flatters: score the winner again
`n` times, then the cut-down diff, and compare those. Every gate runs on the
cut-down diff too. Its body passes `check-pr.py`, with:

- Assurance: the system's tests, and the scorer on the PR head;
- Evidence, from those fresh runs: a table of cases with baseline score, new
  score and spread, and whether a person can finish the case (usable `k` of
  `n` beside the score); the
  held-out score before and after, when cases are held out; one transcript before and after for the
  case that moved most; the judged part before and after;
- a walkthrough of each case, on the baseline and on the winner, in two
  parts. The build: everything the solver made, as its owner sees it in the
  system's own tools for making it, with the try's transcript. The use:
  everything it built, used as its user would, through the main path, the
  refusals and the edge cases its outcome names, with the evidence
  `write-goal` asks of that kind of change. It is walked on what one try left
  standing, before the next reset, by a subagent that did not score it, and
  costs no solver session. It shows the finished result first, every screen
  with real data in it, then each step that failed, shown failing: a list of
  faults alone hides what works;
- the gap ledger: each gap closed, with its commit and the checks it
  turned; each gap still open, with what was tried and why it failed. The
  open ones are the next run's first experiments;
- Release notes: what a user of the system can now do.

Merging follows the grants, as in `write-goal`. A judged drop does not stop
the loop, but its PR waits for the owner even under a merge grant. The next
run starts from the merged main.

## Growing the suite

New cases come from users, never from what the loop found easy. A new case
changes what the score means: record it in evo as a breaking event, take the
baseline again, and compare only from there. It joins the training or the
held-out cases at random, when the run holds cases out.

## Common mistakes

| Mistake | What happens |
| --- | --- |
| A task written in the system's words | The solver is handed the answer; the score measures nothing a user meets. |
| Checks written after seeing the solver's result | They pass what was built, not what was asked. |
| Checks that only find the result exists | A result that refuses nothing scores full. |
| Checks that read stored data behind screens | The score rises while no person can finish the flow. |
| Held-out builds studied by a later fix | The cases no longer show the system works beyond them. |
| A landing with scores and no walkthrough | Nobody has seen what a user gets. |
| A walkthrough of the use alone, or the build alone | Half is unseen: what a user gets, or what was made to give it. |
| Experiments kept to small edits | A missing capability is never built, and the score stalls below it. |
| Gaps found and not tracked | The landing shows a score, not what a user can now do, and the next run starts blind. |
| One try per case | A lucky run is kept, and the next run cannot repeat it. |
| Held-out scores in the loop's score or its output | Nothing is left to show overfitting. |
| Cases held out by default, never discussed | Few or drafted cases split into two noisy halves, and every experiment pays for a floor that guards little. |
| The judged part added to the score | The number rises by pleasing the judge. |
| No transcript in the trace | The loop sees that a case failed, never why. |
| The scorer run from the experiment's own copy | An experiment edits its own exam. |
| Tuning the solver or its prompt | The gain belongs to the solver; the system's users get nothing. |
| No caps at intake | Nothing stops the run but a stalled score, and a noisy score stalls late. |
| Shipping the raw winning diff | Search leftovers, and sometimes a loosened test, land with the gain. |
