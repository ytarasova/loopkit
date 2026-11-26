"""Check that a changeset (a PR, or a goal step's evidence file) carries its complete evidence.

    python3 check-pr.py <PR number or URL | evidence file> [--master <master plan>]

Fails (exit 1) unless the body has these four sections, and a deliverable two more (below):
  ## Assurance  each check in the repo's `assurance` list (tests, coverage, mutation, lint, typecheck, violations,
                security), naming the commit it ran on (on a PR, its head, or an earlier commit when every
                file changed since matches not_code or is under plans_dir); mutation as "N of M killed" in
                its fenced output, with a "Survivor: <mutant>, <why it stands>" line per mutant that lived,
                or "mutation: not-applicable, <why>",
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
  ## Signal     a "Success: ..." line and a "Failure: ..." line, each with a threshold (a number) and a window to
                read it over ("for 1 h", "within 15 minutes of the deploy"), or, with neither, "not-applicable" and why
  ## Review     a line each for simplify, a self-review (by a context that did not write it, naming its model), a security
                review and the constitution cross-check, each with its result; on a step's evidence file, the Owner read
                (a fresh context asked what the owner would object to, naming its model); a UI changeset also a "UX review:" line: each
                use case walked as a first-time person from where they land, never a deep link (can they find
                it, read it, tell what happened, recover from an error; does it match the screens around it)
A deliverable (a PR, a body file, or a goal's evidence/goal.md; not a step's file inside a *-evidence/ directory) also:
  ## Release notes  a paragraph in its users' words: what changed, for whom, what they now see or do (twelve
                    words or more, no PR or issue numbers), or "No user-visible change." alone
  ## User guide     the guide that walks its users through it, by repo path or https URL (not an image, a PR or
                    an issue); on a PR, a guide named only by repo path is among its changed files;
                    "not-applicable, <why>" only beside "No user-visible change."
Section headings match in any case, with or without a trailing colon.
Anything shaped like a credential fails, reported by line number only: AWS and Google keys, GitHub, GitLab,
Anthropic, OpenAI, Stripe, npm and Slack tokens, private keys, JWTs, signed URLs, credentials in a URL or a
curl -u, bearer and basic headers, and password=, token= or api_key= values that mix letters and digits: evidence is posted where others read it.
An image that is not an https URL fails: a local or relative path renders for nobody. "## " and "### " lines
inside fenced blocks are output, not sections, and HTML comments outside them are not read (GitHub does not
render them), except by the credential scan; an unclosed one fails. A PR reads its body and changed files with `gh`.
Settings: .claude/loopkit.json (see the write-goal skill).
"""

import json
import os
import re
import subprocess
import sys

import config

FENCE = re.compile(r"^```.*?^```[^\n]*$", re.M | re.S)
IMAGE = re.compile(r"!\[[^\]\n]{0,512}\]\(\s*([^)\s]+)|<img[^>]{0,1024}\ssrc=[\"']([^\"']+)", re.I)  # bounded: linear scan
SPAN = re.compile(r"`[^`\n]+`")
_N = r"(?<![\d,])(\d{1,7}(?:,\d{3}){0,3})"  # bounded: the scan stays linear on long digit runs
KILLED = re.compile(rf"{_N}\s*(?:/|of|out\s+of)\s*(?:the\s+)?{_N}\s+(?:mutants?\s+)?(?:were\s+)?killed\b"
                    rf"|\bkilled\s+{_N}\s*(?:/|of|out\s+of)\s*{_N}\b", re.I)
# "Survivor: <mutant>, <why it stands>", one line per mutant that lived; "none" or a bare name is no reason
SURVIVOR = re.compile(r"^[^\w\n]*(?:\d+[.)]\s*)?survivors?\b[^\w\n]*(?!(?:none|n/?a|0)\b)\w[^\n]*?[,;:]\s*\w", re.M | re.I)
QUIET = re.compile(r"[\W_]*no user[- ]visible changes?[\W_]*", re.I)  # the whole section, nothing beside it
GUIDE = re.compile(r"https://\S+|(?<![\w./-])[\w./-]{0,255}\w\.(?:md|mdx|rst|adoc|txt|html?|pdf)\b", re.I)  # bounded: linear
PICTURE = re.compile(r"!\[[^\][\n]{0,512}\]\([^)\n]{0,2048}\)")  # an image is not a guide
REVIEW = {"simplify": r"simplif\w*", "a self-review": r"self-review\w*", "a security review": r"security review\w*",
          "the constitution cross-check": r"constitution\w*"}
# Shapes of credentials that evidence (a curl exchange, a CLI run, a screenshot's caption) must never carry.
# A value that is wholly a placeholder, or names itself one, is not a credential.
_PLACEHOLDER = (r"(?!(?:x+|X+|\*+|\.+|<[^>\s]{0,64}>|\[?redacted\]?|\$\{?\w+\}?)(?![\w.~+/=-]))"
                r"(?![\w-]{0,64}(?i:example|dummy|fake|sample|your_|placeholder|changeme))")
