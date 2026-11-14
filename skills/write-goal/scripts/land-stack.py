"""Land a stack of PRs from the bottom, so no PR is closed and no change is lost.

    python3 land-stack.py <PR> [<PR> ...] [--method squash|rebase] [--allow-no-checks] [--run]

PRs are given bottom first, each based on the one before. Without --run it prints the plan and changes nothing.
With --run it does one step and stops, because merging main up into the next PR changes that PR's head and its
evidence must be read again there (check-pr.py fails stale assurance). Run it again after that; PRs already merged
are skipped, and a landing cut short (a merge queue, a failed push) is finished first.

Landing the lowest open PR:
  1. check: open; from this repo; `gh` and git's `origin` are the same repository; based on main, and main is in its
     head; every check complete and green (none registered fails unless --allow-no-checks); check-pr.py ok; no open PR
     but the next is based on its branch; the next PR is based on its branch and holds all of it (a fix made below and
     never merged up would otherwise be lost);
  2. merge it (squash by default; rebase keeps each commit's author) and confirm GitHub says MERGED (a merge queue only
     queues; then it stops, nothing else changed);
  3. finish: retarget the next PR to main, delete the branch, merge origin/main into the next PR's branch in a temporary
     worktree with a plain merge (any conflict stops it, nothing pushed), and push plainly: no rebase, no force-push.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = "number,state,baseRefName,headRefName,isCrossRepository,statusCheckRollup"
RED = ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE", "ERROR")


def run(*cmd: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def sh(*cmd: str, cwd: str | None = None) -> str:
    r = run(*cmd, cwd=cwd)
    if r.returncode:
        sys.exit(f"stopped: {' '.join(cmd)}\n{(r.stderr or r.stdout).strip()}")
    return r.stdout


def pr(n: str) -> dict:
    return json.loads(sh("gh", "pr", "view", n, "--json", FIELDS))


def contains(ancestor: str, ref: str) -> bool:
    return run("git", "merge-base", "--is-ancestor", ancestor, ref).returncode == 0


def same_repo() -> None:
    gh_repo = sh("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip().lower()
    origin = re.sub(r"\.git$", "", sh("git", "remote", "get-url", "origin").strip()).lower()
    if not origin.endswith("/" + gh_repo) and not origin.endswith(":" + gh_repo):
        sys.exit(f"stopped: gh talks to {gh_repo} but git's origin is {origin}: point them at the same repository")


def check(n: str, nxt: str, allow_no_checks: bool) -> dict:
    p = pr(n)
    if p["state"] != "OPEN":
        sys.exit(f"stopped: #{n} is {p['state'].lower()}")
    if p["isCrossRepository"]:
        sys.exit(f"stopped: #{n} comes from a fork; land it by hand")
    if p["baseRefName"] != "main":
        sys.exit(f"stopped: #{n} targets {p['baseRefName']}, not main: land the PR below it first")
    checks = p["statusCheckRollup"] or []
    if not checks and not allow_no_checks:
        sys.exit(f"stopped: #{n} has no checks registered yet; wait for CI, or pass --allow-no-checks for a repo without CI")
    failed = [c.get("name") or c.get("context") for c in checks
              if (c.get("conclusion") or "").upper() in RED or (c.get("state") or "").upper() in RED]
    if failed:
        sys.exit(f"stopped: #{n} has failed checks: {', '.join(map(str, failed))}")
    pending = [c.get("name") or c.get("context") for c in checks
               if ("status" in c and (c.get("status") or "").upper() != "COMPLETED")
               or (c.get("state") or "").upper() in ("PENDING", "EXPECTED")]
    if pending:
        sys.exit(f"stopped: #{n} has checks still running: {', '.join(map(str, pending))}")
    sh("git", "fetch", "-q", "origin")
    if not contains("origin/main", f"origin/{p['headRefName']}"):
        sys.exit(f"stopped: #{n}'s branch does not hold main: merge main up into it, re-run its assurance, then land it")
    r = run(sys.executable, os.path.join(HERE, "check-pr.py"), n)
    if r.returncode:
        sys.exit(f"stopped: check-pr.py fails on #{n}:\n{(r.stdout + r.stderr).strip()}")
    stacked = json.loads(sh("gh", "pr", "list", "--base", p["headRefName"], "--state", "open", "--json", "number"))
    others = sorted(str(q["number"]) for q in stacked if str(q["number"]) != nxt)
    if others:
        sys.exit(f"stopped: #{', #'.join(others)} also target{'s' if len(others) == 1 else ''} {p['headRefName']}: "
                 "deleting it would close them; put them in the stack, or retarget them first")
    if nxt:
        q = pr(nxt)
        if q["baseRefName"] != p["headRefName"]:
            sys.exit(f"stopped: #{nxt} is not based on #{n}'s branch {p['headRefName']}: give the stack in order")
        if not contains(f"origin/{p['headRefName']}", f"origin/{q['headRefName']}"):
            sys.exit(f"stopped: #{nxt}'s branch lacks commits of #{n}'s ({p['headRefName']}): merge {p['headRefName']} up into "
                     f"{q['headRefName']} first, or a fix made below is lost")
    return p


def finish(branch: str, nxt: str) -> None:
    """After `branch`'s PR merged: retarget the next PR, delete the branch, merge main up into the next branch."""
    if nxt and pr(nxt)["baseRefName"] != "main":
        sh("gh", "pr", "edit", nxt, "--base", "main")  # before the branch goes: deleting a PR's base closes it
    gone = run("git", "push", "-q", "origin", "--delete", branch)
    if gone.returncode and "remote ref does not exist" not in gone.stderr:  # the repo may delete merged branches itself
        sys.exit(f"stopped: deleting {branch} failed; rerun to finish:\n{gone.stderr.strip()}")
    print(f"{branch} deleted")
    if not nxt:
        print("stack landed")
        return
    nb = pr(nxt)["headRefName"]
    sh("git", "fetch", "-q", "origin")
    if contains("origin/main", f"origin/{nb}"):
        print(f"#{nxt} already holds main")
        return
    with tempfile.TemporaryDirectory() as tmp:
        wt = os.path.join(tmp, "wt")
        sh("git", "worktree", "add", "-q", "--detach", wt, f"origin/{nb}")  # detached: it may be checked out elsewhere
        try:
            if run("git", "merge", "-q", "--no-edit", "origin/main", cwd=wt).returncode:
                conflicted = run("git", "diff", "--name-only", "--diff-filter=U", cwd=wt).stdout.split()
                sys.exit(f"stopped: merging main into {nb} conflicts in {conflicted[:3]}: resolve it by hand, push, then rerun; "
                         "nothing was pushed")
            sh("git", "push", "-q", "origin", f"HEAD:{nb}", cwd=wt)
            head = sh("git", "rev-parse", "HEAD", cwd=wt).strip()
        finally:
            run("git", "worktree", "remove", "--force", wt)
    print(f"#{nxt} now holds main, at {head[:9]}: re-run its assurance on that commit, update its PR body, then run this again")


