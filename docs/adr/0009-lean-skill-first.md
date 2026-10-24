# 0009. Ship v1 as a Claude Code skill with two small Python scripts

Status: Accepted, 2026-10-23. Defers 0001, 0004, 0006 (local engine) and 0008.

## Context
The design prototype (`docs/design/guided.html`) was produced with three things:
- a ~25-line diff parser
- Claude reading the code and writing the review data
- a tiny build script that injects that data into an HTML template

That *is* the product loop. The Go binary, our own LSP client, the local LLM engine
and multi-channel distribution (ADRs 0001, 0004, 0006, 0008) add 3–4 weeks before
anyone can use it, and nobody needs them yet.

## Decision
v1 is a skill in `skills/greybeard/`:
- **`scripts/collect.py`**: a git/gh diff turned into `facts.json` (hunks with old/new
  line numbers, file tags). Python stdlib only.
- **Claude, following `SKILL.md`**: reads `facts.json` and the code, using Claude Code's
  LSP tool when available and grep otherwise, then writes `review.json`.
- **`scripts/build.py`**: validates `review.json` against `facts.json` and refuses
  missing hunks or broken references. It injects both into
  `assets/review.tpl.html` and writes one HTML file.
- The contract lives in `references/review-format.md`.

## Consequences
- Usable in days. It's validated on real PRs before investing in anything else.
- Requires Python 3 and git (plus `gh` for PR numbers).
- **Deferred, not dropped:** revisit the Go binary, distribution and the local engine
  once the skill has been useful on about 5 real PRs.
- `rough.js` loads from a CDN for now. Inline it before sharing pages that must work
  offline (ADR 0007).
