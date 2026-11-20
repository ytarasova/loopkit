# Optimize: make a system better at what its users ask of it

Status: approved by the owner, 2026-11-19. Revised the same day on the owner's corrections and on what building
showed; see "Changed after approval" at the end.

## Intent

A system has users, and they bring it tasks. Today it gets part of each done. The owner wants a loop that closes the
gap:

- start from a baseline and a set of real cases;
- a solver attempts each case against the system and gets a completeness score against the desired outcome;
- the gaps say what to change in the system;
- the change ships, the whole set runs again, and the score climbs;
- across all cases at once, not one.

The owner's framing: "a 'classic' optimization loop with criteria, or autoresearch loop", with evo
(github.com/evo-hq/evo) "under the hood", and "It is an optimization problem at the end." The kit stays general (the
owner: "do not overfit!", "keep loopkit generic!"). The system may be a product, an API, an MCP server, a library, a
prompt set or a pipeline. A product whose users have Claude build on it through an MCP server is one example, not the
frame.

## Goals

- A loopkit skill that sets up and runs this loop in any repo with a system to improve.
- The score is steady enough that a gain means something.
- The loop runs unattended and lands each run's result as a PR with its evidence, the way write-goal runs land.

## Non-goals

- Building our own search loop, tree, frontier or dashboard. evo does that.
- Tuning the solver or its prompts. What changes is the system.
- Scoring taste as the score. What only a reader can decide is judged separately (below), never folded into the number.

## Anti-goals (a failure even if the score rises)

- The score rises because the loop changed the cases, the checks or the scorer.
- The score rises on the cases the loop looked at, and not on the held-out ones.
- A change fits one case instead of improving the system (a tool, a branch or a doc page named after the case).
- The solver passed by working around the system instead of through its public surface.
- A kept change breaks the system's own tests.

## Approaches considered

1. **A loopkit-native loop** (keep or revert by score, run by write-goal). No dependency, but we would rebuild what evo
   already has: per-task traces, gates that inherit, a frontier, parallel worktrees, a dashboard.