def main() -> None:
    args = sys.argv[1:]
    go, allow_no_checks = "--run" in args, "--allow-no-checks" in args
    method = "squash"
    if "--method" in args:
        i = args.index("--method")
        method = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    args = [a for a in args if a not in ("--run", "--allow-no-checks")]
    if not args or method not in ("squash", "rebase") or not all(a.isdigit() for a in args):
        sys.exit(__doc__)
    states = {n: pr(n) for n in args}
    todo = [n for n in args if states[n]["state"] != "MERGED"]
    closed = next((n for n in todo if states[n]["state"] != "OPEN"), None)
    if closed:
        sys.exit(f"stopped: #{closed} is closed, not merged")
    nxt = todo[1] if len(todo) > 1 else ""
    # A landing cut short: the PR before the first open one merged, but its branch, the retarget or the merge-up remain.
    done = [n for n in args if states[n]["state"] == "MERGED"]
    if done and go:
        last, first = states[done[-1]]["headRefName"], (todo[0] if todo else "")
        sh("git", "fetch", "-q", "--prune", "origin")
        unfinished = run("git", "rev-parse", "--verify", "-q", f"origin/{last}").returncode == 0 or bool(
            first and (states[first]["baseRefName"] != "main"
                       or not contains("origin/main", f"origin/{states[first]['headRefName']}")))
        if unfinished:
            same_repo()
            print(f"#{done[-1]} merged earlier; finishing its landing")
            finish(last, first)
            return
    if not todo:
        print("every PR in the stack is merged")
        return
    n = todo[0]
    if not go:
        print(f"- check #{n}: open, from this repo, based on main and holding it, checks green, check-pr ok, "
              f"nothing else stacked on it{f', and #{nxt} holds all of it' if nxt else ''}")
        print(f"- merge #{n} (--{method}) and confirm it is MERGED")
        if nxt:
            print(f"- retarget #{nxt} to main before that branch goes, delete the branch")
            print(f"- merge origin/main into #{nxt}'s branch (any conflict stops it), push; then re-run #{nxt}'s assurance "
                  "on its new head, update its PR body, and run this again")
        else:
            print(f"- delete #{n}'s branch")
        print("plan only; add --run to land it")
        return
    same_repo()
    p = check(n, nxt, allow_no_checks)
    merged = run("gh", "pr", "merge", n, f"--{method}")
    if pr(n)["state"] != "MERGED":
        sys.exit(f"stopped: #{n} is not merged ({(merged.stderr or 'queued').strip()[:200]}): nothing else changed; "
                 "rerun once it merges")
    print(f"#{n} landed ({method})")
    finish(p["headRefName"], nxt)


if __name__ == "__main__":
    main()
