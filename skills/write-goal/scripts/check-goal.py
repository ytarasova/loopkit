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
  master      "## Use cases" with "| UC<n> | who does what | ui, service or cli |" rows, each named on some
              plan's "Proves UC<n>." line (a use case no step proves is a hole)
  progress    a Now line, "Waiting on", "In flight", Steps with a checkbox per gate, a Log; warns over 80 KB;
              every ticked step is "Plan N step M" and names its own evidence file,
              "(<plans_dir>/<date>-<slug>-evidence/<N>.<M>.md)", which exists and passes check-pr.py with each
              use case proven for its surface (assurance, evidence by use case, signal, review);
              once every step is ticked, "<date>-<slug>-evidence/goal.md" proves the whole: it passes
              check-pr.py and has a "### UC<n>" for every use case in the master plan
Settings: .claude/loopkit.json (see the write-goal skill).
"""

import glob
import importlib
import os
import re
import sys

import config

check_pr = importlib.import_module("check-pr")  # the file keeps its CLI name

EM_DASH = "\u2014"
CORE_RULES = {
    "CONSTITUTION.md": "read CONSTITUTION.md and CLAUDE.md",
    "did not write": "each review stage runs in a context that did not write the change",
    "PASS is a claim": "an implementer's PASS is rerun, not trusted",
    "In flight": "a dispatch or unsafe step is recorded before it runs",
    "Waiting on": "a human step is recorded, pushed and ends the run",
    "stacked PRs": "plans ship as stacked PRs, one per plan",
    "check-pr.py": "every changeset carries its complete evidence, checked",
}
UNIT = r"(s|sec|min|minutes?|m|h|hours?|d|days?)\b"
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
    if master:
        for s in ("Use cases", "Order", "Decisions, answered"):
            if s not in secs:
                fails.append(f'master plan has no "## {s}" section')
        cases = sorted(set(re.findall(r"^\| *(UC\d+) *\|", secs.get("Use cases", ""), re.M)), key=lambda c: int(c[2:]))
        if "Use cases" in secs and not cases:
            fails.append('master plan "## Use cases" has no "| UC1 | ..." row')
        claims = re.findall(r"\bProves\b[^\n]*", "\n".join(plans.values()))
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
        if "**Now" not in prog:
            fails.append('progress file has no "**Now" line')
        for s in ("Waiting on", "In flight"):
            if not any(h.startswith(s) for h in psecs):
                fails.append(f'progress file has no "## {s}" section')
        steps = psecs.get("Steps", "")
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
                    proven(path)
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
    plans, slug = cfg["plans_dir"], args[0]
    dates = args[1:] or sorted(
        os.path.basename(p)[:10]
        for p in glob.glob(f"{plans}/????-??-??-{slug}-*.md")
        if re.fullmatch(rf"\d{{4}}-\d\d-\d\d-{re.escape(slug)}-(goal|master|progress)\.md", os.path.basename(p))
    )
    if len(set(dates)) != 1:
        sys.exit(f'no single goal for "{slug}" in {plans} (found {sorted(set(dates)) or "none"}); give its date')
    base = f"{plans}/{dates[0]}-{slug}"

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
    fails = missing + fails

    for w in warns:
        print("warn:", w)
    for f in fails:
        print("FAIL:", f)
    print("ok" if not fails else f"{len(fails)} failing")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
