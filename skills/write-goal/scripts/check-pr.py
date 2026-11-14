"""Check that a changeset (a PR, or a goal step's evidence file) carries its complete evidence.

    python3 check-pr.py <PR number or URL | evidence file> [--master <master plan>]

Fails (exit 1) unless the body has all four sections:
  ## Assurance  each check in the repo's `assurance` list (tests, coverage, lint, typecheck, violations),
                named in a heading, a bullet or a fenced block, with the output it printed in a fenced block
  ## Evidence   a "### UC<n> <who does what, and what they end up with>" per use case it proves, each
                with its proof for the use case's surface:
                  ui       the flow in screenshots, two or more (https URLs, not inside code): where the person
                           lands, each step, and what they end up with
                  service  a fenced block holding the curl request and the response it got
                  cli      a fenced block holding the run, "$ <command>" and its output
                  unknown  a fenced block or a screenshot
                A use case's surface comes from the master plan's Use cases table (--master, or check-goal);
                a PR's changed files matching the repo's `surfaces` also require that kind of proof somewhere.
  ## Signal     a "Success: ..." line and a "Failure: ..." line (the metric, log line or alert to watch during
                the rollout, with its threshold), or, with neither, "not-applicable" and the reason
  ## Review     a line each for simplify, a self-review (by a context that did not write it) and the
                constitution cross-check, each with its result; a UI changeset also a "UX review:" line: each
                use case walked as a first-time person from where they land, never a deep link (can they find
                it, read it, tell what happened, recover from an error; does it match the screens around it)
An image that is not an https URL fails: a local or relative path renders for nobody. "## " and "### " lines
inside fenced blocks are output, not sections. A PR reads its body and changed files with `gh`.
Settings: .claude/loopkit.json (see the write-goal skill).
"""

import json
import os
import re
import subprocess
import sys

import config

FENCE = re.compile(r"^```.*?^```[^\n]*$", re.M | re.S)
IMAGE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)|<img[^>]*\ssrc=[\"']([^\"']+)", re.I)
SPAN = re.compile(r"`[^`\n]+`")
REVIEW = {"simplify": r"simplif\w*", "a self-review": r"self-review\w*", "the constitution cross-check": r"constitution\w*"}
NEED = {"ui": "the flow in screenshots (two or more: where the person lands, through to the outcome)", "service": "a curl request and its response", "cli": 'a "$ <command>" run and its output'}


def masked(text: str) -> str:
    """The text with fenced blocks blanked, offsets kept, so headings inside output are not read as sections."""
    return FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def section(body: str, name: str) -> str:
    m = re.search(rf"^## {name}[ \t]*\n(.*?)(?=^## |\Z)", masked(body), re.M | re.S)
    return body[m.start(1):m.end(1)].strip() if m else ""


def use_cases(evidence: str) -> dict[str, str]:
    heads = list(re.finditer(r"^### (UC\d+)\b", masked(evidence), re.M))
    ends = [h.start() for h in heads[1:]] + [len(evidence)]
    return {h.group(1): evidence[h.start():end] for h, end in zip(heads, ends)}


def images(text: str) -> list[str]:
    return [a or b for a, b in IMAGE.findall(SPAN.sub("", FENCE.sub("", text)))]


def proof(text: str, surface: str) -> bool:
    fences = FENCE.findall(text)
    if surface == "ui":
        return len(images(text)) >= 2  # a flow: where the person lands, through to what they end up with
    if surface == "service":
        return any(re.search(r"\bcurl\b", f) for f in fences)
    if surface == "cli":
        return any(re.search(r"^\$ \S", f, re.M) for f in fences)
    return bool(fences or images(text))


def master_surfaces(master: str) -> dict[str, str]:
    """{UC: surface} from a master plan's Use cases table: | UC<n> | who does what | surface |."""
    rows = re.findall(r"^\| *(UC\d+) *\|.*\| *(ui|service|cli) *\|\s*$", section(master, "Use cases"), re.M)
    return dict(rows)


