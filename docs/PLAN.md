# Greybeard: Development Plan (v1, 100% local)

Decisions: [docs/adr](adr/README.md). Product: [PRD.md](../PRD.md).

## Stack

| Concern | Choice | ADR |
|---|---|---|
| Language | Go, single static binary, no cgo | 0001 |
| CLI | stdlib `flag` + subcommand switch | 0001 |
| Git | `git` CLI via `os/exec` + `bluekeyes/go-gitdiff` | 0003 |
| GitHub | `gh` CLI (optional) | 0003 |
| Code connections | minimal LSP client → `tsgo --lsp` / `typescript-language-server`, grep fallback | 0004 |
| LSP types | `go.lsp.dev/protocol` | 0004 |
| Schemas | Go structs → `invopop/jsonschema` → committed `schemas/*.json` | 0002 |
| Local LLM | any OpenAI-compatible endpoint (Ollama, llama.cpp, LM Studio) via `net/http` | 0006 |
| HTML | `html/template` + `embed`, `alecthomas/chroma`, vanilla JS | 0007 |
| Release | goreleaser → GitHub, Homebrew, npm wrapper, `go install` | 0008 |
| Tests | `go test`, golden files, fixture repos built by script | — |

Four third-party Go dependencies: go-gitdiff, go.lsp.dev/protocol, jsonschema and
chroma.

## Repo layout

```
greybeard/
├── cmd/greybeard/main.go         # subcommand switch: collect, render, review, doctor, eval
├── internal/
│   ├── facts/                    # facts.json + map.json Go types (source of truth), validation
│   ├── git/                      # run git/gh, parse diff → hunks with stable IDs
│   ├── detect/                   # mechanical tags + suspicious flags (ADR 0005)
│   ├── lsp/                      # tiny JSON-RPC/stdio LSP client + server resolution
│   ├── impact/                   # hunk → enclosing symbols → refs/callers/tests
│   ├── engine/                   # Decider + Writer interfaces, local OpenAI-compatible impl
│   └── render/                   # template, assets (css/js) via embed
│       └── assets/
├── schemas/                      # generated: facts.schema.json, map.schema.json
├── skills/greybeard/SKILL.md     # Claude Code skill
├── .claude-plugin/plugin.json
├── evals/                        # labelled hunks for `greybeard eval` (M6)
├── testdata/
│   ├── mkrepo.sh                 # builds fixture git repos deterministically
│   └── golden/                   # expected facts.json / map.json / html snapshots
├── docs/adr/  docs/PLAN.md
├── .goreleaser.yaml
└── go.mod
```

## Commands (v1)

```
greybeard collect [<pr#> | <base>..<head>] [-o facts.json]   # default: current branch vs merge-base with main
greybeard render  <map.json> [-o page.html] [--no-open]
greybeard review  [<pr#> | <range>] --local [--model qwen3:8b] [--endpoint http://localhost:11434/v1]
greybeard doctor                                               # git, gh, tsgo/tsserver, local endpoint
greybeard eval    [--endpoint …]                               # score a Decider on evals/ (M6)
```
`schema` is not a command, because the skill reads `schemas/` from the plugin
directory.

## Milestones

Each milestone ends with something runnable and tested.

### M0: Skeleton (½ day)
- `go mod init`, the `main.go` switch, `doctor` checking git/gh/tsgo
- CI: `go vet`, `go test`, golangci-lint
- `testdata/mkrepo.sh`, which creates a small TS repo with a base and a feature branch
  covering: a rename, a moved function, a formatting-only change, a lockfile bump, a
  real logic change with a caller, and a weakened test

**Done:** `greybeard doctor` runs, and CI is green.

### M1: `collect`, the git and mechanical part (2–3 days)
- `internal/facts`: types for PR meta, commits, files and hunks (ID, path, ranges,
  lines, tags, flags)
- `internal/git`: resolve the base (merge-base with `main`/`master`/`origin/HEAD`), run
  the diffs, parse them, assign hunk IDs
- `internal/detect`: every rule from ADR 0005, each with a table test
- Generate `schemas/facts.schema.json` (`go generate`)

**Done:** golden `facts.json` for the fixture repo. Every hunk is present and the
tags match expectations.

### M2: Code connections via LSP (3–4 days, the riskiest part)
- `internal/lsp`:
  - spawn the server
  - `initialize`
  - `didOpen`
  - `documentSymbol`, `references`, `incomingCalls`, `implementation`
  - timeouts, and shutdown on exit
- Server resolution plus the grep fallback, which marks results as `textual`
- `internal/impact`:
  - hunk → innermost enclosing symbol(s)
  - per symbol: callers, importers, implementers, covering tests
  - nearest tsconfig per file (monorepo)
  - base worktree, only for deleted symbols

**Done:** on the fixture, the changed function lists its real caller and its test,
and a same-named function in another module is not listed. Also tested by hand on
one real-world TS repo.

**Spike first (½ day):** confirm that `tsgo --lsp` answers `references` and
`incomingCalls` on the fixture. If it doesn't, start with `typescript-language-server`.

### M3: `render`, the HTML page (3 days)
- `map.json` types plus validation: every hunk ID appears exactly once (chapter or
  skip list), and chapter order is set
