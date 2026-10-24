# PRD: Greybeard

> Show your PR to the greybeard before anyone else sees it.

**Character:** a grumpy but wise senior dev who has seen every bad PR. The page speaks
in his voice ("The greybeard's questions", "LGTM, kid").

_Draft v0.1, 2026-10-23. Research and evidence: [RESEARCH.md](RESEARCH.md)._

## Problem

AI-generated PRs are too big to review in GitHub's diff view: files sorted
alphabetically, line-level red/green, no story. Even the author can't explain the
change, and a reviewer can't tell what matters, what's noise, or what to say.
Research shows review is mainly about *understanding* (Bacchelli & Bird 2013), and
reviewers most need the rationale and how changed code connects to the rest
(Pascarella 2018). Alphabetical order is judged optimal by only 10% of reviewers
(ICSE 2026).

## Goal

Turn any GitHub PR or local branch into an **HTML review map**: the change told as an
ordered story, with noise separated out and, for every changed block, **what it
connects to and what it impacts**.

## Core principle: Greybeard points, the human reviews

Greybeard never delivers verdicts ("this is a bug", "restore this assertion"). It
directs attention:
- **where to look**, as an attention level per block
- **why it matters**, as facts: callers, entry points reached, contract changes,
  test changes
- **intent checks**, never open questions. Each check traces what the code does and
  asks whether that is intended:
  - **Does:** "Any recipient token now reaches disableReportedSender()."
  - **Impact:** "One recipient, one click, and the account is disabled."
  - **Other way** (optional): "emailReports already counts reports; a threshold could
    build on it."
  - **Intended?** The human answers [Yes, intended] / [No, look again].

  Every "Does" and "Impact" must be checked against the code: call sites, config, CI.
  "Who can hold a token?"-style questions that push the tracing work back onto the
  human aren't allowed.

The review itself, and every judgment, belongs to the human.

## Users

1. **Primary: the author doing a self-review** of an AI-assisted PR before asking for
   review. "If I can't explain my PR, no reviewer can."
2. **Secondary: the reviewer** of someone else's PR. Same map, different closing
   section.

## Non-goals (v1)

- **Greybeard Cloud, our API, Jev and billing.** v1 runs 100% locally. Cloud is
  planned after v1 (see Business model).
- Posting comments to GitHub.
- GitLab or Bitbucket.
- Finding bugs automatically (AI review bots already do this; we focus on understanding).
- Full support for non-TypeScript languages (fallback only).

## User stories

- As an author, I run one command on my branch and get a page that shows me my own PR
  in a sensible reading order, so I can check that I understand every part.
- As an author, I see a list of things to fix before sending (weakened tests, debug
  leftovers, unrelated changes, untested behaviour).
- As an author, I get a draft PR description generated from the map.
- As anyone, for each changed block I see its callers, dependents, related types and
  covering tests.
- As anyone, I can see that every hunk is accounted for (in a chapter or a skip list
  with a reason).
- As a reviewer, I run it on a PR number and get questions to ask the author.

## The page (v1)

1. **Summary:** what the PR claims (title, body, commits), what it actually does in
   3–5 bullets, and any mismatch.
2. **Size and shape:** behavioural vs mechanical LOC, plus a verdict: one sitting, or
   should be split.
3. **Chapters in dependency order** (types/schema → core logic → callers/wiring →
   tests → config/docs). Each chapter shows:
   - its intent in one sentence: "Can you explain this?" (confirm or edit)
   - the diff hunks, in reading order
   - an **impact panel** per changed symbol: callers, importers, implementers,
     covering tests (from the TypeScript language service)
   - a risk badge with the reason
4. **Skip list:** mechanical changes (formatting, renames, moves, lockfiles,
   generated files), each with a reason, expandable.
5. **Tests vs behaviour:** which changes are tested, and which tests were changed,
   weakened or deleted.
6. **Before you send** (self mode) / **Questions for the author** (reviewer mode).
7. **Draft PR description** (self mode).
8. **Coverage:** `N/N hunks accounted for`.

