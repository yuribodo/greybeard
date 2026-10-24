# Review-PR Skill: Research & Brainstorm

_Started 2026-10-23._

## 1. The problem

AI makes PRs bigger. Reviewers, including the person who prompted the code, get a
huge alphabetical list of files with red and green lines and no story. You can't
tell what matters, what's noise, or what to say.

The core issue is not the diff algorithm. **The unit and order of presentation are
wrong.** Lines and files are sorted alphabetically. A reviewer needs *intent → concerns →
risky spots*, in an order where each step explains the next.

## 2. What the evidence says

### Size kills review quality
- **Cisco/SmartBear study** (2,500 reviews, 10 months): defect discovery drops sharply
  above ~200–400 LOC per review and after 60–90 minutes. Inspection rates under
  ~300–500 LOC/hour find more defects. The thresholds vary by source and come from one
  2006 team, so treat them as a rough guide. [SmartBear][smartbear], [Cisco case study][cisco]
- **AI PRs are larger:** LinearB's 2026 benchmark (cited by CodeRabbit) says AI-assisted
  PRs are 2.6× larger, get a first review later, and get accepted less often.
  A study of ~33k agent-authored PRs found that unmerged ones were larger, touched more
  files and failed CI more often. [CodeRabbit][coderabbit]
- **The bottleneck has moved to review:** one NBER-cited figure is +741% lines of code
  from agents but only +20% releases. Faros reports AI PRs wait 4.6× longer for a
  reviewer. These are secondhand vendor numbers. [Hyrax][hyrax], [Vaughan][vaughan]

### Review is mostly about *understanding*
- **Bacchelli & Bird, ICSE 2013 (Microsoft):** finding defects is the top stated
  motivation for review, but reviews find fewer defects than expected. Their main
  benefits are knowledge transfer and team awareness. **Understanding the change is
  the central difficulty, and current tools don't support it.** [paper][bacchelli]
- **Pascarella et al., CSCW 2018 "Information Needs in Code Review":** 900 review
  comments, 7 categories of need. The top needs: *rationale* (why), *context* (how the
  changed methods and variables are used elsewhere), and *is my understanding correct?*
  [paper][pascarella]
- **Code Review as Decision-Making (2025):** think-aloud study, 34 reviews. Reviewers
  go through an **Orientation phase** (establish context and rationale), then an
  **Analytical phase** (understand, assess, plan the rest). Tools should support
  orientation explicitly. [arXiv 2507.09637][crdm]

### Order and grouping matter
- **Google eng-practices, "Navigating a CL":** (1) does the change make sense at all?
  (2) look at the *main part* first, usually the file with the most logical changes.
  (3) go through the rest in a sensible order. If the core design is wrong, comment
  right away and stop. [Google][google-nav]
- **"Breaking the Alphabet", ICSE 2026** (1,355 developers): tools default to
  alphabetical order; only **10.2%** of reviewers call it optimal. **66%** want
  dependency-aware grouping and custom ordering. [ICSE 2026][alphabet]
- **EASE 2023 (JetBrains):** files shown higher get more comments, so position biases
  attention. Ordering by diff size beats alphabetical order at surfacing problematic
  files. [EASE 2023][ease]
- **Tangled changes hurt review:** a PeerJ controlled experiment found that PRs mixing
  unrelated concerns hinder review. Untangling algorithms exist: Herzig & Zeller,
  Dias et al., Microsoft's *ClusterChanges* (Barnett et al., ICSE 2015, which
  partitions by def-use links), and CoRA (ASE 2019, decomposes *and describes*
  tangled changes). [PeerJ][peerj], [CoRA][cora]
- **Refactorings hidden in diffs:** changes that contain refactorings are harder to
  review (Microsoft, Xerox). Tools like **RAID** (RefDiff) and **RefactorInsight**
  (RefactoringMiner) mark "this is a move/rename/extract" so the reviewer can skip it.
  [RAID][raid], [RefactorInsight][refinsight]

### Tests: read them, and be suspicious
- **Spadini et al., ICSE 2019, "Test-Driven Code Review"** (93 developers, 150+
  reviews): reading tests first found the same number of production defects, *more*
  test defects, and fewer maintainability notes. Most developers still prefer to
  read production code first. [paper][tdcr]
- **For agent code specifically:** agents edit assertions to match broken behaviour,
  delete or skip tests, and lower coverage thresholds, so a green build proves
  little. **Read changed tests with more suspicion than changed code.**
  [Addy Osmani][osmani], [Aviator][aviator]

### How experts look at code
- Eye-tracking studies find that experts **scan globally first, then focus**. In
  Uwano 2007, reviewers who skipped the scan phase took longer to find defects.
  Hauser et al. 2021 propose a phase model. [Hauser et al.][eyetrack]

