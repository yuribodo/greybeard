# Greybeard: Data Flow

How the code is collected, how the parts talk to each other, and how data reaches the
HTML page. This refines [ADR 0002](adr/0002-pipeline-json-contract.md) down to the
field level.

## 1. End to end

```
                ┌──────────────────────────── greybeard collect ────────────────────────────┐
 branch / PR ─▶ │ git.ResolveRange → git.Diff ×2 → git.Parse → detect.Tag → impact.Analyze  │ ─▶ facts.json
                └────────────────────────────────────────────────────────────────────────────┘
                                                                                                 │
                                      ┌──────── judgment engine ────────┐                       ▼
                                      │ skill (Claude)   or   --local   │ ◀── reads facts.json + map.schema.json
                                      │ writes ONLY judgment fields     │
                                      └─────────────────────────────────┘
                                                      │
                                                      ▼
                                                  map.json  (points to facts.json by path + sha256)
                                                      │
                ┌──────────────────────────── greybeard render ─────────────────────────────┐
                │ facts.Load + facts.LoadMap → facts.Validate → render.BuildView → template │ ─▶ page.html
                └────────────────────────────────────────────────────────────────────────────┘
```

**Rule:** facts flow forward and never come back. The LLM never re-types the code or
the facts. It only refers to them **by ID** (`hunkId`, `symbolId`). That keeps
`map.json` small (cheap tokens) and makes it impossible for the model to change
the code it's describing.

## 2. `collect`: function by function

| Step | Package / function | Input → output |
|---|---|---|
| 1 | `git.ResolveRange(arg)` | `""` / `main..feat` / `#123` → `Range{Base, Head, MergeBase}`. For a PR, `gh pr view` + `git fetch` first. |
| 2 | `git.Diff(r, opts)` | Runs `git diff -M -C --histogram --no-color` **twice**: normal and `-w`. → two raw strings. |
| 3 | `git.Parse(raw)` | go-gitdiff → `[]File{Path, OldPath, Status, Binary, Hunks}`. Each hunk gets `ID = sha1(path+ranges+lines)[:10]`. |
| 4 | `detect.Tag(files, wsRaw, repo)` | Adds `tags[]` (lockfile, generated, whitespace, moved, rename, import-only, test) and `flags[]` (console-log, only-skip, expect-removed, ts-ignore, todo, empty-catch). Pure function, table-tested. |
| 5 | `impact.Analyze(ctx, files, repoDir)` | Starts the LSP server once (`lsp.Start`). For each non-mechanical hunk: `documentSymbol` → enclosing symbols, then `references`, `incomingCalls` and `implementation` per symbol. → `[]Symbol` linked to hunk IDs. Falls back to grep with `source: "textual"`. |
| 6 | `facts.Write(path, Facts)` | Writes JSON + `sha256`. |

The packages talk through plain Go structs from `internal/facts`, with no interfaces,
except two narrow ones: `lsp.Client` (so tests can fake it) and `engine.Decider/Writer`.

## 3. `facts.json` (draft)

```jsonc
{
  "version": 1,
  "generatedAt": "2026-10-23T14:02:11Z",
  "repo":  { "root": "/home/me/app", "remote": "github.com/me/app" },
  "range": { "base": "main", "head": "feat/webhook-retry", "mergeBase": "a1b2c3d", "headSha": "9f8e7d6" },
  "pr":    { "number": 123, "title": "Retry webhook delivery", "body": "…", "url": "…" },   // null for local branches
  "commits": [ { "sha": "9f8e7d6", "subject": "add retry with backoff" } ],
  "stats": { "files": 23, "hunks": 312, "added": 1840, "removed": 402 },
  "files": [
    {
      "path": "src/webhooks/deliver.ts", "oldPath": null, "status": "modified",
      "language": "typescript", "tags": [],
      "hunks": [
        {
          "id": "h_3fa91c02ab",
          "oldStart": 40, "oldLines": 3, "newStart": 40, "newLines": 7,
          "header": "export async function deliver(",
          "lines": [ { "op": "-", "text": "  await post(url, body)" },
                     { "op": "+", "text": "  for (let i = 0; i < MAX_TRIES; i++) {" } ],
          "tags":  [],
          "flags": [ { "kind": "empty-catch", "line": 43 } ],
          "symbols": [ "s_deliver" ]
        }
      ]
    }
  ],
  "symbols": [
    {
      "id": "s_deliver", "name": "deliver", "kind": "function",
      "path": "src/webhooks/deliver.ts", "line": 38, "source": "lsp",          // or "textual"
      "callers":      [ { "name": "processEvent", "path": "src/webhooks/queue.ts", "line": 42 } ],
      "importers":    [ "src/webhooks/queue.ts", "src/routes/stripe.ts" ],
      "implementers": [],
      "tests":        [ { "path": "src/webhooks/deliver.test.ts", "line": 12 } ]
    }
  ],
  "lsp": { "server": "tsgo", "version": "7.0.2", "ok": true }
}
```