2. **evo runs the loop; loopkit supplies the benchmark and the landing.** Picked by the owner ("we may as well use evo
   under the hood").
3. **Both, switched on whether evo is installed.** Two paths to keep working, for no need anyone has stated.

## Design

### The pieces

| Piece | Owned by | What it is |
| --- | --- | --- |
| System | the adopting repo | what gets improved |
| Case | the adopting repo | one task as its user would state it, the desired outcome, its checks |
| Solver | the adopting repo, set at adoption | whoever attempts each case, often a fresh Claude given only the system's public surface; fixed for a run |
| Clean start | the adopting repo | the state a case begins from; the scorer resets to it before every try |
| Scorer | the adopting repo, from the skill's contract | runs the solver per case and emits per-case scores to evo |
| Gates | the adopting repo | the system's own tests; a held-out floor; the suite and scorer unchanged; no leak; no case-shaped change |
| Loop | evo | `/evo:optimize`: hypotheses, experiments in worktrees, keep or discard, frontier |
| Landing | loopkit | the run's winner as one minimal PR; loopkit's PR body and `check-pr.py`; grants from intake |
| Method | loopkit skill `optimize` | how to write cases and checks, the scorer contract, gates, noise, landing |

### A case

One directory per case in the adopting repo (default `optimize/cases/<slug>/`; the scorer takes the path):

- `task.md`: what the user would say, in a user's words. No names from inside the system, no hints.
- `outcome.md`: the desired outcome in plain sentences, one per thing the user would notice.
- checks: one per outcome sentence, each a command or a check file the repo already understands. A check passes or
  fails on what the solver left behind.
- optionally `judge.md`: what only a reader can decide, with the rubric.

Score of one case = checks passed / checks, over the tries (below). The judged part is reported beside the score and
never added to it, so a change cannot raise the number by pleasing the judge. *(Builder's call:)* the judge runs on the
baseline and on the run's winner only, not per experiment, to keep its cost to two passes a run. A judged drop does
not stop the loop; it is listed in the PR, and a PR with one waits for the owner even under a merge grant.

A case is written from a real user's task. Where it arrives as a conversation or a ticket, the skill says to keep the
source beside it.

### The scorer (the evo benchmark)

One command evo runs per experiment. For each case:

1. Reset to the clean start (the adopting repo says how).
2. Run a fresh solver with the case's `task.md` and the system's public surface, and nothing else. The solver is an
   adoption setting: the one the system's users reach it with, so the system is tuned to how it is really used. It
   stays fixed for a run, so a gain comes from the system.
3. Run the case's checks against what the solver left.
4. Report the case as an evo task (the SDK's `run.report`, or `log_task` in evo's inline mode) with its score, the
   solver's transcript and each check's result.

Each case runs `k` times (default 3). Tries of different cases run in parallel up to a set limit.

*(Builder's call:)* **What is frozen.** The scorer, the cases, their checks, the code that runs the checks, and
whatever defines the clean start all run from the run's baseline commit, whatever the experiment changed. The system
itself is free to change. Otherwise an experiment could change how a check is judged, or start a case already solved,
without touching a case file. evo executes the benchmark from the main repo root, so the scorer is called by a path
that is not the experiment's, and that checkout stays on the baseline for the run.

Trace content matters: evo's scan subagents read the transcripts to find the cross-cutting gap (the solver guessed a
field name five times; nothing lists the valid ones). Without the transcript the loop is blind.

### Gates

- **Suite unchanged (pre).** The frozen files compared with the baseline; an experiment that edits any of them fails
  before it spends a try. (They run from the baseline anyway; the gate makes the attempt visible.) In evo a failed
  gate leaves the experiment uncommitted, for its agent to fix or discard.
- **The system's own tests (pre).** The repo's existing fast suite.
- **Held-out floor (post).** About a third of the cases are held out: scored only in this gate, never in the
  benchmark. The gate fails if the held-out score drops below the baseline's. evo has no built-in held-out set; this
  gate is ours. evo's own advice is that held-out data cannot be hidden from agents in the same repo, only caught, so:
- **No held-out leak (pre).** Fails when the experiment contains distinctive strings from a held-out case (its names,
  its wording).
- **No case-shaped change (pre).** *(Builder's call:)* blocks, per experiment, so the loop never builds on a bad
  change. A fixed-prompt model call reads the experiment's diff against the case titles and fails the gate when a
  change fits one case instead of improving the system.

### Noise

A solver is usually a sampled model, so the same system scores differently on two runs. evo compares scores directly:
it keeps any experiment whose score is higher, with no threshold and no averaging across runs. So the noise handling
lives in the scorer:

- the score evo sees for a case is its mean over tries minus its spread across tries (a lower bound), so a lucky run
  does not pass as a gain; the run's score is the mean of those;
- before the loop, the skill runs the baseline `n` times (default 3) itself (evo's discover does not), records the
  spread, and checks the lower bound is stable;
- a case whose score swings across the full range at baseline is fixed or set aside before the loop, never counted.

### Cost and stopping

One experiment costs (training cases + held-out cases) × `k` solver sessions; a round is up to `subagents` × `budget`
experiments, each retried up to evo's `max-attempts`. evo runs until the score stops rising, which on a noisy benchmark
can be long. So intake sets the caps. evo takes three: `subagents` (experiments at once), `budget` (tries per branch)
and `stall` (rounds with no gain before it stops). It has no round limit and no spend ceiling, so the run counts
rounds itself and the scorer counts solver sessions against the ceiling. The skill states the cost of one round in
sessions before the first.

### Landing

evo searches; loopkit lands. evo's `ship` skill stops for the owner before choosing a winner and before any push, and
writes its own PR body, so an unattended run does not use it. *(Builder's call:)* one optimize run lands as **one PR**:
the run's best valid experiment, reduced to the minimal diff that keeps its score (rerun the scorer and the gates on
the reduced diff), on a branch from the run's baseline. The PR body follows the repo's loopkit rules (`check-pr.py`),
with:

- Assurance: the system's tests, and the scorer on the PR head.
- Evidence: a table of cases, baseline score, new score, spread; the held-out score; one solver transcript before and
  after for the case that moved most; the judged part before and after.
- Release notes: what a user of the system can now do.

Merge and deploy follow the grants given at intake, as in write-goal. The next run starts from the merged main as its
new baseline. A case runs somewhere it can be thrown away; running one anywhere a mistake cannot be undone is an
intake grant like any other irreversible action, which write-goal already covers.

### Growing the suite

New cases come from users. Adding one changes what the score means, so the skill records it as a breaking event in
evo (`evo infra event -m "<reason>" --breaking`), takes a new baseline, and starts a new comparison from there. A case
is added to training or held-out at random, never by whether it passes.

### Where loopkit's other skills come in

- `intent`: capture a user's task in their words before it becomes a case; ask the caps and the grants.
- `analysis-synthesis`: the rules a check must meet (quick, fixed before the work, steady, close to what matters).
- `write-goal`: an unattended optimize run is a goal; its grants decide whether it opens PRs, merges or ships in phases.

## Constraints

- evo installs hooks into the host: a stop-nudge (`evo autonomous`) and an orchestrator-edit gate
  (`evo subagents-only`). Its optimize skill treats both as on unless told otherwise; its CLI leaves both unarmed until
  the command runs. Installing it in a repo is the owner's call per repo; the skill never installs it unasked, and sets
  both switches explicitly: autonomous on, and subagents-only off, because the run's orchestrator still writes its
  progress file.
- evo sends anonymous telemetry by default. A run sets `EVO_TELEMETRY=0`; `evo telemetry off` is global, so it is the
  owner's to run.
- Cost: see Cost and stopping.
- Public loopkit: no product names, people or internal URLs. The kit stays generic: what is specific to one system
  lives in that system's repo, in its adoption.

## Left to the builder

- The skill's exact sections and its scorer contract file, kept short (the owner: "I don't want it to be rigid!").
- How the scorer runs a solver; the skill names the requirements, not the tool.
- Which evo frontier strategy to suggest first; `pareto_per_task` fits a suite of unlike cases.
- A first adopter's own cases, scorer, clean start and solver are a separate piece of work after the skill.

## Changed after approval

Owner corrections:

- The whole design is stated generically (system, case, solver, clean start). The first draft was framed around one
  kind of product and the environment it runs in; those are an adopter's facts, not the kit's.
- "No use-case-shaped tools" became "no case-shaped change", for the same reason.

Found while building, against evo's docs (0.8.0):

- evo has no round limit and no spend ceiling to pass caps to; its knobs are `subagents`, `budget` and `stall`. The
  run and the scorer hold the other two.
- A failed gate does not discard an experiment; it leaves it uncommitted.
- The case-shaped gate reads only the diff, so it runs pre, before any solver session is spent, not post.
- evo's two switches do not disagree across its docs so much as describe two layers (the skill's default, the CLI's
  unarmed state). subagents-only is set off, not on, so a write-goal orchestrator can keep its progress file.
- `evo telemetry off` is global; a run uses `EVO_TELEMETRY=0` instead.
- The lower bound is taken per case, so the per-case scores evo's frontier reads and the run's score agree.
- The case path is a default the scorer takes, not a loopkit setting: no script reads it, so a setting would be a
  knob with nothing behind it.
