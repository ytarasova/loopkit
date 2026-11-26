# Optimize: the parts that must be exact

The method and its reasons are in [`SKILL.md`](SKILL.md). This file holds what an adopting repo would otherwise have
to guess: a case's files, what the scorer must do, the gate commands, and the evo commands a run uses. Names and
paths are defaults; the requirements are not. evo's commands are cited from its docs at version 0.8.0; where the
installed version differs, evo's docs win.

## A case

```
optimize/
  README.md            what holds for every run: the solver, the clean start and how it is reset, k
  scorer.<ext>         the scorer, and beside it the code that runs the checks and resets to the clean start
  cases/<slug>/        the cases the loop is scored on
    task.md            the task as its user would state it
    outcome.md         the desired outcome, one plain sentence per thing the user would notice
    checks.<ext>       one check per outcome sentence, in whatever the repo already runs; a check named
                       `usability_<...>` is a usability step (a person's path through a screen), the rest outcome checks
    judge.md           optional: what only a reader can decide, with its rubric
    replies.md         optional: the user's answers, in order, to what the task says it will be asked
    source.md          where the case came from: the conversation, the ticket, the request
  held-out/<slug>/     the same files, when the run holds cases out; scored only in the baseline and by the held-out floor
  held-out/strings.txt the same condition: strings of the held-out cases, one per line, at least one per case
```

A string belongs in `strings.txt` when no honest change would contain it and the baseline does not: the case's slug,
a value from its sample data, an exact sentence of its task. A word the system's whole domain uses would fail good
changes. The gate catches copying, not paraphrase. The held-out floor catches the rest, on every experiment or once at
the landing, as intake chose. With no cases held out, nothing measured does (SKILL.md, Held-out cases).

What one run sets (the caps, the held-out choice, the usability weighting, the baseline scores, the floor) lives with the run: in its master plan when it is a goal.

## The scorer

One command, for example `optimize/scorer --system <path> --cases <dir> [--tries <k>] [--min-score <x>] [--keep] [--verdict-only]`.

1. It takes the system to score as a path, and the cases as a directory. Everything else it uses (itself, the cases,
   the checks, the clean start) it reads from where it is run, never from the system's path.
2. For each case, `k` times: reset to the clean start; run a fresh solver with `task.md` and the system's public
   surface and nothing else; run the checks. A try scores checks passed over checks; when a case has usability
   steps (`SKILL.md`, Cases), 0.5 x (outcome checks passed / outcome checks) + 0.5 x (usability steps passed /
   usability steps), unless intake set another weighting. The scorer's tests pin which checks are which, so the loop
   cannot score higher by renaming one.
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
   run's ceiling is reached. The ceiling counts solver sessions only; evo's own agents and the case-shaped check are
   bounded by the round limit.
9. Cases run side by side up to a limit the repo sets. A clean start that experiments would share (one service, one
   port, one database) means `subagents=1`, unless the scorer makes one per experiment (evo's
   `sizing-the-round.md`).
10. With `--keep`, it leaves each case's last try standing instead of resetting after it, and prints where each one
    is, so the walkthrough (`SKILL.md`, Landing) reads the result a solver left. The baseline and the landing use it;
    evo's runs do not.
11. It stops every solver it started when it is interrupted or its parent dies, and removes their temporary
    directories. A timeout that kills only the command it ran would otherwise leave the solvers running, and spending.
12. With `--verdict-only`, it prints one line and nothing else, on either stream: `pass`, `below the floor` or
    `could not score`. The scores and transcripts go to a directory outside any worktree that only the run's
    orchestrator reads. The held-out gate uses it.

The whole run stays in the host's harness, on its own sign-in: evo's workers are the host's subagents, and the
scorer, being a shell command, runs each try with the host's headless CLI. No separate API key or SDK. On Claude Code:

```
cd "$(mktemp -d)"                          # the clean start's files only: no repo, no CLAUDE.md
claude -p "$(cat <case>/task.md)" \
  --strict-mcp-config --mcp-config <solver-mcp.json> \
  --tools "" --allowedTools "mcp__<server>__*" \
  --setting-sources "" --no-session-persistence \
  --output-format stream-json --verbose > <trace>.jsonl
```

- `--tools` and `--allowedTools` name exactly the system's public surface: `""` and the MCP server's tools for a system
  reached through MCP; for a library, the tools its users would have (for example `"Bash,Read"`) in a directory
  holding only the package and its docs.