- A hand-written `testdata/golden/map.json` for the fixture
- The template, section by section (PRD "The page"):
  - summary
  - size and shape
  - chapters, with hunks + impact panel + risk + "Can you explain this?"
  - skip list
  - tests vs behaviour
  - Before you send
  - PR description with a copy button
  - coverage line
- chroma highlighting, light and dark mode, keyboard navigation, "understood" checkboxes
- The greybeard voice in section titles and empty states

**Done:** the page renders from the golden map, `render` rejects an incomplete map,
and the HTML snapshot test passes.

### M4: Claude Code skill (2 days), the first usable release
- `skills/greybeard/SKILL.md`. Steps:
  1. Run `greybeard collect`.
  2. Read `facts.json` and `schemas/map.schema.json`.
  3. Read more code only where the facts are thin.
  4. Write `map.json`: chapters in dependency order, intents, risks, the
     before-you-send list and the PR description.
  5. Run `greybeard render`.
  6. Show the path.
- Rules in the skill:
  - It never overrides a mechanical tag.
  - Every hunk is placed.
  - Self-review voice by default.
  - Uncertainty is flagged, never hidden.
- `.claude-plugin/plugin.json`
- First goreleaser release (binaries + npm wrapper + brew)

**Done:** `/greybeard` on the fixture and on one real AI-generated PR produces the
page end to end. **This is the v1 alpha. Use it on our own PRs.**

### M5: GitHub PR input + reviewer mode (1–2 days)
- `collect <pr#>`: `gh pr view`, fetch the head, diff against the base, include
  the PR body and comments
- `map.json` `mode: self | reviewer`. Reviewer mode swaps "Before you send" for "The
  greybeard's questions" and drops the PR description section.

**Done:** works on a public PR number.

### M6: Local engine, no Claude Code (4–5 days)
- `internal/engine`:
  - `Decider` over an OpenAI-compatible endpoint: enum-constrained JSON, plus
    logprob confidence when available
  - `Writer` for prose
- The question set, per hunk:
  - Bool: mechanical, weakened test, debug leftover, related to the goal
  - Choice: layer, chapter
  - Score: risk
- Chapter seeding: cluster hunks by shared symbols and references from M2
  (connected components), then use Choice only for the leftovers
- `greybeard review --local` = collect → engine → render
- `evals/`: ~100 labelled hunks from real PRs, plus `greybeard eval`, which reports
  per-question accuracy and calibration

**Done:** `greybeard review --local` with Ollama produces a valid page, and the eval
baseline is recorded for one small model.

**v1 = M0–M6.** Estimate ~3–4 weeks for one developer.

## Testing strategy
- **Unit:** detector rules (table tests), hunk ID stability, map validation.
- **Golden:** fixture repo → `facts.json`, golden `map.json` → HTML. Update with `-update`.
- **LSP:** integration test behind `-tags lsp`, which needs `tsgo` installed. It runs
  in CI on one job.
- **Engine:** a fake OpenAI-compatible server (`httptest`) for unit tests, plus
  `evals/` for real quality.
- **Dogfood:** from M4 onward, every Greybeard PR gets a Greybeard page.

## Projects to borrow from

| Project | What we take |
|---|---|
| [microsoft/typescript-go](https://github.com/microsoft/typescript-go) | `tsgo --lsp`, our TS code-connection source |
| [meoyawn/tspls](https://pkg.go.dev/github.com/meoyawn/tspls) | Go CLI calling the tsgo language service: prior art for references from Go |
| [bluekeyes/go-gitdiff](https://github.com/bluekeyes/go-gitdiff) | Diff parsing |
| [reviewdog](https://github.com/reviewdog/reviewdog) | Go tool built around diffs and review: structure and diff handling |
| [cli/cli (gh)](https://github.com/cli/cli) | Go CLI conventions and the `gh` JSON fields |
| [difftastic](https://github.com/Wilfred/difftastic) | Ideas for structural/mechanical detection |
| [dandavison/delta](https://github.com/dandavison/delta) | Diff styling and the moved-code idea |
| [diff2html](https://github.com/rtfpessoa/diff2html) | HTML diff layout reference |
| [github-linguist](https://github.com/github-linguist/linguist) | Generated/vendored file rules |
| [goreleaser](https://goreleaser.com) + esbuild/biome npm packaging | Distribution |
| TypeSafe `system-one-adapter-python` | Typed-decision interface on top of general LLMs |
| Sourcegraph Guided Diff Tour, Graphite Code Tours | Product and UX references |

## Risks

| Risk | Mitigation |
|---|---|
| `tsgo --lsp` lacks a request we need, or is slow on big repos | M2 spike; fallback to `typescript-language-server`, then grep; depth-1 impact only |
| Monorepo tsconfig handling | Nearest-tsconfig per file; test on one real monorepo in M2 |
| LLM misplaces or drops hunks | `render` validation rejects it; the skill retries with the missing IDs |
| Small local models give poor prose | Page shows the engine; eval set; skill engine stays the default |
| Ollama logprobs unreliable | Confidence is optional in the schema; llama.cpp is documented as the "best confidence" option |
