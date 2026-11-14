# Rolling out a loopkit change to the repos that adopted it

Each repo that ran `adopt` keeps its own copy of the kit, in its own words. A loopkit change therefore reaches a repo only when
it is ported into that copy. Run these steps in order. A step starts only when the one before it passed.

1. **Land it in loopkit first.**
   - Open a PR whose body passes `check-pr.py`.
   - `test_goal_kit.py` must be green.
   - Mutation: disable each new rule in turn and show the suite fails each time.
   - A review by a fresh context, with its findings fixed or answered.
   - Then merge. Every port reads one commit on loopkit `main`, never a branch that is still moving.
2. **List the adopters and how each lands a change.**
   - Through a PR merged to main.
   - Through a direct push to main.
   - As a local commit only, never pushed.
   - Keep this list outside loopkit: it names private repos. The owner states each repo's landing rule; never guess it.
3. **Write one brief, shared by every port.** It holds:
   - the loopkit commit to port;
   - the owner's words that asked for it;
   - what to land, as numbered items;
   - for each adopter, what is already there to extend rather than duplicate (a PR skill, an existing gate, a reviewer agent);
   - the size limits, such as the goal under 4,000 characters, with counts before and after;
   - the rules below;
   - the report to send back.
4. **Dispatch one subagent per adopter, all at once.** Use sonnet; use opus when the port must map onto an existing structure
   that differs from loopkit's (`write-goal/models.md`). Each subagent works:
   - in its own worktree on a new branch, cut from `origin/main`, or from local `main` for a repo whose changes stay local;
   - with its own backup directory for mutation testing, never a shared one;
   - by the write-goal sequence: tests, mutation, simplify, a self-review and the constitution, with its PR body (or body file)
     passing that repo's `check-pr.py`;
   - without merging. A local-only repo is never pushed, and `gh` is never run against it.
5. **Forward loopkit fixes that land while the ports run.** Send each running port the new commit range and a one-line reason.
6. **Verify each port yourself before landing it.** A port's report is a claim, so check it:
   - Rerun the repo's kit tests.
   - Run `check-pr.py` on its PR or body file.
   - Diff its `check-pr.py` against loopkit's: only the settings may differ.
   - Read its mutation list and its character counts.
   - Check for files clobbered by another port.
7. **Land each port by its repo's rule:** merge the PR, push to main, or fast-forward local main.
8. **Tell every live run in an adopting repo.** A goal already running keeps its old goal text and its old copy of the skill.
   Message its orchestrator to:
   - merge main into its branch, then up its stack;
   - reload the skill;
   - revise its goal, master plan and progress file to the new templates (a progress file may need new
     sections, or stamps written by the new tools, before the checker passes again);
   - meet any new evidence rule before it calls the goal done.

   Then check that it did: the new commit is an ancestor of its branch.
9. **Report one table:** repo, where it landed (the commit), the verification you reran, and what was not ported and why.
