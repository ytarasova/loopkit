"""Check a goal's three files before the owner runs /goal.

    python3 check-goal.py <slug> [<date>]

Fails (exit 1) on what would break or mislead the run; warns on what a person should look at.
  all files   present and non-empty; no {{...}} left; no em-dash (unless ban_em_dash is false)
  goal        at most 4,000 characters (/goal refuses more; warns over 3,000); names the master
              plan and the progress file; keeps the core rules and the repo's goal_rules; ends on
              a "Done means:" line naming gates the master plan defines
  goal+master no backticked command from the repo's bypass list (every command goes through runner)
  master      Order and "Decisions, answered"; one "## Plan N:" section per Order row, each with
              its measured facts, steps, gates, failures, coverage, rollback and human steps;
              every gate with a baseline that is a number or (unconfirmed), a source, and a window
              ("within 15 min") when ends_at is production; every Rollback non-empty, and
              every rollback matching rollback_pattern when one is set
  master      "## Asks": "| A<n> | <the owner's words> | <UC ids that exist, or dropped by <owner> YYYY-MM-DD> |"
  master      "## Use cases" with "| UC<n> | who does what | ui, service or cli |" rows, each on some plan's
              "Proves UC<n>." line (a use case no step proves is a hole)
  master      "## Models" with "Orchestrator: Opus 5.5" or "Fable 5.2" (and the goal naming the same model), and
              "Model: haiku|sonnet|opus" on every numbered step of every plan (write-goal's models.md)
  progress    a "**Now (YYYY-MM-DD HH:MM UTC):**" line no older than the last Log entry; no stamp (Now, Log,
              Approved by, the view) more than 5 minutes ahead of the clock (progress.py writes them);
              "Waiting on", "In flight" and "What is left"; each In flight item ends with its time left,
              and each "What is left" row has one in its last column;
              the live view (`view`) stamped no earlier than Now; Steps with a checkbox per gate; a Log;
              no ticked "Plan" step before "Approved by"; warns over 80 KB
  evidence    every ticked step is "Plan N step M" and names its own evidence file,
              "(<plans_dir>/<date>-<slug>-evidence/<N>.<M>.md)", which exists, passes check-pr.py with each
              use case proven for its surface, and has a "### UC<n>" for each use case its step proves;
              once every step is ticked, "<date>-<slug>-evidence/goal.md" passes check-pr.py and has a
              "### UC<n>" for every use case in the master plan
  progress    "## Owner corrections": every correction the owner gave, each row ending with the kit change that
              encodes it (a commit, a PR or a ticket)
  repo        .superpowers/ is git-ignored when it exists; on a branch other than main, no kit file
              (CONSTITUTION.md, .claude/) changes unless the master plan says it touches one
Settings: .claude/loopkit.json (see the write-goal skill).
"""

import datetime
import glob
import importlib
import os
import re
import subprocess
import sys

import config

check_pr = importlib.import_module("check-pr")  # the file keeps its CLI name

EM_DASH = "\u2014"
CORE_RULES = {
    "CONSTITUTION.md": "read CONSTITUTION.md and CLAUDE.md",
    "did not write": "each review stage runs in a context that did not write the change",
    "PASS is a claim": "an implementer's PASS is rerun, not trusted",
    "nothing skipped": "each task runs the write-goal sequence in order",
    "the model its step names": "each subagent runs on the model its step names",
    "§VIII.4": "a choice about what people see or where their data goes is asked, not ruled",
    "progress.py": "times in the progress file come from the clock",
    "after a compaction": "the goal and the progress file are re-read after a compaction",
    "In flight": "a dispatch or unsafe step is recorded before it runs",
    "Waiting on": "a human step is recorded, pushed and ends the run",
    "stacked PRs": "plans ship as stacked PRs, one per plan",
    "check-pr.py": "every changeset carries its complete evidence, checked",
}
# "Proves UC1, UC2 and UC3": the ids right after "Proves", and nothing after the first other word ("supports UC4").
PROVES = r"\bProves\s+(UC\d+(?:\s*(?:,\s*(?:and\s+)?|and|&)\s*UC\d+)*)"
UNIT = r"(s|sec|mins?|minutes?|m|h|hrs?|hours?|d|days?)\b"
PLAN_PARTS = [
    "**Measured facts",
    "**Steps**",
    "**Gates**",
    "**Failures.**",
    "**Coverage.**",
    "**Rollback.**",
    "**Human steps.**",
]


def sections(body: str) -> dict[str, str]:
    out = {}
    for chunk in re.split(r"^## ", body, flags=re.M)[1:]:
        head, _, rest = chunk.partition("\n")
        out[head.strip()] = rest
    return out