- `--setting-sources ""` and `--strict-mcp-config` keep out the host's own settings, hooks, plugins and other MCP
  servers. The stream's `init` event lists the tools and servers the solver had: the scorer fails the try when it
  lists more than the surface.
- The solver's environment is a list of allowed variables, never the scorer's own: what the CLI and its sign-in need,
  and what the surface needs. Otherwise a host session's variables reach every try: its effort level, its own sockets
  and tokens, an API base URL that sends the solver to another backend unseen. Whatever sets the solver's model or
  effort is pinned and written in `optimize/README.md`.
- The stream is the try's transcript, for the trace.
- A case with `replies.md` runs the same command in one session with `--input-format stream-json`: the task goes in
  as the first user message on stdin, `{"type":"user","message":{"role":"user","content":"..."}}`, and each `result`
  event that ends a turn is answered with the next reply, until none is left and stdin closes. A one-shot `-p` would
  end the try at the first question. Nothing is resumed or saved, and the checks judge what was built, not what was
  asked.
- `--model` pins the solver's model when the adopting repo names one; otherwise the stream's `init` event records it.
- Not `--bare`: it skips the host's sign-in and needs an API key.

The solver stands in for the system's users: where they reach it through an agent, that model and client. It is
written in `optimize/README.md` and unchanged for a run.

## The gates

On evo's local backends (`worktree`, `pool`), `evo run` executes from the main repo root. Keep that checkout on the
run's baseline for the whole run: then a path without `{worktree}` is the frozen copy, and `{worktree}` is the
experiment. A remote backend runs inside the experiment's copy, so nothing there is frozen; this contract does not
cover it. `<base>` is the baseline commit. Register each gate on `root` so every experiment inherits it; a gate
passes or fails by exit code alone.

```bash
# Suite unchanged: no frozen file edited, committed or added. List every frozen path, not only optimize/.
evo gate add root --name suite_unchanged --phase pre --command "sh -c 'git -C \"{worktree}\" diff --quiet <base> -- optimize && test -z \"\$(git -C \"{worktree}\" status --porcelain -- optimize)\"'"

# The system's own tests: the repo's fast suite, run inside the experiment, not from the main root.
evo gate add root --name own_tests --phase pre --command "sh -c 'cd \"{worktree}\" && <the fast suite>'"

# No held-out leak runs whenever the run holds cases out; the held-out floor is a gate only when intake chose every
# experiment (SKILL.md, Held-out cases).
# No held-out leak: no held-out string anywhere outside the suite, tracked or new. Exit 1 from grep is "none found";
# anything else fails the gate, an empty or missing strings.txt included. It reads the experiment's copy of
# strings.txt, which suite_unchanged has already shown to be the baseline's.
evo gate add root --name no_heldout_leak --phase pre --command "sh -c 'test -s \"{worktree}/optimize/held-out/strings.txt\" && { git -C \"{worktree}\" grep -qiF --untracked -f optimize/held-out/strings.txt -- . \":^optimize\"; test \$? -eq 1; }'"

# No case-shaped change: the repo's fixed-prompt check, given the experiment's diff and every case's title,
# held-out ones included.
evo gate add root --name no_case_shaped_change --phase pre --command "<the check> --diff-from <base> --system \"{worktree}\""

# Held-out floor: the held-out cases, not below the lowest of the n baseline runs on them. Registered only when
# intake chose every experiment; when it chose the landing, the same command runs once by hand on the cut-down branch.
evo gate add root --name heldout_floor --command "optimize/scorer --system \"{worktree}\" --cases optimize/held-out --min-score <floor> --verdict-only"

evo gate list root
evo gate check <node_id>     # runs every gate without changing the node: all must pass on the baseline
```

- A pre gate that fails stops that experiment's run before the scorer. The experiment is not committed, and its agent
  fixes it or discards it.
- The floor is the lowest held-out score among the `n` baseline runs, not their mean: a floor at the mean would fail
  an unchanged system about every other time.
- The held-out gate prints its verdict and nothing else (`--verdict-only`). evo's agents read gate output, so a
  held-out score or transcript printed there is a held-out case shown to the loop.
- `own_tests` passes on the baseline. Where the baseline already fails some of the system's checks (known type errors,
  red tests), the gate compares failures, not counts: the baseline's own, measured in the frozen checkout, against the
  experiment's, and it passes when the experiment adds none. The test and typecheck configs are frozen paths. A count
  passes a change that swaps one failure for another, or loosens the config.
