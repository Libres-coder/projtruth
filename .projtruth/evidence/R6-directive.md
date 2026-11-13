# R6 evidence declares the requirements it proves

```
$ python -m unittest tests.test_guard.DirectiveTests -v   # exit 0
test_directive_links_a_file_with_any_name (tests.test_guard.DirectiveTests) ... ok
test_directive_overrides_the_filename (tests.test_guard.DirectiveTests) ... ok
test_directive_parsing (tests.test_guard.DirectiveTests) ... ok
test_report_uses_declared_evidence (tests.test_guard.DirectiveTests) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.087s

OK
```

```
$ git add .projtruth/evidence/recheck.txt   # one file, three requirements
(demo-todo) python -m projtruth guard

```

measured
