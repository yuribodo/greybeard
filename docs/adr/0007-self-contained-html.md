# 0007. Output is one self-contained HTML file

Status: Accepted, 2026-10-23

## Context
The page must open offline, be easy to attach or share, and not need a server or
a build step.

## Decision
- `greybeard render` writes **one `.html` file** with CSS and JS inlined. It uses
  `html/template` with `embed` for the assets.
- Server-side syntax highlighting uses **`alecthomas/chroma`** (pure Go), so there's
  no JS highlighting library.
- **The diff markup is our own,** with no diff2html, because we already have parsed
  hunks and need custom per-hunk UI (impact panel, tags, risk badge).
- Vanilla JS (~200 lines), used only for:
  - expanding and collapsing
  - "mark chapter as understood", saved in `localStorage` per hunk-set hash
  - keyboard navigation (`j`/`k`, `n` for the next chapter)
  - a copy button on the PR description
- Light and dark mode through CSS variables and `prefers-color-scheme`.
- Output goes to `.greybeard/<branch>-<shortsha>.html` (gitignored), and the file is
  opened with `open`/`xdg-open` unless `--no-open` is passed.
- Layout and UX references: Sourcegraph Guided Diff Tour, Graphite Code Tours,
  diff2html and delta (for diff styling).

## Consequences
- No npm toolchain in the repo.
- Large PRs make big files. Collapsed chapters render lazily from an inlined JSON
  blob if size becomes a problem (not in v1).
