"""The repo's loopkit settings: `.claude/loopkit.json` at the git top level, over these defaults."""

import glob
import json
import os
import re
import subprocess
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = ".claude/loopkit.json"
DEFAULTS = {
    "owner": "the owner",
    "plans_dir": "docs/plans",
    "intent_dir": "docs/specs",  # read by the intent skill
    "ends_at": "pr",  # "pr": the goal ends at an open PR; "production": it ends on gates read after deploy
    "orchestrator": "Opus 5.5",  # the default; the intent recommends Opus 5.5 or Fable 5.2 per goal (models.md)
    "max_parallel": 5,
    "runner": "",  # the one entry point for commands, e.g. "make", "rake", "./bin/dev"
    "bypass": [],  # backticked commands that skip the runner, e.g. ["npx", "bundle exec"]
    "goal_rules": {},  # {"text the goal must keep": "the rule it stands for"}
    "assurance": ["tests", "coverage", "lint", "typecheck", "violations", "security"],  # what every changeset shows run, by name
    "surfaces": {},  # {"ui"|"service"|"cli": [regex on changed files]}: what evidence a PR needs, check-pr.py
    "view": "",  # a live view the owner reads (e.g. "Claude Doc"); then the progress file stamps "<view> updated: <time>"
    "rollback_pattern": "",  # regex every plan's Rollback must match, e.g. "[a-z-]+:\\d+"
    "ban_em_dash": True,
}


def to_top() -> None:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    os.chdir(top.stdout.strip() or ".")


def load() -> dict:
    cfg = dict(DEFAULTS)
    if os.path.exists(FILE):
        try:
            with open(FILE) as f:
                cfg.update(json.load(f))
        except json.JSONDecodeError as e:
            sys.exit(f"{FILE} is not valid JSON: {e}")
    bad = []
    if cfg["ends_at"] not in ("pr", "production"):
        bad.append(f'ends_at is {cfg["ends_at"]!r}; use "pr" or "production"')
    if not isinstance(cfg["bypass"], list):
        bad.append("bypass must be a list of commands")
    if not isinstance(cfg["assurance"], list):
        bad.append("assurance must be a list of check names")
    if not isinstance(cfg["surfaces"], dict) or set(cfg["surfaces"]) - {"ui", "service", "cli"}:
        bad.append('surfaces must be {"ui"|"service"|"cli": [regex, ...]}')
    if not isinstance(cfg["goal_rules"], dict):
        bad.append('goal_rules must be {"text": "rule"}')
    try:
        re.compile(cfg["rollback_pattern"])
    except re.error as e:
        bad.append(f"rollback_pattern is not a regex: {e}")
    if bad:
        sys.exit(f"{FILE}: " + "; ".join(bad))
    return cfg


def goal_base(cfg: dict, slug: str, date: str = "") -> str:
    """<plans_dir>/<date>-<slug>, the prefix of a goal's files; exits when the slug names no single goal."""
    plans = cfg["plans_dir"]
    dates = [date] if date else sorted({
        os.path.basename(p)[:10]
        for p in glob.glob(f"{plans}/????-??-??-{slug}-*.md")
        if re.fullmatch(rf"\d{{4}}-\d\d-\d\d-{re.escape(slug)}-(goal|master|progress)\.md", os.path.basename(p))
    })
    if len(dates) != 1:
        sys.exit(f'no single goal for "{slug}" in {plans} (found {dates or "none"}); give its date')
    return f"{plans}/{dates[0]}-{slug}"


def template(kind: str, cfg: dict) -> str:
    """The repo's own copy in .claude/loopkit/ wins over the plugin's."""
    local = f".claude/loopkit/{kind}.md"
    if os.path.exists(local):
        return local
    name = f"goal-{cfg['ends_at']}" if kind == "goal" else kind
    return os.path.join(SKILL, "templates", f"{name}.md")
