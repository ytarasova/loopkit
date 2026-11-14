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
    if "e.g. 2h 30m" in hint:
        return "2h 30m"
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


FAKE_GH = r"""#!/usr/bin/env python3
import json, os, subprocess, sys
state_path = os.environ["FAKE_GH_STATE"]
st = json.load(open(state_path))
a = sys.argv[1:]
def git(*c):
    return subprocess.run(["git", *c], cwd=st["clone"], capture_output=True, text=True, check=True).stdout
def fields(out):  # like gh: only what --json asked for
    want = a[a.index("--json") + 1].split(",")
    return {k: out[k] for k in want if k in out}
def tip(branch):
    return git("ls-remote", "--heads", "origin", branch).split()[:1]
if a[:2] == ["repo", "view"]:
    print(st["repo"])
elif a[:2] == ["pr", "view"]:
    p = st["prs"][a[2]]
    out = {"number": int(a[2]), "state": p["state"], "baseRefName": p["base"], "headRefName": p["head"],
           "isCrossRepository": p.get("fork", False), "statusCheckRollup": p.get("checks", []),
           "files": [{"path": f} for f in p["files"]], "body": p["body"]}
    out["headRefOid"] = p["merged_oid"] if p["state"] == "MERGED" else (tip(p["head"]) or [""])[0]
    print(json.dumps(fields(out)))
elif a[:2] == ["pr", "list"]:
    key = "base" if "--base" in a else "head"
    branch = a[a.index("--" + key) + 1]
    print(json.dumps([{"number": int(k), "isCrossRepository": q.get("fork", False)}
                      for k, q in st["prs"].items() if q["state"] == "OPEN" and q[key] == branch]))
elif a[:2] == ["pr", "edit"]:
    st["prs"][a[2]]["base"] = a[a.index("--base") + 1]
elif a[:2] == ["pr", "merge"]:
    p = st["prs"][a[2]]
    if p.get("blocked"):
        sys.exit("X Pull request is not mergeable: the base branch policy prohibits the merge.")
    if p.get("push_before_merge"):  # someone pushes while the merge is on its way
        git("fetch", "-q", "origin"); git("switch", "-q", "-C", "late", "origin/" + p["head"])
        open(os.path.join(st["clone"], "late.txt"), "w").write("late\n"); git("add", "late.txt")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "late"); git("push", "-q", "origin", "late:" + p["head"])
        p.pop("push_before_merge"); json.dump(st, open(state_path, "w"))
    head = tip(p["head"])[0]
    if "--match-head-commit" in a and a[a.index("--match-head-commit") + 1] != head:
        sys.exit("X Head branch was modified. Review and try the merge again.")
    if not p.get("queue"):
        git("fetch", "-q", "origin"); git("switch", "-q", "-C", p["base"], "origin/" + p["base"])  # into its own base, as GitHub does
        git("merge", "-q", "--squash", "origin/" + p["head"])
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "squash " + a[2]); git("push", "-q", "origin", p["base"])
        p["state"], p["merged_oid"] = "MERGED", head
else:
    sys.exit("fake gh: " + " ".join(a))
json.dump(st, open(state_path, "w"))
"""