def problems(body: str, files: list[str], surfaces: dict[str, list[str]], checks: list[str],
             ucs: dict[str, str] | None = None) -> list[str]:
    out = []
    assurance, evidence, signal, review = (section(body, s) for s in ("Assurance", "Evidence", "Signal", "Review"))

    fences = FENCE.findall(assurance)
    if not fences:
        out.append('no "## Assurance" with each check\'s output in a fenced block')
    else:
        named = "\n".join(fences + re.findall(r"^[ \t]*(?:#+|[-*]|\*\*)[^\n]*", masked(assurance), re.M)).lower()
        out += [f"Assurance does not show {c} (in a heading, a bullet or a fenced block)"
                for c in checks if not re.search(rf"\b{re.escape(c.lower())}\b", named)]

    cases = use_cases(evidence)
    if not evidence:
        out.append('no "## Evidence" section: the change working, told by use case')
    elif not cases:
        out.append('Evidence is not told by use case: no "### UC<n> <who does what>" heading')
    for uc, text in cases.items():
        kind = (ucs or {}).get(uc, "")
        if not proof(text, kind):
            label = f"{uc} ({kind})" if kind else uc
            out.append(f"{label} is not proven: it needs {NEED.get(kind, 'output or a screenshot')}; a link alone is not evidence")
    out += [f"image no reviewer can open (not an https URL): {src}" for src in images(evidence)
            if not src.startswith("https://")]
    hit = {kind for kind, pats in surfaces.items() for f in files if any(re.search(p, f) for p in pats)}
    out += [f"changes {kind} files, so Evidence needs {NEED[kind]}" for kind in sorted(hit) if not proof(evidence, kind)]

    found = {w: re.search(rf"^[^\w\n]*{w}\b[^\w\n]*\w", signal, re.M | re.I) for w in ("Success", "Failure")}
    if not signal:
        out.append('no "## Signal" section: a Success and a Failure line for the rollout, or not-applicable and why')
    elif not any(found.values()):
        if not re.search(r"not-applicable[^\w\n]+\w+[^\w\n]+\w", signal, re.I):
            out.append('Signal has no "Success:" or "Failure:" line, and no "not-applicable" with a reason')
    else:
        out += [f'Signal has no "{w}: <metric, log line or alert, and threshold>" line' for w, m in found.items() if not m]

    if "ui" in hit or "ui" in {(ucs or {}).get(uc) for uc in cases}:
        if not re.search(r"^[^\w\n]*UX review\b[^\w\n]*\w", review, re.M | re.I):
            out.append('a UI changeset needs a "UX review: <result>" line: each use case walked as a first-time person '
                       "from where they land (navigation, legibility, coherence with the screens around it, every state, copy)")
    if not review:
        out.append('no "## Review" section: simplify, a self-review and the constitution cross-check, each with its result')
    else:
        out += [f"Review has no line for {what} with its result" for what, pat in REVIEW.items()
                if not re.search(rf"^[^\w\n]*{pat}\b[^\w\n]*\w", review, re.M | re.I)]
    return out


def main() -> None:
    args = sys.argv[1:]
    master = ""
    if "--master" in args:
        i = args.index("--master")
        if i + 1 >= len(args) or not os.path.isfile(args[i + 1]):
            sys.exit("--master needs the master plan's path")
        master = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    arg = os.path.abspath(args[0]) if os.path.isfile(args[0]) else args[0]
    config.to_top()
    cfg = config.load()
    ucs = master_surfaces(open(master).read()) if master else {}
    if os.path.isfile(arg):
        body, files = open(arg).read(), []
    elif re.fullmatch(r"\d+|https://\S+/pull/\d+", arg):
        try:
            r = subprocess.run(["gh", "pr", "view", arg, "--json", "body,files"], capture_output=True, text=True)
        except FileNotFoundError:
            sys.exit("gh not found: install it, or pass the evidence file")
        if r.returncode:
            sys.exit(r.stderr.strip())
        pr = json.loads(r.stdout)
        body, files = pr["body"] or "", [f["path"] for f in pr["files"]]
        if len(files) >= 100:
            print("warning: gh lists at most 100 changed files; the surface check may miss some")
    else:
        sys.exit(f"no such file, and not a PR number or URL: {args[0]}")
    fails = problems(body, files, cfg["surfaces"], cfg["assurance"], ucs)
    for f in fails:
        print(f"FAIL {f}")
    print("ok" if not fails else f"{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
