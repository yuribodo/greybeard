import re, sys, json
# shortcut: plain unified diff only (no renames/binary); enough for the design prototype
out = {}; cur = None; o = n = 0
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("+++ "): cur = line[6:] if line.startswith("+++ b/") else None; out.setdefault(cur, []); continue
    if line.startswith(("--- ", "diff --git", "index ", "new file", "deleted file")): continue
    m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@ ?(.*)", line)
    if m: o, n = int(m.group(1)), int(m.group(2)); out[cur].append({"ctx": m.group(3), "lines": []}); continue
    if cur is None or not out[cur]: continue
    op, text = (line[:1] or " "), line[1:]
    if op == "\\": continue
    out[cur][-1]["lines"].append([op, text, o if op != "+" else None, n if op != "-" else None])
    if op != "+": o += 1
    if op != "-": n += 1
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"))
print({k: sum(len(h["lines"]) for h in v) for k, v in out.items()})