- The case-shaped check asks one question of each change: would this exist if that case were not in the suite? A
  change that names a case, branches on its inputs, or documents its answer fails.
- After a new baseline (the suite grew), `<base>` and `<floor>` are stale, the landing's by-hand floor included: `evo gate remove root --name <name>` for
  `suite_unchanged`, `no_case_shaped_change` and `heldout_floor` when registered, add them again, and run `evo gate check`.
- At the landing the same commands run by hand on the cut-down branch, with `{worktree}` replaced by its checkout.

## The evo commands a run uses

Never install evo unasked. Under the owner's grant, on Claude Code:

```bash
uv tool install evo-hq-cli==0.8.0
evo install claude-code                       # evo's plugin and hooks; other hosts are named in evo's README
evo update claude-code --version 0.8.0        # an unpinned install moves the CLI to the latest stable: pin it back
evo doctor claude-code                        # confirms the install
```

The plugin loads in a new session, so install before the session that runs the loop starts. `evo status`
succeeding shows a workspace is ready.

```bash
evo init --name "<name>" --target <the system's entry file> \
  --benchmark "optimize/scorer --system {worktree} --cases optimize/cases" \
  --metric max --host <host> --instrumentation-mode <sdk|inline> --per-exp-timeout <seconds>
evo config set frontier-strategy <kind>            # argmax | top_k | epsilon_greedy | softmax | pareto_per_task
evo config set max-attempts <n>                    # retries per experiment; default 3, and each one costs a full score
/evo:optimize subagents=<N> budget=<N> stall=<N> autonomous    # and say "you can edit directly"
evo status                                 # the best valid score
git diff <baseline_commit> <winner_commit> # the winner against the baseline; `evo diff` is scoped to the target
evo exit-optimize-mode                     # stop the loop: at the round limit, or at the spend ceiling
evo gc                                     # at the end: free the finished experiments' worktrees
evo infra event -m "<reason>" --breaking   # the suite changed; then fix the suite in a fresh root and re-baseline:
evo new --parent root -m "baseline: <what changed>"
evo run <new_exp_id>
```

- **Telemetry.** evo sends anonymous telemetry unless turned off. Start the host with `EVO_TELEMETRY=0` in its
  environment, so evo's skills and subagents inherit it; a prefix on one command covers only that command.
  `evo telemetry off` is global, so it is the owner's to run.
- **`--target`** is one entry file, and evo's subagents edit within the target scope. Write the real boundary in
  `.evo/project.md`: the whole system, never the frozen files.
- **Discover.** `/evo:discover` normally builds a benchmark inside its baseline worktree. Here the scorer already
  exists in the repo and is already instrumented, which is discover's first case: nothing to build, nothing to wire.
- **The two switches.** evo's optimize skill arms `autonomous` and `subagents-only` itself as its first action, on
  unless the invocation says otherwise, so a switch set by hand beforehand is overwritten. Say it on the invocation:
  `autonomous` for an unattended run, and "you can edit directly" to leave `subagents-only` off, because the run's
  orchestrator still writes its progress file. Candidate edits stay with evo's subagents either way.
- **The caps.** `subagents` is how many experiments run at once, `budget` how many experiments each subagent may run
  on its branch in a round, `stall` how many rounds with no gain end the loop (default 5). evo has no round limit
  and no spend ceiling: the run counts rounds itself and the scorer's ledger holds the ceiling.
- **Stopping.** `evo exit-optimize-mode` also discards experiments still active, and cannot reach the host's
  subagents: stop those from the host. At the end keep `.evo/` as the run's record, run `evo gc`, and stop the
  dashboard evo started (its supervisor first, `.evo/supervisor.pid`).
- **The frontier.** `argmax` extends the best branch. `pareto_per_task` keeps branches that are best on some case,
  which finds more in a suite of unlike cases and pulls toward the one-case changes the case-shaped gate exists to
  stop; use it only with that gate in place.
- **The winner** is evo ship's: the highest-scoring valid result in the run's history, not the frontier. Valid means
  committed (or pruned as exhausted), with no failed gate and no invalid-pruned ancestor.
- **A new run from a merged main.** evo's 0.8.0 docs do not say how a workspace moves its root to a new commit. Find
  out at the installed version before the second run, and write the answer in `optimize/README.md`.
