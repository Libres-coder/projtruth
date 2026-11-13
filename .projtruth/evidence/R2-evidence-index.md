# R2 Evidence is indexed from both agent-neutral roots

_Run at 2026-11-14 06:12:44_

```
$ python -m unittest tests.test_core.EvidenceTests -v   # exit 0
test_agent_neutral_drop_box_is_scanned (tests.test_core.EvidenceTests) ... ok
test_index_roundtrip (tests.test_core.EvidenceTests) ... ok
test_scan_and_link (tests.test_core.EvidenceTests) ... ok
test_tier_prefers_a_standalone_line (tests.test_core.EvidenceTests)
A test name or a quoted sentence must not decide the tier. ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.039s

OK
```

measured
