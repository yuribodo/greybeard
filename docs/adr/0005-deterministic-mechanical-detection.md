# 0005. Mechanical-change detection is deterministic

Status: Accepted, 2026-10-23

## Context
Separating noise from signal is the cheapest, most trusted win (RAID, difftastic).
An LLM saying "this is just formatting" is a claim. A hash comparison is a fact.

## Decision
`collect` tags hunks and files in Go, with no LLM:

| Tag | Rule |
|---|---|
| `lockfile` | `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock*`, `go.sum`, … |
| `generated` | `.gitattributes` `linguist-generated`, or a header such as `@generated` / `DO NOT EDIT`, or paths like `dist/`, `*.min.js`, `__snapshots__/` |
| `vendored` | `vendor/`, `third_party/`, `linguist-vendored` |
| `rename` | git `R100` (pure rename, no content change) |
| `whitespace` | the hunk disappears in the `-w` diff |
| `moved` | the removed block equals an added block elsewhere after normalising whitespace (hash of trimmed lines, min 3 lines) |
| `import-only` | every changed line is an `import`/`export … from` line (TS/JS) |
| `test` | path matches `*.test.*`, `*.spec.*`, `__tests__/`, `test/` |

Suspicious-pattern flags (`facts.flags[]`) are also regex/AST-light rules:
- `console.log` / `debugger` added
- `.only(` / `.skip(` added
- an `expect(` line removed
- `// @ts-ignore` / `eslint-disable` added
- `TODO` / `FIXME` added
- `catch` with an empty body added

## Consequences
- These tags are shown as facts on the page, and the LLM can't overrule them.
- New rules are a table entry plus a fixture test.
- Inspired by GitHub Linguist's generated/vendored rules (we copy the idea, not
  the code).