The page is a single self-contained HTML file that works offline, in light and dark.

**Chosen direction (2026-10-23, round 4): guided review,** spec in
[docs/design/guided.html](docs/design/guided.html), with the reasoning in
[docs/design/COMPETITORS.md](docs/design/COMPETITORS.md).
- **Brief:** what the PR does, counts (stops that need you, intent checks, things to skim)
  and a small flow chain.
- **One stop per screen,** only for blocks that need a human: "← from", why you're here,
  only the relevant hunks, at most one note, "→ calls" with Peek, at most two intent
  checks, then Next.
- **Skim:** everything low-attention as one expandable list.
- **Done:** your answers, with "look again" items first, plus the draft PR description.

Round 3 is kept below for reference (its components carry over):
design spec in
[docs/design/prototype-map.html](docs/design/prototype-map.html), built on a real PR
(documenso#3446). It supersedes `prototypes.html`.
- **The code is the main content.** Full-width, GitHub-style diffs: real hunks,
  old/new line numbers, +/- rows, no ligatures in code.
- **GitHub visual language.** Mona Sans / system UI, Primer-like colours, file cards,
  a "Viewed" checkbox, alert boxes. No handwriting.
- **The map stays as navigation.** One graph per independent flow, callers above
  callees, tests in a lane, dashed borders for unchanged-but-on-the-path code,
  missing tests shown as a block. Click a block to jump to its code.
- **Blocks in reading order.** Each one has:
  - an attention label
  - "Why look here" facts
  - who calls it / what it calls
  - questions to answer, as checkboxes
  - its diff
- **Greybeard's notes are inline comments** under the exact line, worded to point at
  code, not to judge it.
- **Connections are visible inside the code:**
  - **Call sites are links:** the called name is underlined, and a row under the line
    shows "↳ calls X" with **Peek** (the callee's code inline) and **Go to block**.
  - **Each block has a strip:** "called from" (exact file:line, which jumps to the call
    line) → this block → "calls".
  - **Connectors between cards** ("↓ called from X at file:line"), with blocks
    ordered along the call chain.
  - **Data need:** every edge carries its call-site location (path, line, symbol).
    The LSP gives this through `references` / `incomingCalls`.

## Architecture

A Go single-binary CLI (also installable via npm and Homebrew) plus a thin Claude Code
skill. Details: [docs/adr](docs/adr/README.md) and [docs/PLAN.md](docs/PLAN.md). A JSON format is the contract
between the steps.

```
greybeard collect  →  facts.json  →  LLM step  →  map.json  →  greybeard render  →  page.html
 (deterministic)                (judgment)                  (deterministic)
```

- **`greybeard collect [<pr#> | <base>..<head>]`** (default: current branch vs main):
  - `gh pr view` / `git diff -M -C -w --color-moved`, plus the commit list
  - tags lockfiles, generated/vendored files, renames, whitespace-only and moved hunks
  - TypeScript language service: changed symbols → references, importers,
    implementers, related tests. Falls back to grep for other languages.
- **LLM step**, split in two:
  - **Decisions (typed, per hunk):** Bool, Choice and Score questions, answered with a
    confidence value. Examples: *mechanical?* (Bool), *does this test change weaken an
    assertion?* (Bool), *debug leftover?* (Bool), *related to the PR goal?* (Bool),
    *layer: types | core | wiring | test | config* (Choice), *which chapter?* (Choice),
    *risk 1–5* (Score). Low-confidence answers are flagged on the page, not hidden.
  - **Writing (prose):** chapter names and intents, the summary, before-you-send
    text and the PR description.
  - v1: the Claude Code skill does both.
  - v2: `greybeard review` runs standalone with a pluggable backend:
    - **local (free):** the user's own model or key. Decisions go through any LLM
      with structured output (TypeSafe's open-source System One adapter gives the
      typed interface). Writing goes to any generative model.
    - **cloud (paid):** `GREYBEARD_API_KEY` calls Greybeard Cloud, which runs
      decisions on TypeSafe **Jev** (typed, 70–500 ms, 32k context) and writing on
      a hosted generative model. See Business model.
  - Initial chapters can come from clustering the TypeScript reference graph, so
    the per-hunk "which chapter?" question only picks between existing candidates.
- **`greybeard render map.json`** produces the HTML page.
- **Validation:** `render` refuses a map that doesn't account for every hunk.

Why this design: the logic lives in the package, so the same `map.json` can later
feed a GitHub Action, PR comments, a VS Code panel or an MCP server without a rewrite.
MCP is skipped for v1 because agents can already call a CLI.

## Business model: open core

| | Greybeard CLI + skill | Greybeard Cloud |
|---|---|---|
| Repo | **Public**, open source (MIT) | **Private** |
| Contains | `collect`, `render`, schemas, Claude Code skill, local backends, cloud client | API, auth, metering, billing, Jev + generative model integration, tuned questions and prompts |
| Cost to user | Free: the Claude Code skill, their own key or a local model | Pay per use |
| Why pay | n/a | Fastest path (Jev), no model setup or keys, tuned quality, one bill |

**Cloud API (v1 sketch):**
- `POST /v1/decisions`: a batch of typed questions per hunk → typed answers + confidence.
- `POST /v1/write`: map facts → prose fields.
- Auth via an API key, sent as `Authorization: Bearer`.
- Usage metered per review (or per token) and billed through Stripe usage-based
  billing, with a small free monthly allowance.
- The request and response schemas live in the public package, so the CLI and the
  API share one contract.

**Rules:**
- Local mode must stay fully functional. Cloud sells speed and convenience, not
  features locked away from local users.
- Only hunks and facts are sent, never the whole repo. **Zero data retention by
  default**, stated publicly, because companies won't send code otherwise.
- The CLI shows the estimated cost before a cloud run and the actual cost after.

## Milestones

| # | Deliverable | Done when |
|---|---|---|
| M1 | `facts.json` and `map.json` schemas + `greybeard collect` (git, local branches, mechanical tagging) | Runs on a real branch; every hunk listed and tagged |
| M2 | TypeScript impact analysis in `collect` | Callers and importers correct on a real TS repo, monorepo tsconfig handled |
| M3 | `greybeard render` HTML page | Page renders a hand-written `map.json`; coverage check enforced |
| M4 | Claude Code skill (self-review mode) | `/review-pr` on a branch produces the page end to end |
| M5 | GitHub PR input (`gh`) + reviewer mode | Works on a PR number |
| M6 | Standalone `greybeard review`, local backend | Works without Claude Code, using the user's own key or a local model |
| — | **v1 ends here: 100% local** | |
| M7 (post-v1) | Greybeard Cloud: `/v1/decisions` on Jev, `/v1/write`, API keys, metering, Stripe billing (private repo) | `GREYBEARD_API_KEY=… greybeard review` works and the usage shows up on the bill |

## Success criteria

- On a 1,000+ line AI-generated PR, the author can explain each chapter in one sentence
  after reading the page.
- Under 10% of hunks land in "uncategorized".
- Impact panel references match the language service (no false callers from name
  collisions).
- A reviewer who reads the generated PR description and the page needs fewer
  "what does this do?" comments.

## Open questions

- **Jev terms:** do TypeSafe's terms allow reselling Jev behind our own paid API? Check
  before building M7.
- Benchmark Jev against Claude/Haiku on the decision questions (we have API access).
- Pricing unit: per review, per hunk, or per token? Size of the free allowance?
- npm package name: `greybeard` is taken. Options: `@greybeard/cli` (if the npm org is
  free) or `greybeard-review`, with the command still `greybeard`.
- Where the page opens: a local file in the browser, or a published link to share?
- Large PRs: is there a size limit, or does it chunk the LLM step?
- License (MIT?).
