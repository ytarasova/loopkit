"""Stamp a goal's progress file with the clock, so no time in it is typed or reckoned.

    python3 progress.py <slug> now "<text>"   rewrite the Now line: **Now (YYYY-MM-DD HH:MM UTC):** <text>
    python3 progress.py <slug> log "<text>"   add "- YYYY-MM-DD HH:MM UTC: <text>" at the end of ## Log
    python3 progress.py <slug> view           stamp "<view> updated: YYYY-MM-DD HH:MM UTC" after updating the live view

The time is read once, from the system clock in UTC. Settings: .claude/loopkit.json (see the write-goal skill).
"""

import datetime
import re
import sys

import config


def stamp(text: str, verb: str, words: str, view: str, at: str) -> str:
    if verb == "now":
        line = f"**Now ({at} UTC):** {words}"
        if not re.search(r"^\*\*Now \(", text, re.M):
            sys.exit('the progress file has no "**Now (" line to rewrite')
        return re.sub(r"^\*\*Now \([^)]*\):\*\*[^\n]*", lambda _: line, text, count=1, flags=re.M)
    if verb == "log":
        if not re.search(r"^## Log\b", text, re.M):
            sys.exit('the progress file has no "## Log" section')
        return text.rstrip("\n") + f"\n- {at} UTC: {words}\n"
    if verb == "view":
        if not view:
            sys.exit('no "view" in .claude/loopkit.json: this repo has no live view to stamp')
        line = f"{view} updated: {at} UTC"
        pattern = rf"^{re.escape(view)} updated: [^\n]*"
        if re.search(pattern, text, re.M):
            return re.sub(pattern, lambda _: line, text, count=1, flags=re.M)
        return re.sub(r"^(\*\*Now \([^\n]*)$", lambda m: f"{m.group(1)}\n\n{line}", text, count=1, flags=re.M)
    sys.exit(__doc__)


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2 or args[1] not in ("now", "log", "view") or (args[1] != "view" and len(args) != 3):
        sys.exit(__doc__)
    config.to_top()
    cfg = config.load()
    path = f"{config.goal_base(cfg, args[0])}-progress.md"
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    with open(path) as f:
        text = f.read()
    new = stamp(text, args[1], args[2] if len(args) == 3 else "", cfg["view"], at)  # before opening for write: a refusal must not empty the file
    with open(path, "w") as f:
        f.write(new)
    print(f"{path}: {args[1]} at {at} UTC")


if __name__ == "__main__":
    main()
