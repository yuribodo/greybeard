# 0002. Pipeline joined by a JSON contract

Status: Accepted, 2026-10-23

## Context
The work splits into deterministic steps (collect facts, render the page) and a
judgment step (group, order, explain). The judgment step has several possible
engines: Claude Code (skill), a local model, and later Greybeard Cloud. Every one
of them must plug in without touching the others.

## Decision
```
greybeard collect → facts.json → [judgment engine] → map.json → greybeard render → page.html
```
- **`facts.json`**: everything computed without an LLM. It holds the PR metadata,
  the commits, every hunk with a stable ID, the mechanical tags (ADR 0005), and the
  changed symbols with their references (ADR 0004).
- **`map.json`**: facts plus judgment. It holds the summary, the chapters (an
  ordered list of hunk IDs plus intent and risk), the skip list, tests vs behaviour,
  the before-you-send list and the draft PR description.
- Judgment fields are split into **decisions** (Bool/Choice/Score + confidence) and
  **writing** (prose), so the decisions can be swapped for a typed-decision backend
  such as Jev later (ADR 0006).
- The Go structs are the source of truth. `schemas/*.schema.json` is generated from
  them with `invopop/jsonschema` and committed, so the skill and any LLM get the
  exact schema.
- Each file has a `version` field.

## Consequences
- `render` validates `map.json` and **refuses a map that doesn't account for every
  hunk ID**. This enforces the coverage guarantee in code, not in a prompt.
- A user can hand-edit `map.json` and re-render, which also makes it a debugging
  tool.
- Future consumers (a GitHub Action, PR comments, a VS Code panel) read `map.json`.
