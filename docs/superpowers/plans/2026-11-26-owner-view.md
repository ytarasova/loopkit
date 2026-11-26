# The owner's view inside the run: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** loopkit 0.14.0: the run judges its work as the owner would (an owner's reader at five points, a 30-minute watch), with checks the worker cannot bend, and corrections that reach the run and its repo the same day.

**Architecture:** Three script changes in `skills/write-goal/scripts` (a `lessons` setting, a `watch` stamp with its age check, an Owner read line on a step's evidence), then skill text: a new `write-goal/owner-reader.md` and `write-goal/agents/walker.md`, the principle and step 8 in `write-goal/SKILL.md`, optimize's observing checks, and rollout rule 8. Four stacked PRs: design, scripts, write-goal text, optimize and the release.

**Tech Stack:** Python 3.10+ standard library; Markdown skills; the kit's own test, `skills/write-goal/scripts/test_goal_kit.py`.

**Spec:** `docs/superpowers/specs/2026-11-26-owner-view-design.md`

## Global Constraints

- The kit stays generic: no product, repo, person or company named (the kit test checks names from git config and authors).
- No em-dash anywhere (`git grep $'—'` empty).
- `write-goal/SKILL.md` stays under 500 lines (one adopter's cap).
- Run tests with Python 3.10 or newer (`python3 --version`); the system `python3` may be 3.9.
- Each PR body passes `check-pr.py <PR>`; land with `gh pr merge --squash --delete-branch` after CI, bottom of the stack first.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A progress file with In flight empty and no `Watched:` stamp: no watch failure (nothing to watch).
- A progress file written before 0.14 (no `Watched:` line, In flight non-empty): fails with the age from the first Log entry, and the message says what to run.
- A `Watched:` stamp ahead of the clock: caught by the existing ahead-of-clock check, like every other stamp.
- A deliverable (a PR body, `evidence/goal.md`) with no Owner read line: still passes; only a step's evidence file needs it.
- `lessons` set to a path outside `.claude/`, changed on a state branch: the kit-on-a-branch check fails it; the default path is already under `.claude/` and must not be reported twice.

---

### Task 1: The `lessons` setting, covered by the kit-on-a-branch check

**Files:**
- Modify: `skills/write-goal/scripts/config.py` (DEFAULTS, `load()` validation)
- Modify: `skills/write-goal/scripts/check-goal.py:365-377` (the diff paths), docstring line 34-35
- Test: `skills/write-goal/scripts/test_goal_kit.py` (beside the `kit files changed` asserts, ~line 880)

**Interfaces:**
- Produces: `cfg["lessons"]: str`, default `".claude/loopkit/lessons.md"`; `load()` reports `lessons must be a path` when it is not a non-empty string.

- [ ] **Step 1: Write the failing test** after the existing `kit files changed` asserts, on the same `state/t` branch:

```python
        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            json.dump({**json.load(open(f"{repo}/.claude/loopkit.json")), "lessons": "docs/feedback.md"}, f)
        os.makedirs(f"{repo}/docs", exist_ok=True)
        with open(f"{repo}/docs/feedback.md", "a") as f:
            f.write("| 1 | a lesson |\n")
        git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "lesson on the branch")
        out = check()
        assert "kit files changed on state/t" in out and "docs/feedback.md" in out, out
```

- [ ] **Step 2: Run it and see it fail:** `python3 skills/write-goal/scripts/test_goal_kit.py` → AssertionError at the new assert.
- [ ] **Step 3: Implement.** Add `"lessons": ".claude/loopkit/lessons.md"` to DEFAULTS with the comment `# the repo's lessons file; a row on a run's branch only is caught like a kit file`. In `check-goal.py`, pass `cfg["lessons"]` as a third path to the `git diff --name-only` call, deduplicated by git; extend the docstring's repo line to "(CONSTITUTION.md, .claude/, the lessons file)".
- [ ] **Step 4: Run it and see it pass:** `goal kit ok`.
- [ ] **Step 5: Commit** `write-goal: the lessons file is a setting, and a kit file to check-goal`.

### Task 2: `progress.py watch`, and the watch's age in check-goal

**Files:**
- Modify: `skills/write-goal/scripts/progress.py` (docstring, `stamp()`, `verbs`)
- Modify: `skills/write-goal/scripts/check-goal.py:254-280` (stamps, a new fail), docstring progress line
- Test: `skills/write-goal/scripts/test_goal_kit.py` (the progress.py block, after the `view` asserts ~line 935)

**Interfaces:**
- Produces: the line `Watched: YYYY-MM-DD HH:MM UTC`, placed by `after_now(text, line, r"^Watched: [^\n]*")`; `progress.py <slug> [<date>] watch` (two args, like `view`).
- check-goal fail text begins `the watch is ` and ends `(dispatch a watch pass, then progress.py watch)`.

- [ ] **Step 1: Write the failing tests**, in the progress.py block:

```python
        assert stamp("watch").returncode == 0 and re.search(r"^Watched: \S+ \S+ UTC$", read(), re.M)
        assert "the watch is" not in run("check-goal.py", "t", cwd=repo).stdout
        flying = read().replace("- Nothing.", "- step 2, sonnet, 40m", 1)
        with open(prog, "w") as f:  # an old watch while work is in flight
            f.write(re.sub(r"^Watched: .*$", "Watched: 2026-01-01 08:00 UTC", flying, flags=re.M))
        out = run("check-goal.py", "t", cwd=repo).stdout
        assert "the watch is" in out and "progress.py watch" in out, out
        with open(prog, "w") as f:  # no watch yet: the age counts from the run's first Log entry
            f.write(re.sub(r"^Watched: .*\n\n?", "", flying, flags=re.M))
        assert "the watch is" in run("check-goal.py", "t", cwd=repo).stdout
        with open(prog, "w") as f:  # nothing in flight: nothing to watch
            f.write(re.sub(r"^Watched: .*$", "Watched: 2026-01-01 08:00 UTC", flying.replace("- step 2, sonnet, 40m", "- Nothing.", 1), flags=re.M))
        assert "the watch is" not in run("check-goal.py", "t", cwd=repo).stdout
        with open(prog, "w") as f:
            f.write(re.sub(r"^Watched: .*$", "Watched: 2999-01-01 09:00 UTC", flying, flags=re.M))
        assert "ahead of the clock: 2999-01-01 09:00 UTC" in run("check-goal.py", "t", cwd=repo).stdout
```

The fixture's In flight empty line is `- Nothing.`; if it reads otherwise, use the fixture's text.

- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.** `progress.py`: verb `watch` stamps `Watched: {at} UTC` via `after_now`; `verbs["watch"] = 2`; docstring line `python3 progress.py <slug> [<date>] watch    stamp "Watched: YYYY-MM-DD HH:MM UTC" after a watch pass`. `check-goal.py`: parse `watched = re.search(rf"^Watched: {stamp_at}", prog, re.M)`, add it to `stamps`; when In flight has an item (the same `findall` the time-left check uses) and the clock is more than 45 minutes past `watched` (or, with none, past `min(logged)`), fail `the watch is {n} min old while work is in flight: a fresh pass runs at least every 30 min (dispatch a watch pass, then progress.py watch)`. Compute ages from parsed datetimes, not strings.
- [ ] **Step 4: Run and see them pass.**
- [ ] **Step 5: Commit** `write-goal: progress.py watch, and check-goal holds the watch to 45 minutes`.

### Task 3: A step's evidence carries its Owner read

**Files:**
- Modify: `skills/write-goal/scripts/check-pr.py` (`problems()` signature, Review checks ~296-306, the call ~352, docstring Review line)
- Modify: `skills/write-goal/scripts/test_goal_kit.py` (the `1.1.md` fixture ~line 815, new asserts)

**Interfaces:**
- Produces: `problems(body, files, surfaces, checks, ucs=None, deliverable=False, step=False) -> list[str]`; main passes `step=step`. With `step=True` and a Review section, a missing line matching `^[^\w\n]*owner read\w*\b[^\w\n]*\w` gives `a step's evidence needs an "Owner read, by a fresh <model> context: <result>" line in Review (write-goal/owner-reader.md)`; a line without a model gives `the Owner read line names no model`.

- [ ] **Step 1: Write the failing tests.** Where the test writes `1.1.md` from `good` and expects ok, first assert the missing line, then add it:

```python
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good.split("\n## Release notes")[0])
        assert 'needs an "Owner read' in check(progress=ticked), check(progress=ticked)
        owner = "- Owner read, by a fresh sonnet context: nothing the owner would object to\n"
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good.split("\n## Release notes")[0] + owner)
        assert check(progress=ticked).strip().endswith("ok"), check(progress=ticked)
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good.split("\n## Release notes")[0] + owner.replace(" sonnet", ""))
        assert "Owner read line names no model" in check(progress=ticked)
```

and keep `assert pr(good).strip() == "ok"` passing (a deliverable needs no Owner read). Every later fixture that writes a step file and expects ok gets `owner` appended.

- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** in `problems()`, beside the Self-review model check, gated on `step`; docstring Review line gains "and, on a step's evidence file, the Owner read (naming its model)".
- [ ] **Step 4: Run and see them pass.**
- [ ] **Step 5: Commit** `check-pr: a step's evidence carries its Owner read`.

PR 2 = Tasks 1 to 3, titled `write-goal 0.14 (1/3): lessons setting, watch stamp, Owner read line`, base `design/owner-view`.

### Task 4: write-goal text: the principle, the reader, the watch, the walker

**Files:**
- Create: `skills/write-goal/owner-reader.md`
- Create: `skills/write-goal/agents/walker.md`
- Modify: `skills/write-goal/SKILL.md` (lifecycle opening, the sequence table, While it runs, UX review list, §3 progress file bullets, Common mistakes)
- Modify: `skills/write-goal/subagents.md` (every prompt carries the Owner corrections rows; stop by pid or folder)
- Modify: `skills/write-goal/templates/progress.md` (a `Watched:` line under Now, if the template carries the view stamp the same way)
- Modify: `skills/adopt/rollout.md` (rule 8), `skills/adopt/SKILL.md` (copy the walker into the repo's agents)

**Interfaces:**
- Consumes: Task 2's `progress.py watch` and 45-minute rule; Task 3's Owner read line text; Task 1's `lessons` setting.
- Produces: `owner-reader.md` headings `# The owner's reader and the watch`, `## What it carries`, `## Where it reads`, `## What it returns`, `## The watch`; `agents/walker.md` frontmatter `name: walker`, `tools:` a browser's tools and `Write`, no `Bash`.

- [ ] **Step 1: `owner-reader.md`.** Carry spec sections 2 and 3 as rules, in the kit's voice: what the prompt carries (the intent's words, Asks, the lessons file at `lessons`, this run's Owner corrections, the thing read, the running product at a task); the one question; object and ask, with an ask holding only the work that depends on it (its In flight or What is left row names the ask) and a grant without the owner's words dropped as an object; the five points table; models (sonnet at a dispatch and a message, the step's model or higher at a task, opus at the plan and a PR); the watch: a fresh sonnet pass at least every 30 minutes while In flight lists anything, reading the progress diff and each in-flight transcript's tail since the last pass, then `progress.py <slug> watch`; findings acted on the same turn.
- [ ] **Step 2: `agents/walker.md`.** A Claude Code agent: description "Walks a product as its user, through its own screens, and reports each flow as works unpatched or blocked at <step>". Tools: the browser's (name the playwright MCP tools generically, `mcp__playwright__*` style, with a note that adopt rewrites them for the repo's browser) and `Write`. Body: setup is only the repo's committed seed and the product's own screens, listed in the report; never edit data; the UX list's new items (where a click lands, hidden or off-screen controls at each width, validation that does not say what to fix, clicks a task takes).
- [ ] **Step 3: `SKILL.md`.** (a) Open "The lifecycle" with: "Done means the work's user can do it in the product, unaided, and the owner would accept it. Every rule below is a case of that." (b) Insert sequence row 8 `Owner read: what would the owner object to? (owner-reader.md) | owner's reader, a fresh context | no object; an ask is under Waiting on, holding only what depends on it`, renumber 8-10 to 9-11, and point the "Review lines" row at both lines. (c) While it runs: "A watch pass at least every 30 minutes while anything is in flight (`owner-reader.md`), stamped `progress.py <slug> watch`"; "An "eta?" is answered with a time, and with what moved it since the last answer." (d) UX review list: the four new items; "walking it" names `agents/walker.md`. (e) A paragraph after the UX list: main's tests are not changed to make a branch pass unless that change is the ask named in the master plan; a test failing on main is fixed at its cause in its own PR off main, an expected result named, never a count raised; a live fault found on main (security, data loss) goes to the owner as its own PR off main. (f) Common mistakes rows: "A walk that edits data to pass | The flow works for the tester, not for the person"; "The owner's view left to the owner | They catch what the run should have, and relay it back". Keep the file under 500 lines; move text to `owner-reader.md` if it is not.
- [ ] **Step 4: `subagents.md`.** Every prompt carries this run's Owner corrections rows; a process is stopped by its pid or its working folder, never by a pattern of the command that started it.
- [ ] **Step 5: `rollout.md` rule 8 and `adopt/SKILL.md`.** Rule 8 gains: "A correction the run's own owner gave is the second exception: the run takes it mid-run, alone, and its repo's change ships off main the same turn; one marked general is carried to loopkit by a kit session." Adopt copies `write-goal/agents/walker.md` to `.claude/agents/walker.md`, with the repo's browser tools.
- [ ] **Step 6: Verify:** `python3 skills/write-goal/scripts/test_goal_kit.py` → `goal kit ok`; `wc -l skills/write-goal/SKILL.md` under 500; `git grep $'—' -- skills` empty.
- [ ] **Step 7: Commit** `write-goal 0.14: the owner's reader, the watch, the walker`.

PR 3 = Task 4, base PR 2's branch.

### Task 5: optimize, the version and the changelog

**Files:**
- Modify: `skills/optimize/SKILL.md` (Cases, Landing, Common mistakes), `skills/optimize/contract.md` (if it states the score's formula)
- Modify: `CHANGELOG.md`, `.claude-plugin/plugin.json` (`"version": "0.14.0"`)

- [ ] **Step 1: optimize.** Cases: a check on a result used through screens observes the running product, never reads its source to guess what a screen shows; usability steps and outcome checks weigh half each by default, so many easy steps cannot drown out the outcomes, and intake may set another weighting. Landing: the walkthrough is made with `write-goal/agents/walker.md`. Common mistakes: "A usability check that reads source | Each review finds a new shape it misreads, and the loop games the rest". In `contract.md`, where the scorer's output or score is defined, add the weighting.
- [ ] **Step 2: CHANGELOG 0.14.0**, with an upgrade paragraph: set `lessons` when the lessons file is not `.claude/loopkit/lessons.md`; copy the walker; step files of a goal started on 0.13 keep passing only if that goal keeps its kit (rule 8), so upgrade between goals; add `Watched:` to the progress template.
- [ ] **Step 3: Verify** as Task 4 Step 6; bump the version.
- [ ] **Step 4: Commit** `loopkit 0.14.0: optimize observes, and the release`.

PR 4 = Task 5, base PR 3's branch. PR 1 = the design and this plan, base `main`.

### Task 6: Land, then port

- [ ] **Step 1:** For PRs 1 to 4 in order: `check-pr.py <n>` ok, `gh pr checks <n> --watch` green, `gh pr merge <n> --squash --delete-branch`, retarget the next to `main`.
- [ ] **Step 2:** Port by `adopt/rollout.md` to the three adopting repos, each repo's own landing rule; their `check-pr.py`, `check-goal.py` and `progress.py` copies differ, so each script change is ported by hand with that repo's kit test (or its fitness suite). Set each repo's `lessons` where its lessons file is not the default.
- [ ] **Step 3:** One table to the owner: repo, where it landed, what was rerun, what was not ported and why.
