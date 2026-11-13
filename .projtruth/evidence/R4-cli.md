# R4 CLI mirrors the core and gates CI

_Run at 2026-11-14 04:12:17_

```
$ python -m unittest tests.test_core.ImportTests -v   # exit 0
test_import_missing_file_is_an_error (tests.test_core.ImportTests) ... ok
test_import_spec (tests.test_core.ImportTests) ... ok
test_import_spec_is_idempotent (tests.test_core.ImportTests) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.040s

OK

```

```
$ python -m unittest tests.test_core.RegistryValidationTests -v   # exit 0
test_a_criterion_id_that_cannot_link_is_quarantined (tests.test_core.RegistryValidationTests) ... ok
test_duplicate_ids_are_quarantined (tests.test_core.RegistryValidationTests) ... ok
test_files_must_be_a_list_of_strings (tests.test_core.RegistryValidationTests) ... ok
test_unreadable_registry_raises_instead_of_looking_empty (tests.test_core.RegistryValidationTests) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.022s

OK

```

measured
