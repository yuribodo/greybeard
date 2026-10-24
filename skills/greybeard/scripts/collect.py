#!/usr/bin/env python3
"""Turn a PR or a local git range into facts.json (see references/review-format.md)."""
import argparse, json, os, re, shutil, subprocess, sys

HUNK = re.compile(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)")
LOCKFILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "Cargo.lock",
             "go.sum", "poetry.lock", "composer.lock", "Gemfile.lock"}
GENERATED = ("dist/", "build/", "__generated__", ".min.js", ".min.css", "__snapshots__")
TESTS = (".test.", ".spec.", "__tests__/", "/tests/", "/test/")


class Fail(Exception):
    pass


def path_tags(path):
    # shortcut: tags come from path substrings only, upgrade to real globs if false positives show up
    p = "/" + path
    tags = []
    if path.rsplit("/", 1)[-1] in LOCKFILES: tags.append("lockfile")
    if any(g in p for g in GENERATED): tags.append("generated")
    if any(t in p for t in TESTS): tags.append("test")
    return tags


def parse_diff(text):
    files, cur, in_hunk, o, n = {}, None, False, 0, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            # shortcut: assumes unquoted paths without " b/" in them; ---/+++/rename lines override when present
            a, _, b = line[len("diff --git a/"):].partition(" b/")
            cur = {"status": "modified", "old_path": None, "tags": [], "hunks": [], "_a": a, "_b": b}
            files[b] = cur; in_hunk = False
            continue
        if cur is None: continue
        m = HUNK.match(line)
        if m:
            o, n = int(m.group(1)), int(m.group(2))
            cur["hunks"].append({"ctx": m.group(3).strip(), "lines": []}); in_hunk = True
            continue
        if not in_hunk:  # file header lines
            if line.startswith("new file mode"): cur["status"] = "added"
            elif line.startswith("deleted file mode"): cur["status"] = "deleted"
            elif line.startswith("rename from "): cur["status"], cur["_a"] = "renamed", line[12:]
            elif line.startswith("rename to "): cur["_b"] = line[10:]
            elif line.startswith("--- a/"): cur["_a"] = line[6:]
            elif line.startswith("+++ b/"): cur["_b"] = line[6:]
            elif line.startswith("Binary files ") and line.endswith(" differ"): cur["tags"].append("binary")
            continue
        op, body = (line[:1] or " "), line[1:]
        if op == "\\": continue  # "\ No newline at end of file"
        cur["hunks"][-1]["lines"].append([op, body, o if op != "+" else None, n if op != "-" else None])
        if op != "+": o += 1
        if op != "-": n += 1

    out, adds, dels = {}, 0, 0
    for f in files.values():
        a, b = f.pop("_a"), f.pop("_b")
        path = a if f["status"] == "deleted" else b
        if f["status"] == "renamed": f["old_path"] = a
        lines = [l for h in f["hunks"] for l in h["lines"]]
        tags = path_tags(path) + f["tags"]
        if "generated" not in tags and any("@generated" in l[1] or "DO NOT EDIT" in l[1] for l in lines):
            tags.append("generated")
        f["tags"] = tags
        adds += sum(l[0] == "+" for l in lines)
        dels += sum(l[0] == "-" for l in lines)
        out[path] = f
    return {"stats": {"files": len(out), "additions": adds, "deletions": dels}, "files": out}


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        raise Fail(f"{cmd[0]} is not installed or not on PATH")
    if r.returncode != 0:
        raise Fail(f"`{' '.join(cmd)}` failed: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def git(repo, *args):
    return run(["git", *args], repo)


def default_base(repo):
    for ref in ("origin/HEAD", "main", "master"):
        if subprocess.run(["git", "rev-parse", "--verify", "-q", ref], cwd=repo, capture_output=True).returncode == 0:
            return ref
    raise Fail("could not find a default branch (tried origin/HEAD, main, master); pass a RANGE")


def collect_local(repo, rng):
    top = git(repo, "rev-parse", "--show-toplevel").strip()
    if rng:
        base, sep, head = rng.partition("...") if "..." in rng else rng.partition("..")
        if not sep or not base or not head: raise Fail(f"bad range {rng!r}, expected BASE..HEAD or BASE...HEAD")
    else:
        base, head = default_base(top), git(top, "rev-parse", "--abbrev-ref", "HEAD").strip()
    diff = git(top, "diff", "--no-color", "--no-ext-diff", "-M", "--diff-algorithm=histogram", f"{base}...{head}")
    commits = git(top, "log", "--reverse", "--format=%s", f"{base}..{head}").splitlines()
    source = {"kind": "local", "repo": top, "base": base, "head": head, "pr": None, "commits": commits}
    return source, diff, top


def collect_pr(repo, pr):
    if not shutil.which("gh"): raise Fail("gh (GitHub CLI) is not installed; see https://cli.github.com")
    diff = run(["gh", "pr", "diff", pr], repo)
    v = json.loads(run(["gh", "pr", "view", pr, "--json",
                        "number,title,url,author,body,state,mergedAt,baseRefName,headRefName,commits"], repo))
    m = re.match(r"https?://[^/]+/([^/]+/[^/]+)/pull/", pr)
    name = m.group(1) if m else run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], repo).strip()
    source = {"kind": "pr", "repo": name, "base": v["baseRefName"], "head": v["headRefName"],
              "pr": {"number": v["number"], "title": v["title"], "url": v["url"],
                     "author": (v.get("author") or {}).get("login"), "body": v.get("body") or "",
                     "state": v["state"], "mergedAt": v.get("mergedAt")},
              "commits": [c["messageHeadline"] for c in v.get("commits") or []]}
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=repo, capture_output=True, text=True)
    return source, diff, r.stdout.strip() if r.returncode == 0 else repo


def exclude_greybeard(top):
    """Keep .greybeard/ out of git without touching the user's .gitignore."""
    r = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=top, capture_output=True, text=True)
    if r.returncode: return  # not a git repo (e.g. --pr run outside one)
    path = os.path.join(top, r.stdout.strip())
    current = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    if ".greybeard/" not in current:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(".greybeard/\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collect PR/branch diff facts for Greybeard.")
    ap.add_argument("--pr", help="PR number or URL (uses gh)")
    ap.add_argument("range", nargs="?", help="BASE..HEAD or BASE...HEAD (default: merge-base with default branch)")
    ap.add_argument("-o", "--output", help="output path (default: <repo>/.greybeard/facts.json)")
    ap.add_argument("--repo", default=os.getcwd(), help="repository path (default: cwd)")
    args = ap.parse_args(argv)
    try:
        if not os.path.isdir(args.repo): raise Fail(f"{args.repo} is not a directory")
        if args.pr:
            source, diff, top = collect_pr(args.repo, args.pr)
        else:
            if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=args.repo, capture_output=True).returncode:
                raise Fail(f"{args.repo} is not a git repository")
            source, diff, top = collect_local(args.repo, args.range)
        if not diff.strip(): raise Fail("the diff is empty, nothing to review")
        facts = {"version": 1, "source": source, **parse_diff(diff)}
        out = args.output or os.path.join(top, ".greybeard", "facts.json")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(facts, fh, indent=1, ensure_ascii=False)
        if not args.output: exclude_greybeard(top)
    except Fail as e:
        print(f"collect.py: {e}", file=sys.stderr)
        return 1
    s = facts["stats"]
    print(out)
    print(f"{s['files']} files, +{s['additions']} -{s['deletions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
