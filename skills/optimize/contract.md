# Optimize: the parts that must be exact

The method is in [`SKILL.md`](SKILL.md). This file holds what an adopting repo would otherwise have to guess: a case's
files, what the scorer must do, the gate commands, and the evo commands a run uses. Names and paths are defaults; the
requirements are not. evo's commands are cited from its docs at version 0.8.0; where the installed version differs,
evo's docs win.

## A case

```
optimize/
  README.md            the choices fixed for a run: the solver, the clean start, k, the caps, the baseline scores
  scorer.<ext>         the scorer, and beside it the code that runs the checks and resets to the clean start
  cases/<slug>/        the cases the loop is scored on
    task.md            the task as its user would state it
    outcome.md         the desired outcome, one plain sentence per thing the user would notice
    checks.<ext>       one check per outcome sentence, in whatever the repo already runs
    judge.md           optional: what only a reader can decide, with its rubric
    source.md          where the case came from: the conversation, the ticket, the request
  held-out/<slug>/     the same files; scored only by the held-out gate
  held-out/strings.txt one distinctive string of a held-out case per line: its slug, its names, its wording
```

A string in `strings.txt` is distinctive when the baseline does not already contain it: the leak gate must pass on the
baseline.

## The scorer

One command, for example `optimize/scorer --system <path> --cases <dir> [--tries <k>] [--min-score <x>]`.

1. It takes the system to score as a path, and the cases as a directory. Everything else it uses (itself, the cases,
   the checks, the clean start) it reads from where it is run, never from the system's path.
2. For each case, `k` times: reset to the clean start; run a fresh solver with `task.md` and the system's public
   surface and nothing else; run the checks. A try scores checks passed over checks.
3. A case's score is its mean over the tries minus its spread across them (the standard deviation, unless the repo
   records another), never below zero. The run's score is the mean of the cases' scores.
4. It reports each case to evo once, with every try's transcript and every check's result in the trace, and a
   `failure_reason` tag that stays the same across runs:
   - SDK mode (`from evo_agent import Run`): `run.log(task_id, {...})` per event, then
     `run.report(task_id, score=..., summary=..., failure_reason=..., cost=...)`, and `run.finish()` once, in a
     `try`/`finally`. `finish()` takes the mean of the reported scores.
   - Inline mode: evo's `log_task` per case and `write_result` once.
   - Either way the wire is the same: `{"score": 0.75, "tasks": {"<case>": 1.0, ...}}` at `EVO_RESULT_PATH`, and a
     `task_<id>.json` per case under `EVO_TRACES_DIR`.
5. It runs without evo's variables too, printing the scores: the baseline runs and the gates call it that way (evo
   gives gates the runtime env, not the `EVO_*` variables).
6. It exits 0 when it finished, however low the score. A solver that failed a case scored zero; it did not crash the
   scorer. It exits non-zero only when it could not score, or, with `--min-score`, when the score is below it.
7. Transcripts carry no secrets: redact before logging.
8. It counts the solver sessions it starts in a ledger outside any worktree, and refuses to start (non-zero) once the
   run's spend ceiling is reached.
9. Cases run side by side up to a limit the repo sets.

How it runs a solver (an agent SDK, a headless CLI with a tool config) is the repo's choice. The solver's model and
client are the ones the system's users reach it with, written in `optimize/README.md`, and unchanged for a run.

## The gates

`evo run` executes from the main repo root. Keep that checkout on the run's baseline for the whole run: then a path
without `{worktree}` is the frozen copy, and `{worktree}` is the experiment. `<base>` is the baseline commit. Register each on
`root` so every experiment inherits it; a gate passes or fails by exit code alone.

```bash
# Suite unchanged: no frozen file edited, committed or added. List every frozen path, not only optimize/.
evo gate add root --name suite_unchanged --phase pre --command "sh -c 'git -C {worktree} diff --quiet <base> -- optimize && test -z \"\$(git -C {worktree} status --porcelain -- optimize)\"'"

# The system's own tests: the repo's fast suite, run in the experiment.
evo gate add root --name own_tests --phase pre --command "<the fast suite, in {worktree}>"

# No held-out leak: no held-out string anywhere outside the suite, tracked or new. Exit 1 from grep is "none found";
# anything else, a missing strings.txt included, fails the gate. It reads the experiment's copy of strings.txt, which
# suite_unchanged has already shown to be the baseline's.
evo gate add root --name no_heldout_leak --phase pre --command "sh -c 'git -C {worktree} grep -qiF --untracked -f optimize/held-out/strings.txt -- . \":^optimize\"; test \$? -eq 1'"

# No case-shaped change: the repo's fixed-prompt check, given the experiment's diff and the case titles.
evo gate add root --name no_case_shaped_change --phase pre --command "<the check> --diff-from <base> --system {worktree}"

# Held-out floor: the held-out cases, not below their baseline lower bound.
evo gate add root --name heldout_floor --command "optimize/scorer --system {worktree} --cases optimize/held-out --min-score <baseline held-out score>"

evo gate list root
evo gate check <node_id>     # runs every gate without changing the node: all must pass on the baseline
```

A pre gate that fails stops the run of that experiment before the scorer; the experiment is not committed, and its
agent fixes it or discards it. The case-shaped check's prompt asks one question of each change: would this exist if
that case were not in the suite? A change that names a case, branches on its inputs, or documents its answer fails.

## The evo commands a run uses

Never install evo unasked. Under the owner's grant, evo's own steps are `uv tool install evo-hq-cli` and
`evo install <host>`; `evo status` succeeding shows a workspace is ready.

```bash
EVO_TELEMETRY=0 evo ...                    # telemetry off for a command or a session; `evo telemetry off` is global,
                                           # so it is the owner's to run
evo init --name "<name>" --target <the system's entry file> \
  --benchmark "optimize/scorer --system {worktree} --cases optimize/cases" \
  --metric max --host <host> --instrumentation-mode <sdk|inline> --per-exp-timeout <seconds>
evo config set frontier-strategy pareto_per_task   # a first choice for a suite of unlike cases
evo config set max-attempts <n>                    # retries per experiment; default 3, and each one costs a full score
evo autonomous on                          # the keep-going nudge, for an unattended run
evo subagents-only off                     # the run's orchestrator still writes its progress file; candidate edits
                                           # stay with evo's subagents either way
/evo:optimize subagents=<N> budget=<N> stall=<N>
evo status                                 # the best valid score
evo diff <root_id> <winner_id>             # the winner against the baseline
evo exit-optimize-mode                     # stop the loop: at the round limit, or at the spend ceiling
evo infra event -m "<reason>" --breaking   # the suite changed; then a new baseline:
evo new --parent root -m "baseline: <what changed>"
evo run <new_exp_id>
```

- `/evo:discover` normally builds a benchmark inside its baseline worktree. Here the scorer already exists in the
  repo and is already instrumented, which is discover's first case: nothing to build, nothing to wire.
- Set both switches every run. evo's optimize skill treats `autonomous` and `subagents-only` as on unless told
  otherwise, and its CLI leaves both unarmed until the command is run.
- `subagents` is how many experiments run at once, `budget` how many tries each branch gets in a round, `stall` how
  many rounds with no gain end the loop (default 5). evo has no round limit and no spend ceiling: the run counts
  rounds itself and stops with `evo exit-optimize-mode`, and the scorer's ledger holds the ceiling.
- The winner is the highest-scoring valid experiment in the run, not the frontier: committed, every gate passed.
- How evo starts again from a merged main is evo's; read its discover skill at the installed version.