# A keyword's value counts only when it mixes letters and digits, as real secrets do ("hunter2..."), so test names,
# resource names ("app-db-credentials-prod") and calls ("make_test_token()") pass.
_MIXED = r"(?=[^\s\"'<>]{0,256}\d)(?=[^\s\"'<>]{0,256}[A-Za-z])"  # bounded: the scan stays linear on large bodies
SECRET = re.compile(
    r"AKIA(?![0-9A-Z]{0,9}EXAMPLE)[0-9A-Z]{16}|ASIA[0-9A-Z]{16}"
    r"|(?i:aws.{0,20}?secret.{0,20}?[=:\"'\s])\s*[\"']?[A-Za-z0-9/+]{40}\b"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|glpat-[A-Za-z0-9_-]{20,}"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|sk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}"
    r"|[sr]k_live_[0-9A-Za-z]{20,}|npm_[A-Za-z0-9]{36}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|xapp-[0-9A-Za-z-]{10,}|hooks\.slack\.com/services/T\w+/B\w+/\w+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"
    r"|(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"|\b[a-z][a-z0-9+.-]{0,31}://[^\s:/@]{0,128}:(?!\$|\*+@|<)[^\s@/<*]{3,128}@"
    r"|(?i:x-goog-signature|x-amz-signature|[?&]sig)=[A-Za-z0-9%/+=]{16,}"
    r"|(?i:authorization:\s*bearer\s+)" + _PLACEHOLDER + r"[A-Za-z0-9._~+/=-]{20,}"
    r"|(?i:authorization:\s*basic\s+)" + _PLACEHOLDER + r"[A-Za-z0-9+/=]{12,}"
    r"|(?i:(?:^|\s)(?:-u|--user)\s+)[^\s:'\"]+:" + _PLACEHOLDER + r"[^\s'\"]{6,}"
    r"|(?i:(?<![A-Za-z0-9])(?:password|passwd|pwd|secret|client[_-]?secret|api[_-]?key|access[_-]?key|token)\b[\"']?\s*[=:]\s*[\"']?)"
    + _PLACEHOLDER + _MIXED + r"[^\s\"'<>,;()]{8,}(?![\w(])"
)
_UNIT = r"(?:s|sec|seconds?|mins?|minutes?|m|h|hrs?|hours?|d|days?|weeks?)"
_COUNT = r"(?:\d+|one|two|three|four|five|six|ten|fifteen|twenty|thirty|an?)"
_FILLER = r"(?:(?:the|a|an|first|next|any|last|consecutive)\s+){0,2}"
# A window to read a signal over, told apart from a threshold ("p99 over 2 s" has none):
WINDOW = "|".join((
    rf"\b(?:for|within|during)\s+{_FILLER}{_COUNT}[\s-]*(?:consecutive\s+)?{_UNIT}\b",  # for 1 h, within 15 minutes, for five minutes
    rf"\b(?:over|in|for|during)\s+(?:the|a|an|any)\s+(?:(?:first|next|last|following|consecutive)\s+(?:{_COUNT}[\s-]*)?{_UNIT}"
    rf"|(?:{_COUNT}[\s-]*{_UNIT}[\s-]+)?(?:rolling\s+)?window|{_UNIT})\b",  # over the next 24 hours, in any 5-minute window, over the first hour
    rf"\b{_COUNT}[\s-]*{_UNIT}\s+(?:rolling\s+)?window\b",  # a 1h window, a 1-hour rolling window
    rf"/\s*{_COUNT}\s*{_UNIT}\b",  # 5 errors / 10 min
    rf"\b(?:over|in|after)\s+(?:the\s+)?{_COUNT}[\s-]*{_UNIT}\s+(?:of|after)\s+the\s+(?:deploy|release|rollout)",  # in the 30 min after the deploy
))
# "in 10 min" or "over 2 h" alone may be a threshold ("responds in 1 s"); it is a window when the line has its own threshold.
# Seconds read as latency, so a bare window is minutes or longer: "in 10 min" beside its own number, not "in 1 s".
_BARE = r"\b(?:over|in)\s+(?:\d+|one|two|three|four|five|six|ten|fifteen|twenty|thirty|an?)[\s-]*(?:mins?|minutes?|m|h|hrs?|hours?|d|days?|weeks?)\b"
_THRESHOLD = r"\d"


def has_window(line: str) -> bool:
    if re.search(WINDOW, line, re.I):
        return True
    bare = re.search(_BARE, line, re.I)
    return bool(bare and re.search(_THRESHOLD, line[:bare.start()] + line[bare.end():], re.I))


