import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from projtruth import cli, evidence, freshness, report, store  # noqa: E402

GIT = shutil.which("git")


def mk(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


SPEC = """# spec
### R1 add thing
- 验收:add works
- Accept: add twice works
### R2 list things
- 验收:list shows
"""


class StoreTests(unittest.TestCase):
    def test_crud_and_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            ok, _ = store.add_requirement(tmp, "R1", "title", ["c1", "c2"])
            self.assertTrue(ok)
            self.assertFalse(store.add_requirement(tmp, "R1", "dup")[0])
            self.assertFalse(store.add_requirement(tmp, "bogus", "t")[0])
            req = store.list_requirements(tmp)[0]
            self.assertEqual([c["id"] for c in req["criteria"]], ["R1.1", "R1.2"])
            self.assertEqual(req["files"], [])
            self.assertTrue(store.set_status(tmp, "R1", "verified")[0])
            self.assertFalse(store.set_status(tmp, "R1", "bogus")[0])
            self.assertTrue(store.set_files(tmp, "R1", ["a.py"])[0])
            self.assertEqual(store.list_requirements(tmp)[0]["files"], ["a.py"])
            store.append_decision(tmp, "use memory store", "R4 only needs refresh persistence")
            self.assertEqual(len(store.list_decisions(tmp)), 1)

    def test_corrupt_decision_line_does_not_hide_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.append_decision(tmp, "first")
            with open(os.path.join(tmp, ".projtruth", "decisions.jsonl"), "a",
                      encoding="utf-8") as f:
                f.write("{not json\n")
            store.append_decision(tmp, "second")
            self.assertEqual([d["decision"] for d in store.list_decisions(tmp)],
                             ["first", "second"])

    def test_atomic_save_leaves_readable_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"])
            self.assertFalse(os.path.exists(
                os.path.join(tmp, ".projtruth", "requirements.json.tmp")))
            self.assertEqual(len(store.load(tmp)["requirements"]), 1)


class ImportTests(unittest.TestCase):
    def test_import_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, "spec.md"), SPEC)
            ok, msg = cli.import_spec(tmp, os.path.join(tmp, "spec.md"))
            self.assertTrue(ok, msg)
            reqs = store.list_requirements(tmp)
            self.assertEqual([r["id"] for r in reqs], ["R1", "R2"])
            self.assertEqual(len(reqs[0]["criteria"]), 2)
            self.assertEqual(reqs[0]["criteria"][1]["text"], "add twice works")

    def test_import_missing_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok, msg = cli.import_spec(tmp, os.path.join(tmp, "nope.md"))
            self.assertFalse(ok)
            self.assertIn("cannot read", msg)


class EvidenceTests(unittest.TestCase):
    def test_scan_and_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".claude", "skills", "verify-x", "evidence", "d", "r1-add.md"),
               "```\nHTTP 201\n```\nmeasured\n")
            mk(os.path.join(tmp, ".claude", "skills", "verify-x", "evidence", "d", "R2-list.md"),
               "```\nok\n```\ninferred\n")
            mk(os.path.join(tmp, ".claude", "skills", "verify-x", "evidence", "d", "notes.md"),
               "not linked\n")
            idx = evidence.scan(tmp)
            self.assertIn("R1", idx)
            self.assertIn("R2", idx)
            self.assertEqual(idx["R1"][0]["tier"], "measured")
            self.assertEqual(idx["R2"][0]["tier"], "inferred")
            self.assertEqual(len([k for k in idx if k not in ("R1", "R2")]), 0)

    def test_agent_neutral_drop_box_is_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".projtruth", "evidence", "R3.1-build.txt"), "ok\n")
            idx = evidence.scan(tmp)
            self.assertIn("R3.1", idx)
            self.assertEqual(idx["R3.1"][0]["file"], ".projtruth/evidence/R3.1-build.txt")

    def test_index_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-a.md"), "measured\n")
            evidence.save_index(tmp, evidence.scan(tmp))
            loaded = evidence.load_index(tmp) or {}
            self.assertIn("R1", loaded)


