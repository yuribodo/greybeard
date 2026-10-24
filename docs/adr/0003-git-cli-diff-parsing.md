# 0003. Shell out to the git CLI and parse its unified diff

Status: Accepted, 2026-10-23

## Context
We need rename and copy detection, the histogram algorithm, whitespace-insensitive
comparison, `range-diff` (later) and the user's own git config. go-git implements
only part of that.

## Decision
- Run the user's `git` via `os/exec`:
  - the diff: `git diff --no-color --no-ext-diff -M -C --diff-algorithm=histogram <base>...<head>`
  - the whitespace check: the same diff with `-w`
- Parse the output with **`github.com/bluekeyes/go-gitdiff`** (pure Go, handles
  renames, binary files and modes).
- GitHub PRs: `gh pr view --json title,body,baseRefName,headRefName,commits,files`,
  then fetch the head and diff locally. With no `gh`, local branches still work.
- Hunk ID = `sha1(path + old range + new range + content)`, truncated. It stays
  stable across runs of the same diff.

## Consequences
- Requires git ≥ 2.30 on PATH (a `doctor` check reports it).
- Behaviour matches what the user sees in `git diff`, with no surprises.
