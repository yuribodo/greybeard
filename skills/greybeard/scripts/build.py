#!/usr/bin/env python3
"""Validate review.json against facts.json and render review.html.

Usage: python3 build.py FACTS_JSON REVIEW_JSON [-o OUT.html]
The rules are the "What build.py enforces" section of references/review-format.md.
"""
import argparse, json, os, sys

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "review.tpl.html")
VIEWS = {"brief", "skim", "done"}  # page views a stop id must not shadow
STATES = {"merged", "open", "draft", "local"}


def missing(obj, fields, where):
    if not isinstance(obj, dict):
        return [f"{where}: must be an object"]
    return [f"{where}: missing {f!r}" for f in fields if obj.get(f) in (None, "", [])]


def dupes(items, where):
    seen, out = set(), []
    for it in items:
        i = it.get("id") if isinstance(it, dict) else None
        if i in seen:
            out.append(f"duplicate {where} id {i!r}")
        seen.add(i)
    return out


def span(hunk):
    """New-line span of a hunk; old-line span for a pure deletion."""
    nums = [l[3] for l in hunk["lines"] if l[3] is not None] or [l[2] for l in hunk["lines"] if l[2] is not None]
    return min(nums), max(nums)


def covered(path, hunk, review):
    if any(path in s.get("files", []) for s in review.get("skim", [])):
        return True
    lo, hi = span(hunk)
    for stop in review.get("stops", []):
        for src in stop.get("src", []):
            if src.get("path") == path and not src.get("snip"):
                r = src.get("range")
                if not r or (r[0] <= hi and r[1] >= lo):
                    return True
    return False


def shown_lines(src, facts, review):
    """New-file line numbers a src displays (what a note can point at)."""
    if src.get("snip"):
        s = review.get("snippets", {}).get(src["path"], {})
        return set(range(s.get("start", 0), s.get("start", 0) + len(s.get("lines", []))))
    r = src.get("range")
    return {l[3] for h in facts["files"].get(src["path"], {}).get("hunks", []) for l in h["lines"]
            if l[0] != "-" and l[3] is not None and (not r or r[0] <= l[3] <= r[1])}


def check_src(src, where, facts, review):
    p = src.get("path")
    if src.get("snip"):
        return [] if p in review.get("snippets", {}) else [f"{where}: snippet {p!r} is not in snippets"]
    out = [] if p in facts["files"] else [f"{where}: path {p!r} is not in facts.files"]
    r = src.get("range")
    if r is not None and not (isinstance(r, list) and len(r) == 2 and r[0] <= r[1]):
        out.append(f"{where}: range must be [start, end]")
    return out


