# R7 report --changed scopes to touched requirements

_Run at 2026-11-14 04:12:20_

```
$ python -m unittest tests.test_guard.GlobTests -v   # exit 0
test_directory_pattern_covers_the_subtree (tests.test_guard.GlobTests) ... ok
test_double_star_spans_directories (tests.test_guard.GlobTests) ... ok
test_outside_patterns_match_nothing (tests.test_guard.GlobTests) ... ok
test_single_star_stops_at_a_slash (tests.test_guard.GlobTests) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.001s

OK

```

```
$ python -m projtruth report --changed HEAD   # only server.py changed   # exit 0
# projtruth status report (2026-11-14 04:12) - changes since HEAD: 2 file(s), 2 requirement(s) in scope

| requirement | status | criteria | evidence | tier | scope | freshest evidence | changed files |
|---|---|---|---|---|---|---|---|
| R1 api | **pending** | 1 | 0 | - | 1 pattern(s) | - | server.py |
| R2 ui | **pending** | 1 | 0 | - | 1 pattern(s) | - | - |

## Needs attention (2 of 2)
- R1 (pending, not started): no evidence
- R2 (pending, not started): no evidence
```

measured
