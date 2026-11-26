# The owner's view inside the run

Status: draft for the owner, 2026-11-26. The owner chose C (where the reader runs) and A (an ask holds only
the work that depends on it).

## Intent

The owner keeps giving the same kind of feedback, and keeps being the one who catches problems: "why did I have to
remind about the evidence?", "did we actually make the system usable? or we just chased the scores?", "ensure this
doesn't happen again!", "Please update your UX skills so I don't need to repeat myself... Think as a user." The owner
asked why the run did not know these things already.

The record of one optimize run and its follow-on goal answers that:

- **Every measure was met, not the goal behind it.**
  - The score rose from 0.18 to 0.43 while two of six flows could be finished.
  - Walks passed on data the tester fixed by hand.
  - A usability check read source code to guess what a screen shows; fifteen review rounds each found a new shape it
    misread.
  - A failing test's expected count was raised.

  In each case the worker controlled both the work and the check that judged it.
- **The kit lists failures it has seen.** Its UX review names navigation, readability, states and widths. Data fixed
  by hand and where a click lands were not on the list, so nobody looked.
- **The principle was stated, and written down as patches.** "Think as a user" became wording rules, not the rule
  that done means a person can do it in the product, unaided.
- **Reviewers judged against lists, not against the owner.** One passed a hidden button as an existing rule.
- **About half the catches came from outside the run.** Side notes from a fresh reader of the session caught eight:
  - a grants list naming permissions the owner never gave;
  - held-out builds handed to the fix work;
  - menu writes open to anyone signed in;
  - walks passing on data fixed by hand;
  - a button hidden where it could have shown its reason;
  - a choice about customer data made by a helper;
  - security holes found that were already on main;
  - main's own test left failing.

  The reader worked. It sat outside the run and reported to the owner, who relayed it back.
- **Fixes reach a running goal late.** A run finishes on the kit it started with, and its lessons sat on its state
  branch. A kit release made mid-run never reached it.

## Goals

- The run judges its own work as the owner would, at fixed points and on a watch, before the owner has to.
- A check the worker cannot bend: a walk that cannot touch data, a score that observes the running product.
- One principle the kit states first, with its lists as examples of it.
- A correction reaches the running goal the turn it is given, and its repo's main the same turn; a general one is
  marked for loopkit's rollout.

## Non-goals

- Replacing the harness's side notes. They stay; the run stops depending on them.
- A hook or a harness setting. Everything here is skill text, a subagent the kit describes, and the kit's scripts.
- Asking the owner more. The owner's reader raises a question only when the answer is the owner's (§VIII.4, the
  grants); everything else it sends back as work.

## Anti-goals (a failure even if every check passes)

- The owner's reader becomes a rubber stamp: it passes what the reviewers passed.
- The owner is asked more often, about choices the run could have made.
- Review cost grows past what it catches: a reader per message, a watcher reading whole transcripts.
- The run slows on long subagents that stall (the lesson of 0.13.2): no reader or watcher is long-lived.

## Approaches

Where the owner's reader runs:

- **A. At fixed points.** The plan, each dispatch prompt, each task before it joins its plan branch, each PR, and
  each message claiming something is done. It catches all eight before they reach main; about one call per task.
- **B. A standing watcher.** A pass over the progress file and the running transcripts every 30 minutes. It catches
  a choice made mid-task hours sooner; it costs tokens all the time.
- **C. Both:** A as the gate, B as the early warning.

The owner chose C.

## The design

### 1. The principle, first

`write-goal` opens its lifecycle with one line: done means the work's user can do it in the product, unaided, and the
owner would accept it. The UX review list, the evidence rules and the optimize checks are stated as cases of it. The
owner's reader asks it in those words.

### 2. The owner's reader

A fresh context, never one that wrote or reviewed the thing it reads. Its prompt carries:

