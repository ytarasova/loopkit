"""Land the lowest PR of a stack, so no PR is closed and no commit is lost.

    python3 land-stack.py <PR> [<PR> ...] [--method squash|rebase] [--allow-no-checks] [--run]

PRs are given bottom first, each based on the one before. Without --run it prints what it would do. With --run it lands
the lowest open PR and stops; it never merges main up into the next branch, because a conflict there needs judgment:
it prints the commands, and the agent runs them, re-runs that PR's assurance on its new head, then runs this again.

A PR of the stack that merged earlier (by this tool, a merge queue or by hand) is finished first, and the run stops
there: the PR above it is retargeted onto the merged PR's own base, then its branch is deleted, only while its tip is
still the merged commit and no open PR of this repo is based on it or comes from it. Otherwise the lowest open PR lands
only when:
  - it is open, from this repo, and `gh` and git's `origin` are the same repository;
  - it is based on main and holds main;
  - its checks are complete and the newest run of each is green (none registered stops it, unless --allow-no-checks);
  - check-pr.py passes on it (its assurance ran on its head);
  - no open PR but the next is based on its branch, and the next is based on its branch and holds every non-merge
    commit of it that main does not (a fix made below and never merged up would otherwise be lost).
It merges with --match-head-commit (a push after the checks cannot land unchecked) and confirms GitHub says MERGED (a
merge queue only queues; then it stops and nothing else changes).
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = "number,state,baseRefName,headRefName,headRefOid,isCrossRepository,statusCheckRollup"
RED = ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE", "ERROR")


def run(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def sh(*cmd: str) -> str:
    r = run(*cmd)
    if r.returncode:
        sys.exit(f"stopped: {' '.join(cmd)}\n{(r.stderr or r.stdout).strip()}")
    return r.stdout


def pr(n: str) -> dict:
    return json.loads(sh("gh", "pr", "view", n, "--json", FIELDS))


def open_prs(flag: str, branch: str) -> list[str]:
    found = json.loads(sh("gh", "pr", "list", flag, branch, "--state", "open", "--json", "number,isCrossRepository"))
    # --head matches the branch name in any fork too; only this repo's own branch is ours
    return [str(q["number"]) for q in found if flag != "--head" or not q.get("isCrossRepository")]


def same_repo() -> None:
    gh_repo = sh("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip().lower()
    origin = re.sub(r"\.git$", "", sh("git", "remote", "get-url", "origin").strip()).lower()
    if not origin.endswith("/" + gh_repo) and not origin.endswith(":" + gh_repo):
        shown = re.sub(r"//[^/@]*@", "//", origin)  # an origin URL may carry a token
        sys.exit(f"stopped: gh talks to {gh_repo} but git's origin is {shown}: point them at the same repository")


def merge_up_steps(nxt: dict) -> str:
    b, n = nxt["headRefName"], nxt["number"]
    return (f"merge main up into #{n}'s branch, resolve any conflict by hand, push plainly:\n"
            f"  git fetch origin && git switch {b} && git merge origin/main && git push origin {b}\n"
            f"then re-run #{n}'s assurance on the new head, update its PR body, and run this again")


def finish(merged: dict, nxt: dict | None) -> None:
    """A merged PR's branch: retarget the next PR off it, then delete it, but only while nothing else depends on it."""
    branch, oid = merged["headRefName"], merged["headRefOid"]
    if nxt and nxt["baseRefName"] == branch:  # onto the merged PR's own base: main, or a branch below that is still open
        sh("gh", "pr", "edit", str(nxt["number"]), "--base", merged["baseRefName"])  # before the branch goes: deleting a base closes its PRs
    tip = sh("git", "ls-remote", "origin", f"refs/heads/{branch}").split()  # the full ref: a bare name also matches a/<branch>
    if not tip:
        print(f"{branch} is already gone")
        return
    if tip[0] != oid:
        sys.exit(f"stopped: {branch} moved after #{merged['number']} merged (now {tip[0][:9]}, merged {oid[:9]}): "
                 "a later commit would be lost; land it in its own PR, then delete the branch by hand")
    users = sorted(set(open_prs("--base", branch) + open_prs("--head", branch)))
    if users:
        sys.exit(f"stopped: open PR #{', #'.join(users)} still use{'s' if len(users) == 1 else ''} {branch}: retarget or close them first")
    # The lease closes the race between the tip check above and this delete: a push in between makes it fail.
    sh("git", "push", "-q", f"--force-with-lease=refs/heads/{branch}:{oid}", "origin", "--delete", branch)
    print(f"{branch} deleted")


def latest(checks: list[dict]) -> list[dict]:
    """The newest run of each check: a run on a body edit or a re-run replaces the one it re-did on the same commit."""
    newest: dict = {}
    for c in checks:
        key = (c.get("workflowName") or "", c.get("name") or c.get("context"))
        if key not in newest or (c.get("startedAt") or "") >= (newest[key].get("startedAt") or ""):
            newest[key] = c
    return list(newest.values())


