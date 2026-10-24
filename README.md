# Greybeard

> Show your PR to the greybeard before anyone else sees it.

AI makes pull requests huge, and even their authors can't explain them. Greybeard is a
[Claude Code](https://claude.com/claude-code) skill that turns a PR or a local branch into a
guided review page:
- **A brief** with a connection map of each flow in the change.
- **A few stops**, one block of code per screen. Each shows where the block is called
  from, why it matters, what it calls, and the unchanged code on the path.
- **Intent checks** at each stop. Greybeard traces what the code does and its impact,
  then asks *"is this what you intended?"*. It points; you judge.
- **A skim list** for everything mechanical. Every hunk is accounted for.
- **A final screen** with your answers and a draft PR description.

**Status:** early. The skill works end to end on real PRs. See [`docs/`](docs/) for the
research, PRD, architecture decisions and design prototypes.

## Use it

Requires Python 3, git, and [gh](https://cli.github.com) for PR numbers.

```bash
git clone https://github.com/yuribodo/greybeard
ln -s "$PWD/greybeard/skills/greybeard" ~/.claude/skills/greybeard
```

Then, in Claude Code inside your repo: *"review my branch with greybeard"*, or *"walk me
through PR #123"*.

The scripts also run on their own:

```bash
python3 skills/greybeard/scripts/collect.py --pr 123       # → .greybeard/facts.json
python3 skills/greybeard/scripts/build.py .greybeard/facts.json .greybeard/review.json
```

## Develop

```bash
python3 -m unittest discover -s tests
```

## License

MIT. The test fixture in `tests/fixtures/documenso-3446/` contains AGPL-3.0 code; see its
`NOTICE.md`.
