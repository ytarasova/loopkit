"""Land a stack of PRs from the bottom, the way the lessons say, so no PR is closed and no change is lost.

    python3 land-stack.py <PR> [<PR> ...] [--method squash|rebase] [--run]

PRs are given bottom first. Without --run it prints the plan and changes nothing. For each PR, in order:
  1. check: it is open, its base is main (the one below has landed), check-pr.py passes on it, no check failed;
  2. retarget the next PR to main BEFORE this one's branch goes (deleting a PR's base closes the PR);
  3. merge it (squash by default; rebase keeps each commit's author);
  4. delete its branch;
  5. merge origin/main into the next PR's branch in a temporary worktree, resolving any conflict to the next branch's side
     (it already holds the work below), check its diff against main holds only its own files, and push plainly
     (no rebase, no force-push).
It stops at the first step that fails and says where; a rerun starts from the first PR still open.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(*cmd: str, cwd: str | None = None) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        sys.exit(f"stopped: {' '.join(cmd)}\n{(r.stderr or r.stdout).strip()}")
    return r.stdout


def pr(n: str) -> dict:
    return json.loads(sh("gh", "pr", "view", n, "--json", "number,state,baseRefName,headRefName,statusCheckRollup,files"))


def plan(prs: list[str], method: str) -> list[tuple[str, list[str]]]:
    """[(what, command)] for the whole stack; a step whose command is [] is a check done in Python."""
    steps = []
    for i, n in enumerate(prs):
        nxt = prs[i + 1] if i + 1 < len(prs) else None
        steps.append((f"check #{n}: open, based on main, check-pr ok, no failed check", []))
        if nxt:
            steps.append((f"retarget #{nxt} to main before #{n}'s branch goes", ["gh", "pr", "edit", nxt, "--base", "main"]))
        steps.append((f"merge #{n}", ["gh", "pr", "merge", n, f"--{method}"]))
        steps.append((f"delete #{n}'s branch", []))
        if nxt:
            steps.append((f"merge origin/main into #{nxt}'s branch, conflicts to its side; its diff holds only its files; push", []))
    return steps


def check(n: str) -> None:
    p = pr(n)
    if p["state"] != "OPEN":
        sys.exit(f"stopped: #{n} is {p['state'].lower()}")
    if p["baseRefName"] != "main":
        sys.exit(f"stopped: #{n} targets {p['baseRefName']}, not main: land the PR below it first")
    failed = [c.get("name") for c in p["statusCheckRollup"] or [] if (c.get("conclusion") or "").upper() in ("FAILURE", "TIMED_OUT", "CANCELLED")]
    if failed:
        sys.exit(f"stopped: #{n} has failed checks: {', '.join(failed)}")
    r = subprocess.run([sys.executable, os.path.join(HERE, "check-pr.py"), n], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"stopped: check-pr.py fails on #{n}:\n{r.stdout.strip()}")


def merge_up(n: str) -> None:
    p = pr(n)
    branch, own = p["headRefName"], {f["path"] for f in p["files"]}
    sh("git", "fetch", "-q", "origin")
    with tempfile.TemporaryDirectory() as tmp:
        wt = os.path.join(tmp, "wt")
        sh("git", "worktree", "add", "-q", "--detach", wt, f"origin/{branch}")  # detached: the branch may be checked out elsewhere
        try:
            if subprocess.run(["git", "merge", "-q", "--no-edit", "origin/main"], cwd=wt, capture_output=True).returncode:
                conflicted = sh("git", "diff", "--name-only", "--diff-filter=U", cwd=wt).split()
                sh("git", "checkout", "--ours", "--", *conflicted, cwd=wt)
                sh("git", "add", "--", *conflicted, cwd=wt)
                sh("git", "commit", "-q", "--no-edit", cwd=wt)
            extra = set(sh("git", "diff", "--name-only", "origin/main", cwd=wt).split()) - own
            if extra:
                sys.exit(f"stopped: after the merge, #{n}'s diff against main also changes {sorted(extra)[:3]}: resolve by hand")
            sh("git", "push", "-q", "origin", f"HEAD:{branch}", cwd=wt)
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
    if not run:
        for what, cmd in plan(args, method):
            print(f"- {what}" + (f": {' '.join(cmd)}" if cmd else ""))
        print("plan only; add --run to land it")
        return
    for i, n in enumerate(args):
        nxt = args[i + 1] if i + 1 < len(args) else None
        check(n)
        branch = pr(n)["headRefName"]
        if nxt:
            sh("gh", "pr", "edit", nxt, "--base", "main")
        sh("gh", "pr", "merge", n, f"--{method}")
        sh("git", "push", "-q", "origin", "--delete", branch)
        print(f"#{n} landed ({method}); its branch {branch} deleted")
        if nxt:
            merge_up(nxt)
            print(f"#{nxt} now holds main and only its own change")
    print("stack landed")


if __name__ == "__main__":
    main()
