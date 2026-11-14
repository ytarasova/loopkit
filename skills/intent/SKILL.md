---
name: intent
description: Use when someone describes a problem, a feature, a bug or an idea in their own words and the next step is to write it down before any spec, plan or code. Also on "capture the intent", "grill me", "interview me about", "write an intent", or a ticket key given as the start of work. Not for a feasibility question or a one-file change.
argument-hint: "[ticket key or a sentence]"
---

# Intent

The first document of a piece of work: what is wrong, what should be true
instead, who and what it touches, what must not change, and what is still
open. Written with the originator, not for them, and short enough to read in
two minutes. On a multi-day run it is what the goal's gates trace back to.

The interview form is adapted from Matt Pocock's `grilling` skill (MIT,
github.com/mattpocock/skills). The refusal of vague answers and the skip logic
come from Switch Dimension's `molten-validate` (MIT,
github.com/switch-dimension/molten-os-core).

## What the interview is

A design tree: every answer opens the questions that depend on it. The
**frontier** is every question that can be asked now without guessing at an
answer not yet heard. Ask one question at a time, the most blocking first, in
plain words with your recommended answer, then wait. Recompute the frontier
from the answer.
The interview ends when the frontier is empty, not when the template is full.

Facts are your job. Before asking, look up what the repo, the ticket and the
last few related PRs already say, and state what you found instead of asking.
A question the originator cannot answer better than a grep is a defect.

## Question shape

```
<title>
<the question in plain words, with the choices if there are natural ones>
Recommended: <your answer and why, one line>
```

Never name a file, a field or an option number the originator has not seen;
say what it means.

If a ticket key was given, read the ticket and its linked PRs first and open
with what is already known. Skip any question the first message already
answered; confirm it in one line instead.

## What counts as an answer

- "Everyone", "users", "the business" are not affected users. Ask who, by
  role, and how many.
- "It should just work" is not an outcome. Ask what a person will see or be
  able to do that they cannot today.
- A constraint with no owner is a wish. Ask who set it.
- An open question stays open. Write it under Open questions with who can
  answer it; do not resolve it by assumption.

## Writing it

When the frontier is empty, or the originator says "enough", write
`<intent_dir>/YYYY-MM-DD-<slug>-intent.md` from `template.md` in this
directory. `intent_dir` comes from `.claude/loopkit.json` (default
`docs/specs`). Every sentence in it traces to an answer or a lookup. The Proof
section ends with the riskiest assumption: the one thing that, if false, makes
the outcome not worth building, and what would show it false. Fill "How it should run" from `../write-goal/models.md` and
say it in chat as one line: "This is best handled by Fable 5.2, because ..."
(or Opus 5.5). Show the draft,
ask for corrections, then mark it accepted with the originator's name and the
date. Point to the file when done; do not recap it in chat.

## Exits

Offer, do not assume:

- A spec, when the design is still open.
- `superpowers:writing-plans`, when the intent is small enough to plan
  directly.
- `write-goal`, when the work should run unattended: the Proof items become
  the master plan's gates, and the Open questions become its "Decisions,
  answered" rows or human steps.

## Common mistakes

| Mistake | Instead |
| --- | --- |
| Writing the document from the first message | The first question first, even for a clear ask. A document with questions inside it is a draft |
| Asking the whole frontier at once | One question at a time, most blocking first, with a recommendation |
| Leaving scope implicit | Write what is out of scope, and every assumption, for the originator to confirm |
| Asking for a fact | Look it up, state it, ask only for the decision |
| Filling Open questions with your own guesses | Leave them open, name who can answer |
| Interviewing past the point of use | Stop when a planner could act on it without asking anything back |
