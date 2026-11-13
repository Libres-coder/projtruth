import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from projtruth import evidence, freshness, guard, report, store  # noqa: E402

GIT = shutil.which("git")


def mk(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class DirectiveTests(unittest.TestCase):
    """Evidence declares what it proves; the filename is only a fallback."""

    def test_directive_links_a_file_with_any_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".projtruth", "evidence", "ci-run.txt"),
               "projtruth: R2, R3.1\n```\nok\n```\nmeasured\n")
            idx = evidence.scan(tmp)
            self.assertIn("R2", idx)
            self.assertIn("R3.1", idx)
            self.assertEqual(idx["R2"][0]["file"], ".projtruth/evidence/ci-run.txt")

    def test_directive_overrides_the_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-wrong.md"),
               "<!-- projtruth: R3 -->\n```\nok\n```\nmeasured\n")
            idx = evidence.scan(tmp)
            self.assertNotIn("R1", idx)
            self.assertIn("R3", idx)

    def test_directive_parsing(self):
        self.assertEqual(evidence.declared_ids("projtruth: r1.2, R4\n"),
                         ["R1.2", "R4"])
        self.assertEqual(evidence.declared_ids("<!-- projtruth: R1 -->"), ["R1"])
        self.assertEqual(evidence.declared_ids("no directive here\n"), [])
        self.assertEqual(evidence.declared_ids("projtruth: R1 R1\n"), ["R1"])

    def test_report_uses_declared_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"], files=["app.py"])
            mk(os.path.join(tmp, ".projtruth", "evidence", "nightly.log"),
               "projtruth: R1\n```\nok\n```\nmeasured\n")
            idx = evidence.scan(tmp)
            self.assertEqual(report.compute_status(store.list_requirements(tmp)[0],
                                                   idx, freshness.Clock(tmp))[0],
                             "verified")


class ReviewFixesTests(unittest.TestCase):
    """Regressions from the 2026-11-14 review: a gate that passes a deleted
    implementation is worse than no gate."""

    def _git(self, tmp, *args, date=None):
        env = dict(os.environ)
        if date is not None:
            env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = str(date)
        subprocess.run([GIT, "-C", tmp] + list(args), check=True,
                       capture_output=True, env=env)

    def _repo(self, tmp, files=("app.py",), scope=None, evidence_name="R1-ok.md"):
        store.init(tmp)
        store.add_requirement(tmp, "R1", "t", ["c"],
                              files=list(scope if scope is not None else files))
        for i, rel in enumerate(files):
            mk(os.path.join(tmp, rel), "x = 1\n")
        mk(os.path.join(tmp, ".projtruth", "evidence", evidence_name),
           "```\nok\n```\nmeasured\n")
        self._git(tmp, "init", "-q")
        self._git(tmp, "config", "user.email", "t@example.com")
        self._git(tmp, "config", "user.name", "t")
        self._git(tmp, "add", "-A")
        self._git(tmp, "commit", "-qm", "init", date=1700000000)

    def _status(self, tmp):
        req = store.list_requirements(tmp)[0]
        return report.compute_status(req, evidence.scan(tmp),
                                     freshness.Clock(tmp))[0]

    def test_deleting_the_only_file_makes_the_requirement_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp)
            self.assertEqual(self._status(tmp), "verified")
            self._git(tmp, "rm", "-q", "app.py")
            self._git(tmp, "commit", "-qm", "remove", date=1700000100)
            self.assertEqual(self._status(tmp), "stale",
                             "a deleted implementation is a change")

    def test_evidence_for_R10_does_not_excuse_R1(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "one", ["c"], files=["app.py"])
            store.add_requirement(tmp, "R10", "ten", ["c"], files=["ten.py"])
            for rel in ("app.py", "ten.py"):
                mk(os.path.join(tmp, rel), "x = 1\n")
            for rel in ("R1-ok.md", "R10-ok.md"):
                mk(os.path.join(tmp, ".projtruth", "evidence", rel),
                   "```\nok\n```\nmeasured\n")
            self._git(tmp, "init", "-q")
            self._git(tmp, "config", "user.email", "t@example.com")
            self._git(tmp, "config", "user.name", "t")
            self._git(tmp, "add", "-A")
            self._git(tmp, "commit", "-qm", "init", date=1700000000)
            mk(os.path.join(tmp, "app.py"), "x = 2\n")
            self._git(tmp, "add", "app.py")
            blocking = guard.evaluate(tmp)
            self.assertEqual([r["id"] for r, _ in blocking], ["R1"])
            mk(os.path.join(tmp, ".projtruth", "evidence", "R10-rerun.md"),
               "```\nok\n```\nmeasured\n")
            self._git(tmp, "add", ".projtruth/evidence/R10-rerun.md")
            blocking = guard.evaluate(tmp)
            self.assertEqual([r["id"] for r, _ in blocking], ["R1"],
                             "R10 evidence must not count for R1")

    def test_renaming_the_only_file_makes_the_requirement_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp, files=("old.py",))
            self.assertEqual(self._status(tmp), "verified")
            self._git(tmp, "mv", "old.py", "new.py")
            self._git(tmp, "commit", "-qm", "rename", date=1700000100)
            self.assertEqual(self._status(tmp), "stale",
                             "a rename is a change to the scope")

    def test_a_staged_evidence_deletion_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp)
            mk(os.path.join(tmp, "app.py"), "x = 2\n")
            self._git(tmp, "add", "app.py")
            self._git(tmp, "rm", "-q", ".projtruth/evidence/R1-ok.md")
            self.assertEqual([r["id"] for r, _ in guard.evaluate(tmp)], ["R1"])

    @unittest.skipUnless(os.name == "nt", "case-insensitive filesystem")
    def test_a_scope_in_a_different_case_still_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp, files=("Server.py",), scope=("server.py",))
            self.assertEqual(self._status(tmp), "verified")
            mk(os.path.join(tmp, "Server.py"), "x = 2\n")
            self._git(tmp, "add", "Server.py")
            self.assertEqual([r["id"] for r, _ in guard.evaluate(tmp)], ["R1"])
            self._git(tmp, "commit", "-qm", "edit", date=1700000100)
            req = store.list_requirements(tmp)[0]
            self.assertEqual(report.compute_status(req, evidence.scan(tmp),
                                                   freshness.Clock(tmp))[0], "stale")


