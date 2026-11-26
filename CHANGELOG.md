# Changelog

## 0.14.0

The run judges its work as the owner would, before the owner has to. One optimize run and its follow-on goal showed
why: every measure was met and not the goal behind it (a score up while flows stayed unusable, walks passing on data
fixed by hand), and about half the catches came from a reader outside the run, relayed by the owner.

- `write-goal` states its principle first: done means the work's user can do it in the product, unaided, and the owner
  would accept it.
- The owner's reader (`write-goal/owner-reader.md`): a fresh context carrying the intent, the Asks and every
  correction the owner gave, asked one question, what would the owner object to here. It reads the plan, each
  dispatch, each task (step 8 of the sequence), each PR and each message claiming done. An object goes back as work;
  an ask holds only the work that depends on it. `check-pr.py` fails a step's evidence file without its
  `Owner read, by a fresh <model> context:` line.
- The watch: a fresh pass at least every 30 minutes while work is in flight, over the progress diff and the tails of
  the running transcripts. `progress.py <slug> watch` stamps it; `check-goal.py` fails a watch over 45 minutes old.
- The walker (`write-goal/agents/walker.md`): a browser and nothing else, so no walk fixes data by hand. Each flow
  reports `works unpatched` or `blocked at <step>`. The UX review gains where a click lands, hidden or off-screen
  controls, validation that does not say what to fix, and click counts.
- Main's tests are not changed to make a branch pass; a test failing on main, or a live fault found there, goes to the
  owner as its own PR off main.
- A correction reaches the run the turn it is given: every later dispatch carries the Owner corrections rows, and a
  live run takes its own owner's correction mid-run (`rollout.md`, rule 8). The lessons file is a setting, `lessons`,
  and `check-goal.py` treats it as a kit file, so a lesson left only on a run's branch fails.
- `optimize`: a usability check observes the running product, never its source, and usability steps and outcome
  checks weigh half each by default.
- Smaller: an "eta?" is answered with a time and what moved it; a process is stopped by its pid or folder, never by a
  pattern of its command.

Upgrading from 0.13: set `lessons` when the repo's lessons file is not `.claude/loopkit/lessons.md`; copy
`write-goal/agents/walker.md` to `.claude/agents/walker.md`, naming the repo's browser tools. A goal started on 0.13
keeps its kit (its step files have no Owner read line), so upgrade between goals.

## 0.13.5

Seven owner corrections from one optimize run and its follow-on goal, where the run answered each in the moment and
wrote down none:

- `write-goal`: a correction from the owner is a row of Owner corrections the turn it is given, and the retro reads
  every owner message of the run against the table. Each PR reaches the owner as its own message, with its link, when
  it opens and before any merge the run makes: a PR under the owner's own login notifies nobody. To the owner,
  "merged" means into main; a task combined into its plan branch is "in the plan branch".
- `write-goal/subagents.md`: which subagents are running is read from the harness's list and their shells, never from
  memory; none is left held open by a shell at the close.
- `intent`: each grant quotes the originator's words and when; a grant with no words was not given.
- `optimize`: when people use the result through screens, a case's checks read what a person can do there (reach it,
  pick each choice, open a row, save), and the landing reports usable `k` of `n` beside the score. A score had risen
  from 0.18 to 0.43 while two of six flows could be finished. A walkthrough shows the finished result first, then the
  steps that failed. A held-out case is spent once a later goal studies its build; the next check needs fresh cases.

## 0.13.4

- `progress.py` reports a `check-goal.py` that stopped before judging the goal (a usage error, a crash) as a failure,
  with its last line. 0.13.3 printed `check-goal: ok` for it.

## 0.13.3

- `progress.py` runs `check-goal.py` after every stamp and prints each failure, so a state change shows what lags: a
  live view not updated since the Now line, a progress file to archive, a ticked step with no evidence. The stamp
  stands either way; the run fixes a failure before its next step or puts it under Waiting on. A run that checked
  only when a task merged left its live view nine hours behind through a loop and a landing.

## 0.13.2

- `write-goal`'s subagent rules move to `subagents.md`, with what every prompt carries, and gain three lessons from an
  optimize run whose subagents stalled silently for 43 and 85 minutes. Every prompt now asks for small edits pushed
  after each item, a wait on a pid or a file and never on `pgrep -f` of the waiting command's own string, and a
  deadline on every run. The orchestrator reads each transcript as it runs. After 15 minutes with no tool call it stops
  the subagent, confirms it stopped, commits its tree as wip and dispatches the replacement. `SKILL.md` keeps a
  pointer and one Common mistakes row, and stays under 500 lines.

## 0.13.1

- `write-goal`'s retro tidies the repo's lessons after adding to them: two that say one thing merge; one is removed only
  after `git grep` shows what it names is gone; one another adopter also holds moves into loopkit. The lessons file
  only grew before.

## 0.13.0

