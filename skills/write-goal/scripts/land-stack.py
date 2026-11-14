"""Land a stack of PRs from the bottom, the way the lessons say, so no PR is closed and no change is lost.

    python3 land-stack.py <PR> [<PR> ...] [--method squash|rebase] [--run]

PRs are given bottom first, each based on the one before. Without --run it prints the plan and changes nothing.
With --run it lands the lowest PR still open, then stops, because merging main up into the next PR changes that PR's
head and its evidence must be read again on the new head (check-pr.py fails stale assurance). Run it again after the
next PR's assurance is re-run; PRs already merged are skipped. For the PR it lands:
  1. check: open, from this repo (not a fork), based on main, every check complete and none failed, check-pr.py ok;
     the next PR is based on this one's branch, and no other open PR is;
  2. note the next PR's own files against this branch, before this branch goes;
  3. retarget the next PR to main (deleting a PR's base branch closes that PR);
  4. merge (squash by default; rebase keeps each commit's author), and confirm GitHub says MERGED, since a merge queue
     only queues it;
  5. delete its branch;
  6. merge origin/main into the next PR's branch in a temporary worktree, conflicting hunks taken from the next branch
     (it already holds the work below), and stop unless the result changes only the next PR's own files: a fix made
     below and never merged up would otherwise be reverted. Push plainly: no rebase, no force-push.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = "number,state,baseRefName,headRefName,isCrossRepository,statusCheckRollup"


def sh(*cmd: str, cwd: str | None = None) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        sys.exit(f"stopped: {' '.join(cmd)}\n{(r.stderr or r.stdout).strip()}")
    return r.stdout


def pr(n: str) -> dict:
    return json.loads(sh("gh", "pr", "view", n, "--json", FIELDS))


def check(n: str, nxt: str | None) -> dict:
    p = pr(n)
    if p["state"] != "OPEN":
        sys.exit(f"stopped: #{n} is {p['state'].lower()}")
    if p["isCrossRepository"]:
        sys.exit(f"stopped: #{n} comes from a fork; land it by hand")
    if p["baseRefName"] != "main":
        sys.exit(f"stopped: #{n} targets {p['baseRefName']}, not main: land the PR below it first")
    checks = p["statusCheckRollup"] or []
    failed = [c.get("name") or c.get("context") for c in checks
              if (c.get("conclusion") or "").upper() in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED")
              or (c.get("state") or "").upper() in ("FAILURE", "ERROR")]
    if failed:
        sys.exit(f"stopped: #{n} has failed checks: {', '.join(map(str, failed))}")
    pending = [c.get("name") or c.get("context") for c in checks
               if ("status" in c and (c.get("status") or "").upper() != "COMPLETED") or (c.get("state") or "").upper() in ("PENDING", "EXPECTED")]
    if pending:
        sys.exit(f"stopped: #{n} has checks still running: {', '.join(map(str, pending))}")
    r = subprocess.run([sys.executable, os.path.join(HERE, "check-pr.py"), n], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"stopped: check-pr.py fails on #{n}:\n{(r.stdout + r.stderr).strip()}")
    stacked = json.loads(sh("gh", "pr", "list", "--base", p["headRefName"], "--state", "open", "--json", "number"))
    others = sorted(str(q["number"]) for q in stacked if str(q["number"]) != nxt)
    if others:
        sys.exit(f"stopped: #{', #'.join(others)} also target{'s' if len(others) == 1 else ''} {p['headRefName']}: "
                 "deleting it would close them; put them in the stack, or retarget them first")
    if nxt and pr(nxt)["baseRefName"] != p["headRefName"]:
        sys.exit(f"stopped: #{nxt} is not based on #{n}'s branch {p['headRefName']}: give the stack in order")
    return p


def merge_up(branch: str, own: set[str]) -> str:
    """Merge origin/main into `branch`; returns the new head."""
    sh("git", "fetch", "-q", "origin")
    with tempfile.TemporaryDirectory() as tmp:
        wt = os.path.join(tmp, "wt")
        sh("git", "worktree", "add", "-q", "--detach", wt, f"origin/{branch}")  # detached: it may be checked out elsewhere
        try:
            # -X ours takes the branch's side only where hunks conflict; main's other changes to a file survive.
            sh("git", "merge", "-q", "--no-edit", "-X", "ours", "origin/main", cwd=wt)
            extra = set(sh("git", "diff", "--name-only", "origin/main", "HEAD", cwd=wt).split()) - own
            if extra:
                sys.exit(f"stopped: merged up, {branch} would also change {sorted(extra)[:3]} against main, which is not its own "
                         "change (a fix below never merged up?): resolve by hand; nothing was pushed")
            sh("git", "push", "-q", "origin", f"HEAD:{branch}", cwd=wt)
            return sh("git", "rev-parse", "HEAD", cwd=wt).strip()
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", wt], capture_output=True)


def main() -> None:
    args = sys.argv[1:]
    run = "--run" in args
    method = "squash"
    if "--method" in args:
        i = args.index("--method")
        method = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    args = [a for a in args if a != "--run"]
    if not args or method not in ("squash", "rebase") or not all(a.isdigit() for a in args):
        sys.exit(__doc__)
    states = {n: pr(n)["state"] for n in args}
    todo = [n for n in args if states[n] != "MERGED"]
    if not todo:
        print("every PR in the stack is merged")
        return
    if any(states[n] != "OPEN" for n in todo):
        sys.exit(f"stopped: #{next(n for n in todo if states[n] != 'OPEN')} is closed, not merged")
    n = todo[0]
    nxt = todo[1] if len(todo) > 1 else None
    if not run:
        print(f"- check #{n}: open, from this repo, based on main, checks complete and green, check-pr ok, nothing else stacked on it")
        if nxt:
            print(f"- note #{nxt}'s own files against #{n}'s branch, then retarget #{nxt} to main before that branch goes")
        print(f"- merge #{n} (--{method}), confirm it is MERGED, delete its branch")
        if nxt:
            print(f"- merge origin/main into #{nxt}'s branch (conflicting hunks from its side); stop unless it changes only its own files; push")
            print(f"- then rerun #{nxt}'s assurance on its new head, update its PR body, and run this again")
        print("plan only; add --run to land it")
        return
    p = check(n, nxt)
    branch = p["headRefName"]
    nb, own = "", set()
    if nxt:
        nb = pr(nxt)["headRefName"]
        sh("git", "fetch", "-q", "origin")
        own = set(sh("git", "diff", "--name-only", f"origin/{branch}...origin/{nb}").split())
        sh("gh", "pr", "edit", nxt, "--base", "main")
    sh("gh", "pr", "merge", n, f"--{method}")
    if pr(n)["state"] != "MERGED":
        sys.exit(f"stopped: #{n} is queued, not merged (a merge queue?): its branch is kept; rerun once it merges")
    gone = subprocess.run(["git", "push", "-q", "origin", "--delete", branch], capture_output=True, text=True)
    if gone.returncode and "remote ref does not exist" not in gone.stderr:  # the repo may delete merged branches itself
        sys.exit(f"stopped: #{n} merged, but deleting {branch} failed:\n{gone.stderr.strip()}")
    print(f"#{n} landed ({method}); its branch {branch} deleted")
    if nxt:
        head = merge_up(nb, own)
        print(f"#{nxt} holds main and only its own change, now at {head[:9]}: rerun its assurance on that commit, "
              f"update its PR body, then run land-stack.py again")
    else:
        print("stack landed")


if __name__ == "__main__":
    main()
