# R5 registry writes are atomic and tolerant of damaged logs

```
$ python.exe -m unittest tests.test_core.StoreTests -v   # exit 0
test_atomic_save_leaves_readable_state (tests.test_core.StoreTests) ... ok
test_corrupt_decision_line_does_not_hide_the_rest (tests.test_core.StoreTests) ... ok
test_corrupt_registry_is_quarantined_not_overwritten (tests.test_core.StoreTests) ... ok
test_crud_and_decisions (tests.test_core.StoreTests) ... ok
test_single_strings_are_not_split_into_characters (tests.test_core.StoreTests) ... ok
test_unsafe_file_patterns_are_rejected (tests.test_core.StoreTests) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.069s

OK
```

measured