### Practitioner consensus (blogs, forums)
- Triage by **blast radius**: auth, payments, data handling, migrations, concurrency,
  public APIs, anything user-facing or hard to undo. Give config tweaks a glance.
  [Aviator][aviator], [Osmani][osmani]
- **Make the author do the intent work:** require a purpose statement, test output and
  proof the tests ran. [Osmani][osmani]
- Small diffs and stacked PRs. [Graphite][graphite-stack]
- Forum sentiment: "if someone constantly pushes slop and you have to review it, they
  offload their work to you." [ITK discourse][itk], [Reddit snapshot][reddit]

## 3. Existing tools (what we can copy and what we can beat)

| Tool | Idea | Notes |
|---|---|---|
| **Sourcegraph Guided Diff Tour** (beta) | Groups files by intent, most important first, short explanation per section, track viewed files | Closest to our idea. [link][sg] |
| **Graphite Code Tours** (Apr 2026) | Narrative walkthrough next to the diff, built from description, comments, stack and code | Plans visual impact and "tests supporting this change". [link][gt] |
| **CodeSee Review Map Tours**, **Tell Request** | Author-written viewing order and visual map | Manual. [CodeSee][codesee] |
| **difftastic** | AST diff: ignores reformatting and whitespace churn | `difft --check-only --exit-code` tells you whether anything structural changed. [blog][difft] |
| **SemanticDiff** | Goes past AST: detects invariant changes (`1337` vs `0x539`), moved code | VS Code extension and GitHub app. [link][semdiff] |
| **sem** | Diffs functions and classes, not lines | [link][sem] |
| **CodeRabbit / Graphite Agent / etc.** | AI bot comments | They *find issues*, but don't help a human *understand* the change. |

**The gap:** the bots grade the code, the tours narrate it, and the semantic diffs remove
noise. Nothing combines all three into a *reviewer's reading plan* that runs locally in
Claude Code against any branch.

## 4. Things git already gives us for free

```bash
git diff --stat -M -C base...head          # renames/copies detected, sizes
git diff -w --ignore-blank-lines           # drop whitespace-only noise
git diff --color-moved=zebra --color-moved-ws=allow-indentation-change   # moved blocks
git diff --diff-algorithm=histogram        # cleaner hunks
git range-diff base old-head new-head      # "what changed since I last reviewed"
git log --oneline base..head               # commit story, if the author kept one
gh pr view N --json title,body,files,commits,reviews   # intent + prior discussion
```
`git range-diff` is underused, and "what changed since my last review" is a real pain
point on PRs that get re-pushed.

## 5. Design principles (from the evidence)

1. **Orientation before analysis.** Start with what the PR claims to do and whether it
   makes sense, before showing any code. (CRDM, Google, Pascarella)
2. **Separate noise from signal.** Classify each hunk as *mechanical* (formatting,
   rename, move, generated code, lockfiles, snapshots, import shuffles) or
   *behavioral*. Collapse mechanical hunks, but list them so nothing is hidden. (RAID,
   difftastic)
3. **Group by concern, not by file.** Untangle into "chapters". (ClusterChanges, CoRA,
   Sourcegraph)
4. **Order by dependency.** Contracts, types and schema first, then core logic, then
   callers and wiring, then tests, then config and docs. The core change goes first.
   (Google, Breaking the Alphabet)
5. **Point attention with risk.** Flag blast-radius areas and *suspicious patterns*:
   deleted checks, broadened permissions, swallowed errors, weakened tests, changed
   assertions, new dependencies, migrations, concurrency. (Osmani, Aviator)
6. **Give context the diff hides.** For each changed function, show who calls it and
   what else depends on it. (Pascarella: the top need)
7. **Ask questions, don't just state findings.** Give the reviewer "what to verify" and
   "what to ask the author", which also answers "what am I supposed to say?".
8. **Stay small.** A chapter should fit the ~200–400 LOC budget. If the PR can't be
   chunked that way, say so and suggest how to split it. (Cisco, stacked diffs)
9. **Never claim completeness you didn't earn.** Every hunk ends up in a chapter or in
   the skipped list. The skill shows coverage ("312/312 hunks accounted for").

## 6. Skill concept (brainstorm)

**Name ideas:** `review-pr`, `pr-map`, `diff-tour`, `read-this-pr`.

**Input:** a PR number (`gh`), a branch, or `base..head`. Defaults to the current branch
vs main.

**Output, a "Review Map":**
1. **TL;DR (orientation):** what the PR claims (title, body, linked issue), what it
   *actually* does in 3–5 bullets, and any mismatch between the two.
2. **Size & shape:** files and LOC, split into behavioral vs mechanical, and a verdict:
   reviewable in one sitting or should be split.
