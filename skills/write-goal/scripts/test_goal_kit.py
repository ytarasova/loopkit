"""Self-check for new-goal.py and check-goal.py: python3 test_goal_kit.py

In a throwaway git repo: new-goal refuses an unadopted template, then scaffolds an adopted one; the
checker fails it unfilled, passes it filled, and fails it over 4,000 characters, with an em-dash,
with a gate that has no baseline, and with a command that skips the runner; in production
mode it also fails a gate with no window and a rollback with no revision. check-pr passes a body with
evidence and a signal, and fails one missing either, with a link alone, with a local image, or with UI
changes and no screenshot.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")


def fill(m: re.Match) -> str:
    hint = m.group(1)
    if "Opus 5.5 or Fable 5.2" in hint:
        return "Opus 5.5"
    if "haiku, sonnet or opus" in hint:
        return "sonnet, a specified function"
    if "gates that must hold" in hint:
        return "G1"
    if "the number" in hint:
        return "404 at 09:10"
    if hint.strip().startswith("window"):
        return "10 min of the deploy"
    return "filled"


def run(script: str, *args: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, os.path.join(HERE, script), *args], cwd=cwd, capture_output=True, text=True
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "init", "-q", repo], check=True)
        new = ("new-goal.py", "--slug", "t", "--title", "T", "--date", "2026-01-01")

        raw = run(*new, cwd=repo)
        assert raw.returncode == 1 and "adopt" in raw.stderr, raw.stderr

        os.makedirs(f"{repo}/.claude/loopkit")
        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            json.dump({"owner": "Sam", "runner": "make", "bypass": ["npx"]}, f)
        with open(f"{TEMPLATES}/goal-pr.md") as f:
            adopted = re.sub(r"\{\{PROJECT:[^}]*\}\}", "`make test`", f.read())
        with open(f"{repo}/.claude/loopkit/goal.md", "w") as f:
            f.write(adopted)

        made = run(*new, cwd=repo)
        assert made.returncode == 0, made.stderr
        base = f"{repo}/docs/plans/2026-01-01-t"

        fresh = run("check-goal.py", "t", cwd=repo)
        assert fresh.returncode == 1 and "unfilled" in fresh.stdout, fresh.stdout

        texts = {}
        for kind in ("goal", "master", "progress"):
            with open(f"{base}-{kind}.md") as f:
                body = f.read()
            texts[kind] = re.sub(r"\{\{FILL:([^}]*)\}\}", fill, body)
        assert "Sam" in texts["goal"] and "up to 5 implementers" in texts["goal"], texts["goal"]
        assert "{{" not in texts["goal"] and "the model its step names" in texts["goal"], texts["goal"]

        def check(**changed: str) -> str:
            for kind, body in {**texts, **changed}.items():
                with open(f"{base}-{kind}.md", "w") as f:
                    f.write(body)
            return run("check-goal.py", "t", cwd=repo).stdout

        assert check().strip().endswith("ok"), check()
        assert "refuses over 4,000" in check(goal=texts["goal"] + "x" * 4001)
        assert "em-dash" in check(goal=texts["goal"] + "\N{EM DASH}")
        m = texts["master"]
        assert "G1 has no baseline" in check(master=m.replace("Baseline: 404 at 09:10", "Baseline: unknown"))
        assert "missing or empty" in check(progress="")
        assert "In flight" in check(goal=texts["goal"].replace("In flight", "in flight"))
        assert "stacked PRs" in check(goal=texts["goal"].replace("stacked PRs", "PRs"))
        assert "complete evidence" in check(goal=texts["goal"].replace("check-pr.py", "a check"))
        assert "write-goal sequence" in check(goal=texts["goal"].replace("nothing skipped", "mostly"))
        assert "In flight" in check(progress=texts["progress"].replace("## In flight", "## Later"))
        assert "runs `npx`" in check(master=m + "\n`npx vitest run`\n")
        assert "runs `npx`" in check(master=m + "\n`cd web && npx`\n")
        assert "runs `npx`" in check(master=m + "\n```sh\nmake setup\ncd web && npx tsc\n```\n")
        assert "runs `npx`" in check(master=m + '\n`sh -c "npx x"`\n')
        assert "runs `npx`" not in check(master=m + "\n`make test` and never npx or `make lint`\n")
        assert "runs `npx`" not in check(master=m + "\n`make npxlike`\n")
        assert "Rollback is empty" in check(master=re.sub(r"\*\*Rollback\.\*\*[^\n]*", "**Rollback.**", m))
        nowindow = m.replace("within 10 min of the deploy", "over 5")
        assert "no window" not in check(master=nowindow)
        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            json.dump({"runner": "make", "ends_at": "production", "rollback_pattern": r"app:\d+"}, f)
        prod = check(master=nowindow)
        assert "G1 has no window" in prod and "Rollback does not match" in prod, prod
        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            f.write('{"ends_at": "prod"}')
        assert "ends_at" in run("check-goal.py", "t", cwd=repo).stderr
        assert "slug" in run("new-goal.py", "--slug", "a/b", "--title", "T", cwd=repo).stderr

        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            json.dump({"assurance": ["tests", "lint"], "surfaces": {"ui": ["^web/"]}}, f)

        def pr(body: str) -> str:
            with open(f"{repo}/body.md", "w") as f:
                f.write(body)
            return run("check-pr.py", "body.md", cwd=repo).stdout

        good = (
            "## Assurance\n\n```\n$ make tests\n12 passed\n$ make lint\n0 errors\n```\n\n"
            "## Evidence\n\n### UC1 An admin exports a report and gets a CSV\n\n```\n$ curl -s /export\n200 a,b\n```\n\n"
            "## Signal\n\n- Success: exports.ok above 99% for 1 h\n- Failure: exports.error above 1% in 10 min\n\n"
            "## Review\n\n- Simplify: 2 lines removed\n- Self-review, by a fresh context: clean\n- Constitution: cross-checked, clean\n"
        )
        assert pr(good).strip() == "ok", pr(good)
        for name, cut in (("Assurance", "## Assurance"), ("Evidence", "## Evidence"), ("Signal", "## Signal"), ("Review", "## Review")):
            assert f'no "## {name}"' in pr(good.replace(cut, "## Other")), name
        assert "does not show lint" in pr(good.replace("make lint\n0 errors", "x"))
        assert "not told by use case" in pr(good.replace("### UC1", "### Export"))
        assert "a link alone" in pr(good.replace("```\n$ curl -s /export\n200 a,b\n```", "[report](https://x.y/r)"))
        assert '"Failure: <metric' in pr(good.replace("- Failure", "- Watch"))
        assert '"Failure: <metric' in pr(good.replace("- Failure: exports.error above 1% in 10 min", "- Failure"))
        assert "Success" not in pr(good.replace("- Success", "Success"))
        signals = "- Success: exports.ok above 99% for 1 h\n- Failure: exports.error above 1% in 10 min"
        assert pr(good.replace(signals, "not-applicable: a docs change")).strip() == "ok"
        assert "no \"not-applicable\" with a reason" in pr(good.replace(signals, "not-applicable"))
        assert '"Failure: <metric' in pr(good.replace(signals, "- Success: a\nnot-applicable here really"))
        assert "line for simplify" in pr(good.replace("- Simplify: 2 lines removed\n", ""))
        assert "line for simplify" in pr(good.replace("- Simplify: 2 lines removed", "- Simplify"))
        assert "a self-review" in pr(good.replace("- Self-review", "- Read"))
        assert "constitution" in pr(good.replace("- Constitution: cross-checked, clean", "- no constitution read"))
        assert "does not show lint" in pr(good.replace("$ make lint\n0 errors", "x").replace("```\n\n## Evidence", "```\nlint was fine\n\n## Evidence"))
        fenced = good.replace("12 passed\n", "12 passed\n$ git status -sb\n## main...origin/main\n### UC9 not a heading\n")
        assert pr(fenced).strip() == "ok", pr(fenced)
        assert pr(good.replace("```\n$ curl", "![s]( https://x.y/s.png)\n\n```\n$ curl")).strip() == "ok"
        assert "no such file" in run("check-pr.py", "nofile", cwd=repo).stderr
        os.makedirs(f"{repo}/bin")
        os.symlink(shutil.which("git"), f"{repo}/bin/git")
        nogh = subprocess.run([sys.executable, os.path.join(HERE, "check-pr.py"), "12"], cwd=repo,
                              capture_output=True, text=True, env={"PATH": f"{repo}/bin"})
        assert "gh not found" in nogh.stderr, nogh.stderr
        shot = good.replace("```\n$ curl", "![step 1](/private/tmp/s/j1.jpg)\n\n```\n$ curl")
        assert "(not an https URL): /private/tmp/s/j1.jpg" in pr(shot), pr(shot)
        assert pr(shot.replace("/private/tmp/s/j1.jpg", "https://github.com/o/r/blob/evidence/t/j1.jpg?raw=true")).strip() == "ok"
        assert pr(good.replace("200 a,b", "200 a,b\n`![x](/tmp/a.png)`")).strip() == "ok"
        coded = good.replace("```\n$ curl -s /export\n200 a,b\n```", "`![x](https://x.y/a.png)`")
        assert "UC1 is not proven: it needs output or a screenshot" in pr(coded), pr(coded)
        sys.path.insert(0, HERE)
        problems = __import__("importlib").import_module("check-pr").problems
        kinds = {"ui": [r"^web/"], "service": [r"^api/"], "cli": [r"^cli/"]}
        assert problems(good, ["api/x.py"], kinds, ["tests"]) == []
        assert any(x.startswith("changes ui files, so Evidence needs the flow") for x in problems(good, ["web/a.tsx"], kinds, ["tests"]))
        assert any("curl" in x for x in problems(good.replace("curl -s /export", "GET /export"), ["api/x.py"], kinds, ["tests"]))
        assert any("changes cli files" in x for x in problems(good.replace("$ curl", "curl"), ["cli/main.go"], kinds, ["tests"]))
        ui_fail = problems(good, [], {}, ["tests"], {"UC1": "ui"})
        assert any(x.startswith("UC1 (ui) is not proven: it needs the flow") for x in ui_fail) and any("UX review" in x for x in ui_fail), ui_fail
        shot1 = "![land](https://x.y/1.png)\n\n```\n$ curl"
        flow = good.replace("```\n$ curl", shot1.replace("\n\n```", "\n![done](https://x.y/2.png)\n\n```"))
        assert any("needs the flow" in x for x in problems(good.replace("```\n$ curl", shot1), [], {}, ["tests"], {"UC1": "ui"}))
        assert ["a UI" in x for x in problems(flow, [], {}, ["tests"], {"UC1": "ui"})] == [True], problems(flow, [], {}, ["tests"], {"UC1": "ui"})
        assert problems(flow + "- UX review, walked from the home page: clean\n", [], {}, ["tests"], {"UC1": "ui"}) == []
        assert any("UX review" in x for x in problems(flow, ["web/a.tsx"], kinds, ["tests"]))
        assert problems(good, [], {}, ["tests"], {"UC1": "service"}) == []
        assert any("UC1 (cli)" in x for x in problems(good.replace("$ curl", "curl"), [], {}, ["tests"], {"UC1": "cli"}))

        ev = f"{repo}/docs/plans/2026-01-01-t-evidence"
        os.makedirs(ev)
        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            json.dump({"owner": "Sam", "runner": "make", "bypass": ["npx"], "assurance": ["tests", "lint"]}, f)
        p = texts["progress"]
        assert check().strip().endswith("ok"), check()
        ticked = p.replace("- [ ] Plan 1 step 1: filled", "- [X] Plan 1 step 1: filled (docs/plans/2026-01-01-t-evidence/1.1.md)")
        assert "evidence file does not exist" in check(progress=ticked)
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good.replace("## Review", "## Other"))
        assert '1.1.md: no "## Review"' in check(progress=ticked)
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good)
        assert check(progress=ticked).strip().endswith("ok"), check(progress=ticked)
        assert "does not name its evidence file" in check(progress=p.replace("- [ ] Plan 1 step 1", "- [x] Plan 1 step 1"))
        assert "does not name its evidence file" in check(progress=ticked.replace("evidence/1.1.md", "evidence/2.1.md"))
        assert "is not \"Plan N step M\"" in check(progress=ticked.replace("Plan 1 step 1", "Plan 1 task 1"))
        assert "UC1 is proven by no plan step" in check(master=m.replace("Proves UC1.", ""))
        assert "step names no model" in check(master=m.replace("Model: sonnet, a specified function.", ""))
        assert "step names no model" not in check(master=m.replace("Model: sonnet, a specified function.", "Model: haiku, a rename."))
        assert "names no orchestrator" in check(master=re.sub(r"Orchestrator: [^\n]*", "Orchestrator: someone", m))
        fable = re.sub(r"Orchestrator: \S+", "Orchestrator: Fable 5.2,", m)
        assert "the goal does not name it" in check(master=fable), check(master=fable)
        assert "the goal does not name it" not in check(master=fable, goal=texts["goal"].replace("Opus 5.5", "Fable 5.2"))
        assert "each subagent runs on the model" in check(goal=texts["goal"].replace("the model its step names", "a model"))
        assert "UC1 is proven by no plan step" in check(master=m.replace("Proves UC1.", "Does not cover UC1."))
        ui = m.replace("| UC1 | filled | filled |", "| UC1 | filled | ui |")
        assert "1.1.md: UC1 (ui) is not proven: it needs the flow" in check(master=ui, progress=ticked), check(master=ui, progress=ticked)
        done = re.sub(r"^- \[ \] ", "- [x] ", ticked, flags=re.M)
        assert "the whole has no evidence" in check(progress=done), check(progress=done)
        two = m.replace("| UC1 |", "| UC2 | x | cli |\n| UC1 |").replace("Proves UC1.", "Proves UC1 and UC2.")
        with open(f"{ev}/goal.md", "w") as f:
            f.write(good)
        assert "goal.md does not prove UC2" in check(master=two, progress=done)
        assert check(progress=done).strip().endswith("ok"), check(progress=done)
        with open(f"{ev}/goal.md", "w") as f:
            f.write(good.replace("## Signal", "## Other"))
        assert 'goal.md: no "## Signal"' in check(progress=done)
        assert '"## Use cases"' in check(master=m.replace("## Use cases", "## Cases"))
    print("goal kit ok")


if __name__ == "__main__":
    main()
