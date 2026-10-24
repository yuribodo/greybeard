---
name: greybeard
description: Turn a pull request or local branch into a guided, visual review page that walks a human through the change one stop at a time. It shows the code, how each changed block connects to the rest of the system (callers, entry points, unchanged code on the path, missing tests), and asks "is this what you intended?" about each traced behaviour. Use this whenever someone wants to review, self-review, understand or explain a PR, a diff, a branch or a big AI-generated change, especially when they say the diff is too big, they don't know where to look, or they need to explain their own PR before sending it, even if they don't name Greybeard.
---

# Greybeard

Greybeard helps a human review a change, usually their own AI-written PR before
sending it. You do the tracing and the human does the judging. The output is one
HTML page:
- a brief with the big picture (a connection map per flow)
- a few **stops**, each showing one block of code: where it's called from, why it
  matters, what it calls, and 1–2 intent checks
- a **skim** list for everything that needs no decision
- a final screen with the human's answers and a draft PR description

## The one principle: point, don't judge

Never say "this is a bug", "fix this" or "this should be…". The human owns every
judgment. You trace what the code actually does and its concrete impact, then ask
whether that's intended. A wrong confident claim is worse than no claim, so every
"does" and "impact" must be something you verified in the code: call sites, config,
CI files, the callee's body. If you can't verify it, leave it out.

Good check:
- **Does:** "This procedure is public. Any request with a valid recipient token now
  reaches disableReportedSender()."
- **Impact:** "One recipient clicking Report once can disable the sender's account. The
  rate limit only stops the same recipient reporting twice in 7 days."
- **Ask:** "Is one recipient meant to be enough?"
- **Other way** (optional): "emailReports already counts reports per organisation; a
  threshold could build on it."

Bad: "Who can hold a recipient token?" This pushes the tracing back onto the human.
Bad: "This is insecure, add a threshold." This is a verdict.

## Workflow

### 1. Collect the facts

```bash
python3 <skill-dir>/scripts/collect.py              # current branch vs its merge-base with main
python3 <skill-dir>/scripts/collect.py --pr 123     # a GitHub PR (needs gh)
python3 <skill-dir>/scripts/collect.py main..feat   # any range
```

Run it with the skill's base directory as `<skill-dir>`. It prints a per-file
overview (status, +/−, hunk line ranges), then writes `.greybeard/facts.json`: every
file and hunk with old/new line numbers,
plus tags (lockfile, generated, test, binary). It also adds `.greybeard/` to
`.git/info/exclude`, which keeps it out of git without touching their `.gitignore`.

### 2. Understand the change before writing anything

Check `source.pr.state` first. If the user assumes something the facts contradict (they
say "before it ships" but it's already merged, or it's a draft), tell them in one line.
The review still helps; they just shouldn't be misled about where the PR stands.

Read `facts.json`, then read the actual code around each change, not just the hunks.
Its `files` is an object keyed by path.
For every changed function, type, route, job or config value:
- **Callers and callees.** Use the LSP tool if available (find references, incoming
  calls). It's more accurate than text search. Otherwise use `grep -rn`.
- **Entry points:** which routes, jobs, crons, CLIs or UI actions can run this code.
- **Unchanged code on the path.** A function the diff doesn't touch can still be
  affected, for example one that now gets called from a new place, or a caller that
  ignores a new return value. These are often the most valuable things to show.
- **Tests:** which tests cover it, which were weakened, which are skipped in CI (check
  the CI workflow and env files), and what has no test at all.
- **Independent flows.** If the changes form separate groups that share no code,
  they're separate flows. Say so, and mention any place where they meet (a link, an
  event, shared data). A tiny unrelated change (a one-line tweak elsewhere) doesn't
  need its own flow. Put it in skim and say in its line that it's unrelated.
- **What's missing.** Look for things the change should have touched but didn't: a
  test, a preview or registry file the sibling feature has, a migration. Once you've
  verified one, it becomes a `missing` node in the map.

### 3. Decide what needs a human: the stops

A stop is a block where a decision is needed. Typical PRs have 3–8, and a small PR may
have only 1 or 2. Never pad. Fewer, sharper stops beat many weak ones, because every
stop costs the reviewer attention.
- **Order them along the call chain** (entry → logic → rules → side effects).
- **A tests stop only when tests changed in a way that needs a decision,** for example
  weakened assertions or tests that CI skips. When there are simply no tests, a
  `missing` node in the map says it without spending a stop.
- **`att: "high"`** ("Look closely") for public surface, auth, money, data deletion,
  irreversible effects, and contract changes many callers depend on. **`"med"`** for
  the rest.
- **The same decision copied in several places** makes one stop with several `src`
  blocks side by side. Comparing them is the point.
- **Code outside the repo matters sometimes,** such as a dependency's behaviour you
  verified in its source. Show it as a snippet with the lines given by hand, and give
  the `src` a `title` naming the package and version (e.g. `better-auth@1.7.0 ·
  dist/session.mjs`), so nobody mistakes it for repo code.
- **Show only the relevant lines** with `range`. Unchanged code goes in `snippets`
  with `snip: true`. Give `{start, end}` and let the build read the lines from the
  repo, instead of copying code into the JSON.
- **A small mechanical hunk in a file that also has a stop** (an import, say) goes to
  skim as `{path, range}`. Don't stretch the stop to cover it.
- **`why`:** one sentence in behaviour terms.
- **`note`:** at most one, on the exact line that matters, and it points rather than
  judges.
- **`checks`:** 1–2, in the format above. If nothing needs a decision, the block
  belongs in skim, not in a stop.

### 4. Everything else goes to skim

Group the rest into skim entries (templates, wiring, imports, renames, lockfiles,
generated code, test helpers), each with one line saying what it is. Every hunk must
end up in a stop or in skim. The build refuses otherwise, which guarantees nothing
is hidden.

### 5. The connection map

Build `graph` per flow:
- **nodes:** stops (`stop`), unchanged context such as entry points (`ctx`), skim items
  (`skim`), tests in the side lane (`lane`), and `missing` for verified gaps. The table
  in `references/review-format.md` says how these combine.
- **edges:** caller → callee, with a short verb ("calls", "queues", "renders"). An edge
  can also link a changed block to existing code it must stay consistent with ("same
  lookup as", "should match"). Draw it from the changed block.
- **`cross`:** links between flows

Keep labels short. Long names get shrunk to fit.

### 6. Write review.json and build

The exact format is in `references/review-format.md`. Read it before writing. Then:

```bash
python3 <skill-dir>/scripts/build.py .greybeard/facts.json .greybeard/review.json -o .greybeard/review.html
```

Run it from the repo root, so snippets given as `{start, end}` can be read.

If it prints problems (uncovered hunks, broken references, malformed stops), fix
`review.json` and rebuild until it passes. Then open the page (`xdg-open` on Linux,
`open` on macOS) and give the user the path.

In chat, keep it short. The page carries the detail, and repeating it in chat just
makes the reviewer read everything twice. Use this shape:

```
Review ready: .greybeard/review.html. 3 stops, 5 intent checks, 4 things to skim.
Most worth your attention:
- <one line>
- <one line>
```

Add one more line only if something about the PR's state needs saying (see step 2).

## Writing style for everything on the page

Write plain, short sentences that a busy developer reads in one pass. Name things
the way the code names them. No hedging filler, no praise, no emoji. The `lead` says
what the PR changes in behaviour terms, not which files it touches. The
`prDescription` is a draft the author can paste: what, the reading order, the
behaviour to know, and the tests.
