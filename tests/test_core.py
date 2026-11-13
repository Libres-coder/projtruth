import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

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
            self.assertTrue(store.set_status(tmp, "R1", "implemented")[0])
            self.assertFalse(store.set_status(tmp, "R1", "bogus")[0])
            ok, msg = store.set_status(tmp, "R1", "verified")
            self.assertFalse(ok, "verified is computed from evidence, not declared")
            self.assertIn("evidence", msg)
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
            leftovers = [f for f in os.listdir(os.path.join(tmp, ".projtruth"))
                         if f.endswith(".tmp")]
            self.assertEqual(leftovers, [], "temp file must be renamed, not left behind")

    def test_single_strings_are_not_split_into_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            self.assertTrue(store.add_requirement(tmp, "R3", "t", "only criterion",
                                                  files="a.py")[0])
            req = store.list_requirements(tmp)[0]
            self.assertEqual([c["text"] for c in req["criteria"]], ["only criterion"])
            self.assertEqual(req["files"], ["a.py"])

    def test_unsafe_file_patterns_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            ok, msg = store.add_requirement(tmp, "R1", "t", ["c"], files=["../secret.py"])
            self.assertFalse(ok)
            self.assertIn("inside the repo", msg)
            store.add_requirement(tmp, "R2", "t", ["c"])
            self.assertFalse(store.set_files(tmp, "R2", ["C:/Windows/system32/x.dll"])[0])
            self.assertFalse(store.set_files(tmp, "R2", ["/etc/passwd"])[0])

    def test_registry_of_the_wrong_shape_is_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            path = os.path.join(tmp, ".projtruth", "requirements.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"requirements": [1]}')     # valid JSON, unusable shape
            self.assertEqual(store.list_requirements(tmp), [])
            self.assertEqual(len([f for f in os.listdir(os.path.join(tmp, ".projtruth"))
                                  if ".corrupt-" in f]), 1)

    def test_dict_arguments_are_refused_not_mangled(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            ok, msg = store.add_requirement(tmp, "R1", "t", {"text": "x"})
            self.assertFalse(ok)
            self.assertIn("list of strings", msg)
            store.add_requirement(tmp, "R1", "t", ["c"])
            self.assertFalse(store.set_files(tmp, "R1", {"a.py": True})[0])

    def test_corrupt_registry_is_quarantined_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            path = os.path.join(tmp, ".projtruth", "requirements.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{ this is not json")
            self.assertEqual(store.list_requirements(tmp), [])
            leftovers = [f for f in os.listdir(os.path.join(tmp, ".projtruth"))
                         if ".corrupt-" in f]
            self.assertEqual(len(leftovers), 1, "damaged registry must be kept")
            self.assertTrue(store.add_requirement(tmp, "R1", "t", ["c"])[0])


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

    def test_import_spec_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, "spec.md"), SPEC)
            cli.import_spec(tmp, os.path.join(tmp, "spec.md"))
            cli.import_spec(tmp, os.path.join(tmp, "spec.md"))
            reqs = store.list_requirements(tmp)
            self.assertEqual([r["id"] for r in reqs], ["R1", "R2"])
            self.assertEqual(len(reqs[0]["criteria"]), 2,
                             "re-import must not duplicate criteria")
            self.assertEqual([c["id"] for c in reqs[0]["criteria"]], ["R1.1", "R1.2"])

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

    def test_tier_prefers_a_standalone_line(self):
        """A test name or a quoted sentence must not decide the tier."""
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-a.md"),
               "```\n$ pytest -k guessed_evidence\n1 passed\n```\n\nmeasured\n")
            idx = evidence.scan(tmp)
            self.assertEqual(idx["R1"][0]["tier"], "measured")

    def test_index_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-a.md"), "measured\n")
            evidence.save_index(tmp, evidence.scan(tmp))
            loaded = evidence.load_index(tmp) or {}
            self.assertIn("R1", loaded)