class ReportTests(unittest.TestCase):
    def _mk_ev(self, tmp, crit_file, mtime):
        p = os.path.join(tmp, ".claude", "skills", "verify-x", "evidence", "d", crit_file)
        mk(p, "```\nok\n```\nmeasured\n")
        os.utime(p, (mtime, mtime))

    def test_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "fresh", ["c"])
            store.add_requirement(tmp, "R2", "stale", ["c"])
            store.add_requirement(tmp, "R3", "none", ["c"])
            now = time.time()
            src = os.path.join(tmp, "app.py")
            mk(src, "x\n")
            os.utime(src, (now - 100, now - 100))
            self._mk_ev(tmp, "r1-a.md", now)
            self._mk_ev(tmp, "r2-a.md", now - 500)
            idx = evidence.scan(tmp)
            reqs = {r["id"]: r for r in store.list_requirements(tmp)}
            clock = freshness.Clock(tmp)
            self.assertEqual(report.compute_status(reqs["R1"], idx, clock)[0], "verified")
            self.assertEqual(report.compute_status(reqs["R2"], idx, clock)[0], "stale")
            self.assertIn(report.compute_status(reqs["R3"], idx, clock)[0],
                          ("pending", "unverified"))
            out = report.render(list(reqs.values()), idx, clock)
            self.assertIn("Needs attention", out)
            self.assertIn("R2", out)

    def test_scope_ignores_unrelated_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "scoped", ["c"], files=["api.py"])
            store.add_requirement(tmp, "R2", "unscoped", ["c"])
            now = time.time()
            mk(os.path.join(tmp, "api.py"), "x\n")
            mk(os.path.join(tmp, "other.py"), "y\n")
            for name in ("api.py", "other.py"):
                os.utime(os.path.join(tmp, name), (now - 1000, now - 1000))
            self._mk_ev(tmp, "r1-a.md", now - 500)
            self._mk_ev(tmp, "r2-a.md", now - 500)
            os.utime(os.path.join(tmp, "other.py"), (now, now))  # unrelated edit
            idx = evidence.scan(tmp)
            reqs = {r["id"]: r for r in store.list_requirements(tmp)}
            clock = freshness.Clock(tmp)
            self.assertEqual(report.compute_status(reqs["R1"], idx, clock)[0], "verified")
            self.assertEqual(report.compute_status(reqs["R2"], idx, clock)[0], "stale")

    def test_scope_matching_nothing_is_never_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "planned", ["c"], files=["future/**/*.py"])
            self._mk_ev(tmp, "r1-a.md", time.time() - 500)
            idx = evidence.scan(tmp)
            clock = freshness.Clock(tmp)
            self.assertEqual(report.compute_status(store.list_requirements(tmp)[0],
                                                   idx, clock)[0], "verified")

    def test_empty_registry_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            out = report.render([], {}, freshness.Clock(tmp))
            self.assertIn("No requirements registered", out)

    def test_report_exit_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"])
            self.assertEqual(cli.main(["--repo", tmp, "report", "--strict"]), 1)
            self.assertEqual(cli.main(["--repo", tmp, "report"]), 0)


class JsonTests(unittest.TestCase):
    def test_as_json_is_stable_and_serialisable(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"])
            payload = report.as_json(store.list_requirements(tmp), {},
                                     freshness.Clock(tmp))
            json.dumps(payload)
            self.assertEqual(payload[0]["id"], "R1")
            self.assertEqual(payload[0]["criteria"][0]["id"], "R1.1")
            self.assertIn(payload[0]["status"], store.VALID_STATUS)


@unittest.skipUnless(GIT, "git not installed")
class GitFreshnessTests(unittest.TestCase):
    """The reason this module exists: mtime lies after a clone or checkout."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self._git("init")

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *args, date=None):
        env = dict(os.environ)
        env.setdefault("GIT_AUTHOR_NAME", "t")
        env.setdefault("GIT_AUTHOR_EMAIL", "t@example.com")
        env.setdefault("GIT_COMMITTER_NAME", "t")
        env.setdefault("GIT_COMMITTER_EMAIL", "t@example.com")
        if date:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
        subprocess.run(["git", "-C", self.repo] + list(args), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

    def _commit(self, msg, date):
        self._git("add", "-A")
        self._git("commit", "-m", msg, date=date)

    def test_commit_times_beat_reset_mtimes(self):
        """Checkout resets every mtime; git still knows the evidence is newer."""
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        # simulate git checkout: everything looks touched just now
        now = time.time()
        os.utime(os.path.join(self.repo, "app.py"), (now, now))
        os.utime(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), (now, now))
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")

    def test_uncommitted_edit_is_stale(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")
        mk(os.path.join(self.repo, "app.py"), "v2\n")          # dirty, not committed
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "stale")

    def test_later_commit_is_stale(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        self._commit("change", "2026-01-03T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "stale")

    def test_tool_state_and_new_evidence_are_not_source_changes(self):
        """Regression: `init` writes an untracked .projtruth/, and a fresh
        evidence file is untracked too. Neither may mark the project stale -
        that is exactly what made the first dogfood run useless."""
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-more.md"), "measured\n")
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")

    def test_bookkeeping_commit_is_not_a_source_change(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        mk(os.path.join(self.repo, "README.md"), "docs\n")
        self._commit("docs", "2026-01-03T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"])       # whole-repo scope
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")

    def test_non_git_falls_back_to_mtime(self):
        with tempfile.TemporaryDirectory() as plain:
            mk(os.path.join(plain, "app.py"), "v1\n")
            os.utime(os.path.join(plain, "app.py"), (1000, 1000))
            clock = freshness.Clock(plain)
            self.assertFalse(clock.is_git())
            self.assertEqual(clock.latest_change(), 1000.0)


if __name__ == "__main__":
    unittest.main()
