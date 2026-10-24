import copy, json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "greybeard", "scripts")
sys.path.insert(0, SCRIPTS)
from build import validate  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "documenso-3446")
FACTS = json.load(open(os.path.join(FIX, "facts.json"), encoding="utf-8"))
REVIEW = json.load(open(os.path.join(FIX, "review.json"), encoding="utf-8"))


def stop(review, sid):
    return next(s for s in review["stops"] if s["id"] == sid)


class BuildTest(unittest.TestCase):
    def problems(self, mutate):
        r = copy.deepcopy(REVIEW)
        mutate(r)
        return validate(FACTS, r)

    def test_fixture_validates_and_builds(self):
        self.assertEqual(validate(FACTS, REVIEW), [])
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.html")
            res = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build.py"), os.path.join(FIX, "facts.json"),
                                  os.path.join(FIX, "review.json"), "-o", out], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            with open(out, encoding="utf-8") as f:
                html = f.read()
        self.assertIn(REVIEW["pr"]["title"], html)
        self.assertNotIn("/*__", html)

    def test_uncovered_hunk(self):
        def drop(r):
            next(s for s in r["skim"] if s["id"] == "wire")["files"].remove("packages/lib/jobs/client.ts")
        p = self.problems(drop)
        self.assertTrue(any(x.startswith("uncovered hunk: packages/lib/jobs/client.ts") for x in p), p)

    def test_bad_call_reference(self):
        p = self.problems(lambda r: stop(r, "drs")["calls"][0].update(to="foo"))
        self.assertIn('stop \'drs\': calls[0].to \'foo\' is not a stop or "skim"', p)

    def test_three_checks(self):
        p = self.problems(lambda r: stop(r, "tests")["checks"].append(stop(r, "tests")["checks"][0]))
        self.assertIn("stop 'tests': needs 1-2 checks, has 3", p)

    def test_note_on_hidden_line(self):
        p = self.problems(lambda r: stop(r, "route")["note"].update(line=10))
        self.assertTrue(any("stop 'route': note line 10" in x for x in p), p)

    def test_failed_build_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "review.json")
            r = copy.deepcopy(REVIEW)
            r["skim"] = []
            with open(bad, "w", encoding="utf-8") as f:
                json.dump(r, f)
            res = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build.py"), os.path.join(FIX, "facts.json"), bad],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn("uncovered hunk", res.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "review.html")))


if __name__ == "__main__":
    unittest.main()
