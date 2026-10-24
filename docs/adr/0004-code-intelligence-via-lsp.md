# 0004. Code connections via LSP

Status: Accepted, 2026-10-23

## Context
The core feature is "for each changed block, what does it connect to and what does it
impact?". Grep gives false matches (same name, other symbol) and misses aliased
imports and re-exports. TypeScript 7 (`tsgo`, the native Go port) shipped in July 2026
with an LSP server (`tsgo --lsp`) that doesn't need Node.js. Older projects use
`typescript-language-server`.

## Decision
- Greybeard includes a **minimal LSP client** (JSON-RPC over stdio) that uses only
  these requests:
  - `initialize`
  - `textDocument/didOpen`
  - `textDocument/documentSymbol`: maps each hunk to the symbols that enclose it
  - `textDocument/references`
  - `callHierarchy/incomingCalls`
  - `textDocument/implementation`
- It uses the `go.lsp.dev/protocol` types.
- Server resolution order:
  1. `node_modules/.bin/tsgo --lsp`
  2. `tsgo` on PATH
  3. `typescript-language-server --stdio`
  4. **grep fallback**, with each result marked `confidence: "textual"` on the page
- It runs **on the head checkout only**. A symbol that was deleted gets its references
  from the base, using a `git worktree` at the base commit, only when needed.
- Impact is capped at depth 1: direct callers and importers. "Show more" is a later
  feature.
- Test files that reference a changed symbol become its "covering tests".

## Consequences
- Other languages work with no Greybeard code changes once their server is
  configured (gopls, pyright, rust-analyzer). v1 only *tests* TypeScript.
- Monorepos have one LSP root per tsconfig project. Greybeard picks the nearest
  `tsconfig.json` for each file.
- The LSP server needs a working install (`node_modules` present). `greybeard doctor`
  reports when it isn't, and the run falls back to grep instead of failing.
- References: `microsoft/typescript-go`, `meoyawn/tspls` (calls the tsgo language
  service in process, useful prior art), `go.lsp.dev/protocol`.