class GlobTests(unittest.TestCase):
    def test_double_star_spans_directories(self):
        self.assertTrue(freshness.path_matches("web/app.js", "web/**/*.js"))
        self.assertTrue(freshness.path_matches("web/x/y.js", "web/**/*.js"))
        self.assertFalse(freshness.path_matches("web/x/y.css", "web/**/*.js"))

    def test_single_star_stops_at_a_slash(self):
        self.assertTrue(freshness.path_matches("src/a.py", "src/*.py"))
        self.assertFalse(freshness.path_matches("src/deep/a.py", "src/*.py"))

    def test_directory_pattern_covers_the_subtree(self):
        self.assertTrue(freshness.path_matches("web/app.js", "web"))
        self.assertFalse(freshness.path_matches("webapp/app.js", "web"))

    def test_outside_patterns_match_nothing(self):
        self.assertFalse(freshness.path_matches("a.py", "../a.py"))
        self.assertFalse(freshness.path_matches("a.py", "C:/a.py"))


@unittest.skipUnless(GIT, "git not installed")
class GitRepoTest(unittest.TestCase):
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
        return subprocess.run(["git", "-C", self.repo] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              env=env).stdout

    def _commit(self, msg, date):
        self._git("add", "-A")
        self._git("commit", "-m", msg, date=date)

    def _verified_repo(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"),
           "```\nok\n```\nmeasured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])

    def test_changed_files_sees_commits_and_worktree(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("one", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        self._commit("two", "2026-01-02T00:00:00+0000")
        mk(os.path.join(self.repo, "new.py"), "x\n")
        changed = freshness.changed_files(self.repo, "HEAD~1")
        self.assertEqual(changed, ["app.py", "new.py"])
        self.assertEqual(freshness.changed_files(self.repo, "nope"), None)

    def test_changed_report_scopes_to_touched_requirements(self):
        self._verified_repo()
        store.add_requirement(self.repo, "R2", "other", ["c"], files=["other.py"])
        mk(os.path.join(self.repo, "other.py"), "x\n")
        mk(os.path.join(self.repo, "other.py"), "y\n")     # uncommitted change
        idx = evidence.scan(self.repo)
        pairs = report.changed_subset(store.list_requirements(self.repo), idx,
                                      freshness.Clock(self.repo), ["other.py"])
        self.assertEqual([r["id"] for r, _ in pairs], ["R2"])

    def test_guard_blocks_a_commit_that_invalidates_evidence(self):
        self._verified_repo()
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        self._git("add", "app.py")
        blocking = guard.evaluate(self.repo)
        self.assertEqual([r["id"] for r, _ in blocking], ["R1"])
        self.assertEqual(guard.main(self.repo), 1)
        self.assertEqual(guard.main(self.repo, allow=True), 0)

    def test_guard_allows_when_evidence_is_staged(self):
        self._verified_repo()
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-rerun.md"),
           "```\nok again\n```\nmeasured\n")
        self._git("add", "-A")
        self.assertEqual(guard.evaluate(self.repo), [])

    def test_guard_allows_declared_evidence_in_another_file(self):
        self._verified_repo()
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "nightly.txt"),
           "projtruth: R1\n```\nok\n```\nmeasured\n")
        self._git("add", "-A")
        self.assertEqual(guard.evaluate(self.repo), [])

    def test_guard_ignores_already_stale_requirements(self):
        self._verified_repo()
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        self._commit("change", "2026-01-03T00:00:00+0000")
        mk(os.path.join(self.repo, "app.py"), "v3\n")
        self._git("add", "app.py")
        self.assertEqual(guard.evaluate(self.repo), [],
                         "an already-stale requirement must not trap the repo")

    def test_guard_is_silent_without_requirements(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("one", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, "app.py"), "v2\n")
        self._git("add", "app.py")
        self.assertEqual(guard.main(self.repo), 0)

    def test_hook_install_status_uninstall(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("one", "2026-01-01T00:00:00+0000")
        self.assertEqual(guard.hook_command(self.repo, "install"), 0)
        path = guard._hook_path(self.repo)
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertIn(guard.MARKER, f.read())
        self.assertEqual(guard.hook_command(self.repo, "status"), 0)
        self.assertEqual(guard.hook_command(self.repo, "uninstall"), 0)
        self.assertFalse(os.path.exists(path))

    def test_hook_refuses_to_clobber_a_foreign_hook(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("one", "2026-01-01T00:00:00+0000")
        path = guard._hook_path(self.repo)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho mine\n")
        self.assertEqual(guard.hook_command(self.repo, "install"), 1)
        self.assertEqual(guard.hook_command(self.repo, "install", force=True), 0)
        with open(path, encoding="utf-8") as f:
            self.assertIn(guard.MARKER, f.read())


if __name__ == "__main__":
    unittest.main()
