# The {{PROJECT: project name}} Constitution

How we work on {{PROJECT: what this repo is, in one line}}. It applies to people, AI coding agents, and any tool that touches this repo. `CLAUDE.md` links to this file at the top.

This file sets principles. Its examples show a rule; they do not limit it. If a clause looks wrong, propose an edit instead of quietly breaking it (§VIII.3).

---

## I. One way to do each thing

1. **Nothing here is legacy.** Code marked legacy, deprecated, old, or "v2", and any compatibility shim, is a bug.
2. **Delete and migrate in the same PR.** When something is replaced, the replacement and the deletion ship together, the deletion in its own commit. No parallel paths.
3. **One canonical path.** Pick the system of record and remove the alternatives.

## II. Done means the real flow works

1. **A feature is done when a real user path shows it working.** Types, lint and unit tests are necessary, not enough.
2. **Smoke steps in a PR are obligations.** Run them, or say in the PR why they could not run.
3. **UI changes are opened and clicked through.** A screenshot in the PR proves it ran.
4. **A changeset is done only with its complete evidence** (a task merged to its branch, a fix, a PR), where a reviewer opens it. Assurance: every technical check with its command and output ({{PROJECT: the checks, e.g. "tests, coverage, lint, typecheck, and violations: static analysis, security, fitness"}}). The change working, told by use case (who does what, and what they end up with, failures included): a UI by a screenshot per step, newer than its screen; a service by the curl request and its response; a CLI by the command run and its output. A link or a local path is not evidence.
5. **Every changeset names its signal.** The success and the failure signal to watch during the rollout (a metric, log line or alert, with its threshold), or "not-applicable" and why.
6. **Every changeset is simplified, self-reviewed and cross-checked against this constitution,** each with its result, and the work verifies itself piece by piece and as a whole: each changeset proves the use cases it touches, and the finished work proves every use case again, on the final code.
7. **A UI is reviewed as a person uses it, not as a set of screens.** A reviewer that did not build it walks each use case as a first-time user, from where that person lands, never from a deep link. A screen that works but cannot be found, cannot be read (contrast, size, truncation), breaks the patterns of the screens around it, hides its empty, loading or error state, or leaves the person unsure what happened, fails the review.
8. **Done is said, not asked for.** Every report says what shipped without being asked: merged or not, deployed or not, every pipeline green or not, verified in the real environment or not, and what was skipped, removed or left out, each with its reason.

## III. Causes, not symptoms

1. **Fix the root cause.** A raised timeout, a swallowed error, a deleted failing test, or a type silenced to compile is a symptom patch and is rejected.
2. **Measure a cause before writing it down.** A cause is one bisect or one log line, not a reading of the code.
3. **After a fix, look for the same shortcut elsewhere.** Grep the siblings of the function you fixed.
4. **Three failed fixes for one failure means the model is wrong.** Question the design, not the fourth fix.
5. **Delete or rename, then sweep every reference.** Your diff cannot show what it orphaned.
6. **A defect you find is yours.** Fix it in this run, or file it and link the ticket in the report. "Left alone", "out of scope" or "pre-existing" with no link is not an answer.

## IV. Code

1. **Deep modules, small interfaces.** A unit does a lot behind a small contract. No pass-through layers.
2. **Each file owns one thing.** Split by responsibility, not by technical layer.
3. **YAGNI.** No speculative scaffolding, no parameter with one valid value, no interface with one implementation.
4. **Comments say why, never what.** No task references, ticket numbers or spec section numbers in code.
5. **No shims for unused code.** If nothing calls it, delete it.
6. **Limits are settings, not literals.** A threshold, window, size or count that someone may tune is a named setting with a default, never a number inside logic.
7. **{{PROJECT: house writing rule, e.g. "No em-dashes in chat, code, docs or commits." or delete this line}}**

## V. Tests

1. **Tests are fast, useful and reliable.** A flaky test is a bug, not noise.
2. **There are no pre-existing failures.** A red test or stale rot in a file you touch is yours to fix.
3. **Local matches CI.** When they disagree, find out why.
4. **{{PROJECT: how tests share state, e.g. "The suites share one database; run one tier at a time." or delete this line}}**

