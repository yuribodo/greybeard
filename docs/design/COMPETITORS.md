# How Others Show a PR (2026-10-23)

## The tools

| Tool | Where it lives | What it shows | Tone |
|---|---|---|---|
| **CodeRabbit** walkthrough | A collapsible GitHub comment | Summary · grouped changed-files table · Mermaid sequence diagram · **review effort 1–5** · related issues/PRs · suggested reviewers | Judges (findings) |
| **Greptile** | A GitHub comment and inline comments | Summary · **confidence score 0–5** (merge readiness) · findings list linked to inline comments · auto diagram (sequence / ER / class / flow, chosen by what changed; none for trivial PRs) · P0/P1/P2 badges | Judges |
| **Qodo / PR-Agent** `/review` | A GitHub comment | Effort estimate · **focus files**: "inspect these first" · key issues as inline comments · tests? · security? · **"can be split"** · risk low/med/high · merge recommendation | Judges |
| **Sourcegraph Diff Tour** (beta) | Sourcegraph diff page, "Tour" tab | Important files first, related files grouped into sections, explanations for the diff, each section and each file · mark viewed | Explains |
| **Graphite Code Tours** (Apr 2026) | Graphite PR page | A guided walkthrough, **narrative next to the diff**, in sequence ("like an engineer walking you through it") · planned: visual impact and supporting tests | Explains |
| **Cursor `pr-review-canvas`** (skill) | A local canvas | Sections by reviewer value: **core → wiring → boilerplate** (boilerplate = file list only) · **pseudocode** next to dense logic · **concrete example traced through old vs new code** · rare callout tags ("Subtle", "Breaking"): *"overuse destroys signal"* · "be creative per PR" | Explains |
| **Haystack** | A web canvas | The PR chunked into logical sections on an infinite canvas, read in sequence; focus on intent over lines | Explains |
| **Diffity** tour (skill) | A local browser viewer | A sidebar narrative plus highlighted code, step by step | Explains |
| **Reviewable** | Its own web app | Per-file "reviewed" state · **"mark reviewed and go to next file"** · per-thread state (discussing / satisfied / blocking) | Tracks progress |

Sources: [CodeRabbit walkthroughs](https://docs.coderabbit.ai/pr-reviews/walkthroughs) ·
[Greptile review anatomy](https://www.greptile.com/docs/code-review/first-pr-review.md) ·
[PR-Agent /review](https://github.com/qodo-ai/pr-agent/blob/main/docs/docs/tools/review.md) ·
[Sourcegraph Diff Tour](https://sourcegraph.com/docs/diff-tour) ·
[Graphite Code Tours](https://graphite.com/blog/code-tours) ·
[cursor/plugins pr-review-canvas](https://github.com/cursor/plugins/tree/main/pr-review-canvas) ·
[Haystack](https://www.producthunt.com/p/haystack-editor/haystack-code-reviewer) ·
[Diffity](https://cdn.jsdelivr.net/gh/nilbuild/diffity@main/README.md) ·
[Reviewable (feature review)](https://gitlab.com/gitlab-org/gitlab-foss/-/issues/27116)

## What they have that we don't

1. **One step at a time.** The tours (Sourcegraph, Graphite, Diffity) show one stop, its
   explanation and the code. We show everything at once.
2. **Restraint.** pr-review-canvas reserves callouts for "genuinely tricky items". We put an
   alert, a strip, checks, comments and link rows on *every* block.
3. **An effort number up front.** CodeRabbit (1–5), Qodo: "how big is this, really?"
4. **Pseudocode and an example trace** for dense logic (pr-review-canvas): confirm the intent
   before reading the syntax.
5. **The right diagram for the change.** Greptile picks a sequence, ER, class or flow diagram,
   and none for trivial PRs. Our graph always looks the same.
6. **A "can be split" verdict** (Qodo). We only state the fact ("two flows, no shared code").
7. **They live inside GitHub.** We're a separate page, by choice: local, works before a PR
   exists.

## What we have that they don't

1. **Unchanged code on the path.** `disableUser()` didn't change, but a public endpoint can now
   trigger it. Every tool above only describes the diff.
2. **Entry points reached:** which routes, jobs and crons can run the changed code.
3. **Intent checks instead of verdicts:** Does → Impact → Intended? Verified against the code;
   the human decides. The others score, judge and label P0.
4. **Exact call-site links and Peek** inside the diff: caller and callee side by side.
5. **Missing tests as a first-class block.**
6. **Independent flows** detected and shown separately (the PR is really two changes).
7. **Deterministic facts kept apart from the LLM,** plus the guarantee that every hunk is
   accounted for. Local, open source, works with any model.

## Takeaway for our design

Keep our differentiators, and adopt their **restraint** and **one-step-at-a-time** focus.
