# Which model runs what

One orchestrator for the whole goal, and a model per step, each chosen for the work and written down with its reason. Say the
choice to the owner when it is made: "This is best handled by Fable 5.2, because ...", at the end of the intent and again at
the top of the master plan. The owner overrules it in one word; nobody has to ask.

Prices are per million tokens, input and output, from the Claude API docs: Fable 5.2 $8 / $40, Opus 5.5 $4 / $20, Sonnet 5.5
$2 / $10. Read current prices and model names from the docs before quoting them; do not quote these from memory.

## The orchestrator: Opus 5.5 or Fable 5.2

Opus 5.5 is the default: long-running agentic coding and knowledge work. Fable 5.2 is the most capable model, for demanding
reasoning and long-horizon agentic work, at twice Opus's price. The docs' own advice: start on Opus, move to Fable when Opus at
higher effort still falls short.

Recommend **Fable 5.2** when any of these holds, and name which:

- the run is long-horizon: several plans, or more than a day unattended, with rulings that build on each other;
- the design is open across modules, and a wrong ruling costs more than the run (a data model, an API contract, a migration);
- the goal deploys to production, moves data, or touches auth or security, so a wrong call is hard to take back;
- an Opus run on this work already stalled, missed its gates, or made rulings the owner reversed.

Otherwise recommend **Opus 5.5**: the plans are clear, the steps are well specified, and the gates are mechanical.

## A model per step

The master plan writes `Model: <haiku | sonnet | opus>` on every step, with its reason in a few words. The orchestrator
dispatches each subagent on that model.

| Model | For | Not for |
| --- | --- | --- |
| haiku | Mechanical work with an output a script can check: a rename across files, a grep sweep, an inventory, collecting command output, rendering CLI pictures, running the checkers | Anything that decides, designs or reviews |
| sonnet | A step the plan specifies fully: a function and its tests, a screen from a design, a spec, docs, an evidence walkthrough, most correctness reviews | Open design, a cross-module change, a failure nobody understands yet |
| opus | Design inside a step, a change across modules, concurrency, data integrity, a migration, a failed gate's diagnosis, a whole-branch review, the UX review, a review of a high-risk path | Work a smaller model does as well |

Fable is for the orchestrator. A step that needs it is a step the plan has not split or specified yet; split it, or write
the design down first.

## Reviewers and escalation

- A reviewer runs on at least the implementer's model, and on opus for a high-risk path (auth, data, money, migrations,
  concurrency) and for the UX review.
- A step whose review fails twice, or whose gate still fails after one fix, moves up one model for its next attempt (haiku to
  sonnet, sonnet to opus), recorded as a `Ruling:` with its cost. It never moves down mid-step.
- A step the plan put on a larger model than it needed is a finding in the plan's review; the next plan sizes it down.
