# 0008. Distribution

Status: Accepted, 2026-10-23

## Context
The target users are TypeScript developers, who live in npm, and Claude Code users,
who install skills and plugins. The binary is Go.

## Decision
- **goreleaser** builds darwin/linux/windows × amd64/arm64 and publishes to:
  - GitHub Releases
  - a Homebrew tap
  - **npm**, in the esbuild/biome pattern: a small `greybeard-review` wrapper
    package with per-platform `optionalDependencies` that hold the binary. The
    command is `greybeard`.
  - `go install github.com/<org>/greybeard/cmd/greybeard@latest`
- The skill ships in the same repo as a **Claude Code plugin**:
  - `.claude-plugin/plugin.json`
  - `skills/greybeard/SKILL.md`
- The skill checks that `greybeard` is on PATH and prints the install command if
  it isn't.
- License: MIT.

## Consequences
- One tag produces every artifact.
- The npm name `greybeard` is taken. Use `@greybeard/cli` if the npm org can be
  registered, otherwise `greybeard-review`.
