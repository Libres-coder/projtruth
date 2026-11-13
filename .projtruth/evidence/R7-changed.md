# R7 report --changed scopes the report to touched requirements

_Run at 2026-11-14 06:12:45_

```
$ python -m unittest tests.test_guard.GitRepoTest.test_changed_files_sees_commits_and_worktree tests.test_guard.GitRepoTest.test_changed_report_scopes_to_touched_requirements -v   # exit 0
test_changed_files_sees_commits_and_worktree (tests.test_guard.GitRepoTest) ... ok
test_changed_report_scopes_to_touched_requirements (tests.test_guard.GitRepoTest) ... ok

----------------------------------------------------------------------
Ran 2 tests in 1.514s

OK
```

measured
