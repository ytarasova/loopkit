"""Self-check for new-goal.py and check-goal.py: python3 test_goal_kit.py

In a throwaway git repo: new-goal refuses an unadopted template, then scaffolds an adopted one; the
checker fails it unfilled, passes it filled, and fails it over 4,000 characters, with an em-dash,
with a gate that has no baseline, and with a command that skips the runner; in production
mode it also fails a gate with no window and a rollback with no revision.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")


def fill(m: re.Match) -> str:
    hint = m.group(1)
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
        assert "Sam" in texts["goal"] and "up to 5 sonnet" in texts["goal"], texts["goal"]
        assert "{{" not in texts["goal"] and "by a sonnet subagent" in texts["goal"], texts["goal"]

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
    print("goal kit ok")


if __name__ == "__main__":
    main()
