# R1 Status is computed from evidence and real code changes

_Run at 2026-11-14 06:12:34_

```
$ python -m unittest tests.test_core.GitFreshnessTests -v   # exit 0
test_bookkeeping_commit_is_not_a_source_change (tests.test_core.GitFreshnessTests) ... ok
test_cjk_filename_dirty_is_seen (tests.test_core.GitFreshnessTests)
git quotes non-ASCII paths by default; unquoted (-z) matching is what ... ok
test_commit_times_beat_reset_mtimes (tests.test_core.GitFreshnessTests)
Checkout resets every mtime; git still knows the evidence is newer. ... ok
test_directory_scope_covers_the_subtree (tests.test_core.GitFreshnessTests)
`files: ["src"]` must mean src/**, not 'matches nothing, never stale'. ... ok
test_later_commit_is_stale (tests.test_core.GitFreshnessTests) ... ok
test_non_git_falls_back_to_mtime (tests.test_core.GitFreshnessTests) ... ok
test_refreshing_evidence_in_place_beats_its_old_commit (tests.test_core.GitFreshnessTests)
Re-running a check edits the evidence file. That edit is newer than ... ok
test_tool_state_and_new_evidence_are_not_source_changes (tests.test_core.GitFreshnessTests)
Regression: `init` writes an untracked .projtruth/, and a fresh ... ok
test_uncommitted_edit_is_stale (tests.test_core.GitFreshnessTests) ... ok
test_uncommitted_edit_older_than_evidence_is_fresh (tests.test_core.GitFreshnessTests)
An edit at 10:00 and evidence written at 10:05: the evidence answers ... ok
test_untracked_directory_of_new_source_files_counts (tests.test_core.GitFreshnessTests) ... ok

----------------------------------------------------------------------
Ran 11 tests in 10.072s

OK
```

measured
