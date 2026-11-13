"""The repo's loopkit settings: `.claude/loopkit.json` at the git top level, over these defaults."""

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
    "orchestrator": "Opus 5.5",
    "implementer": "sonnet",
    "reviewer": "sonnet",  # model for both review stages; never the implementer of the change
    "max_parallel": 5,
    "runner": "",  # the one entry point for commands, e.g. "make", "rake", "./bin/dev"
    "bypass": [],  # backticked commands that skip the runner, e.g. ["npx", "bundle exec"]
    "goal_rules": {},  # {"text the goal must keep": "the rule it stands for"}
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
    if not isinstance(cfg["goal_rules"], dict):
        bad.append('goal_rules must be {"text": "rule"}')
    try:
        re.compile(cfg["rollback_pattern"])
    except re.error as e:
        bad.append(f"rollback_pattern is not a regex: {e}")
    if bad:
        sys.exit(f"{FILE}: " + "; ".join(bad))
    return cfg


def template(kind: str, cfg: dict) -> str:
    """The repo's own copy in .claude/loopkit/ wins over the plugin's."""
    local = f".claude/loopkit/{kind}.md"
    if os.path.exists(local):
        return local
    name = f"goal-{cfg['ends_at']}" if kind == "goal" else kind
    return os.path.join(SKILL, "templates", f"{name}.md")
