# Subagents

What the orchestrator puts in each subagent's prompt, and how it notices one
that has stalled. Read before each dispatch.

**What every subagent prompt carries**, because a subagent knows only its
prompt: the step numbers it owns and the sequence in `SKILL.md`; the task and the use
cases it proves, quoted from the master plan; its worktree, branch and files;
the commands for each check in `assurance`; its evidence file's path and the
`check-pr.py` command; and that its report is a claim the orchestrator will
rerun. A reviewer's prompt carries the diff range and the spec, never the
implementer's account of them.

Every prompt also carries this run's Owner corrections rows, so a correction
given mid-run reaches each later dispatch.

**How a subagent works without stalling**, in every prompt too: small edits,
committed and pushed after each item, never a large file in one call; a wait
on a pid or an output file, never on `pgrep -f` of a string the waiting
command itself contains, which matches that command and never ends; and a
deadline on every run it starts, in the test and under `timeout`, since a
runner can hang on a signal it handles without exiting.

**A silent subagent is stalled, not busy.** Read each dispatched subagent's
transcript as it runs. After 15 minutes with no tool call, stop it with the
harness's own stop (`TaskStop`) and confirm it stopped, commit its tree as
wip, and dispatch the replacement from there. A subagent that ended its turn
while its own background run continues is not finished: stopping that run
wakes it, and it starts again beside its replacement, in the same worktree.

**Which subagents are running** is read from the harness's own list and each
one's shells, never from memory. One finished but held open by a shell it
started is still running; at the close, none is. A process is stopped by
its pid or its working folder, never by a pattern of the command that
started it: another agent's run matches the same pattern.
