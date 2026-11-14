"""Check that a PR body carries its own evidence and signal.

    python3 check-pr.py <PR number | body file>

Fails (exit 1) when the body:
  has no "## Evidence" section, or one with no command output (a fenced block) and no image;
  shows an image that is not an https URL (a local or relative path renders for nobody);
  changes a file matching the repo's ui_paths and shows no image in Evidence;
  has no "## Signal" section, or an empty one.
Signal names the metric, log line or alert that shows the change working after deploy, with its threshold,
or says "not-applicable" and why. A PR number reads the body and changed files with `gh`; a file reads the body only.
Settings: .claude/loopkit.json (see the write-goal skill).
"""

import json
import os
import re
import subprocess
import sys

import config

IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)|<img[^>]*\ssrc=[\"']([^\"']+)", re.I)


def section(body: str, name: str) -> str:
    m = re.search(rf"^## {name}\b[^\n]*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    return m.group(1).strip() if m else ""


def problems(body: str, files: list[str], ui_paths: list[str]) -> list[str]:
    out = []
    evidence, signal = section(body, "Evidence"), section(body, "Signal")
    images = [a or b for a, b in IMAGE.findall(evidence)]
    if not evidence:
        out.append('no "## Evidence" section: each claim\'s command and output, a screenshot per UI change')
    elif "```" not in evidence and not images:
        out.append("Evidence has no command output (a fenced block) and no image; a link alone is not evidence")
    out += [f"image no reviewer can open (not an https URL): {src}" for src in images if not src.startswith("https://")]
    ui = [f for f in files if any(re.search(p, f) for p in ui_paths)]
    if ui and not images:
        out.append(f"changes UI ({ui[0]}{' and more' if len(ui) > 1 else ''}) but Evidence shows no screenshot")
    if not signal:
        out.append('no "## Signal" section: the metric, log line or alert that shows it working, or not-applicable and why')
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
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
    fails = problems(body, files, cfg["ui_paths"])
    for f in fails:
        print(f"FAIL {f}")
    print("ok" if not fails else f"{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