- the intent, in the owner's words, and the master plan's Asks;
- every correction the owner has given in this repo: the repo's lessons file and the current run's Owner
  corrections, in full. Archived progress files are not carried: a correction settles in the lessons file at the
  retro (builder's call: cost over completeness, since the retro already moves what lasts);
- the thing to read, and for a task the running product, not the diff alone;
- one question: what would the owner object to here? Each finding quotes the ask, the correction or the principle
  it breaks.

Each finding is one of two kinds:

- **object:** the work goes back to the step that owns it, as a review finding does;
- **ask:** a choice that is the owner's (people or their data, an ending). It goes under Waiting on with the run's
  recommendation, and the owner hears it in the next message. Only the work that depends on the answer waits: that
  task or step is held, named in its In flight or "What is left" row as waiting on the ask, and everything else
  carries on (the owner's choice, 2026-11-26). A grant written without the owner's words is not an ask: it is
  dropped (an object), so the run never acts on a permission nobody gave.

It reads at five points:

| Point | It reads | Catches (from the record) |
| --- | --- | --- |
| Plan written, before the first dispatch | the master plan, the goal, the Granted list | grants never given |
| Each dispatch | the subagent's prompt | held-out builds handed to the fix work |
| Each task, after UX review and before Review lines | the evidence file, the walk, the running product | data fixed by hand, a hidden button, a data choice made alone, open writes |
| Each PR, before it opens | the body and the branch | live faults on main, main's test changed or left failing |
| Each message claiming done, merged or fixed | the message and its evidence | "merged" for a plan branch, a PR never shown |

At a task it is step 8 of the sequence, "Owner read", after UX review (after review, when the task has no UI) and
before the Review lines. Every task has one, UI or not: for a service or CLI task it reads the evidence and uses the
surface as its user would, read-only. It writes `Owner read,
by a fresh <model> context: <result>` into the evidence file, and `check-pr.py` fails an evidence file of a task
without that line, as it fails a Self-review line that names no model. At the other points its result goes in the
progress file's Log.

Models: sonnet at each dispatch and message; the step's model or higher at a task; opus at the plan and each PR.

### 3. The watch

The watch is not a long-lived agent. It is a fresh sonnet pass the orchestrator dispatches at least every 30 minutes
while anything is In flight. It reads:

- the progress file's diff since the last watch;
- the tail of each In flight subagent's transcript since the last watch, never a whole transcript;
- the same corrections and asks the owner's reader carries.

It returns object or ask findings, as the reader does. The orchestrator acts the same turn: an object goes to the
subagent that owns the work, or stops and redispatches it; an ask goes under Waiting on and to the owner.

`progress.py <slug> watch` stamps `Watched: <time>`. `check-goal.py` fails a progress file whose last watch is more
than 45 minutes old while In flight lists anything; with no stamp yet, the age counts from the run's first Log entry.
It prints that failure at each stamp (0.13.3).

### 4. Checks the worker cannot bend

- **The walk.** A walker gets the product's own surface and nothing else: a browser, and a Write for its report. No
  shell, no database, no repo. The kit ships its definition (`write-goal/agents/walker.md`, tools listed in its
  frontmatter); adopt copies it into the repo's agents. Its setup is the repo's committed seed and what the product's
  own screens can do, run before the walk and listed in its report. The walker is the tool, not a new reviewer: UX
review, the Owner read and an optimize walkthrough drive the product through it. The unbendable walk is for UIs; a
service or CLI walk keeps to the public surface by instruction, as today. Each flow reports `works unpatched` or `blocked
  at <step>`; a flow that needed data no screen can make is blocked, naming the missing step.
- **What a walk looks at.** The UX review list gains:
  - where each click lands, and whether the person can tell where they are;
  - a control hidden, off-screen or out of reach at a width;
  - a validation or error message that does not say what to fix;
  - the clicks a task takes, against the screens around it.
- **The score.** An optimize check on a result used through screens observes the running product, never reads its
  source to guess. Usability steps and outcome checks weigh half each by default, so many easy steps cannot drown
  out the outcomes; intake may set another weighting.
- **Main's tests.** A run never changes a test that exists on main to make its branch pass, unless that behaviour's
  change is the ask, named in the master plan. A test failing on main is fixed at its cause in its own PR off main;
  an expected result is named, never covered by raising a count. A live fault the run finds on main (security, data
  loss) goes to the owner as its own PR off main, not with the stack.

### 5. A correction reaches the run, and the repos, the same day

- A correction is a row of Owner corrections the turn it is given (0.13.5), and the run applies it at once: every
  later dispatch prompt carries the Owner corrections rows (`subagents.md`), and the owner's reader and the watch read
  them. The `/goal` text and `.claude/` do not change mid-run, so nothing trips the kit-on-a-branch check.
- Its change to the repo's own kit or lessons ships off main the same turn, never on the state branch, within the
  run's grants for its repo. A correction any repo would hit is marked `general` in its row; carrying it to loopkit
  and the other repos is a kit session's job (`rollout.md`), not the run's, which holds grants for one repo only.
- `rollout.md`'s rule 8 changes: a live run takes a correction its own owner gave, alone, mid-run; it still does not
  migrate to a new kit version.
- The lessons file is a setting, `lessons` in `.claude/loopkit.json`, default `.claude/loopkit/lessons.md`.
  `check-goal.py`'s kit-on-a-branch check covers that path, so a lessons file kept outside `.claude/` (one repo's
  owner feedback register) is caught when its rows sit only on a run's branch.

### 6. Two smaller rules from the same record

- An "eta?" is answered with a time, and with what moved it since the last answer.
- A process is stopped by its pid or its working folder, never by a pattern of the command that started it: another
  agent's run matches the same pattern.

## Where it lives

- `write-goal/SKILL.md`: the principle; step 8 in the sequence; pointers. Kept under 500 lines: the reader and the
  watch are described in a new `write-goal/owner-reader.md`, read before each dispatch as `subagents.md` is.
- `write-goal/agents/walker.md`: the walker's definition.
- `write-goal/scripts`: `check-pr.py` (the Owner read line), `progress.py` (`watch`), `check-goal.py` (the watch age,
  the `lessons` path), `config.py` (`lessons`), and the kit test.
- `optimize/SKILL.md`: observing checks and the default weighting.
- `adopt/rollout.md`: rule 8; `adopt/SKILL.md`: copying the walker.
- A version, 0.14.0, and its CHANGELOG entry with the upgrade steps.

## Rollout

The three repos that use the kit take it as any release (`rollout.md`). Their `check-pr.py` and `check-goal.py`
copies have diverged from loopkit's, so the script changes are ported by hand per repo, with each repo's kit test.
One repo caps a skill file at 500 lines, which the new file keeps clear of. The goal running now ends before this
lands and takes nothing from it; its next goal starts on 0.14.

## Left to the builder

- The exact prompts of the reader and the watch, within section 2's contents.
- How the watch finds the tail of a transcript in the host harness.
- The walker's tool names for the browser the repo uses.
- Test shapes for the script changes.
