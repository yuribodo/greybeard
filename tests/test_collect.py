import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "greybeard", "scripts")
sys.path.insert(0, SCRIPTS)
from collect import parse_diff  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "documenso-3446")

SMALL = """\
diff --git a/src/old.py b/src/new.py
similarity index 90%
rename from src/old.py
rename to src/new.py
index 1111111..2222222 100644
--- a/src/old.py
+++ b/src/new.py
@@ -1,3 +1,3 @@ def top():
 a = 1
-b = 2
+b = 3
 c = 4
@@ -10,2 +10,3 @@
 x = 1
+y = 2
 z = 3
\\ No newline at end of file
diff --git a/gone.txt b/gone.txt
deleted file mode 100644
index 3333333..0000000
--- a/gone.txt
+++ /dev/null
@@ -1,2 +0,0 @@
-one
-two
diff --git a/img/logo.png b/img/logo.png
new file mode 100644
index 0000000..4444444
Binary files /dev/null and b/img/logo.png differ
diff --git a/web/yarn.lock b/web/yarn.lock
index 5555555..6666666 100644
--- a/web/yarn.lock
+++ b/web/yarn.lock
@@ -1 +1 @@
-old
+new
"""


class ParseTest(unittest.TestCase):
    def test_documenso_fixture(self):
        with open(os.path.join(FIX, "pr.diff"), encoding="utf-8") as f:
            got = parse_diff(f.read())
        with open(os.path.join(FIX, "facts.json"), encoding="utf-8") as f:
            want = json.load(f)
        self.assertEqual(got["stats"], want["stats"])
        self.assertEqual(got["files"], want["files"])

    def test_small_diff(self):
        d = parse_diff(SMALL)
        f = d["files"]
        self.assertEqual(sorted(f), ["gone.txt", "img/logo.png", "src/new.py", "web/yarn.lock"])
        r = f["src/new.py"]
        self.assertEqual((r["status"], r["old_path"]), ("renamed", "src/old.py"))
        self.assertEqual([h["ctx"] for h in r["hunks"]], ["def top():", ""])
        self.assertEqual(r["hunks"][0]["lines"][1:3], [["-", "b = 2", 2, None], ["+", "b = 3", None, 2]])
        self.assertEqual(r["hunks"][1]["lines"][-1], [" ", "z = 3", 11, 12])  # "\ No newline" skipped
        self.assertEqual(f["gone.txt"]["status"], "deleted")
        self.assertEqual(f["gone.txt"]["hunks"][0]["lines"][1], ["-", "two", 2, None])
        self.assertEqual(f["img/logo.png"], {"status": "added", "old_path": None, "tags": ["binary"], "hunks": []})
        self.assertEqual(f["web/yarn.lock"]["tags"], ["lockfile"])
        self.assertEqual(d["stats"], {"files": 4, "additions": 3, "deletions": 4})


class LocalModeTest(unittest.TestCase):
    def test_range_end_to_end(self):
        with tempfile.TemporaryDirectory() as repo:
            def g(*a):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, check=True,
                               capture_output=True)
            g("init", "-q", "-b", "main")
            with open(os.path.join(repo, "a.txt"), "w") as f: f.write("one\n")
            g("add", "."); g("commit", "-qm", "init")
            g("checkout", "-qb", "feat")
            with open(os.path.join(repo, "a.txt"), "a") as f: f.write("two\n")
            g("commit", "-qam", "add two")
            out = os.path.join(repo, "out.json")
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "collect.py"), "main...feat", "-o", out,
                                "--repo", repo], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out) as f: facts = json.load(f)
            self.assertEqual(facts["source"]["kind"], "local")
            self.assertIsNone(facts["source"]["pr"])
            self.assertEqual(facts["source"]["commits"], ["add two"])
            self.assertEqual(facts["stats"], {"files": 1, "additions": 1, "deletions": 0})
            self.assertEqual(facts["files"]["a.txt"]["hunks"][0]["lines"][-1], ["+", "two", None, 2])
            # default output goes to .greybeard/ and keeps it out of git, once
            for _ in range(2):
                r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "collect.py"), "main...feat", "--repo", repo],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(os.path.join(repo, ".greybeard", "facts.json")))
            with open(os.path.join(repo, ".git", "info", "exclude")) as f:
                self.assertEqual(f.read().splitlines().count(".greybeard/"), 1)

    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "collect.py"), "--repo", d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("not a git repository", r.stderr)
            self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
