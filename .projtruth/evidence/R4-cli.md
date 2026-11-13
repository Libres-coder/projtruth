# R4 CLI mirrors the core and gates CI

_Run at 2026-11-14 06:03:32_

```
$ python -m unittest tests.test_core.ScopeReportTests -v   # exit 0
R1  t
  src/*.py                         glob    0 file(s)  - matches nothing - a typo fails silently
R1  t
  src/*.py                         glob    1 file(s)
test_a_case_mismatch_is_explained (tests.test_core.ScopeReportTests) ... ok
test_a_glob_that_matches_nothing_says_so (tests.test_core.ScopeReportTests) ... ok
test_an_unsafe_pattern_is_named (tests.test_core.ScopeReportTests) ... ok
test_cli_strict_fails_on_a_scope_that_matches_nothing (tests.test_core.ScopeReportTests) ... scope check: 1 pattern(s) cannot match on every platform
ok
test_exact_file_and_directory (tests.test_core.ScopeReportTests) ... ok
test_match_case_is_path_aware (tests.test_core.ScopeReportTests) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.034s

OK
```

```
$ python -m projtruth scopes   # exit 0
R1  Status is computed from evidence and real code changes
  projtruth/report.py              file    1 file(s)
  projtruth/freshness.py           file    1 file(s)
R2  Evidence is indexed from both agent-neutral roots
  projtruth/evidence.py            file    1 file(s)
R3  MCP server speaks stdio JSON-RPC 2.0 with 8 tools
  projtruth/mcp_server.py          file    1 file(s)
R4  CLI mirrors the core and gates CI
  projtruth/cli.py                 file    1 file(s)
R5  Registry writes are atomic and tolerant of damaged logs
  projtruth/store.py               file    1 file(s)
R6  Evidence can declare the requirements it proves
  projtruth/evidence.py            file    1 file(s)
R7  report --changed scopes the report to touched requirements
  projtruth/freshness.py           file    1 file(s)
  projtruth/report.py              file    1 file(s)
  projtruth/cli.py                 file    1 file(s)
  projtruth/mcp_server.py          file    1 file(s)
R8  The commit guard refuses to invalidate verified evidence
  projtruth/guard.py               file    1 file(s)
  projtruth/cli.py                 file    1 file(s)
```

measured
