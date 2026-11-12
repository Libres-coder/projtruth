# CI gate

`projtruth report --strict` exits `1` unless every requirement is `verified`.
That is the whole gate; nothing else is needed to wire it in.

```yaml
# .github/workflows/truth.yml
name: truth
on: [push, pull_request]
jobs:
  truth:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # freshness compares commit times; a shallow clone lies
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install git+https://github.com/Libres-coder/projtruth
      - run: projtruth report --strict
```

`fetch-depth: 0` matters: with a shallow clone, `git log -1 --format=%ct` on
evidence files can return the graft commit's time and freshness judgements
become arbitrary.

## Pre-commit variant

```bash
projtruth report --strict || {
  echo "unverified requirements - see: projtruth report"
  exit 1
}
```

If the gate is only meant for release branches, run it there instead of on
every push: a WIP branch is legitimately full of `pending` requirements.

## What the gate is not

- It does not run your tests. It checks that *someone recorded a run* after the
  last code change. Pair it with the `verify-first` PreToolUse hook if you want
  commits blocked at the moment of committing.
- It cannot see work that was never registered as a requirement. A green gate
  means "everything we wrote down is proven", not "the product is correct".
- It trusts the evidence files, so a fabricated evidence file passes. The tier
  word (`measured`/`inferred`/`guessed`) is reported, not enforced; treat a repo
  full of `guessed` as a red flag rather than a pass.

## Exit codes

| code | meaning |
|---|---|
| 0 | report printed. Without `--strict` this says nothing about the statuses |
| 1 | `--strict` and at least one requirement is not verified; also when the registry is empty, because an empty registry cannot be green |
| 2 | usage error (argparse) |
