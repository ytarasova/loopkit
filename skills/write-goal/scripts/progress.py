"""Stamp a goal's progress file with the clock, so no time in it is typed or reckoned.

    python3 progress.py <slug> [<date>] now "<text>"       rewrite the Now paragraph: **Now (YYYY-MM-DD HH:MM UTC):** <text>
    python3 progress.py <slug> [<date>] log "<text>"       add "- YYYY-MM-DD HH:MM UTC: <text>" at the end of ## Log
    python3 progress.py <slug> [<date>] approve "<words>"  record "Approved by <owner> YYYY-MM-DD HH:MM UTC: <words>"
    python3 progress.py <slug> [<date>] view               stamp "<view> updated: YYYY-MM-DD HH:MM UTC" after updating it

The time is read once, from the system clock in UTC. The file is replaced whole, or left as it was.
Settings: .claude/loopkit.json (see the write-goal skill).
"""

import datetime
import os
import re
import sys
import tempfile

import config

# The Now paragraph: its line and the lines that continue it, up to a blank line, a heading or another stamp.
NOW = re.compile(r"^\*\*Now \([^)\n]*\):\*\*[^\n]*(?:\n(?!\n|#|Approved by |[^\n]* updated: )[^\n]*)*", re.M)


def after_now(text: str, line: str, pattern: str) -> str:
    """Replace the line `pattern` matches, or put `line` right after the Now paragraph."""
    new, count = re.subn(pattern, lambda _: line, text, count=1, flags=re.M)
    if count:
        return new
    new, count = NOW.subn(lambda m: f"{m.group(0)}\n\n{line}", text, count=1)
    if not count:
        sys.exit('the progress file has no "**Now (...):**" paragraph to stamp after')
    return new


def stamp(text: str, verb: str, words: str, cfg: dict, at: str) -> str:
    if "\n" in words:
        sys.exit("the text must be one line")
    if verb == "now":
        new, count = NOW.subn(lambda _: f"**Now ({at} UTC):** {words}", text, count=1)
        if not count:
            sys.exit('the progress file has no "**Now (...):**" paragraph to rewrite')
        return new
    if verb == "log":
        log = re.search(r"^## Log\b[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if not log:
            sys.exit('the progress file has no "## Log" section')
        end = log.start(1) + len(log.group(1).rstrip("\n"))
        text = f"{text[:end]}\n- {at} UTC: {words}{text[end:]}"
        # A log entry is a state change, so the Now line's time moves with it; its text stays.
        return re.sub(r"^(\*\*Now \()[^)\n]*(\):\*\*)", lambda m: f"{m.group(1)}{at} UTC{m.group(2)}", text, count=1, flags=re.M)
    if verb == "approve":
        if not words.strip():
            sys.exit("approve needs the owner's words")
        return after_now(text, f"Approved by {cfg['owner']} {at} UTC: {words}", r"^Approved by [^\n]*")
    if verb == "view":
        if not cfg["view"]:
            sys.exit('no "view" in .claude/loopkit.json: this repo has no live view to stamp')
        return after_now(text, f"{cfg['view']} updated: {at} UTC", rf"^{re.escape(cfg['view'])} updated: [^\n]*")
    sys.exit(__doc__)


def main() -> None:
    args = sys.argv[1:]
    date = args.pop(1) if len(args) > 2 and re.fullmatch(r"\d{4}-\d\d-\d\d", args[1]) else ""
    verbs = {"now": 3, "log": 3, "approve": 3, "view": 2}
    if len(args) < 2 or verbs.get(args[1]) != len(args):
        sys.exit(__doc__)
    config.to_top()
    cfg = config.load()
    path = f"{config.goal_base(cfg, args[0], date)}-progress.md"
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    if not os.path.isfile(path):
        sys.exit(f"no progress file at {path}: check the slug and the date (the default date is UTC)")
    with open(path) as f:
        new = stamp(f.read(), args[1], args[2] if len(args) == 3 else "", cfg, at)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
    with os.fdopen(fd, "w") as f:
        f.write(new)
    os.chmod(tmp, os.stat(path).st_mode)
    os.replace(tmp, path)
    print(f"{path}: {args[1]} at {at} UTC")


if __name__ == "__main__":
    main()
