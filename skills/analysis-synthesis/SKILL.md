---
name: analysis-synthesis
description: Use whenever work is too big to do and check in one pass, in any domain: a goal, a plan, a migration, a research question, a review, a document, an incident. Also on "break this down", "divide this", "fan this out", "how do we split this", "how do we know each part is right", "put the pieces together", or when parts came back and need to become one answer.
---

# Analysis and synthesis

Big work goes fast and stays right when it is taken apart into pieces that can
each be done and checked on their own, and put back together with a check at
every join. Taking apart is analysis; putting together is synthesis. The
method is the same for code, research, reviews and writing. This skill is a way
of thinking, not a form: use as much of it as the work needs.

## Analysis: take the whole apart

Start from the ask, in the owner's words, and split it into parts. Split a part
again until each piece is one worker's job in one context, and has its own
verification.
The result is a tree: the ask at the root, pieces at the leaves.

**A verification says, on its own, whether a piece is right.** A test, a
benchmark number, a count, a script's output, a quote matched against its
source, a page that renders. It is what lets a worker hill-climb alone and
know when it is done, and what lets many workers run at once without waiting
on each other. A good verification is:

- **quick**, minutes not hours, so a worker can run it after every change;
- **run before the work**: one that already passes proves nothing, unless
  the piece must keep it passing (a refactor, a rename);
- **fixed before the work**: the worker never edits it to pass. Changing it
  is a decision, made above the worker and written down;
- **steady**: the same input gives the same answer. One that fails, then
  passes on a rerun, is broken: fix it, or record why it cannot be trusted
  with its runs; never count it green. A warning is its claim, answered with
  evidence, never dismissed;
- **close to what matters**: it predicts the verification of the part above.

Where no command can check a piece (a design call, prose, taste), say who
judges it and against what. That judged part is where the work slows down for
everyone, so keep it small: split off every piece that can be checked, and
leave only the judgment.

Split along the seams the work already has: modules, questions, sources,
sections, failure modes. Put what everything shares (types, a schema, a fake,
a glossary, an outline) first, as its own piece, so the rest can run side by
side. Note what each piece needs from the others; that order is the only
order. A tree that is one long chain has no width; look for another seam.

## The work: run what is ready

Run every piece whose needs are met, as many at once as the machine and the
budget allow, not in list order. When the approach to a piece is open and its
verification reads a number, try a few approaches at once and keep the best reading;
say what the others scored.

## Synthesis: put it back together

Bottom up, every join gets checked:

1. **Rerun each child's verification,** or carry its output forward when nothing
   it covers changed since. A child's PASS is a claim, never the result.
2. **Compose**, then read the whole for what no piece could see: two parts
   that contradict, a gap between them, the same thing done twice, names that
   drift.
3. **Run the part's own verification**: an integration test, a gate, the section read
   against its question, the whole read against the ask.

When every child passed and the parent fails, a child's verification missed
something. Fix it first (add the check that would have caught it), then the
piece.
Otherwise the same miss comes back.

Synthesis ends at the root: the whole answers the ask, in the owner's words,
with each claim traceable to the piece and the check behind it.

## Sending work back

The work is not only forward. Verification sends a piece back to the work,
the work sends a split back to analysis, analysis sends an ask back to its
author's words. Work goes back to the level that caused the failure, no
further. The level above decides, and records one line: what failed, where it
went, what it invalidated, what changed. Each return changes something: the
check, the split, the worker, or the reading of the ask. A second return for
the same cause goes one level higher. At the top the piece is parked: the
rest is delivered, and the piece is listed as not done, with its evidence.

## Evidence, kept as it is made

Every piece leaves its evidence when it is done: what was checked, on what,
and what it printed, written by whoever did it. Analysis leaves the split and
why; a send-back leaves its line. A join gathers its children's evidence and
adds only its own. Rebuilding evidence after the fact costs more than the
work did, and proves less.

## Hierarchy: a lead per subtree

When a subtree is too big for one context, give it a lead: an agent that does
analysis and synthesis for that subtree only, and hands back the composed part
with its verification output. The level above treats that as a claim and reruns
it. Rules that keep a hierarchy honest:

- **One writer of shared state.** The root owns the plan, the state file and
  the record of decisions; leads report to it.
- **Only the root asks the owner.** A lead that hits a question stops that
  path and hands it up.
- **Each level checks the level below** before merging up, never deeper and
  never less.
- **Depth is earned.** Add a level only when a subtree will not fit one
  context, usually orchestrator, lead and worker at most.

## In every domain

| Work | Pieces | Verification | The join |
| --- | --- | --- | --- |
| A goal (`write-goal`) | plans, then steps | each step's tests, assurance, `check-pr.py` | the plan branch's gates, the PR, `goal.md`; when shipping, each phase's signals after its deploy |
| A research question | sub-questions, then sources | each claim quoted against its source | the answer read against the question, contradictions named |
| A review | dimensions, then files | each finding reproduced at its `file:line` | findings deduplicated, ranked, verified |
| A document | sections | each section answers its question; facts checked | read whole as its reader, against its purpose |
| An incident | timelines, systems | each cause shown by a log, metric or replay | causes joined; the fix checked against every one |

## Common mistakes

| Mistake | What happens |
| --- | --- |
| Splitting by size, not by seams | Pieces that cannot be checked alone; every join is a surprise. |
| A piece with no verification | Its worker cannot tell when it is done; it stops early or never. |
| The worker changes its verification | The check passes and the piece is still wrong. |
| A flaky check counted green | The join trusts a result nobody can repeat. |
| Synthesis by concatenation | Contradictions and gaps between pieces ship. |
| Trusting a lead's PASS | One level's blind spot becomes everyone's. |
| A deeper tree than the work needs | Each level adds hand-offs and loses detail. |
| Evidence rebuilt at the end | The proof is reconstructed, not observed, and costs more than the work. |
| The same send-back retried | Nothing changed, so the same failure comes back. |
