# R7 report --changed scopes to touched requirements

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
$ (demo-todo) echo '# demonstration edit' >> server.py
python -m projtruth report --changed HEAD   # exit 0
# projtruth status report (2026-11-13 17:22) - changes since HEAD: 3 file(s), 3 requirement(s) in scope

| requirement | status | criteria | evidence | tier | scope | freshest evidence | changed files |
|---|---|---|---|---|---|---|---|
| R1 待办创建(API) | **stale** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 | server.py |
| R2 待办列表(API) | **stale** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 | server.py |
| R3 待办完成切换(API) | **stale** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 | server.py |

## Needs attention (3 of 3)
- R1 (stale, re-verify): code changed 0m ago, after evidence 2026-11-13 05:50 (.claude/skills/verify-demo/evidence/2026-11-13/r1-create.md)
- R2 (stale, re-verify): code changed 0m ago, after evidence 2026-11-13 05:50 (.claude/skills/verify-demo/evidence/2026-11-13/r2-list.md)
- R3 (stale, re-verify): code changed 0m ago, after evidence 2026-11-13 05:50 (.claude/skills/verify-demo/evidence/2026-11-13/r3-toggle.md)
```

measured