- `optimize` no longer holds cases out by default. Intake decides it with the owner:
  - none: every case trains, and the landing PR waits for the owner even under a merge grant;
  - at the landing: held-out cases are scored in the baseline and on the cut-down winner only, and a winner below the
    floor does not land;
  - every experiment: the held-out floor is an evo gate, at held-out cases x `k` sessions an experiment.

  The master plan records the choice. A floor near zero is reported to the owner before round one.

## 0.12.9

- `optimize` intake: a session loads evo only if it started after the install, so the run's session starts then, with
  `EVO_TELEMETRY=0`. A run whose session predated the install had to hand over to a new one mid-run.

## 0.12.8

- `optimize`'s walkthrough has two parts: the build, everything the solver made as its owner sees it in the system's
  own tools for making it, with the try's transcript; and the use, as before. Either alone leaves half unseen.
- Intake decides what a solver hears when it stops to ask though its task did not say it would: a standing reply in
  every case's replies, or the try ends there.
- The held-out gate prints its verdict only (`--verdict-only`): evo's agents read gate output, so held-out scores or
  transcripts printed there showed the loop the held-out cases.
- The scorer gives the solver an allowlisted environment with its model and effort pinned, and stops every solver it
  started when it is interrupted or its parent dies.
- `own_tests` on a baseline that already fails some checks compares failures, not counts, with the test and
  typecheck configs frozen.

## 0.12.7

- `optimize` closes the gaps it finds, not only scores them. After the baseline each gap goes in a gap ledger with
  its evidence, the checks it fails and its state. An experiment may build a whole missing capability, with its
  migration, tests and docs. The landing PR lists each gap closed, with its commit, and each gap still open, with what
  was tried; the open ones start the next run.

## 0.12.6

- `optimize` runs a task that waits on its user: a case's optional `replies.md` holds that user's answers, and the
  scorer sends them in one session with `--input-format stream-json`, the next one after each turn ends. A one-shot
  `claude -p` ended the try at the first question.

## 0.12.5

- `optimize`'s evidence text is generic: an outcome covers the main path, what the result must refuse and the edge
  cases the task implies, and each walkthrough carries the evidence `write-goal` asks of that kind of change, rather
  than the skill naming screens, roles or kinds of system. What a walkthrough covers in one system belongs in its
  repo, in the run's intake.

## 0.12.4

- `optimize` asks for complete evidence of what each case built. A case's outcome and checks cover the result in
  use: the main path, validation and the edge cases the task implies, not only that a thing was created. The baseline
  and the landing walk each case's result as its user would (a UI through `write-goal`'s UX review, with screenshots
  of every state), and the landing PR carries those walkthroughs before and after.
- The scorer takes `--keep`, which leaves each case's last try standing for that walkthrough.

## 0.12.3

- `optimize` takes a written intake: `/optimize <intake file>` starts at Discover and runs on as one goal, so the
  prompt names the run and nothing else. Intake now ends as that file.
- `contract.md` names the evo install for Claude Code (`evo install claude-code`), pins the CLI back to 0.8.0 after
  it, and checks it with `evo doctor`.

## 0.12.2

- `optimize` stays in the host's harness, on its own sign-in: evo's workers are the host's subagents, and the scorer
  runs each solver try as a headless `claude -p` limited to the system's public surface (`contract.md`, the scorer).
  No separate API key or SDK.

## 0.12.1

- `optimize` runs its own Discover step between intake and the suite: it reads the system's public surface, how a
  clean start is made, what can check a result and the gate suite, and maps each case's gaps before any score.
  adopt no longer reads these itself; it points to the step.

## 0.12.0

A loop for work that has no finished state, only a score to raise.

- A new skill, `optimize`: a system (a product, an API, an MCP server, a library, a prompt set, a pipeline) is scored
  on many of its users' tasks at once, and a loop changes the system until the score rises. evo
  (github.com/evo-hq/evo) runs the search; loopkit supplies the cases, the scorer contract, the gates and the landing.
- The score is built to be trusted: each case is tried `k` times and reports a lower bound, the suite and the scorer
  are frozen for a run, a third of the cases are held out and watched for leaks, a change that fits one case instead
  of improving the system is failed, and what only a reader can judge is reported beside the score, never in it.
- One run lands as one PR, the smallest diff that keeps the winner's score, with its body checked by `check-pr.py`.
- `skills/optimize/contract.md` holds the exact parts: a case's files, what the scorer must do, the gate commands,
  and the evo commands, cited from evo 0.8.0.
- A house rule for the kit itself: it stays generic (README, Customizing).

Upgrading from 0.11: nothing changes for a repo that does not optimize. One that will: copy `skills/optimize/` into
its copy of the kit, and follow adopt's "A repo that will optimize". Installing evo adds hooks to the host and sends
anonymous telemetry unless turned off, so it waits for the owner's word, per repo.

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
