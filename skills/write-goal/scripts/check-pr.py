"""Check that a changeset (a PR, or a goal step's evidence file) carries its complete evidence.

    python3 check-pr.py <PR number or URL | evidence file> [--master <master plan>]

Fails (exit 1) unless the body has all four sections:
  ## Assurance  each check in the repo's `assurance` list (tests, coverage, lint, typecheck, violations, security),
                named in a heading, a bullet or a fenced block, with the output it printed in a fenced block
  ## Evidence   a "### UC<n> <who does what, and what they end up with>" per use case it proves, each with
                its proof for the use case's surface (a step that only enables one, such as a fake or a
                client, writes "### Supports UC<n> <how>" with its tests' output instead):
                  ui       the flow in screenshots, two or more (https URLs, not inside code): where the person
                           lands, each step, and what they end up with
                  service  a fenced block holding the curl request and the response it got
                  cli      a fenced block holding the run, "$ <command>" and its output
                  unknown  a fenced block or a screenshot
                A use case's surface comes from the master plan's Use cases table (--master, or check-goal);
                a PR's changed files matching the repo's `surfaces` also require that kind of proof somewhere.
  ## Signal     a "Success: ..." line and a "Failure: ..." line (the metric, log line or alert to watch during
                the rollout, with its threshold), or, with neither, "not-applicable" and the reason
  ## Review     a line each for simplify, a self-review (by a context that did not write it), a security
                review and the constitution cross-check, each with its result; a UI changeset also a "UX review:" line: each
                use case walked as a first-time person from where they land, never a deep link (can they find
                it, read it, tell what happened, recover from an error; does it match the screens around it)
Anything shaped like a credential fails, reported by line number only: AWS and Google keys, GitHub, GitLab,
Anthropic, OpenAI, Stripe, npm and Slack tokens, private keys, JWTs, signed URLs, credentials in a URL or a
curl -u, bearer and basic headers, and password=, token= or api_key= values that mix letters and digits: evidence is posted where others read it.
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
REVIEW = {"simplify": r"simplif\w*", "a self-review": r"self-review\w*", "a security review": r"security review\w*",
          "the constitution cross-check": r"constitution\w*"}
# Shapes of credentials that evidence (a curl exchange, a CLI run, a screenshot's caption) must never carry.
# A value that is wholly a placeholder, or names itself one, is not a credential.
_PLACEHOLDER = (r"(?!(?:x+|X+|\*+|\.+|<[^>]*>|\[?redacted\]?|\$\{?\w+\}?)(?![\w.~+/=-]))"
                r"(?![\w-]*(?i:example|dummy|fake|sample|your_|placeholder|changeme))")
# A keyword's value counts only when it mixes letters and digits, as real secrets do ("hunter2..."), so test names,
# resource names ("app-db-credentials-prod") and calls ("make_test_token()") pass.
_MIXED = r"(?=[^\s\"'<>]*\d)(?=[^\s\"'<>]*[A-Za-z])"
SECRET = re.compile(
    r"AKIA(?![0-9A-Z]*EXAMPLE)[0-9A-Z]{16}|ASIA[0-9A-Z]{16}"
    r"|(?i:aws.{0,20}?secret.{0,20}?[=:\"'\s])\s*[\"']?[A-Za-z0-9/+]{40}\b"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|glpat-[A-Za-z0-9_-]{20,}"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|sk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}"
    r"|[sr]k_live_[0-9A-Za-z]{20,}|npm_[A-Za-z0-9]{36}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|xapp-[0-9A-Za-z-]{10,}|hooks\.slack\.com/services/T\w+/B\w+/\w+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"
    r"|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"|\b[a-z][a-z0-9+.-]*://[^\s:/@]*:(?!\$|\*+@|<)[^\s@/<*]{3,}@"
    r"|(?i:x-goog-signature|[?&]sig)=[A-Za-z0-9%/+=]{16,}"
    r"|(?i:authorization:\s*bearer\s+)" + _PLACEHOLDER + r"[A-Za-z0-9._~+/=-]{20,}"
    r"|(?i:authorization:\s*basic\s+)" + _PLACEHOLDER + r"[A-Za-z0-9+/=]{12,}"
    r"|(?i:(?:^|\s)(?:-u|--user)\s+)[^\s:'\"]+:" + _PLACEHOLDER + r"[^\s'\"]{6,}"
    r"|(?i:\b(?:password|passwd|pwd|secret|client[_-]?secret|api[_-]?key|access[_-]?key|token)\b[\"']?\s*[=:]\s*[\"']?)"
    + _PLACEHOLDER + _MIXED + r"[^\s\"'<>,;()]{8,}(?![\w(])"
)
WINDOW = r"\b(?:for|over|within|in|after|per)\s+(?:the\s+)?(?:\d+\s*)?(?:s|sec|seconds?|mins?|minutes?|m|h|hrs?|hours?|d|days?|weeks?|deploys?|runs?|requests?)\b"
NEED = {"ui": "the flow in screenshots (two or more: where the person lands, through to the outcome)", "service": "a curl request and its response", "cli": 'a "$ <command>" run and its output'}


def masked(text: str) -> str:
    """The text with fenced blocks blanked, offsets kept, so headings inside output are not read as sections."""
    return FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def section(body: str, name: str) -> str:
    m = re.search(rf"^## {name}[ \t]*\n(.*?)(?=^## |\Z)", masked(body), re.M | re.S)
    return body[m.start(1):m.end(1)].strip() if m else ""


def use_cases(evidence: str) -> dict[str, str]:
    heads = list(re.finditer(r"^### ((?:Supports )?UC\d+)\b", masked(evidence), re.M))
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


def stale(body: str, head: str) -> list[str]:
    """The Assurance must name the commit it ran on, and on a PR that commit is the PR's head."""
    shas = re.findall(r"\b[0-9a-f]{7,40}\b", section(body, "Assurance"))
    if not shas:
        return [f'Assurance names no commit: say what it ran on ("on {head[:9]}"), so a reader can tell it is current']
    if not any(head.startswith(s) for s in shas):
        return [f"Assurance ran on {', '.join(sorted(set(s[:9] for s in shas)))}, not the PR head {head[:9]}: run it again on the head"]
    return []


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
        kind = (ucs or {}).get(uc, "")  # "Supports UC<n>" is no key of ucs: plumbing shows its tests, not a surface
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
        # The watch after the merge reads these lines: each needs a number to compare and a window to read it over.
        for w in ("Success", "Failure"):
            line = re.search(rf"^[^\w\n]*{w}\b[^\n]*", signal, re.M | re.I)
            if line and not (re.search(r"\d", line.group(0)) and re.search(WINDOW, line.group(0), re.I)):
                out.append(f'Signal\'s {w} line needs a threshold and a window to read it over ("above 99% for 1 h", "0 errors within 15 min")')

    if "ui" in hit or "ui" in {(ucs or {}).get(uc) for uc in cases}:
        if not re.search(r"^[^\w\n]*UX review\b[^\w\n]*\w", review, re.M | re.I):
            out.append('a UI changeset needs a "UX review: <result>" line: each use case walked as a first-time person '
                       "from where they land (navigation, legibility, coherence with the screens around it, every state, copy)")
    if not review:
        out.append('no "## Review" section: simplify, a self-review, a security review and the constitution cross-check, each with its result')
    else:
        out += [f"Review has no line for {what} with its result" for what, pat in REVIEW.items()
                if not re.search(rf"^[^\w\n]*{pat}\b[^\w\n]*\w", review, re.M | re.I)]
        own = re.search(r"^[^\w\n]*self-review\b[^\n]*", review, re.M | re.I)
        if own and not re.search(r"\b(?:haiku|sonnet|opus|fable)\b", own.group(0), re.I):
            out.append('the Self-review line names no model: say which ran it, in a context that did not write the change ("Self-review, by a fresh opus context: ...")')
    out += [f"line {body.count(chr(10), 0, m.start()) + 1} carries what looks like a credential: blank it before it is posted"
            for m in SECRET.finditer(body)][:3]
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
    head = ""
    if os.path.isfile(arg):
        body, files = open(arg).read(), []
    elif re.fullmatch(r"\d+|https://\S+/pull/\d+", arg):
        try:
            r = subprocess.run(["gh", "pr", "view", arg, "--json", "body,files,headRefOid"], capture_output=True, text=True)
        except FileNotFoundError:
            sys.exit("gh not found: install it, or pass the evidence file")
        if r.returncode:
            sys.exit(r.stderr.strip())
        pr = json.loads(r.stdout)
        body, files = pr["body"] or "", [f["path"] for f in pr["files"]]
        head = pr["headRefOid"]
        if len(files) >= 100:
            print("warning: gh lists at most 100 changed files; the surface check may miss some")
    else:
        sys.exit(f"no such file, and not a PR number or URL: {args[0]}")
    fails = problems(body, files, cfg["surfaces"], cfg["assurance"], ucs) + (stale(body, head) if head else [])
    for f in fails:
        print(f"FAIL {f}")
    print("ok" if not fails else f"{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
