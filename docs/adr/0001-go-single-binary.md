# 0001. Go, shipped as a single binary

Status: Accepted, 2026-10-23

## Context
Greybeard is a CLI that runs on developers' machines and in CI. It shells out to git,
talks to language servers, calls local LLMs and renders HTML. The first target is
TypeScript repos, but the tool itself should not need Node.js installed to run.

## Decision
Write Greybeard in **Go**, shipped as one static binary.

## Consequences
- One file to install, fast startup, and trivial cross-compilation (`GOOS/GOARCH`).
- The standard library covers what we need: `os/exec` (git, LSP servers),
  `net/http` (LLM endpoints), `html/template` + `embed` (the page) and
  `encoding/json` (the contract).
- We can't import the TypeScript compiler API directly. Code connections come
  from a language server over LSP instead (ADR 0004), which also makes other
  languages possible later.
- **No cgo**, which rules out tree-sitter bindings. Symbol boundaries come from LSP
  `documentSymbol` (ADR 0004).
- CLI parsing uses the stdlib `flag` package with a subcommand switch. Upgrade to
  cobra only if the command surface grows past ~5 commands.