NEED = {"ui": "the flow in screenshots (two or more: where the person lands, through to the outcome)", "service": "a curl request and its response", "cli": 'a "$ <command>" run and its output'}


def masked(text: str) -> str:
    """The text with fenced blocks blanked, offsets kept, so headings inside output are not read as sections."""
    return FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)


def comments(text: str) -> tuple[str, int]:
    """The text with HTML comments blanked, offsets kept, as GitHub hides them: nothing inside one is evidence. A comment
    inside a fenced block or an inline code span is output. An unclosed one hides the rest of the body (GitHub does so
    after a line start, a list marker, a quote or an HTML line; failing closed covers them all), and its offset is
    returned, or -1."""
    shown = SPAN.sub(lambda m: " " * len(m.group()), masked(text))
    out, i, unclosed = [], 0, -1
    while (start := shown.find("<!--", i)) != -1:
        end = shown.find("-->", start + 2)
        if end < 0:
            unclosed, end = start, len(text)
        else:
            end += 3
        out += [text[i:start], re.sub(r"[^\n]", " ", text[start:end])]
        i = end
    return "".join(out) + text[i:], unclosed


def uncommented(text: str) -> str:
    return comments(text)[0]


def section(body: str, name: str) -> str:
    body = uncommented(body.replace("\r\n", "\n"))  # a body edited in the browser comes back with CRLF
    m = re.search(rf"^## (?i:{name}):?[ \t]*\n(.*?)(?=^## |\Z)", masked(body), re.M | re.S)
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


def stale(body: str, head: str, changed=lambda a, b: None, plans_dir: str = "docs/plans",
          not_code: tuple[str, ...] = (r"\.md$",)) -> list[str]:
    """The Assurance must name the commit it ran on: the PR's head, or one since which no code changed.

    `changed(a, b)` lists the files changed between two commits, or None when it cannot tell. Evidence is
    written once: a commit that touches only the goal's own files or `not_code` (Markdown, by default) never
    makes it be taken again.
    """
    plans = os.path.normpath(plans_dir) + "/"  # "./docs/plans/" and "docs/plans" alike
    shas = re.findall(r"\b[0-9a-f]{7,40}\b", section(body, "Assurance"))
    if not shas:
        return [f'Assurance names no commit: say what it ran on ("on {head[:9]}"), so a reader can tell it is current']
    if any(head.startswith(s) for s in shas):
        return []
    for s in shas:
        files = changed(s, head)
        if files is not None and all(f.startswith(plans) or any(re.search(r, f) for r in not_code) for f in files):
            return []
    return [f"Assurance ran on {', '.join(sorted(set(s[:9] for s in shas)))}, not the PR head {head[:9]}, and code changed "
            "since (or the commits are not fetched): run it again on the head"]


def git_changed(a: str, b: str) -> list[str] | None:
    """Every path changed between two commits; a rename lists both names. None when either is not fetched."""
    r = subprocess.run(["git", "diff", "--name-only", "--no-renames", "-z", a, b], capture_output=True, text=True)
    return None if r.returncode else [f for f in r.stdout.split("\0") if f]


def notes_and_guide(body: str, files: list[str]) -> list[str]:
    """What a deliverable tells its users: the release notes, and the guide they follow."""
    out = []
    notes, guide = section(body, "Release notes"), section(body, "User guide")
    quiet = QUIET.fullmatch(notes)
    if not notes:
        out.append('no "## Release notes": what changed, for whom, and what they now see, in their words; '
                   'or "No user-visible change."')
    elif not quiet and len(re.findall(r"[^\W\d_]{2,}", masked(notes))) < 12:  # words in any script
        out.append("Release notes are too short to tell a user what changed (what, for whom, what they now see or do); "
                   'a change no user sees writes "No user-visible change." alone')
    if re.search(r"(?<![\w&])#\d+\b|/(?:pull|issues)/\d+", SPAN.sub("", masked(notes))):
        out.append("Release notes cite a PR or issue number: say what changed in the reader's words; receipts stay in the PR")
    named = [n for n in GUIDE.findall(PICTURE.sub("", masked(guide))) if not re.search(r"/(?:pull|issues)/\d", n)]  # nor a PR
    paths = [n for n in named if not n.startswith("https://")]
    if not guide:
        out.append('no "## User guide": the guide that walks users through the change, by repo path or https URL, '
                   'or "not-applicable, <why>" for no user-visible change')
    elif named:
        if files and len(paths) == len(named) and not set(paths) & set(files):
            out.append(f"User guide names {', '.join(paths[:3])}, which this PR does not change: update the guide in the same change")
    elif re.search(r"^[^\w\n]*not-applicable[^\w\n]+\w", guide, re.M | re.I):
        if notes and not quiet:
            out.append("User guide is not-applicable, but the Release notes describe a change: update the guide users follow")
    else:
        out.append('User guide names no guide: its repo path or https URL and what this change added to it; or '
                   '"not-applicable, <why>" beside "No user-visible change."')
    return out