class RegistryValidationTests(unittest.TestCase):
    """Malformed-but-plausible registries must be quarantined, not half-read."""

    def _registry(self, tmp, body):
        mk(os.path.join(tmp, ".projtruth", "requirements.json"), body)

    def _quarantined(self, tmp):
        return [n for n in os.listdir(os.path.join(tmp, ".projtruth"))
                if ".corrupt-" in n]

    def test_files_must_be_a_list_of_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._registry(tmp, '{"requirements": [{"id": "R1", '
                                '"files": "app.py", "criteria": []}]}')
            self.assertEqual(store.list_requirements(tmp), [])
            self.assertTrue(self._quarantined(tmp))

    def test_duplicate_ids_are_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._registry(tmp, '{"requirements": [{"id": "R1", "criteria": []}, '
                                '{"id": "r1", "criteria": []}]}')
            self.assertEqual(store.list_requirements(tmp), [])
            self.assertTrue(self._quarantined(tmp))

    def test_a_criterion_id_that_cannot_link_is_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._registry(tmp, '{"requirements": [{"id": "R1", "criteria": '
                                '[{"id": "foo", "text": "x"}]}]}')
            self.assertEqual(store.list_requirements(tmp), [])
            self.assertTrue(self._quarantined(tmp))

    def test_unreadable_registry_raises_instead_of_looking_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            with mock.patch("builtins.open", side_effect=PermissionError("busy")):
                with self.assertRaises(store.RegistryUnreadable):
                    store.load(tmp)


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
            self.assertEqual(cli.main(["--repo", tmp, "report", "--strict"]), 1,
                             "an empty registry must not pass the gate vacuously")

    def test_requirement_without_criteria_still_links_its_own_evidence(self):
        """Regression: _req_evidence used to iterate criteria only, so a
        criteria-less R5 with R5-ok.md was stuck at pending forever."""
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R5", "no criteria")
            mk(os.path.join(tmp, ".projtruth", "evidence", "R5-ok.md"),
               "```\nok\n```\nmeasured\n")
            idx = evidence.scan(tmp)
            status, _ = report.compute_status(
                store.list_requirements(tmp)[0], idx, freshness.Clock(tmp))
            self.assertEqual(status, "verified")

    def test_table_reports_evidence_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"])
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-ok.md"),
               "```\nok\n```\ninferred\n")
            out = report.render(store.list_requirements(tmp), evidence.scan(tmp),
                                freshness.Clock(tmp))
            self.assertIn("| tier |", out)
            self.assertIn("inferred", out)

    def test_verified_evidence_without_a_tier_is_reported_in_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"])
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-ok.md"),
               "```\nok\n```\n")
            out = report.render(store.list_requirements(tmp), evidence.scan(tmp),
                                freshness.Clock(tmp))
            self.assertIn("Evidence quality", out)
            self.assertIn("R1", out)

    def test_measured_evidence_stays_out_of_the_quality_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.init(tmp)
            store.add_requirement(tmp, "R1", "t", ["c"])
            mk(os.path.join(tmp, ".projtruth", "evidence", "R1-ok.md"),
               "```\nok\n```\nmeasured\n")
            out = report.render(store.list_requirements(tmp), evidence.scan(tmp),
                                freshness.Clock(tmp))
            self.assertNotIn("Evidence quality", out)

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
            self.assertIn("evidence_tier", payload[0])


