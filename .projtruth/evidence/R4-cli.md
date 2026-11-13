# R4 the CLI mirrors the core and gates CI

```
$ python -m unittest tests.test_core.ImportTests -v   # exit 0
test_import_missing_file_is_an_error (tests.test_core.ImportTests) ... ok
test_import_spec (tests.test_core.ImportTests) ... ok
test_import_spec_is_idempotent (tests.test_core.ImportTests) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.043s

OK
```

measured