## VI. How work runs

1. **Plan first, then execute fast.** Non-trivial work goes intent, spec, plan, execute. A plan names exact files and exact commands.
2. **Size subagents to the work.** Fan out only for independent units with files that do not overlap. Give each one unit, check its evidence (command output, `file:line`) before accepting it, and end with one table: unit, result, evidence.
3. **Two review stages per task: correctness, then quality.** Each stage runs in a context that did not write the change and reads the diff and the spec, never the author's account of them. An implementer's PASS is a claim: rerun its test and read the diff.
4. **Do the obvious next step without asking.** When something fails, change the model, the context or the scope before retrying. The same input to the same model gives the same failure.
5. **Report BLOCKED instead of retrying blindly.** Bad work is worse than no work.
6. **Big cross-cutting changes land in revertable steps,** each one verified.
7. **Verification passes or fails.** A test, a build, a screenshot, a metric, with the output it printed. "Looks right" is not a verification.
8. **Look before you ask.** The knowledge base, the CLI, the MCP servers and the CI runners come first. Never hand the owner a step you can take; a human step is one nothing you have can do.
9. **Ask in plain words, one question at a time, with your recommendation.** Do the literal ask; when a verb has two readings, ask once. A question naming a file or an option number the owner has not seen is not a question.
10. **A correction from the owner goes into the skill the same turn,** not into memory or a note, so it is never given twice; one that changes this file is proposed to the owner the same turn (§VIII.3).
11. **Edit files with the edit tools.** The shell is the fallback for what they cannot do.

## VII. Branches and merges

1. **{{PROJECT: merge style, e.g. "Squash merge by default."}}**
2. **On an owner-only branch a force-push needs no ask; elsewhere merge `origin/main` and push plainly.**
3. **Tactical fixes may self-merge once CI is green.** Anything user-facing or architectural is the owner's merge unless they granted it.
4. **Every CI gate is green before merge.** {{PROJECT: name the required checks}}. A failing check is a bug to fix, not to bypass.
5. **Never skip hooks or signing** unless the owner asks for it.
6. **Pull before starting and again before merging.**
7. **Changes ship as stacked PRs.** One reviewable PR per step, each branched from the step before it and targeting that branch. Merge from the bottom; after each merge, merge `origin/main` into the next branch and retarget it, with no rebase or force-push (§VII.2).

## VIII. When in doubt

1. **Question an architecture that feels wrong.** Say so and propose the fix.
2. **Ask before anything you cannot take back.** The test is whether one wrong attempt can be undone. Code and a commit on your own branch can be undone, so they need no permission (§VI.4). Merging follows §VII.3. A force-push to a shared branch, `rm -rf`, a dropped table, a deleted branch, discarded uncommitted work, a sent message and {{PROJECT: shared or production state, e.g. "anything in AWS, staging or production"}} cannot, so they wait for the owner. An authorization covers the operation named and nothing beyond it.
3. **When the owner's directive contradicts this file,** the directive wins for that session. If the preference has changed for good, propose an edit here.
4. **A choice about people or their data is the owner's.** One that changes what a person sees or can do, or where a customer's data goes or what happens to it on a failure, is asked in the turn it comes up, as one question with a recommendation, and recorded under Waiting on; work goes on with what does not depend on it. A ruling written in a ledger is not asking.
5. **Protected resources need permission.** {{PROJECT: the environments, tenants, shared models, paid services and repos no agent touches unasked}}. Never mint a credential for yourself.
6. **Trace before you delete.** Name what referenced it and why it goes; infrastructure shows its plan's destroys first.
7. **Leave nothing behind.** At the end of the work, its worktrees, branches, containers and processes are gone.

{{PROJECT: project sections from here on (domain language, stack idioms, deploy rules), numbered IX onward; each clause earned by a real mistake or a real constraint, or delete this line}}

## How to use this

- At the start of a non-trivial task, read §I to §VIII.
- Before merging, read §VII.
- When you break a clause on purpose, cite it in the PR and say why.
