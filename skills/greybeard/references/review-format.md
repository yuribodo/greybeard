# Greybeard data format

The pipeline:

```
collect.py  →  facts.json  →  you (Claude) write review.json  →  build.py  →  review.html
```

- `facts.json` is produced by a script. Never edit it.
- `review.json` is your judgment, and it refers to the facts by **file path and line
  number only**. Never copy code into it, except unchanged context in `snippets`.

## facts.json (written by `scripts/collect.py`)

```jsonc
{
  "version": 1,
  "source": {
    "kind": "pr",                       // "pr" (gh) or "local" (git range)
    "repo": "documenso/documenso",      // "owner/name" for PRs, the repo path for local
    "base": "main", "head": "feat/x",   // branch names, or refs for local
    "pr": {                             // null when kind == "local"
      "number": 3446, "title": "…", "url": "https://github.com/…", "author": "Mythie",
      "body": "…", "state": "MERGED", "mergedAt": "2026-10-15T04:10:24Z"
    },
    "commits": ["feat: …", "…"]          // subjects, oldest first
  },
  "stats": {"files": 16, "additions": 484, "deletions": 11},
  "files": {
    "packages/lib/utils/sender-trust.ts": {
      "status": "added",                // added | modified | deleted | renamed
      "old_path": null,                 // set when renamed
      "tags": [],                       // any of: lockfile, generated, test, binary
      "hunks": [
        {
          "ctx": "export const run = async",   // text after the second @@, may be ""
          "lines": [
            ["+", "import type { OrganisationClaim } from '@prisma/client';", null, 1],
            [" ", "unchanged line", 12, 14],
            ["-", "removed line", 13, null]
          ]                             // [op, text, old line | null, new line | null]
        }
      ]
    }
  }
}
```

## review.json (written by you)

