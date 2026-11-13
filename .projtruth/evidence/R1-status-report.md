# R1 status is computed from evidence and real code changes

_Run at 2026-11-14 04:12:16_

```
$ python -m unittest tests.test_core.ReportTests -v   # exit 0
# projtruth status report (2026-11-14 04:12)

No requirements registered yet. Run `projtruth import-spec spec.md` or add one with req_add.
# projtruth status report (2026-11-14 04:12)

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 t | **pending** | 1 | 0 | - | repo | - |

## Needs attention (1 of 1)
- R1 (pending, not started): no evidence
# projtruth status report (2026-11-14 04:12)

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 t | **pending** | 1 | 0 | - | repo | - |

## Needs attention (1 of 1)
- R1 (pending, not started): no evidence
test_empty_registry_says_so (tests.test_core.ReportTests) ... strict: no requirements registered - nothing to gate on
ok
test_measured_evidence_stays_out_of_the_quality_section (tests.test_core.ReportTests) ... ok
test_report_exit_strict (tests.test_core.ReportTests) ... strict: not verified: R1
ok
test_requirement_without_criteria_still_links_its_own_evidence (tests.test_core.ReportTests)
Regression: _req_evidence used to iterate criteria only, so a ... ok
test_scope_ignores_unrelated_changes (tests.test_core.ReportTests) ... ok
test_scope_matching_nothing_is_never_stale (tests.test_core.ReportTests) ... ok
test_statuses (tests.test_core.ReportTests) ... ok
test_table_reports_evidence_tier (tests.test_core.ReportTests) ... ok
test_verified_evidence_without_a_tier_is_reported_in_quality (tests.test_core.ReportTests) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.606s

OK

```

measured