def gate_ids(text: str) -> set[int]:
    ids = set()
    for a, b in re.findall(r"\bG(\d+)(?:\s*(?:to|-)\s*G(\d+))?", text):
        ids.update(range(int(a), int(b or a) + 1))
    return ids


def section_of(secs: dict[str, str], name: str) -> str:
    """A progress section by the start of its heading, so "## In flight (2)" is still In flight."""
    return next((body for head, body in secs.items() if head.startswith(name)), "")


def check(goal: str, master: str, prog: str, cfg: dict, evidence: str = "") -> tuple[list[str], list[str]]:
    fails: list[str] = []
    warns: list[str] = []
    gate_parts = [
        ('baseline read as a number ("Baseline: 404 at 09:10") or "(unconfirmed)"',
         r"\bBaseline:[^\n]*?(\d|\(unconfirmed\))"),
        ('source ("Source: <command or dashboard>")', r"\bSources?:\s*\S"),
    ]
    if cfg["ends_at"] == "production":
        gate_parts.append(('window ("within 15 min", "over 24 h")', rf"\b(within|over)\s+(the\b|\d+\s*{UNIT})"))
    bypass = (
        re.compile(
            r"(?:^|[\s;&|(\"'])(" + "|".join(re.escape(c) for c in cfg["bypass"]) + r")(?=$|[\s\"'])"
        )
        if cfg["bypass"]
        else None
    )

    for name, body in (("goal", goal), ("master plan", master), ("progress file", prog)):
        left = re.findall(r"\{\{[^}]*\}\}", body)
        if left:
            fails.append(f"{name} has {len(left)} unfilled placeholder(s), e.g. {left[0]}")
        if cfg["ban_em_dash"] and EM_DASH in body:
            fails.append(f"{name} has {body.count(EM_DASH)} em-dash(es)")

    secs = sections(master)
    plans = {h: b for h, b in secs.items() if re.match(r"Plan \d+:", h)}
    defined: dict[int, str] = {}

    if goal:
        n = len(goal)
        if n > 4000:
            fails.append(f"goal is {n} characters; /goal refuses over 4,000")
        elif n > 3000:
            warns.append(f"goal is {n} characters; keep it under 3,000 so a revision has room")
        for needle, rule in {**CORE_RULES, **cfg["goal_rules"]}.items():
            # Section names are matched as written: "in flight" also means a CI run in progress.
            exact = needle in ("In flight", "Waiting on")
            if (needle not in goal) if exact else (needle.lower() not in goal.lower()):
                fails.append(f'goal lost a rule: {rule} (no "{needle}")')
        for kind in ("master", "progress"):
            if not re.search(rf"{re.escape(cfg['plans_dir'])}/\S+-{kind}\.md", goal):
                fails.append(f"goal does not name the {kind} file")

    if bypass:
        for name, body in (("goal", goal), ("master plan", master)):
            fences = re.findall(r"^```[^\n]*\n(.*?)^```", body, re.M | re.S)
            spans = re.findall(r"`([^`\n]+)`", re.sub(r"^```.*?^```", "", body, flags=re.M | re.S))
            snippets = [ln for f in fences for ln in f.splitlines()] + spans
            for cmd in sorted({m for s in snippets for m in bypass.findall(s)}):
                fails.append(f"{name} runs `{cmd}` directly; every command goes through {cfg['runner']}")

    cases: list[str] = []
    step_proves: dict[tuple[str, str], set[str]] = {}
    if master:
        for s in ("Asks", "Use cases", "Models", "Order", "Decisions, answered"):
            if s not in secs:
                fails.append(f'master plan has no "## {s}" section')
        cases = sorted(set(re.findall(r"^\| *(UC\d+) *\|", secs.get("Use cases", ""), re.M)), key=lambda c: int(c[2:]))
        if "Use cases" in secs and not cases:
            fails.append('master plan "## Use cases" has no "| UC1 | ..." row')
        ask_lines = re.findall(r"^\|? *A\d+ *\|[^\n]*", secs.get("Asks", ""), re.M)
        if "Asks" in secs and not ask_lines:
            fails.append('master plan "## Asks" has no "| A1 | <the owner\'s words> | UC1 |" row')
        dropped = rf"^dropped by {re.escape(cfg['owner'])} \d{{4}}-\d\d-\d\d\b"
        for line in ask_lines:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not line.startswith("|") or not line.rstrip().endswith("|") or len(cells) < 3:
                fails.append(f"Asks row is not \"| A<n> | <the owner's words> | <UC ids, or dropped by {cfg['owner']} YYYY-MM-DD> |\": {line[:60]}")
                continue
            ask, last = cells[0], cells[-1]
            ids = re.findall(r"\bUC\d+\b", last)
            if re.match(dropped, last, re.I):
                continue
            if not ids:
                fails.append(f"{ask} maps to no use case and was not dropped by {cfg['owner']} on a date: every ask is built and proven, or dropped by name")
            fails.extend(f"{ask} names {uc}, which the Use cases table does not define" for uc in ids if uc not in cases)
        orch = re.search(r"^Orchestrator:\s*((?:Opus|Fable)\s+[\d.]+)", secs.get("Models", ""), re.M)
        if "Models" in secs and not orch:
            fails.append('master plan "## Models" names no orchestrator ("Orchestrator: Opus 5.5" or "Fable 5.2", and why)')
        elif orch and goal and orch.group(1) not in goal:
            fails.append(f"master plan's orchestrator is {orch.group(1)} but the goal does not name it; rescaffold with --orchestrator")
        for head, body in plans.items():
            block = body.split("**Steps**", 1)[1].split("\n**", 1)[0] if "**Steps**" in body else ""
            for step in re.findall(r"^\d+\.\s[^\n]*", block, re.M):
                if not re.search(r"\bModel:\s*(haiku|sonnet|opus)\b", step, re.I):
                    fails.append(f'"{head}" step names no model ("Model: haiku, sonnet or opus"): {step[:50]}')
        for head, body in plans.items():
            n = re.match(r"Plan (\d+)", head)
            block = body.split("**Steps**", 1)[1].split("\n**", 1)[0] if "**Steps**" in body else ""
            for m, line in re.findall(r"^(\d+)\.\s(.*?)(?=^\d+\.\s|\Z)", block, re.M | re.S):  # a step runs to the next
                claim = re.search(PROVES, line)
                if n and claim:
                    step_proves[(n.group(1), m)] = set(re.findall(r"\bUC\d+\b", claim.group(1)))
        claims = re.findall(PROVES, "\n".join(plans.values()))
        proven = set(re.findall(r"\bUC\d+\b", "\n".join(claims)))
        for uc in cases:
            if uc not in proven:
                fails.append(f'{uc} is proven by no plan step ("Proves {uc}."): a use case no step proves is a hole')
        rows = re.findall(r"^\| *\d+ *\|", secs.get("Order", ""), re.M)
        if len(rows) != len(plans):
            fails.append(
                f'master plan Order has {len(rows)} row(s) but {len(plans)} "## Plan N:" section(s)'
            )
        for row in re.findall(r"^\|(.*)\|\s*$", secs.get("Decisions, answered", ""), re.M)[2:]:
            cells = [c.strip() for c in row.split("|")]
            if len(cells) < 2 or not cells[1]:
                fails.append(f"decision has no answer: {cells[0]}")
        roots = "|".join({"docs", re.escape(cfg["plans_dir"].split("/")[0])})
        for path in sorted(set(re.findall(rf"`((?:{roots})/[^`<>*]+\.md)`", master))):
            if not os.path.exists(path):
                fails.append(f"master plan names a file that does not exist: {path}")
        for head, body in plans.items():
            for part in PLAN_PARTS:
                if part not in body:
                    fails.append(f'"{head}" has no {part} paragraph')
            gates = body.split("**Gates**", 1)[-1].split("\n**", 1)[0] if "**Gates**" in body else ""
            items = re.split(r"\n(?=- \*\*G\d)", gates)[1:]
            if "**Gates**" in body and not items:
                fails.append(f'"{head}" has no gate ("- **G1 name.** ...")')
            for item in items:
                gid = int(re.match(r"- \*\*G(\d+)", item).group(1))
                if gid in defined:
                    fails.append(f"G{gid} is defined twice ({defined[gid]} and {head})")
                defined[gid] = head
                for what, pattern in gate_parts:
                    if not re.search(pattern, item, re.I):
                        fails.append(f"G{gid} has no {what}")
            rollback = (
                body.split("**Rollback.**", 1)[-1].split("\n**", 1)[0].strip()
                if "**Rollback.**" in body
                else None
            )
            if rollback == "":
                fails.append(f'"{head}" Rollback is empty')
            elif rollback and cfg["rollback_pattern"] and not re.search(cfg["rollback_pattern"], rollback):
                fails.append(f'"{head}" Rollback does not match /{cfg["rollback_pattern"]}/')
        unconfirmed = len(re.findall(r"(?<!`)\(unconfirmed\)", master))
        if unconfirmed:
            warns.append(f"master plan marks {unconfirmed} fact(s) (unconfirmed); each needs a step that reads it")

    if goal:
        done = re.search(r"^Done means:(.*)$", goal, re.M)
        if not done or not gate_ids(done.group(1)):
            fails.append('goal does not end on a measurement: no "Done means:" line naming gates (G1 ...)')
        elif master:
            named = gate_ids(done.group(1))
            for g in sorted(named - defined.keys()):
                fails.append(f"goal's Done means names G{g}, which the master plan does not define")
            for g in sorted(defined.keys() - named):
                warns.append(f"G{g} is in the master plan but not in the goal's Done means")

    if prog:
        psecs = sections(prog)
        stamp_at = r"(\d{4}-\d\d-\d\d \d\d:\d\d)(?::\d\d)? UTC"
        now_at = re.search(rf"^\*\*Now \({stamp_at}\):\*\*", prog, re.M)
        logged = re.findall(rf"^- {stamp_at}", section_of(psecs, "Log"), re.M)
        approved = re.search(rf"^Approved by .+? {stamp_at}: \S", prog, re.M)
        view_at = re.search(rf"^{re.escape(cfg['view'])} updated: {stamp_at}", prog, re.M) if cfg["view"] else None
        # Stamped times come from the clock (progress.py), never reckoned: one ahead of now was made up.
        # Other dates in the file (a freeze that lifts next week) are plans, not stamps, and are not checked.
        clock = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        late = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        stamps = [m.group(1) for m in (now_at, approved, view_at) if m] + logged
        fails.extend(f"progress file has a stamp ahead of the clock: {t} UTC (now {clock} UTC); stamp with progress.py"
                     for t in sorted(set(stamps)) if t > late)
        if not now_at:
            fails.append('progress file has no "**Now (YYYY-MM-DD HH:MM UTC):**" line (progress.py now "<text>" writes it)')
        else:
            if logged and max(logged) > now_at.group(1):
                fails.append(f"the Now line ({now_at.group(1)} UTC) is older than the last Log entry ({max(logged)} UTC): rewrite it at every state change")
            if cfg["view"] and (not view_at or view_at.group(1) < now_at.group(1)):
                fails.append(f'the {cfg["view"]} lags the progress file: no "{cfg["view"]} updated: <time>" at or after the Now line '
                             f'(update it, then progress.py view)')
        time_left = rf"\d+\s*{UNIT}(?:\s*\d+\s*{UNIT})?"
        for item in re.findall(r"^- (?!(?:nothing|none)\b)([^\n]+)", section_of(psecs, "In flight"), re.M | re.I):
            if not re.search(rf"{time_left}[\s.)]*$", item, re.I):
                fails.append(f'In flight item does not end with its time left ("1h 20m", "35m"): {item[:60]}')
        left = re.sub(r"^```.*?^```", "", section_of(psecs, "What is left"), flags=re.M | re.S)
        tables = re.findall(r"(?:^\|[^\n]*\|[ \t]*\n?)+", left, re.M)
        rows = [r for t in tables for r in t.splitlines()[1:] if not re.fullmatch(r"[|:\- \t]+", r)]
        for row in rows:  # each table's first row is its header
            last = row.strip().strip("|").split("|")[-1]
            if not re.search(time_left, last, re.I):
                fails.append(f'"What is left" row has no time left in its last column: {row.strip()[:60]}')
        for row in re.findall(r"^\|(?! *(?:When|:?-+:?) *\|)[^\n]*\|[ \t]*$", section_of(psecs, "Owner corrections"), re.M):
            last = row.strip().strip("|").split("|")[-1]
            if not re.search(r"\b[0-9a-f]{7,40}\b|#\d+|https://\S+/pull/\d+|\b(?!(?:UTF|SHA|ISO|RFC|TLS|CVE)-)[A-Z][A-Z0-9]+-\d+\b", last):
                fails.append(f"owner correction with no kit change: {row.strip()[:60]} (its commit, PR or ticket, §VI.10)")
        for s in ("Waiting on", "In flight", "What is left", "Owner corrections"):
            if not any(h.startswith(s) for h in psecs):
                fails.append(f'progress file has no "## {s}" section')
        steps = psecs.get("Steps", "")
        if re.search(r"^- \[[xX]\] Plan", steps, re.M) and not approved:
            fails.append('a step is ticked but the master plan was never approved: progress.py approve "<their words>" comes before any code')
        if not re.search(r"^- \[[ xX]\] ", steps, re.M):
            fails.append('progress file has no "## Steps" checklist')
        for g in sorted(defined):
            if not re.search(rf"^- \[[ xX]\] G{g}\b", steps, re.M):
                fails.append(f"progress file Steps has no checkbox for G{g}")
        if evidence:
            ucs = check_pr.master_surfaces(master)

            def proven(path: str) -> str:
                """The evidence file's text, after recording each way it falls short."""
                if not os.path.isfile(path):
                    return ""
                with open(path) as f:
                    body = f.read()
                fails.extend(f"{path}: {p}" for p in check_pr.problems(body, [], cfg["surfaces"], cfg["assurance"], ucs))
                return body

            ticked = re.findall(r"^- \[[xX]\] ([^\n]*)", steps, re.M)
            for line in ticked:
                if re.match(r"(G\d+|Baselines)\b", line):
                    continue
                step = re.match(r"Plan (\d+) step (\d+)\b", line, re.I)
                if not step:
                    fails.append(f'ticked step is not "Plan N step M", so its evidence cannot be checked: {line[:60]}')
                    continue
                path = f"{evidence}/{step.group(1)}.{step.group(2)}.md"
                if f"({path})" not in line:
                    fails.append(f"ticked step does not name its evidence file ({path}): {line[:60]}")
                elif not os.path.isfile(path):
                    fails.append(f"ticked step's evidence file does not exist: {path}")
                else:
                    shown = check_pr.use_cases(check_pr.section(proven(path), "Evidence"))
                    fails.extend(f"{path} has no \"### {uc}\": Plan {step.group(1)} step {step.group(2)} proves it, "
                                 f"so \"Supports {uc}\" does not stand in for its proof"
                                 for uc in sorted(step_proves.get((step.group(1), step.group(2)), ())) if uc not in shown)
            if ticked and not re.search(r"^- \[ \] ", steps, re.M):
                # Every piece is proven; now the whole: every use case again, on the final code, in one file.
                whole = f"{evidence}/goal.md"
                if not os.path.isfile(whole):
                    fails.append(f"every step is ticked but the whole has no evidence: {whole} (every use case, on the final code)")
                else:
                    shown = check_pr.use_cases(check_pr.section(proven(whole), "Evidence"))
                    fails.extend(f"{whole} does not prove {uc}" for uc in cases if uc not in shown)
        if not re.search(r"^- \S", psecs.get("Log", ""), re.M):
            fails.append('progress file has no "## Log" line')
        size = len(prog.encode())
        if size > 80_000:
            warns.append(f"progress file is {size // 1000} KB; a resume reads all of it")

    return fails, warns


