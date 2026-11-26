# The owner's reader and the watch

Done means the work's user can do it in the product, unaided, and the owner
would accept it. The reviewers check the work against lists; the owner's
reader checks it against the owner. Without it, the owner catches what the
run should have, and relays it back.

## What it carries

A fresh context, never one that wrote or reviewed the thing it reads. Its
prompt carries:

- the intent, in the owner's words, and the master plan's Asks;
- every correction the owner has given in this repo: the lessons file (the
  `lessons` setting) and this run's Owner corrections, in full;
- the thing to read, and at a task the running product, walked through
  `agents/walker.md`, not the diff alone;
- one question: what would the owner object to here? Each finding quotes the
  ask, the correction or the principle above that it breaks.

## What it returns

Each finding is one of two kinds:

- **object:** the work goes back to the step that owns it, as a review
  finding does. A grant written without the owner's words is an object: it is
  dropped, so the run never acts on a permission nobody gave.
- **ask:** a choice that is the owner's (people or their data, an ending).
  It goes under Waiting on with the run's recommendation, and the owner hears
  it in the next message. Only the work that depends on the answer waits: it
  moves from In flight to "What is left", its row naming the ask, so held work
  alone keeps no watch due. Everything else carries on.

It never asks what the run can rule on; an ask that is not the owner's is
sent back as work.

## Where it reads

| Point | It reads | Model |
| --- | --- | --- |
| The plan, before the first dispatch | the master plan, the goal, the Granted list | opus |
| Each implementer or fix dispatch | the subagent's prompt | sonnet |
| Each task: step 8 of the sequence | the evidence file, the walk, the running product | the step's model or higher |
| Each PR, before it opens | the body and the branch | opus |
| Each message claiming done, merged or fixed | the message and its evidence | sonnet |

Reviewers, the walker, the watch and the reader itself are not dispatches
it reads. At a UI task it reads step 7's walker report and drives the
walker again only for what that report left out.

At a task the reader writes its own line, `Owner read, by a fresh <model>
context: <result>`, into the evidence file's Review (making the section if
it is not there yet); the reviewers write theirs beside it at step 9.
`check-pr.py` fails a step's evidence file without it, or with no model
named. A task with no UI is read through its
surface as its user meets it (the service, the CLI), read-only. At the
other points the result is a Log line.

## The watch

Not a long-lived agent: a fresh sonnet pass the orchestrator dispatches at
least every 30 minutes while In flight lists anything. It reads:

- the progress file's diff since the last watch;
- each In flight subagent's transcript entries stamped after the last
  `Watched:` time (each entry carries its time), never a whole transcript;
- the corrections and asks the owner's reader carries.

It returns object or ask findings, as the reader does. The orchestrator acts
the same turn: an object goes to the subagent that owns the work, or that
subagent is stopped and redispatched (`subagents.md`); an ask goes under
Waiting on and to the owner. Then `progress.py <slug> watch` stamps
`Watched: <time>`; the first dispatch stamps the first. While work is in
flight, `check-goal.py` fails a watch more than 45 minutes old, or none.

## A correction during the run

- It is a row of Owner corrections the turn it is given, and every later
  dispatch prompt carries the rows (`subagents.md`); the reader and the
  watch read them. The `/goal` text and `.claude/` do not change mid-run.
- Its change to the repo's kit or lessons file (`lessons`) ships off main
  the same turn, within the run's grants for its repo, never on the state
  branch.
- One any repo would hit is marked `general` in its row ("general: <the
  repo's commit or PR>"). Carrying it to loopkit and the other repos is a
  kit session's job (`adopt/rollout.md`), not the run's.

## What the owner is told

- Each PR reaches the owner as a message of its own, with its link, when it
  opens and before any merge the run makes: one opened under the owner's own
  login notifies nobody.
- To the owner, "merged" means merged into main. A task combined into its
  plan branch is "in the plan branch".
- An "eta?" is answered with a time, and with what moved it since the last
  answer.
