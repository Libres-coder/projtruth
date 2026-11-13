# R6 evidence declares the requirements it proves

```
$ python -m unittest tests.test_guard.DirectiveTests -v   # exit 0
test_directive_links_a_file_with_any_name (tests.test_guard.DirectiveTests) ... ok
test_directive_overrides_the_filename (tests.test_guard.DirectiveTests) ... ok
test_directive_parsing (tests.test_guard.DirectiveTests) ... ok
test_report_uses_declared_evidence (tests.test_guard.DirectiveTests) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.096s

OK
```

```
$ python -m projtruth report   # one file declares R1 and R2.1   # exit 0
# projtruth status report (2026-11-13 19:33)

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 a | **verified** | 1 | 1 | measured | repo | 2026-11-13 19:33 |
| R2 b | **verified** | 1 | 1 | measured | repo | 2026-11-13 19:33 |

All 2 requirement(s) verified with fresh evidence.
```

measured