3. **Skip list:** collapsed mechanical changes, each with the reason (e.g. "moved
   verbatim", "formatting only", "lockfile", "generated").
4. **Chapters in reading order.** Each one has:
   - its intent in one sentence
   - `file:line` hunks to read, in order
   - context: callers and dependents of the changed symbols
   - a risk badge and *why*
   - "Check that…" questions
5. **Tests vs behavior:** which behavior changes have tests, which don't, and which
   tests were weakened, deleted or rewritten.
6. **Draft comments / questions for the author:** ready to paste.
7. **Coverage line:** every hunk accounted for.

**Modes (later):**
- `--walk`: interactive, one chapter at a time. The reviewer says "next" or asks
  questions.
- `--since-last-review`: uses `git range-diff` and the reviewer's last reviewed SHA.
- `--html`: a published page with collapsible chapters and an inline diff, for big
  PRs or for sharing with the team.
- `--self`: author mode. Pre-review your own AI-generated PR before asking anyone
  (Osmani's "make the author do the intent work").
- `--comment`: post the map as a PR comment (needs explicit confirmation).

**How it could work inside a skill:**
1. Collect: `gh pr view`, `git diff` (with -M -C -w and color-moved), and the commit list.
2. Cheap deterministic pre-pass: a small script that tags lockfiles, generated or
   vendored files, pure renames, and whitespace-only or moved hunks. Use `difft` if
   it's installed.
3. Model pass: group the remaining hunks into concerns, order them by dependency, find
   callers with grep or LSP, and assign risk.
4. Check: every hunk is in a chapter or in the skip list.
5. Render as markdown in the terminal (default) or as HTML.

## 7. Decisions (2026-10-23)

- **Sources:** GitHub PRs (via `gh`) and local branches. No GitLab.
- **Output:** an HTML page. The terminal only prints the link.
- **PR comments:** not now. Focus on visualization.
- **Language focus:** TypeScript. Use the TS compiler/language service for real
  "what is this block connected to" data (references, callers, types), with grep as
  the fallback for other languages.
- **Core feature:** for each changed block, show what it connects to and what it
  impacts.
- **Mode:** self-review is the default ("if I can't explain my PR, no reviewer can").
  Reviewer mode uses the same map with different wording in the last section and
  comes second.

## Sources

[smartbear]: https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/
[cisco]: https://agileconnection.com/article/largest-case-study-code-reviews-ever
[coderabbit]: https://www.coderabbit.ai/guides/code-review-best-practices-for-ai-generated-code
[hyrax]: https://hyrax.dev/blog/mit-wharton-code-review-bottleneck-2026
[vaughan]: https://codex.danielvaughan.com/2026/05/24/human-review-bottleneck-code-review-strategies-agent-output/
[bacchelli]: https://www.microsoft.com/en-us/research/?p=164195
[pascarella]: https://research.tudelft.nl/en/publications/information-needs-in-contemporary-code-review
[crdm]: https://arxiv.org/abs/2507.09637
[google-nav]: https://google.github.io/eng-practices/review/reviewer/navigate.html
[alphabet]: https://conf.researchr.org/details/icse-2026/icse-2026-research-track/310/Breaking-the-Alphabet-Rethinking-File-Ordering-in-Code-Review
[ease]: https://conf.researchr.org/details/ease-2023/ease-2023-industry/3/Assessing-the-Impact-of-File-Ordering-Strategies-on-Code-Review-Process
[peerj]: https://peerj.com/articles/cs-193/
[cora]: https://www.se.cs.uni-saarland.de/conferences/ASE/ase2019/details/ase-2019-papers/33/CoRA-Decomposing-and-Describing-Tangled-Code-Changes-for-Reviewer.html
[raid]: https://ar5iv.arxiv.org/html/2103.11453
[refinsight]: https://arxiv.org/pdf/2108.11202
[tdcr]: https://2019.icse-conferences.org/details/icse-2019-Technical-Papers/29/Test-Driven-Code-Review-An-Empirical-Study
[osmani]: https://addyosmani.com/blog/agentic-code-review/
[aviator]: https://www.aviator.co/blog/?p=5968
[eyetrack]: https://research.utu.fi/converis/portal/detail/Publication/499173240?lang=en_US
[graphite-stack]: https://graphite.dev/guides/benefits-of-stacked-diffs-in-code-review
[itk]: https://discourse.itk.org/t/ai-generated-pull-requests-overwhelming-hard-to-review-carefully/7728
[reddit]: https://reddit.sentinel-team.org/posts/1pvtq6l/snapshots/2025-12-26T20%3A27%3A59.0515Z
[sg]: https://sourcegraph.com/changelog/guided-diff-tour-beta
[gt]: https://graphite.com/blog/code-tours
[codesee]: https://docs.codesee.io/docs/review-map-tours
[difft]: https://blog.openreplay.com/review-ai-generated-code-difftastic/
[semdiff]: https://semanticdiff.com/blog/semanticdiff-vs-difftastic/
[sem]: https://braindetox.kr/en/posts/sem_semantic_version_control_2026.html
