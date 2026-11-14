"""Scaffold a goal's three files from the templates.

    python3 new-goal.py --slug S --title T [--date D]

Writes <plans_dir>/<date>-<slug>-goal.md, -master.md and -progress.md, refusing to overwrite any file
that exists. Settings come from .claude/loopkit.json; templates from .claude/loopkit/ when the repo
has its own, else from this skill. Every per-goal blank reads {{FILL: ...}}; check-goal.py fails
until none is left.
"""

import argparse
import datetime
import os
import re
import sys

import config


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--slug", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--date", default=datetime.date.today().isoformat())
    a = p.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.slug):
        sys.exit(f"slug {a.slug!r}: lowercase letters, digits and hyphens only")
    try:
        datetime.date.fromisoformat(a.date)
    except ValueError:
        sys.exit(f"date {a.date!r}: use YYYY-MM-DD")

    config.to_top()
    cfg = config.load()
    plans = cfg["plans_dir"]
    subs = {
        "{{SLUG}}": a.slug,
        "{{TITLE}}": a.title,
        "{{DATE}}": a.date,
        "{{OWNER}}": cfg["owner"],
        "{{PLANS_DIR}}": plans,
        "{{ORCHESTRATOR}}": cfg["orchestrator"],
        "{{IMPLEMENTER}}": cfg["implementer"],
        "{{REVIEWER}}": cfg["reviewer"],
        "{{MAX_PARALLEL}}": str(cfg["max_parallel"]),
        "{{RUNNER}}": cfg["runner"],
        "{{ASSURANCE}}": ", ".join(cfg["assurance"]),
    }
    targets = {f"{plans}/{a.date}-{a.slug}-{k}.md": k for k in ("goal", "master", "progress")}
    clash = [t for t in targets if os.path.exists(t)]
    if clash:
        sys.exit("Already there, nothing written: " + ", ".join(clash))

    bodies = {}
    for dest, kind in targets.items():
        src = config.template(kind, cfg)
        with open(src) as f:
            body = f.read()
        if "{{PROJECT:" in body:
            sys.exit(f"{src} still has {{{{PROJECT: ...}}}} blanks; run the loopkit adopt skill first")
        if "{{RUNNER}}" in body and not cfg["runner"]:
            sys.exit(f'{src} names the runner; set "runner" in {config.FILE} or drop that sentence')
        for k, v in subs.items():
            body = body.replace(k, v)
        bodies[dest] = body

    os.makedirs(plans, exist_ok=True)
    for dest, body in bodies.items():
        with open(dest, "w") as f:
            f.write(body)
        print("wrote", dest)
    print(
        "\nNext (write-goal skill): measure the baselines, fill every {{FILL: ...}}, then run"
        f" check-goal.py {a.slug}"
    )


if __name__ == "__main__":
    main()
