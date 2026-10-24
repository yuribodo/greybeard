# 0006. LLM step: Claude Code skill first, then a local typed-decision layer

Status: Accepted, 2026-10-23

## Context
v1 runs 100% locally. Jev (TypeSafe) is the inspiration for the *decision* half:
typed answers (Bool/Choice/Score) with a confidence value, fast and cheap. Jev's
weights are closed and it's a hosted API, so it doesn't fit local v1. TypeSafe's
open-source `system-one-adapter-python` shows the same interface can run on top
of general LLMs.

## Decision
Two engines fill in `map.json`:

1. **Skill engine (M4, the default).** The Claude Code skill runs `greybeard collect`,
   reads `facts.json` and the schema, writes `map.json`, then runs
   `greybeard render`. Claude does both the decisions and the writing.
2. **Local engine (M6): `greybeard review --local`.** Greybeard calls any
   **OpenAI-compatible endpoint**: Ollama, llama.cpp `llama-server`, LM Studio or
   vLLM.
   - **Decider**, our own small open Jev-like layer, implemented in Go:
     - Each question is `{id, kind: bool|choice|score, prompt, options}`.
     - The output is constrained with a JSON schema whose answer is an `enum`.
     - When the server returns logprobs, confidence = the normalised probability
       of the chosen option's first token. Otherwise the answer is sampled with
       `confidence: null`.
     - Answers below a threshold are shown as "unsure" on the page.
   - **Writer:** the same endpoint, free text, one call per chapter plus one for
     the summary and PR description.
   - Default model: a small instruct model (Qwen3/Gemma-class, 4–8B). It's
     configurable.

```go
type Decider interface { Decide(ctx, state string, qs []Question) ([]Answer, error) }
type Writer  interface { Write(ctx, prompt string, schema any) (json.RawMessage, error) }
```
Post-v1, the Greybeard Cloud backend (Jev) implements the same `Decider`.

## Consequences
- An **eval set** is needed from M6 onward: `evals/` holds labelled hunks (mechanical?
  risk? weakened test?), plus a `greybeard eval` command that scores any `Decider`.
  It's also how we compare against Jev later.
- Small local models are weaker at writing. The page says which engine produced it.
- Logprob support varies by server. llama.cpp exposes it, Ollama's needs verifying
  per version. The code handles its absence.
- No Python dependency: we reimplement the adapter idea (~150 lines), we don't
  wrap it.