```jsonc
{
  "version": 1,
  "pr": {                       // shown in the header; copy from facts.source
    "title": "feat: disable accounts on report…", "number": 3446,
    "url": "https://github.com/documenso/documenso/pull/3446", "author": "Mythie",
    "base": "main", "head": "feat/disable-accounts-on-report",
    "state": "merged",          // lowercase: merged | open | draft | local (facts has "MERGED")
    "date": "Oct 15, 2026"      // optional, free text
  },
  "lead": "One or two plain sentences: what this PR changes, in behaviour terms.",
  "flows": [{"id": "A", "title": "A · A report can disable the sender"}],

  "stops": [{
    "id": "route",              // unique; used in links
    "flow": "A",                // a flows[].id, or "both"
    "name": "reportRecipientRoute",
    "att": "high",              // high = "Look closely", med = "Worth a look"
    "kind": "tRPC procedure · public",
    "why": "One sentence: why the reviewer is here.",
    "from": [                   // who leads here. "to" links to another stop; omit it for context
      {"to": "drs", "label": "disableReportedSender", "at": "disable-reported-sender.ts:49"},
      {"label": "/report/$token page", "at": "report.$token.tsx:43"}   // "at": file:line, or just the file for a page
    ],
    "src": [                    // the code shown, in order; each needs a path from facts.files or snippets
      {"path": "packages/…/report-recipient.ts", "range": [92, 105]},   // new-file line range; omit = whole file
      {"path": "packages/…/disable-user.ts", "snip": true},             // unchanged code from snippets
      {"path": "…", "range": [173, 178], "title": "send-signing-email · user = who sent it"}
    ],
    "note": {"path": "packages/…/report-recipient.ts", "line": 98,       // optional, at most one per stop
             "text": "Points at something. Never a verdict."},
    "calls": [                  // what this code calls. "to" is a stop id or "skim"
      {"to": "drs", "label": "disableReportedSender", "line": 98},       // line: where the call is (or null)
      {"to": "skim", "skim": "job", "label": "send.account.disabled.email", "line": 62}
    ],
    "checks": [{                // 1–2 per stop
      "does":   "What the code does, traced and verified.",
      "impact": "The concrete consequence.",
      "ask":    "Is that what you intended?",
      "alt":    "Optional: a real alternative that already exists in the code."
    }]
  }],

  "skim": [{"id": "job", "name": "send.account.disabled.email",
            "desc": "One line on what it is and why it needs no decision.",
            "files": [
              "packages/lib/jobs/definitions/emails/send-account-disabled-email.handler.ts",   // whole file
              {"path": "packages/…/report-recipient.ts", "range": [3, 3]}  // part of a file: e.g. an import in a file that also has a stop
            ]}],

  "snippets": {                 // unchanged code worth showing (callers, code on the path).
                                // a dependency's code works too: give "lines" yourself, title the src with package@version
    "packages/lib/server-only/user/disable-user.ts": [   // one block, or a list of blocks
      {"start": 26, "end": 31},  // preferred: build.py reads these lines from the repo, no copying
      {"start": 40, "lines": ["      await tx.webhook.updateMany({", "…"]}   // or give the lines yourself
    ]
  },

  "peek": {                     // optional: what "Peek" shows for a stop (default: its first src).
                                // set it when the first src is long: peek the few lines that define the block
    "drs": {"path": "packages/…/disable-reported-sender.ts", "range": [46, 53]}
  },

  "graph": {                    // the connection map; one diagram per flow
    "nodes": [
      {"id": "page",  "flow": "A", "label": "/report/$token", "kind": "page", "ctx": true},   // context, unchanged
      {"id": "route", "flow": "A", "label": "reportRecipientRoute", "kind": "tRPC · public", "stop": "route"},
      {"id": "job",   "flow": "A", "label": "account-disabled email", "kind": "job", "skim": true},
      {"id": "tA",    "flow": "A", "label": "report-sender.spec.ts", "kind": "e2e test", "stop": "tests", "lane": true},
      {"id": "tB",    "flow": "B", "label": "no tests", "kind": "missing", "stop": "tests", "lane": true, "missing": true}
    ],
    "edges": [["page", "route", "public"], ["route", "drs", "calls"], ["tA", "page", "drives"]],   // caller → callee, or changed → "same lookup as"
    "cross": [{"from": "tpl", "to": "page", "label": "Report link → flow A"}]                     // links between flows
  },

  "prDescription": "Markdown draft for the PR description (useful when the PR has none)."
}
```

### Graph node kinds

| Field | Meaning | Look | Click goes to | Combine with |
|---|---|---|---|---|
| `stop` | a review stop (its id) | solid box, numbered | that stop | `lane` for test stops |
| `skim` | a skim item | dashed box | the skim list | — |
| `ctx` | unchanged code on the path (entry points, callers) | dashed box | nothing | — |
| `lane` | sits in the Tests lane on the right | — | — | `stop`, `skim` (tests that need no decision), or `missing` |
| `missing` | a verified gap: a test, a registry entry, a migration that should exist | red dashed box | its `stop` if it has one | `lane` (tests); `stop` is optional |

A node with none of `stop`, `skim` or `ctx` is still drawn, but it can't be clicked.
A `lane` node must have an outgoing edge (to the block it tests or should test), since
that's what places it in the lane.

## What build.py enforces

It refuses to build, and lists every problem, when:
- **A hunk isn't covered.** Every hunk in `facts.files` must be either inside a stop's
  `src` (same path, with a `range` that overlaps the hunk, or no `range`) or in a `skim`
  entry (the whole file, or a `{path, range}` that overlaps the hunk). This is how "nothing is hidden" is guaranteed.
- **A reference is broken.** That covers:
  - `from[].to`, `calls[].to` / `calls[].skim`
  - `graph` node `stop` and edge ends
  - `cross` ends and `peek` keys
  - a `src` path that is neither in `facts.files` nor in `snippets` (with `snip: true`)
- **A stop is malformed.** That covers:
  - no `checks`, or more than 2
  - a check missing `does`, `impact` or `ask`
  - a `note` whose line isn't among the lines the stop shows
- **Something is missing or duplicated:** missing required fields, or duplicate `id`s.