def problems(body: str, files: list[str], surfaces: dict[str, list[str]], checks: list[str],
             ucs: dict[str, str] | None = None, deliverable: bool = False, step: bool = False) -> list[str]:
    out = []
    assurance, evidence, signal, review = (section(body, s) for s in ("Assurance", "Evidence", "Signal", "Review"))

    fences = FENCE.findall(assurance)
    if not fences:
        out.append('no "## Assurance" with each check\'s output in a fenced block')
    else:
        named = "\n".join(fences + re.findall(r"^[ \t]*(?:#+|[-*]|\*\*)[^\n]*", masked(assurance), re.M)).lower()
        out += [f"Assurance does not show {c} (in a heading, a bullet or a fenced block)"
                for c in checks if not re.search(rf"\b{re.escape(c.lower())}\b", named)]

    if ("mutation" in (c.lower() for c in checks) and assurance
            and not any(x.startswith("Assurance does not show mutation") for x in out)):
        num = lambda x: int((x or "0").replace(",", ""))
        runs = [(num(a or c), num(b or d)) for a, b, c, d in KILLED.findall("\n".join(FENCE.findall(assurance)))]
        runs = [(k, m) for k, m in runs if 1 <= m and k <= m]  # 0 of 0 claims nothing ran
        if not runs and not re.search(r"^[^\w\n]*mutation\w*\b[^\n]*?\bnot-applicable[^\w\n]+\w", assurance, re.M | re.I):
            out.append('Assurance shows no mutation result: "N of M killed" in the fenced output (each new rule or branch '
                       'disabled in turn, its tests run each time), or "mutation: not-applicable, <why>" for a change with no logic')
        lived = max((m - k for k, m in runs), default=0)
        named = len(SURVIVOR.findall(masked(assurance)))
        if lived > named:
            out.append(f"{lived} mutant(s) survived and {named} named: give each its own \"Survivor: <mutant>, <why it stands>\" "
                       "line (equivalent to the original, or the test that now kills it)")

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
    for src in (s for s in images(evidence) if not s.startswith("https://")):
        shown = re.split(r"[?#]", re.sub(r"//[^/@]*@", "//", src))[0]  # never echo a URL's credentials, query or fragment
        out.append("image no reviewer can open (not an https URL)" + ("" if SECRET.search(shown) else f": {shown}"))
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
            # the bullet and its indented continuation lines only: never the window of the bullet after it
            line = re.search(rf"^[^\w\n]*{w}\b[^\n]*(?:\n(?![ \t]*(?:[-*+]|\d+\.)\s)[ \t]+\S[^\n]*)*", signal, re.M | re.I)
            if line and not (re.search(r"\d", line.group(0)) and has_window(line.group(0))):
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
        own = re.search(r"^[^\w\n]*self-review\w*\b[^\n]*", review, re.M | re.I)
        if own and not re.search(r"\b(?:haiku|sonnet|opus|fable)\b", own.group(0), re.I):
            out.append('the Self-review line names no model: say which ran it, in a context that did not write the change ("Self-review, by a fresh opus context: ...")')
        if step:  # a task's own evidence: the owner's reader judged it as the owner would (write-goal/owner-reader.md)
            read = re.search(r"^[^\w\n]*owner read\w*\b[^\w\n]*\w[^\n]*", review, re.M | re.I)
            if not read:
                out.append('a step\'s evidence needs an "Owner read, by a fresh <model> context: <result>" line in Review '
                           "(write-goal/owner-reader.md)")
            elif not re.search(r"\b(?:haiku|sonnet|opus|fable)\b", read.group(0), re.I):
                out.append('the Owner read line names no model: say which fresh context read it ("Owner read, by a fresh sonnet context: ...")')
    if deliverable:
        out += notes_and_guide(body, files)
    unclosed = comments(body.replace("\r\n", "\n"))[1]
    if unclosed >= 0:
        out.append(f"an unclosed <!-- at line {body.count(chr(10), 0, unclosed) + 1} hides the rest of the body on GitHub: "
                   "close it with -->, or put it in `code`")
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
    # A step's evidence file is a piece of a deliverable; a PR, a body file and the goal's whole are deliverables.
    step = (os.path.isfile(arg) and os.path.basename(arg).lower() != "goal.md"
            and any(d.endswith("-evidence") for d in os.path.dirname(arg).split(os.sep)))
    fails = (problems(body, files, cfg["surfaces"], cfg["assurance"], ucs, deliverable=not step, step=step)
             + (stale(body, head, git_changed, cfg["plans_dir"], tuple(cfg["not_code"])) if head else []))
    for f in fails:
        print(f"FAIL {f}")
    print("ok" if not fails else f"{len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