def land_stack_test() -> None:
    """land-stack.py lands one PR per run, never merges main up itself, and stops before it could close a PR or lose a commit."""
    with tempfile.TemporaryDirectory() as tmp:
        def git(*c, cwd=tmp):
            r = subprocess.run(["git", *c], cwd=cwd, capture_output=True, text=True)
            assert r.returncode == 0, f"git {' '.join(c)}: {r.stderr}"
            return r.stdout
        ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
        git("init", "-q", "--bare", "-b", "main", "origin.git")
        git("clone", "-q", "origin.git", "work"); w = os.path.join(tmp, "work")
        bare = os.path.join(tmp, "origin.git")

        def commit(branch, start, name, text):
            git("fetch", "-q", "origin", cwd=w)
            git("switch", "-qC", branch, "origin/" + start, cwd=w)
            open(os.path.join(w, name), "w").write(text)
            git("add", name, cwd=w); git(*ident, "commit", "-qm", name, cwd=w); git("push", "-q", "origin", branch, cwd=w)

        def merge_up(branch):  # what the agent does, by the printed steps
            git("fetch", "-q", "origin", cwd=w); git("switch", "-qC", branch, "origin/" + branch, cwd=w)
            git(*ident, "merge", "-q", "--no-edit", "origin/main", cwd=w); git("push", "-q", "origin", branch, cwd=w)

        open(os.path.join(w, "a.txt"), "w").write("base\n"); git("add", "a.txt", cwd=w); git(*ident, "commit", "-qm", "base", cwd=w)
        git("push", "-q", "origin", "HEAD:main", cwd=w)
        git("clone", "-q", "origin.git", "gh-clone")
        os.makedirs(os.path.join(w, ".claude"), exist_ok=True)
        with open(os.path.join(w, ".claude", "loopkit.json"), "w") as f:
            json.dump({"assurance": ["tests"]}, f)
        body = lambda sha: (
            f"## Assurance\n\n- tests\n```\n$ make tests on {sha}\n1 passed\n```\n\n## Evidence\n\n### UC1 A user does x\n\n```\n$ x\nok\n```\n\n"
            "## Signal\n\nnot-applicable: a test fixture with no runtime\n\n## Review\n\n- Simplify: none\n- Self-review, by a fresh opus context: clean\n"
            "- Security review: clean\n- Constitution: clean\n")
        head = lambda b: git("rev-parse", b, cwd=bare).strip()
        state_file = os.path.join(tmp, "state.json")
        save = lambda st: json.dump(st, open(state_file, "w"))
        load = lambda: json.load(open(state_file))
        add = lambda base, branch, f: dict(state="OPEN", base=base, head=branch, files=[f], body=body(head(branch)))
        refresh = lambda n: (lambda st: (st["prs"][n].update(body=body(head(st["prs"][n]["head"]))), save(st)))(load())
        commit("b1", "main", "one.txt", "1\n"); commit("b2", "b1", "two.txt", "2\n"); commit("b3", "b2", "three.txt", "3\n")
        save({"clone": os.path.join(tmp, "gh-clone"), "repo": os.path.basename(tmp) + "/origin",
              "prs": {"1": add("main", "b1", "one.txt"), "2": add("b1", "b2", "two.txt"), "3": add("b2", "b3", "three.txt")}})
        os.makedirs(os.path.join(tmp, "bin")); gh = os.path.join(tmp, "bin", "gh")
        open(gh, "w").write(FAKE_GH); os.chmod(gh, 0o755)
        env = {**os.environ, "PATH": os.path.join(tmp, "bin") + os.pathsep + os.environ["PATH"], "FAKE_GH_STATE": state_file,
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        land = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, "land-stack.py"), *a], cwd=w, env=env, capture_output=True, text=True)
        go = lambda *a: land(*a, "--run", "--allow-no-checks")
        gone = lambda b: not git("branch", "--list", b, cwd=bare).strip()

        planned = land("1", "2", "3")
        assert "merge main up into #2's branch" in planned.stdout and "plan only" in planned.stdout, planned.stdout
        assert load()["prs"]["1"]["state"] == "OPEN", "a plan changed something"
        unchecked = land("1", "2", "3", "--run")
        assert unchecked.returncode and "no checks registered yet" in unchecked.stderr, unchecked.stderr
        one = go("1", "2", "3")
        assert one.returncode == 0 and "merge main up into #2's branch" in one.stdout, one.stdout + one.stderr
        st = load()
        assert st["prs"]["1"]["state"] == "MERGED" and st["prs"]["2"]["base"] == "main" and gone("b1"), st
        early = go("1", "2", "3")  # the agent has not merged main up yet
        assert early.returncode and "does not hold main" in early.stderr, early.stderr
        merge_up("b2"); refresh("2")
        two = go("1", "2", "3")  # b3 lacks only b2's merge-up commit: that is not a lost commit
        assert two.returncode == 0 and "merge main up into #3's branch" in two.stdout, two.stdout + two.stderr
        merge_up("b3"); refresh("3")
        three = go("1", "2", "3")
        assert three.returncode == 0 and "stack landed" in three.stdout, three.stdout + three.stderr
        assert set(git("ls-tree", "--name-only", "main", cwd=bare).split()) == {"a.txt", "one.txt", "two.txt", "three.txt"}
        assert gone("b2") and gone("b3") and "every PR in the stack is merged" in go("1", "2", "3").stdout
        os.rename(bare, bare + ".away")  # origin unreachable: a failed read is not "no branch"
        unreadable = go("1", "2", "3")
        os.rename(bare + ".away", bare)
        assert unreadable.returncode and "every PR" not in unreadable.stdout and "already gone" not in unreadable.stdout, unreadable.stdout

        # Guards: each stop leaves everything as it was.
        commit("b5", "main", "five.txt", "5\n"); commit("b6", "b5", "six.txt", "6\n"); commit("b7", "b6", "seven.txt", "7\n")
        st = load(); st["prs"].update({"5": add("main", "b5", "five.txt"), "6": add("b5", "b6", "six.txt"),
                                       "7": add("b6", "b7", "seven.txt")}); save(st)
        skip = go("5", "7")
        assert skip.returncode and "#6 also targets b5" in skip.stderr, skip.stderr
        for key, value, words, flags in (("fork", True, "comes from a fork", ()), ("queue", True, "is not merged", ()),
                                         ("blocked", True, "base branch policy prohibits", ()),
                                         ("checks", [{"name": "ci", "status": "IN_PROGRESS"}], "checks still running", ("--run",)),
                                         ("checks", [{"context": "ci", "state": "FAILURE"}], "failed checks", ("--run",)),
                                         ("checks", [{"name": "ci", "status": "COMPLETED", "conclusion": "STALE"}], "failed checks", ("--run",))):
            st = load(); st["prs"]["5"][key] = value; save(st)
            stop = land("5", "6", *(flags or ("--run", "--allow-no-checks")))
            assert stop.returncode and words in stop.stderr, (key, stop.stderr)
            st = load()
            assert st["prs"]["5"]["state"] == "OPEN" and st["prs"]["6"]["base"] == "b5" and not gone("b5"), (key, "a stop changed something")
            st["prs"]["5"].pop(key); save(st)
        st = load(); st["prs"]["5"]["push_before_merge"] = True; save(st)
        raced = go("5", "6")
        assert raced.returncode and "Head branch was modified" in raced.stderr and load()["prs"]["5"]["state"] == "OPEN", raced.stderr
        refresh("5")
        st = load(); st["repo"] = "someone/else"; save(st)
        other = go("5", "6")
        assert other.returncode and "gh talks to someone/else" in other.stderr, other.stderr
        st = load(); st["repo"] = os.path.basename(tmp) + "/origin"; save(st)
        # A queue merges #5 later; the next run finishes its landing (retarget, delete) and says what comes next.
        # An open PR from a fork whose branch is also called b5 is not ours and does not block the delete.
        st = load(); st["prs"]["99"] = dict(state="OPEN", base="main", head="b5", files=["x"], body="", fork=True); save(st)
        subprocess.run([gh, "pr", "merge", "5", "--squash"], env=env, check=True)
        assert "then stop" in land("5", "6", "7").stdout, "the plan should stop after finishing"
        resumed = go("5", "6", "7")
        assert resumed.returncode == 0 and "b5 deleted" in resumed.stdout and "merge main up into #6's branch" in resumed.stdout, resumed.stdout + resumed.stderr
        assert load()["prs"]["6"]["base"] == "main" and gone("b5")
        # A PR merged mid-stack (into its own base, by hand): the one above goes onto that base, not main.
        commit("b30", "main", "t30.txt", "30\n"); commit("b31", "b30", "t31.txt", "31\n"); commit("b32", "b31", "t32.txt", "32\n")
        st = load(); st["prs"].update({"30": add("main", "b30", "t30.txt"), "31": add("b30", "b31", "t31.txt"),
                                       "32": add("b31", "b32", "t32.txt")}); save(st)
        subprocess.run([gh, "pr", "merge", "31", "--squash"], env=env, check=True)
        middle = go("30", "31", "32")
        assert middle.returncode == 0 and "b31 deleted" in middle.stdout and "run this again to land #30" in middle.stdout, middle.stdout + middle.stderr
        st = load()
        assert st["prs"]["32"]["base"] == "b30" and st["prs"]["30"]["base"] == "main", st["prs"]
        # A merged branch that moved, or that an open PR still uses, is never deleted.
        commit("b20", "main", "twenty.txt", "20\n")
        st = load(); st["prs"]["20"] = add("main", "b20", "twenty.txt"); save(st)
        subprocess.run([gh, "pr", "merge", "20", "--squash"], env=env, check=True)
        commit("b20", "b20", "twenty.txt", "20, later\n")
        moved = go("20")
        assert moved.returncode and "b20 moved after #20 merged" in moved.stderr and not gone("b20"), moved.stderr
        commit("b21", "main", "x.txt", "x\n"); commit("b22", "b21", "y.txt", "y\n")
        st = load(); st["prs"].update({"21": add("main", "b21", "x.txt"), "22": add("b21", "b22", "y.txt")}); save(st)
        subprocess.run([gh, "pr", "merge", "21", "--squash"], env=env, check=True)
        used = go("21")  # #22 still targets b21, and the stack given leaves it out
        assert used.returncode and "#22 still uses b21" in used.stderr and not gone("b21"), used.stderr
        # Two PRs that are not a stack; a fix below never merged up; a branch behind main.
        commit("b10", "main", "ten.txt", "10\n"); commit("b11", "main", "eleven.txt", "11\n")
        st = load(); st["prs"].update({"10": add("main", "b10", "ten.txt"), "11": add("main", "b11", "eleven.txt")}); save(st)
        apart = go("10", "11")
        assert apart.returncode and "#11 is not based on #10's branch b10" in apart.stderr, apart.stderr
        commit("b8", "main", "eight.txt", "EIGHT\n"); commit("b9", "b8", "nine.txt", "9\n"); commit("b8", "b8", "eight.txt", "EIGHT-FIXED\n")
        st = load(); st["prs"].update({"8": add("main", "b8", "eight.txt"), "9": add("b8", "b9", "nine.txt")}); save(st)
        lost = go("8", "9")
        assert lost.returncode and "#9's branch lacks 1 commit(s) of #8's" in lost.stderr and load()["prs"]["8"]["state"] == "OPEN", lost.stderr
        commit("b14", "main", "fourteen.txt", "14\n")
        st = load(); st["prs"]["14"] = add("main", "b14", "fourteen.txt"); st["prs"]["14"]["body"] = body(head("b14")).replace("## Signal", "## Other"); save(st)
        gated = go("14")  # land-stack lands nothing check-pr refuses
        assert gated.returncode and "check-pr.py fails on #14" in gated.stderr and 'no "## Signal"' in gated.stderr, gated.stderr
        assert load()["prs"]["14"]["state"] == "OPEN"
        refresh("14"); commit("main", "main", "later.txt", "x\n")
        behind = go("14")
        assert behind.returncode and "does not hold main" in behind.stderr, behind.stderr


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
        assert "Sam" in texts["goal"] and "up to 5 at once" in texts["goal"], texts["goal"]
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
        for needle, rule in (("§VIII.4", "is asked, not ruled"), ("progress.py", "come from the clock"), ("after a compaction", "re-read after a compaction")):
            assert rule in check(goal=texts["goal"].replace(needle, "x")), needle
        assert "write-goal sequence" in check(goal=texts["goal"].replace("nothing skipped", "mostly"))
        assert "In flight" in check(progress=texts["progress"].replace("## In flight", "## Later"))
        pp = texts["progress"]
        flight = lambda item: check(progress=pp.replace("- Nothing.", item))
        assert "does not end with its time left" in flight("- Plan 1 step 1, sonnet, wt-1")
        assert "does not end with its time left" in flight("- Plan 1 step 1, branch feat/2d-chart, sonnet")
        for ok_item in ("- Plan 1 step 1, sonnet, wt-1, 40m", "- None.", "- nothing running", "- step, 1d 5h", "- step, 1h20m",
                        "- step, 90 min.", "- step, 2 hours", "- step, 45 minutes", "- step, 30 mins", "- step, 1 day"):
            assert "does not end with its time left" not in flight(ok_item), ok_item
        assert "does not end with its time left" in check(progress=pp.replace("## In flight", "## In flight (1)").replace("- Nothing.", "- step, sonnet"))
        assert "row has no time left" in check(progress=pp.replace("| 2h 30m |", "| soon |"))
        assert "row has no time left" in check(progress=pp.replace("| filled | nothing | 2h 30m |", "| deploy the 2d view | nothing | soon |"))
        assert "row has no time left" not in check(progress=pp.replace("| --- | --- | --- |", "| :--- | --- | ---: |"))
        assert "row has no time left" not in check(progress=pp.replace("| filled | nothing | 2h 30m |", "| filled | nothing | 2h 30m |\n\n```\n| a | b |\n```"))
        second = pp.replace("| filled | nothing | 2h 30m |", "| filled | nothing | 2h 30m |\n\nLater:\n\n| Step | Time left |\n| --- | --- |\n| report | 1h |")
        assert "row has no time left" not in check(progress=second), check(progress=second)
        assert '"## What is left"' in check(progress=re.sub(r"## What is left.*?(?=## Steps)", "", pp, flags=re.S))
        old_now = re.sub(r"\*\*Now \([^)]*\)", "**Now (2026-01-01 09:00 UTC)", pp)
        assert "older than the last Log entry" in check(progress=old_now + "\n- 2026-01-01 10:00 UTC: later\n")
        assert "ahead of the clock: 2999-01-01 09:00 UTC" in check(progress=pp + "\n- 2999-01-01 09:00 UTC: done\n")
        assert "ahead of the clock" not in check(progress=pp.replace("- Nothing yet.", "- Deploy: the freeze lifts 2999-01-01 09:00 UTC"))
        assert ".superpowers/ is not git-ignored" in (os.makedirs(f"{repo}/.superpowers", exist_ok=True) or check())
        with open(f"{repo}/.gitignore", "a") as f:
            f.write(".superpowers/\n")
        assert ".superpowers/" not in check()
        fixed = pp.replace("| --- | --- | --- |\n\n## Rulings", "| --- | --- | --- |\n| 09:00 | one question at a time | later |\n\n## Rulings")
        assert "owner correction with no kit change" in check(progress=fixed), check(progress=fixed)
        assert "owner correction with no kit change" not in check(progress=fixed.replace("| later |", "| abc1234 |"))
        assert "owner correction with no kit change" not in check(progress=fixed.replace("| later |", "| #12 |"))
        assert "owner correction with no kit change" not in check(progress=fixed.replace("| later |", "| ABC-123 |"))
        assert "owner correction with no kit change" in check(progress=fixed.replace("| later |", "| ticket to follow |"))
        assert "owner correction with no kit change" in check(progress=fixed.replace("| later |", "| UTF-8 |"))
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
            "## Review\n\n- Simplify: 2 lines removed\n- Self-review, by a fresh opus context: clean\n- Security review: no input, auth or data exposure change; clean\n- Constitution: cross-checked, clean\n"
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
        assert "names no model" in pr(good.replace("by a fresh opus context", "by a fresh context"))
        assert "needs a threshold and a window" in pr(good.replace("exports.error above 1% in 10 min", "exports.error goes up"))
        assert "needs a threshold and a window" in pr(good.replace("exports.ok above 99% for 1 h", "exports.ok above 99%"))
        assert "needs a threshold and a window" not in pr(good.replace("exports.error above 1% in 10 min", "0 error logs within 15 minutes"))
        for ok_line in ("error rate under 1% over the first hour", "0 5xx within 15 minutes of the deploy", "p95 under 300 ms for the next 2 hours",
                        "no more than 3 errors in any 5-minute window", "error rate under 1% for one hour", "error rate under 1%\n  over the first day",
                        "0 errors for five minutes", "5xx under 1% for 10 consecutive minutes", "p99 < 200ms, 1h window", "5 errors / 10 min",
                        "error rate above 1% in 10 min", "0 errors over the next 24 hours", "under 1% in the first 30 minutes",
                        "below 1% errors, 1-hour rolling window", "5 errors in 5 minutes", "0 errors in the 30 min after the deploy"):
            assert "needs a threshold and a window" not in pr(good.replace("exports.error above 1% in 10 min", ok_line)), ok_line
        borrowed = good.replace("- Failure: exports.error above 1% in 10 min", "- Failure: exports.error goes up\n- Note: within 15 minutes")
        assert "Failure line needs a threshold and a window" in pr(borrowed), pr(borrowed)  # no window from the next bullet
        for bad_line in ("any 500 after deploy", "HTTP 200 per request", "errors go down", "p99 latency over 2 s",
                         "checkout responds in 1 s", "p99 for the API under 2s", "errors go down for an hour",
                         "99% of requests in 1 s", "more than 1% of requests over 2 s", "page loads in 2 s for 95% of users", "build over 20 minutes",
                         "p99 latency over the 2 s SLO", "99% of requests in the 1 s bucket", "checkout p99 in the 3 s budget"):
            assert "needs a threshold and a window" in pr(good.replace("exports.error above 1% in 10 min", bad_line)), bad_line
        assert "names no model" in pr(good.replace("- Self-review, by a fresh opus context", "- Self-reviewed by a fresh context"))
        stale = __import__("importlib").import_module("check-pr").stale
        head = "0123456789abcdef0123456789abcdef01234567"
        assert "names no commit" in stale(good, head)[0]
        assert stale(good.replace("12 passed", "12 passed on 0123456789"), head) == []
        assert "not the PR head 012345678" in stale(good.replace("12 passed", "12 passed on fedcba987"), head)[0]
        assert "a security review" in pr(good.replace("- Security review: no input, auth or data exposure change; clean\n", ""))
        for leak in ("AKIA" + "ABCDEFGHIJKLMNOP", "ghp_" + "a" * 36, "sk-ant-" + "api03-" + "b" * 30, "xoxb-" + "1234567890-abc",
                     "-----BEGIN " + "RSA PRIVATE KEY-----", "eyJ" + "a" * 12 + ".eyJ" + "b" * 12 + "." + "c" * 12,
                     "Authorization: Bearer " + "d" * 30, "password=" + "hunter2hunter2"):
            assert "looks like a credential" in pr(good.replace("200 a,b", "200 a,b\n" + leak)), leak
        # Built from parts so this file never holds a credential-shaped string whole.
        for leak in ("AWS_SECRET_ACCESS_KEY=" + "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEZ", "AIza" + "S" * 35, "sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc",
                     "npm_" + "a1" * 18, "postgres://app:" + "s3cretP4ss@db.internal:5432/app", "-----BEGIN PGP " + "PRIVATE KEY BLOCK-----",
                     "sk-svcacct-" + "abc_DEF-1234567890abcdefgh", "glpat-" + "abcdefghij1234567890", "xapp-" + "1-A0123-abcdef",
                     "hooks.slack.com/services/" + "T0001/B0002/abcdef", "Authorization: Basic " + "YWRtaW46c2VjcmV0MTIz", "curl -u admin:" + "SuperSecret123 x",
                     '"token": "' + "abcdef0123456789abcdef" + '"', "password=" + "xK9mPq2vL8nR4tWz", "Authorization: Bearer " + "xyzABC123def456ghi789jkl",
                     "password=" + "redactedButReal12345", "password=" + "hunter2abc", "password=" + "Tr0ub4dor&3-horse!",
                     "https://s.blob.core.windows.net/c/f?sv=2020&" + "sig=abcdefghijklmnopqrstuv%3D",
                     "https://b.s3.amazonaws.com/k?X-Amz-Date=20260101&" + "X-Amz-Signature=" + "a1" * 32,
                     "token=x1" + "a" * 70 + "example"):  # past the placeholder's 64-character look, a real value
            assert "looks like a credential" in pr(good.replace("200 a,b", "200 a,b\n" + leak)), leak
        echo = pr(good.replace("```\n$ curl", "![s](http://admin:" + "s3cretP4ss9@host/a.png?sig=abc)\n\n```\n$ curl"))
        assert "s3cret" not in echo and "sig=" not in echo and "(not an https URL): http://host/a.png" in echo, echo
        import time
        scan = __import__("importlib").import_module("check-pr").SECRET
        for adversarial in ("pwd=" * 250_000, "a." * 500_000, "AKIA" * 250_000 + "EXAMPLE", "a" * 1_000_000 + "://",
                            "eyJ" * 333_333, "token=<" * 142_857, " -u a:<" * 142_857):
            began = time.time(); list(scan.finditer(adversarial))  # finditer, as check-pr does: every start, not the first match
            assert time.time() - began < 3, f"the scan is slow on {adversarial[:8]}..."
        images = __import__("importlib").import_module("check-pr").images
        for adversarial in ("<img " * 100_000, "![" * 200_000):
            began = time.time(); images(adversarial)
            assert time.time() - began < 3, f"the image scan is slow on {adversarial[:6]}..."
        leaked = pr(good.replace("200 a,b", "200 a,b\npassword=" + "hunter2hunter2"))
        assert "hunter2" not in leaked and re.search(r"line \d+ carries", leaked), leaked  # never echo the secret
        for safe in ("Authorization: Bearer <token>", "Authorization: Bearer " + "x" * 30, "Authorization: Bearer ***",
                     "token=<redacted>", "password: " + "x" * 16, "api_key=" + "." * 20,
                     "token=dummy-token-for-tests", "api_key=YOUR_API_KEY_HERE", "secret: app-db-credentials-prod",
                     "token = make_test_token()", "token = build_token_v2()", "token: refresh_rejects_expired_tokens PASSED", "AKIA" + "IOSFODNN7EXAMPLE",
                     "0123456789abcdef0123456789abcdef01234567", "123e4567-e89b-12d3-a456-426614174000", "${{ secrets.TOKEN }}",
                     "password=$DB_PASSWORD", "token=example-" + "abc123def456"):
            assert "looks like a credential" not in pr(good.replace("200 a,b", "200 a,b\n" + safe)), safe
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
        support = good.replace("### UC1 An admin exports a report and gets a CSV", "### Supports UC1 A fake export service")
        assert problems(support, [], {}, ["tests"], {"UC1": "ui"}) == [], problems(support, [], {}, ["tests"], {"UC1": "ui"})
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
        unapproved = texts["progress"]
        assert check().strip().endswith("ok"), check()
        assert "never approved" in check(progress=unapproved.replace("- [ ] Plan 1 step 1", "- [x] Plan 1 step 1"))
        p = unapproved.replace("## Waiting on", 'Approved by Sam 2026-01-01 08:00 UTC: "yes, run it"\n\n## Waiting on', 1)
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
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good.replace("### UC1", "### Supports UC1"))
        assert 'has no "### UC1": Plan 1 step 1 proves it' in check(progress=ticked)
        wrapped = m.replace(" Proves UC1. Model: sonnet, a specified function.", " Model: sonnet, a specified function.\n   Proves UC1.")
        assert 'has no "### UC1": Plan 1 step 1 proves it' in check(master=wrapped, progress=ticked), check(master=wrapped, progress=ticked)
        enables = m.replace("Proves UC1.", "Proves UC1. Supports UC2 through the fake.").replace("| UC1 |", "| UC2 | x | cli |\n| UC1 |")
        assert "UC2 is proven by no plan step" in check(master=enables, progress=ticked)
        assert 'has no "### UC2"' not in check(master=enables, progress=ticked)  # "Supports" is not part of the Proves sentence
        comma = enables.replace("Proves UC1. Supports UC2 through the fake.", "Proves UC1, supports UC2 through the fake.")
        assert "UC2 is proven by no plan step" in check(master=comma, progress=ticked)
        oxford = enables.replace("Proves UC1. Supports UC2 through the fake.", "Proves UC1, UC2, and UC3.").replace("| UC1 |", "| UC3 | x | cli |\n| UC1 |")
        assert "UC3 is proven by no plan step" not in check(master=oxford, progress=ticked)
        both = enables.replace("Proves UC1. Supports UC2 through the fake.", "Proves UC1 and UC2.")
        assert "UC2 is proven by no plan step" not in check(master=both, progress=ticked)
        assert 'has no "### UC2": Plan 1 step 1 proves it' in check(master=both, progress=ticked)
        with open(f"{ev}/1.1.md", "w") as f:
            f.write(good)
        assert "UC1 is proven by no plan step" in check(master=m.replace("Proves UC1.", ""))
        asks = lambda row: check(master=m.replace("| A1 | filled | UC1 |", row))
        assert "A1 maps to no use case" in asks("| A1 | filled | later |")
        assert "A1 maps to no use case" not in asks("| A1 | filled | dropped by Sam 2026-01-01 |")
        assert "A1 maps to no use case" in asks("| A1 | filled | dropped by the agent |")
        assert "A2 maps to no use case" in asks("| A1 | filled | UC1 |\n| A2 | make UC9 faster | |")
        assert "A1 names UC77, which the Use cases table does not define" in asks("| A1 | filled | UC77 |")
        assert "Asks row is not" in asks("| A1 | filled | UC1 |\n| A2 | x | later")
        assert "Asks row is not" in asks("| A1 | filled | UC1 |\nA2 | x | later |")
        assert '"## Asks" has no' in check(master=m.replace("| A1 | filled | UC1 |", ""))
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
        # A kit fix made on a feature branch is caught, so it ships off main instead.
        git = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)
        git("add", "-A"); git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        git("update-ref", "refs/remotes/origin/main", "HEAD"); git("switch", "-qc", "state/t")
        assert "kit files changed" not in check()
        with open(f"{repo}/.claude/loopkit/goal.md", "a") as f:
            f.write("\n")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "kit edit")
        assert "kit files changed on state/t (.claude/loopkit/goal.md)" in check()
        assert "kit files changed" not in check(master=m + "\nTouches `.claude/loopkit/goal.md`.\n")
        assert "kit files changed" in check(master=m + "\nKeeps to .claude/loopkit/goal.md as written.\n")  # mentioned, not named
        git("switch", "-q", "-")
        # progress.py stamps from the clock; check-goal holds the live view to the Now line.
        check()  # every file back to its passing text
        prog = f"{base}-progress.md"
        os.chmod(prog, 0o644)
        read = lambda: open(prog).read()
        stamp = lambda *a: run("progress.py", "t", *a, cwd=repo)
        assert stamp("now", "plan 1 started").returncode == 0
        assert stamp("2026-01-01", "log", "plan 1 started").returncode == 0  # the date form
        body = read()
        assert re.search(r"^\*\*Now \(\d{4}-\d\d-\d\d \d\d:\d\d UTC\):\*\* plan 1 started$", body, re.M), body[:300]
        log = body.split("## Log", 1)[1]
        assert re.search(r"^- \d{4}-\d\d-\d\d \d\d:\d\d UTC: plan 1 started$", log, re.M)
        assert os.stat(prog).st_mode & 0o777 == 0o644, "the stamp changed the file's mode"
        for refused in (("view",), ("now", "two\nlines"), ("approve", "")):
            assert stamp(*refused).returncode != 0, refused
            assert read() == body, f"a refused stamp changed the progress file: {refused}"
        with open(prog, "w") as f:  # a two-line Now paragraph, and a section after the Log
            f.write(body.replace("plan 1 started\n\nTimes", "plan 1 started\nsecond line\n\nTimes", 1) + "\n## Notes\n\n- a note\n")
        stamp("now", "plan 2 started")
        stamp("log", "plan 2 started")
        body = read()
        assert "second line" not in body and "plan 2 started" in body.split("## Notes")[0].split("## Log")[1]
        with open(prog, "w") as f:
            f.write(re.sub(r"\*\*Now \([^)]*\)", "**Now (2026-01-01 09:00 UTC)", body, count=1))
        stamp("log", "plan 2 checked")
        body = read()
        now_t = re.search(r"\*\*Now \(([^)]*)\)", body).group(1)
        assert now_t == re.findall(r"^- (\S+ \S+ UTC): plan 2 checked$", body, re.M)[0], "log must move the Now time"
        assert "Pending" not in run("check-goal.py", "t", cwd=repo).stdout
        with open(prog, "w") as f:  # a heading and an approval right under the Now line survive a rewrite
            f.write(re.sub(r"(\*\*Now \([^\n]*)", lambda mm: mm.group(1) + '\nApproved by Sam 2026-01-01 08:00 UTC: "yes"', body, count=1))
        stamp("now", "plan 3 started")
        assert 'Approved by Sam 2026-01-01 08:00 UTC: "yes"' in read()
        with open(prog, "w") as f:
            f.write(body)
        assert "no progress file at" in stamp("2025-01-01", "now", "x").stderr
        assert stamp("approve", "   ").returncode != 0 and read() == body
        assert stamp("approve", '"yes"').returncode == 0 and re.search(r'^Approved by Sam \S+ \S+ UTC: "yes"$', read(), re.M)
        with open(prog, "w") as f:
            f.write(body.replace("**Now (", "**Now: (", 1))
        assert stamp("now", "x").returncode != 0 and "**Now: (" in read()
        with open(prog, "w") as f:
            f.write(body)
        with open(f"{repo}/.claude/loopkit.json", "w") as f:
            json.dump({"owner": "Sam", "runner": "make", "bypass": ["npx"], "assurance": ["tests", "lint"], "view": "Claude Doc"}, f)
        lag = run("check-goal.py", "t", cwd=repo)
        assert "Claude Doc lags" in lag.stdout, lag.stdout + lag.stderr
        stamp("view")
        assert "Claude Doc lags" not in run("check-goal.py", "t", cwd=repo).stdout
    # The kit is public: the skills never name the people who build or run it. Their names come from git config and
    # the commit authors at test time, so they are never written into the repo, not even here.
    names = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, cwd=HERE).stdout
    names += subprocess.run(["git", "log", "--format=%an"], capture_output=True, text=True, cwd=HERE).stdout
    me = {w for w in names.split() if w.isalpha()}
    skills = os.path.dirname(os.path.dirname(HERE))
    for root, _, files in os.walk(skills):
        for name in files:
            if name.endswith((".md", ".py", ".json")):
                with open(os.path.join(root, name)) as f:
                    text = f.read()
                for word in (w for w in me if len(w) > 2):
                    assert not re.search(rf"\b{re.escape(word)}\b", text, re.I), f"{name} names the kit's user ({word})"
    land_stack_test()
    print("goal kit ok")


if __name__ == "__main__":
    main()
