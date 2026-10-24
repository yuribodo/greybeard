# Architecture Decision Records

Format: Context → Decision → Consequences. A record is never edited after it's
accepted. To change a decision, write a new ADR that supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-go-single-binary.md) | Go, shipped as a single binary | Deferred by 0009 |
| [0002](0002-pipeline-json-contract.md) | Pipeline joined by a JSON contract: `facts.json` → `map.json` | Accepted |
| [0003](0003-git-cli-diff-parsing.md) | Shell out to the git CLI and parse its unified diff | Accepted |
| [0004](0004-code-intelligence-via-lsp.md) | Code connections via LSP (`tsgo --lsp` first) | Deferred by 0009 |
| [0005](0005-deterministic-mechanical-detection.md) | Mechanical-change detection is deterministic, with no LLM | Accepted |
| [0006](0006-llm-step-skill-and-local-typed-decisions.md) | LLM step: Claude Code skill first, then a local typed-decision layer | Skill engine accepted; local engine deferred by 0009 |
| [0007](0007-self-contained-html.md) | Output is one self-contained HTML file | Accepted |
| [0008](0008-distribution.md) | Distribution via goreleaser, npm, Homebrew and a Claude Code plugin | Deferred by 0009 |
| [0009](0009-lean-skill-first.md) | v1 is a Claude Code skill with two small Python scripts | Accepted |