def check(p: dict, nxt: dict | None, allow_no_checks: bool) -> None:
    n = p["number"]
    if p["isCrossRepository"]:
        sys.exit(f"stopped: #{n} comes from a fork; land it by hand")
    if p["baseRefName"] != "main":
        sys.exit(f"stopped: #{n} targets {p['baseRefName']}, not main: land the PR below it first")
    checks = p["statusCheckRollup"] or []
    if not checks and not allow_no_checks:
        sys.exit(f"stopped: #{n} has no checks registered yet; wait for CI, or pass --allow-no-checks for a repo without CI")
    failed = [c.get("name") or c.get("context") for c in latest(checks)
              if (c.get("conclusion") or "").upper() in RED or (c.get("state") or "").upper() in RED]
    if failed:
        sys.exit(f"stopped: #{n} has failed checks: {', '.join(map(str, failed))}")
    pending = [c.get("name") or c.get("context") for c in checks
               if ("status" in c and (c.get("status") or "").upper() != "COMPLETED")
               or (c.get("state") or "").upper() in ("PENDING", "EXPECTED")]
    if pending:
        sys.exit(f"stopped: #{n} has checks still running: {', '.join(map(str, pending))}")
    sh("git", "fetch", "-q", "origin")
    if run("git", "merge-base", "--is-ancestor", "origin/main", p["headRefOid"]).returncode:
        sys.exit(f"stopped: #{n}'s branch does not hold main: merge main up into it, re-run its assurance, then land it")
    r = run(sys.executable, os.path.join(HERE, "check-pr.py"), str(n))
    if r.returncode:
        sys.exit(f"stopped: check-pr.py fails on #{n}:\n{(r.stdout + r.stderr).strip()}")
    others = [q for q in open_prs("--base", p["headRefName"]) if not nxt or q != str(nxt["number"])]
    if others:
        sys.exit(f"stopped: #{', #'.join(others)} also target{'s' if len(others) == 1 else ''} {p['headRefName']}: "
                 "landing would close them; put them in the stack, or retarget them first")
    if nxt:
        if nxt["baseRefName"] != p["headRefName"]:
            sys.exit(f"stopped: #{nxt['number']} is not based on #{n}'s branch {p['headRefName']}: give the stack in order")
        lost = sh("git", "rev-list", "--no-merges", p["headRefOid"], f"^{nxt['headRefOid']}", "^origin/main").split()
        if lost:
            sys.exit(f"stopped: #{nxt['number']}'s branch lacks {len(lost)} commit(s) of #{n}'s ({lost[0][:9]}): merge "
                     f"{p['headRefName']} up into {nxt['headRefName']} first, or a fix made below is lost")


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
    first = states[todo[0]] if todo else None
    nxt = states[todo[1]] if len(todo) > 1 else None
    def present(branch: str) -> bool:
        r = run("git", "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}")
        if r.returncode not in (0, 2):  # 2: no such branch; anything else is a failure, not an answer
            sys.exit(f"stopped: cannot read origin's branches:\n{r.stderr.strip()}")
        return r.returncode == 0
    leftover = [states[n] for n in args if states[n]["state"] == "MERGED" and present(states[n]["headRefName"])]
    above = lambda d: next((states[m] for m in args[args.index(str(d["number"])) + 1:] if states[m]["state"] == "OPEN"), None)
    if not go:
        for d in leftover:
            print(f"- finish #{d['number']}, merged earlier: retarget the PR above it, delete {d['headRefName']} if unmoved and unused")
        if leftover:
            print("then stop; run it again to land the next PR")
        elif first:
            holds = f", and #{nxt['number']} holds all of it" if nxt else ""
            print(f"- check #{first['number']}: open, from this repo, based on main and holding it, checks green, "
                  f"check-pr ok, nothing else stacked on it{holds}")
            print(f"- merge #{first['number']} (--{method}, matching its head), confirm MERGED, retarget the next PR, delete its branch")
            if nxt:
                print(f"- then {merge_up_steps(nxt)}")
        print("plan only; add --run to do it")
        return
    same_repo()
    if leftover:
        for d in leftover:  # bottom first; finish() retargets only a PR based on the merged branch
            finish(d, above(d))
        if first:
            now = pr(str(first["number"]))
            sh("git", "fetch", "-q", "origin")
            held = now["baseRefName"] == "main" and not run("git", "merge-base", "--is-ancestor", "origin/main", now["headRefOid"]).returncode
            print("next: run this again to land #%s" % now["number"] if held or now["baseRefName"] != "main" else f"next: {merge_up_steps(now)}")
        return
    if not first:
        print("every PR in the stack is merged")
        return
    check(first, nxt, allow_no_checks)
    merged = run("gh", "pr", "merge", str(first["number"]), f"--{method}", "--match-head-commit", first["headRefOid"])
    after = pr(str(first["number"]))
    if after["state"] != "MERGED":
        sys.exit(f"stopped: #{first['number']} is not merged ({(merged.stderr or 'queued').strip()[:200]}): nothing else "
                 "changed; rerun once it merges")
    print(f"#{first['number']} landed ({method})")
    finish(after, nxt)
    print(f"next: {merge_up_steps(nxt)}" if nxt else "stack landed")


if __name__ == "__main__":
    main()
