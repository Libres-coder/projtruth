# R8 The commit guard refuses to invalidate verified evidence

_Run at 2026-11-14 04:12:33_

```
$ python -m unittest tests.test_guard.GitRepoTest -v   # exit 0
installed C:\Users\LiuDing\AppData\Local\Temp\tmpqy6wrnph\.git\hooks\pre-commit
installed: C:\Users\LiuDing\AppData\Local\Temp\tmpqy6wrnph\.git\hooks\pre-commit
removed C:\Users\LiuDing\AppData\Local\Temp\tmpqy6wrnph\.git\hooks\pre-commit
installed C:\Users\LiuDing\AppData\Local\Temp\tmpuy4ps4ph\.git\hooks\pre-commit
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
test_hook_refuses_to_clobber_a_foreign_hook (tests.test_guard.GitRepoTest) ... refusing to overwrite C:\Users\LiuDing\AppData\Local\Temp\tmpuy4ps4ph\.git\hooks\pre-commit (not ours); use --force
ok

----------------------------------------------------------------------
Ran 9 tests in 10.708s

OK

```

```
$ python -m projtruth guard   # the edit is staged   # exit 1
projtruth: this commit would invalidate proof for 1 requirement(s)

  R1 api
      <- app.py

The evidence is still valid; committing this change makes it stale.
Re-run the check, then stage the new evidence:
  python -m projtruth report
  git add .projtruth/evidence/

Or commit anyway: PROJTRUTH_ALLOW_STALE=1 git commit ...
```

```
$ PROJTRUTH_ALLOW_STALE=1 python -m projtruth guard   # exit 0
projtruth: this commit would invalidate proof for 1 requirement(s)

  R1 api
      <- app.py

The evidence is still valid; committing this change makes it stale.
Re-run the check, then stage the new evidence:
  python -m projtruth report
  git add .projtruth/evidence/

Or commit anyway: PROJTRUTH_ALLOW_STALE=1 git commit ...

projtruth: allowed (PROJTRUTH_ALLOW_STALE)
```

measured
