# R8 The commit guard refuses to invalidate verified evidence

_Run at 2026-11-14 06:03:34_

```
$ python -m unittest tests.test_guard -v   # exit 0
installed C:\Users\LiuDing\AppData\Local\Temp\tmpizkxhryv\.git\hooks\pre-commit
installed: C:\Users\LiuDing\AppData\Local\Temp\tmpizkxhryv\.git\hooks\pre-commit
removed C:\Users\LiuDing\AppData\Local\Temp\tmpizkxhryv\.git\hooks\pre-commit
installed C:\Users\LiuDing\AppData\Local\Temp\tmp39_37reo\.git\hooks\pre-commit
test_directive_links_a_file_with_any_name (tests.test_guard.DirectiveTests) ... ok
test_directive_overrides_the_filename (tests.test_guard.DirectiveTests) ... ok
test_directive_parsing (tests.test_guard.DirectiveTests) ... ok
test_report_uses_declared_evidence (tests.test_guard.DirectiveTests) ... ok
test_changed_files_sees_commits_and_worktree (tests.test_guard.GitRepoTest) ... ok
test_changed_report_scopes_to_touched_requirements (tests.test_guard.GitRepoTest) ... ok
test_guard_allows_declared_evidence_in_another_file (tests.test_guard.GitRepoTest) ... ok
test_guard_allows_when_evidence_is_staged (tests.test_guard.GitRepoTest) ... ok
test_guard_blocks_a_commit_that_invalidates_evidence (tests.test_guard.GitRepoTest) ... projtruth: this commit would invalidate proof for 1 requirement(s)

  R1 t
      <- app.py

The evidence is still valid; committing this change makes it stale.
Re-run the check, then stage the new evidence:
  python -m projtruth report
  git add .projtruth/evidence/

Or commit anyway: PROJTRUTH_ALLOW_STALE=1 git commit ...
projtruth: this commit would invalidate proof for 1 requirement(s)

  R1 t
      <- app.py

The evidence is still valid; committing this change makes it stale.
Re-run the check, then stage the new evidence:
  python -m projtruth report
  git add .projtruth/evidence/

Or commit anyway: PROJTRUTH_ALLOW_STALE=1 git commit ...

projtruth: allowed (PROJTRUTH_ALLOW_STALE)
ok
test_guard_ignores_already_stale_requirements (tests.test_guard.GitRepoTest) ... ok
test_guard_is_silent_without_requirements (tests.test_guard.GitRepoTest) ... ok
test_hook_install_status_uninstall (tests.test_guard.GitRepoTest) ... ok
test_hook_refuses_to_clobber_a_foreign_hook (tests.test_guard.GitRepoTest) ... refusing to overwrite C:\Users\LiuDing\AppData\Local\Temp\tmp39_37reo\.git\hooks\pre-commit (not ours); use --force
ok
test_directory_pattern_covers_the_subtree (tests.test_guard.GlobTests) ... ok
test_double_star_spans_directories (tests.test_guard.GlobTests) ... ok
test_outside_patterns_match_nothing (tests.test_guard.GlobTests) ... ok
test_single_star_stops_at_a_slash (tests.test_guard.GlobTests) ... ok
test_a_scope_in_a_different_case_still_matches (tests.test_guard.ReviewFixesTests) ... ok
test_a_staged_evidence_deletion_is_not_evidence (tests.test_guard.ReviewFixesTests) ... ok
test_deleting_the_only_file_makes_the_requirement_stale (tests.test_guard.ReviewFixesTests) ... ok
test_evidence_for_R10_does_not_excuse_R1 (tests.test_guard.ReviewFixesTests) ... ok
test_renaming_the_only_file_makes_the_requirement_stale (tests.test_guard.ReviewFixesTests) ... ok

----------------------------------------------------------------------
Ran 22 tests in 18.886s

OK
```

measured