def validate(facts, review):
    """Return every problem as a readable string; empty means it builds."""
    p = missing(review, ["pr", "lead", "flows", "stops", "graph"], "review")
    if p:
        return p
    p += missing(review["pr"], ["title", "state"], "pr")
    if review["pr"].get("state") and review["pr"]["state"] not in STATES:
        p.append(f"pr: state must be one of {sorted(STATES)}")
    flows, stops, skim = review["flows"], review["stops"], review.get("skim", [])
    nodes = review["graph"].get("nodes", [])
    for i, f in enumerate(flows):
        p += missing(f, ["id", "title"], f"flows[{i}]")
    for i, s in enumerate(skim):
        p += missing(s, ["id", "name", "desc", "files"], f"skim[{i}]")
        p += [f"skim {s.get('id')!r}: file {f!r} is not in facts.files" for f in s.get("files", []) if f not in facts["files"]]
    p += dupes(flows, "flow") + dupes(stops, "stop") + dupes(skim, "skim") + dupes(nodes, "graph node")
    if p:
        return p
    flow_ids, stop_ids, skim_ids = {f["id"] for f in flows}, {s["id"] for s in stops}, {s["id"] for s in skim}
    node_ids = {n["id"] for n in nodes}

    for s in stops:
        w = f"stop {s.get('id')!r}"
        p += missing(s, ["id", "flow", "name", "att", "kind", "why", "src", "checks"], w)
        if s.get("id") in VIEWS:
            p.append(f"{w}: id is reserved")
        if s.get("flow") not in flow_ids | {"both"}:
            p.append(f"{w}: flow {s.get('flow')!r} is not a flow id or \"both\"")
        if s.get("att") not in (None, "high", "med"):
            p.append(f"{w}: att must be \"high\" or \"med\"")
        for i, f in enumerate(s.get("from", [])):
            if "to" in f and f["to"] not in stop_ids:
                p.append(f"{w}: from[{i}].to {f['to']!r} is not a stop")
        for i, c in enumerate(s.get("calls", [])):
            if c.get("to") == "skim":
                if c.get("skim") not in skim_ids:
                    p.append(f"{w}: calls[{i}].skim {c.get('skim')!r} is not a skim id")
            elif c.get("to") not in stop_ids:
                p.append(f"{w}: calls[{i}].to {c.get('to')!r} is not a stop or \"skim\"")
        for i, src in enumerate(s.get("src", [])):
            p += check_src(src, f"{w}: src[{i}]", facts, review)
        checks = s.get("checks") or []
        if not 1 <= len(checks) <= 2:
            p.append(f"{w}: needs 1-2 checks, has {len(checks)}")
        for i, c in enumerate(checks):
            p += missing(c, ["does", "impact", "ask"], f"{w}: checks[{i}]")
        n = s.get("note")
        if n:
            shown = set().union(*[shown_lines(x, facts, review) for x in s.get("src", []) if x.get("path") == n.get("path")])
            if n.get("line") not in shown:
                p.append(f"{w}: note line {n.get('line')} of {n.get('path')!r} is not among the lines the stop shows")

    for n in nodes:
        w = f"graph node {n['id']!r}"
        p += missing(n, ["flow", "label", "kind"], w)
        if n.get("flow") not in flow_ids:
            p.append(f"{w}: flow {n.get('flow')!r} is not a flow id")
        if "stop" in n and n["stop"] not in stop_ids:
            p.append(f"{w}: stop {n['stop']!r} is not a stop")
    edges = review["graph"].get("edges", [])
    for e in edges:
        p += [f"graph edge {e}: {end!r} is not a node" for end in e[:2] if end not in node_ids]
    for n in nodes:
        if n.get("lane") and not any(e[0] == n["id"] for e in edges):
            p.append(f"graph node {n['id']!r}: a lane node needs an outgoing edge")
    for c in review["graph"].get("cross", []):
        p += [f"graph cross {c.get('label')!r}: {k} {c.get(k)!r} is not a node" for k in ("from", "to") if c.get(k) not in node_ids]
    for k, src in review.get("peek", {}).items():
        if k not in stop_ids:
            p.append(f"peek key {k!r} is not a stop")
        p += check_src(src, f"peek {k!r}", facts, review)

    for path, f in facts["files"].items():
        for h in f["hunks"]:
            if not covered(path, h, review):
                lo, _ = span(h)
                sign = "+" if any(l[3] is not None for l in h["lines"]) else "-"
                p.append(f"uncovered hunk: {path} @@ {sign}{lo}")
    return p


def render(facts, review, template):
    js = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")  # keep </script> inside strings harmless
    rest = {k: v for k, v in facts.items() if k != "files"}
    out = template
    for key, val in (("FILES", {p: f["hunks"] for p, f in facts["files"].items()}), ("FACTS", rest), ("REVIEW", review)):
        mark = f"/*__{key}__*/"
        assert out.count(mark) == 1, f"template must contain {mark} once"
        out = out.replace(mark, js(val))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate review.json and render review.html.")
    ap.add_argument("facts")
    ap.add_argument("review")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    try:
        facts = json.load(open(a.facts, encoding="utf-8"))
        review = json.load(open(a.review, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"cannot read input: {e}", file=sys.stderr)
        return 1
    problems = validate(facts, review)
    if problems:
        print(f"review.json has {len(problems)} problem(s):", file=sys.stderr)
        for x in problems:
            print(f"  - {x}", file=sys.stderr)
        return 1
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.review)), "review.html")
    html = render(facts, review, open(TEMPLATE, encoding="utf-8").read())
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
