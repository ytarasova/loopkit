"""Check that a PR body carries its complete evidence: a part of the work is done only with all of it.

    python3 check-pr.py <PR number | body file>

Fails (exit 1) when the body is missing any of:
  ## Assurance  every technical check in the repo's `assurance` list (tests, coverage, lint, typecheck,
                violations, ...), each named with its command and the output it printed, in fenced blocks
  ## Evidence   told by use case: a "### UC<n> <who does what, and what they end up with>" per use case
                the change proves, each with its proof; the proof, by surface (the repo's `surfaces`,
                matched on the changed files):
                  ui       a screenshot per use-case step, at an https URL
                  service  a real exchange: the curl request and the response it got, in a fenced block
                  cli      the command run and its output ("$ " in a fenced block), or its picture
                any other  command output or a screenshot; a link alone is never evidence
  ## Signal     the success signal and the failure signal to watch during the rollout (metric, log
                line or alert, with its threshold), each on a line starting "Success" and "Failure";
                or "not-applicable" and why
  ## Review     simplify run, a self-review by a context that did not write it, and the constitution
                cross-checked, each named with its result
An image that is not an https URL fails: a local or relative path renders for nobody. An image inside
code is not shown, so it is not counted. A PR number reads the body and changed files with `gh`; a file
reads the body only, so the surface checks need the PR. Settings: .claude/loopkit.json (write-goal skill).
"""

import json
import os
import re
import subprocess
import sys

import config

IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)|<img[^>]*\ssrc=[\"']([^\"']+)", re.I)
FENCE = re.compile(r"```.*?```", re.S)
REVIEW = {"simplif": "simplify", "self-review": "a self-review", "constitution": "the constitution cross-check"}


def section(body: str, name: str) -> str:
    m = re.search(rf"^## {name}\b[^\n]*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else ""


def problems(body: str, files: list[str], surfaces: dict[str, list[str]], checks: list[str]) -> list[str]:
    out = []
    assurance, evidence, signal, review = (section(body, s) for s in ("Assurance", "Evidence", "Signal", "Review"))
    fences = FENCE.findall(evidence)
    shown = re.sub(r"`[^`\n]+`", "", FENCE.sub("", evidence))  # an image in code is not rendered
    images = [a or b for a, b in IMAGE.findall(shown)]

    if not FENCE.search(assurance):
        out.append('no "## Assurance" with each check\'s command and the output it printed in a fenced block')
    else:
        out += [f"Assurance does not show {name}" for name in checks if name.lower() not in assurance.lower()]
    if not evidence:
        out.append('no "## Evidence" section: the change working, shown for its surface')
    else:
        cases = re.split(r"^### (?=UC\d)", evidence, flags=re.M)[1:]
        if not cases:
            out.append('Evidence is not told by use case: no "### UC<n> <who does what>" heading')
        for case in cases:
            if not FENCE.search(case) and not IMAGE.search(re.sub(r"`[^`\n]+`", "", case)):
                out.append(f"{case.splitlines()[0].strip()}: no output and no image; a link alone is not evidence")
    out += [f"image no reviewer can open (not an https URL): {src}" for src in images if not src.startswith("https://")]
    hit = {kind for kind, pats in surfaces.items() for f in files if any(re.search(p, f) for p in pats)}
    if "ui" in hit and not images:
        out.append("changes UI but Evidence shows no screenshot of its use cases")
    if "service" in hit and not any(re.search(r"\bcurl\b", f) for f in fences):
        out.append("changes a service but Evidence shows no curl request and its response")
    if "cli" in hit and not images and not any(re.search(r"^\$ ", f.strip("`").lstrip(), re.M) for f in fences):
        out.append('changes the CLI but Evidence shows no run ("$ <command>" and its output, or its picture)')

    if not signal:
        out.append('no "## Signal" section: the success and failure signals for the rollout, or not-applicable and why')
    elif "not-applicable" not in signal.lower():
        for word in ("Success", "Failure"):
            if not re.search(rf"^\W*{word}", signal, re.M | re.I):
                out.append(f'Signal names no {word.lower()} signal (a line starting "{word}")')

    if not review:
        out.append('no "## Review" section: simplify, a self-review and the constitution cross-check')
    else:
        out += [f"Review does not name {what}" for key, what in REVIEW.items() if key not in review.lower()]
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = os.path.abspath(sys.argv[1]) if os.path.isfile(sys.argv[1]) else sys.argv[1]
    config.to_top()
    cfg = config.load()
    if os.path.isfile(arg):
        body, files = open(arg).read(), []
    else:
        r = subprocess.run(["gh", "pr", "view", arg, "--json", "body,files"], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr.strip())
        pr = json.loads(r.stdout)
        body, files = pr["body"], [f["path"] for f in pr["files"]]
    fails = problems(body, files, cfg["surfaces"], cfg["assurance"])
    for f in fails:
        print(f"FAIL {f}")
    print("ok" if not fails else f"{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
