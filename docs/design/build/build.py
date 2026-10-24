import json, sys
tpl, data, out = sys.argv[1:4]
files = json.load(open(data, encoding="utf-8"))
js = json.dumps(files, ensure_ascii=False).replace("</", "<\\/")  # keep </script> inside strings harmless
html = open(tpl, encoding="utf-8").read()
assert html.count("/*__FILES__*/") == 1
open(out, "w", encoding="utf-8").write(html.replace("/*__FILES__*/", js))
print("wrote", out, len(html) + len(js), "bytes")