@unittest.skipUnless(GIT, "git not installed")
class ScopeReportTests(unittest.TestCase):
    """A scope that matches nothing means "never stale" - a typo fails
    silently. `projtruth scopes` makes the resolution visible."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_file_and_directory(self):
        mk(os.path.join(self.repo, "src", "app.py"), "x = 1\n")
        out = dict((e["pattern"], e) for e in
                   freshness.describe_scope(self.repo, ["src/app.py", "src"]))
        self.assertEqual(out["src/app.py"]["kind"], "file")
        self.assertEqual(out["src/app.py"]["files"], 1)
        self.assertEqual(out["src/app.py"]["note"], "")
        self.assertEqual(out["src"]["kind"], "dir")
        self.assertEqual(out["src"]["files"], 1)

    def test_a_glob_that_matches_nothing_says_so(self):
        mk(os.path.join(self.repo, "src", "app.py"), "x = 1\n")
        out = freshness.describe_scope(self.repo, ["web/*.js"])[0]
        self.assertEqual(out["kind"], "glob")
        self.assertEqual(out["files"], 0)
        self.assertIn("matches nothing", out["note"])

    def test_match_case_is_path_aware(self):
        self.assertTrue(freshness._match_case("src/*.py", "src/a.py"))
        self.assertTrue(freshness._match_case("src/**/*.py", "src/a.py"))
        self.assertTrue(freshness._match_case("src/**/*.py", "src/x/a.py"))
        self.assertFalse(freshness._match_case("SRC/*.py", "src/a.py"))
        self.assertFalse(freshness._match_case("src/*.py", "src/x/a.py"))

    def test_a_case_mismatch_is_explained(self):
        mk(os.path.join(self.repo, "src", "App.py"), "x = 1\n")
        out = freshness.describe_scope(self.repo, ["src/app.py"])[0]
        if os.name == "nt":
            self.assertEqual(out["kind"], "file")
            self.assertIn("case-sensitively", out["note"])
            self.assertIn("App.py", out["note"])
        else:
            self.assertEqual(out["kind"], "missing")

    def test_an_unsafe_pattern_is_named(self):
        out = freshness.describe_scope(self.repo, ["../outside.py"])[0]
        self.assertEqual(out["kind"], "unsafe")

    def test_cli_strict_fails_on_a_scope_that_matches_nothing(self):
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["src/*.py"])
        self.assertEqual(cli.main(["--repo", self.repo, "scopes", "--strict"]), 1)
        mk(os.path.join(self.repo, "src", "app.py"), "x = 1\n")
        self.assertEqual(cli.main(["--repo", self.repo, "scopes", "--strict"]), 0)


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
        """Checkout resets every mtime; git still knows the evidence is newer.

        The mtimes are set deliberately *against* the answer - source newer than
        evidence - so only commit-time logic can produce `verified`. A tool that
        compared mtimes would call this stale.
        """
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        now = time.time()
        os.utime(os.path.join(self.repo, "app.py"), (now, now))                  # newer
        os.utime(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"),
                 (now - 3600, now - 3600))                                       # older
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

    def test_refreshing_evidence_in_place_beats_its_old_commit(self):
        """Re-running a check edits the evidence file. That edit is newer than
        the code change it answers, even before either is committed."""
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        ev = os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md")
        mk(ev, "measured\nold run\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])
        mk(os.path.join(self.repo, "app.py"), "v2\n")     # code changed, uncommitted
        mk(ev, "measured\nnew run\n")                     # evidence re-run, uncommitted
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")

    def test_untracked_directory_of_new_source_files_counts(self):
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["web/**/*.js"])
        mk(os.path.join(self.repo, "web", "app.js"), "x\n")   # whole dir untracked
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "stale")

    def test_uncommitted_edit_older_than_evidence_is_fresh(self):
        """An edit at 10:00 and evidence written at 10:05: the evidence answers
        the edit. Returning 'now' for any dirty file would call this stale."""
        mk(os.path.join(self.repo, "app.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["app.py"])
        mk(os.path.join(self.repo, "app.py"), "v2\n")           # dirty edit...
        mid = time.mktime(time.strptime("2026-01-01 12:00:00", "%Y-%m-%d %H:%M:%S"))
        os.utime(os.path.join(self.repo, "app.py"), (mid, mid))  # ...from before it
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertAlmostEqual(clock.latest_change(["app.py"]), mid, places=0,
                               msg="a dirty file must be timed by its own mtime")
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")

    def test_cjk_filename_dirty_is_seen(self):
        """git quotes non-ASCII paths by default; unquoted (-z) matching is what
        makes a Chinese filename work - and our users have Chinese filenames."""
        mk(os.path.join(self.repo, "中文.py"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["中文.py"])
        idx = evidence.scan(self.repo)
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "verified")
        mk(os.path.join(self.repo, "中文.py"), "v2\n")
        clock = freshness.Clock(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, clock)[0], "stale")

    def test_directory_scope_covers_the_subtree(self):
        """`files: ["src"]` must mean src/**, not 'matches nothing, never stale'."""
        mk(os.path.join(self.repo, "src", "app.js"), "v1\n")
        self._commit("source", "2026-01-01T00:00:00+0000")
        mk(os.path.join(self.repo, ".projtruth", "evidence", "R1-ok.md"), "measured\n")
        self._commit("evidence", "2026-01-02T00:00:00+0000")
        store.init(self.repo)
        store.add_requirement(self.repo, "R1", "t", ["c"], files=["src"])
        idx = evidence.scan(self.repo)
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, freshness.Clock(self.repo))[0],
                         "verified")
        mk(os.path.join(self.repo, "src", "app.js"), "v2\n")
        self.assertEqual(report.compute_status(store.list_requirements(self.repo)[0],
                                               idx, freshness.Clock(self.repo))[0],
                         "stale")

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