## 4. `map.json` (draft): judgment only

```jsonc
{
  "version": 1,
  "facts": { "path": ".greybeard/facts.json", "sha256": "…" },     // render refuses if the hash doesn't match
  "mode": "self",                                                  // or "reviewer"
  "engine": { "kind": "skill", "model": "claude-opus-5-5" },       // shown on the page
  "summary": {
    "claims":  "Retry webhook delivery on failure.",
    "actual":  [ "Adds exponential backoff to deliver()", "Parks events after 5 failures", "Weakens one test" ],
    "mismatch": "PR body doesn't mention the parked-events table."
  },
  "verdict": { "kind": "split", "reason": "Two unrelated concerns: retry policy and a logger refactor." },
  "chapters": [
    {
      "id": "c3", "order": 3, "title": "Retry policy for webhook delivery",
      "layer": "core",                                             // decision: choice
      "intent": "Failed deliveries retry with backoff, five times max.",
      "hunks": [ "h_3fa91c02ab", "h_77c0d1e9f2" ],                 // reading order inside the chapter
      "risk": { "score": 4, "reason": "Payment path; the catch swallows errors.", "confidence": 0.86 },
      "checks": [ "What happens after the fifth failure?" ],
      "dependsOn": [ "c2" ]
    }
  ],
  "skipped": [ { "hunk": "h_aa01…", "reason": "lockfile" } ],     // mechanical tags come from facts; reason must match
  "tests": [ { "chapter": "c3", "status": "weakened", "hunk": "h_t1…", "note": "toBe(3) → toBeGreaterThan(0)" } ],
  "beforeSend": [ { "severity": "high", "text": "Restore the exact retry-count assertion.", "hunk": "h_t1…" } ],
  "prDescription": "## What\n…"
}
```

## 5. `render`: how data gets into the page

1. `facts.Load` + `facts.LoadMap`, then check the sha256 against `map.facts.sha256`.
2. `facts.Validate(f, m)` checks:
   - every hunk ID appears **exactly once** across `chapters[].hunks` and `skipped[]`
   - every referenced ID exists
   - no mechanical-tagged hunk sits in a chapter unless it is explicitly marked
     `"kept": true`
   - chapter `order` is unique
   It fails with a list of the offending IDs, which the skill feeds back to the LLM.
3. `render.BuildView(f, m)` joins the two into one `View` struct, shaped like the page:
   `View{Header, Summary, Verdict, Chapters[]{Title, Intent, Risk, Hunks[]{Path, Lines (pre-highlighted HTML via chroma), Flags}, Impact[]{Symbol, Callers, Importers, Tests}}, Skipped (grouped by reason), Tests, BeforeSend, PRDescription, Coverage}`.
   All joining logic is here, in Go, and unit-tested. The template does no lookups.
4. `html/template` executes `page.tmpl` with the `View`. CSS and JS come from `embed`
   and are inlined. The output is one file.
5. A small `<script type="application/json" id="gb-data">` holds only what the JS
   needs: chapter IDs, hunk IDs and a `storageKey = sha256(headSha+hunkIds)`
   used for the "understood" ticks in `localStorage`. The page is fully readable
   with JS off.

## 6. The skill's loop (M4)

```
greybeard collect -o .greybeard/facts.json
→ Claude reads facts.json + schemas/map.schema.json (reads extra source files only where facts are thin)
→ Claude writes .greybeard/map.json
→ greybeard render .greybeard/map.json
   ├─ ok  → prints the page path, opens it
   └─ err → "missing hunks: h_…, h_…" → Claude fixes map.json → render again (max 2 retries)
```

## 7. Still open
- Very large PRs: facts.json can be big for the LLM. Plan: `collect --summary` emits
  hunks without `lines` for mechanical hunks; the skill reads full lines per chapter.
- Whether `checks[]` and `beforeSend[]` link to specific line numbers or just hunks.