def main() -> None:
    args = sys.argv[1:]
    if len(args) not in (1, 2):
        sys.exit(__doc__)
    config.to_top()
    cfg = config.load()
    base = config.goal_base(cfg, args[0], args[1] if len(args) > 1 else "")

    texts, missing = [], []
    for kind in ("goal", "master", "progress"):
        path = f"{base}-{kind}.md"
        if os.path.exists(path) and os.path.getsize(path):
            with open(path) as f:
                texts.append(f.read())
        else:
            missing.append(f"missing or empty: {path}")
            texts.append("")
    fails, warns = check(*texts, cfg, f"{base}-evidence")
    branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    if not branch:
        warns.append("HEAD is detached: the kit-on-a-feature-branch check did not run")
    elif branch not in ("main", "master"):
        diff = subprocess.run(["git", "diff", "--name-only", "origin/main...HEAD", "--", "CONSTITUTION.md", ".claude"],
                              capture_output=True, text=True)
        # A kit file the master plan names is part of the goal's own work; any other is a fix that belongs off main.
        kit = [f for f in diff.stdout.split() if f"`{f}`" not in texts[1]]  # named as a path, not merely mentioned
        if diff.returncode:
            warns.append("no origin/main to compare with: the kit-on-a-feature-branch check did not run")
        elif kit:
            fails.append(f"kit files changed on {branch} ({kit[0]}{' and more' if len(kit) > 1 else ''}): a kit fix ships as its "
                         "own PR off main, so the next run and the other repos get it (rollout.md)")
    ignored = subprocess.run(["git", "check-ignore", "-q", ".superpowers"]).returncode == 0
    if os.path.isdir(".superpowers") and not ignored:
        fails.append(".superpowers/ is not git-ignored: subagent ledgers will be committed (add it to .gitignore)")
    fails = missing + fails

    for w in warns:
        print("warn:", w)
    for f in fails:
        print("FAIL:", f)
    print("ok" if not fails else f"{len(fails)} failing")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
