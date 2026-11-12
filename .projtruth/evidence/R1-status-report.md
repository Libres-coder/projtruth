# R1 status is computed from evidence and real code changes

```
$ python.exe -m unittest tests.test_core.ReportTests -v   # exit 0
# projtruth status report (2026-11-13 07:34)

No requirements registered yet. Run `projtruth import-spec spec.md` or add one with req_add.
# projtruth status report (2026-11-13 07:34)

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 t | **pending** | 1 | 0 | - | repo | - |

## Needs attention (1 of 1)
- R1 (pending, not started): no evidence
# projtruth status report (2026-11-13 07:34)

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 t | **pending** | 1 | 0 | - | repo | - |

## Needs attention (1 of 1)
- R1 (pending, not started): no evidence
test_empty_registry_says_so (tests.test_core.ReportTests) ... strict: no requirements registered - nothing to gate on
ok
test_report_exit_strict (tests.test_core.ReportTests) ... strict: not verified: R1
ok
test_requirement_without_criteria_still_links_its_own_evidence (tests.test_core.ReportTests)
Regression: _req_evidence used to iterate criteria only, so a ... ok
test_scope_ignores_unrelated_changes (tests.test_core.ReportTests) ... ok
test_scope_matching_nothing_is_never_stale (tests.test_core.ReportTests) ... ok
test_statuses (tests.test_core.ReportTests) ... ok
test_table_reports_evidence_tier (tests.test_core.ReportTests) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.476s

OK
```

```
$ python.exe -m unittest tests.test_core.GitFreshnessTests -v   # exit 0
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
Ran 11 tests in 11.073s

OK
```

measured
