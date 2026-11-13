# Contributing

Thanks for looking. This project is deliberately small; the fastest way to get a
change merged is to keep it that way.

## Ground rules

- **Standard library only.** No runtime dependencies, ever. If a feature needs a
  library, it belongs in a different tool.
- **Python 3.8+.** No walrus-only tricks, no `match`, no `str.removeprefix`.
- **Mechanism over instruction.** If a rule matters, a test or an exit code should
  enforce it, not a paragraph in a SKILL.md.
- **No claim without evidence.** A PR that says "works" is a draft. Paste the
  command and its output, or add a test.

## Run the tests

```bash
python -m unittest discover -s tests -v
projtruth hook install          # optional: the guard in this repo's own commits
```

The git-freshness tests create throwaway repositories in the system temp
directory and set `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` for determinism. They
skip automatically when `git` is not on `PATH`.

## Layout

```
projtruth/          package (store, evidence, freshness, report, cli, mcp_server)
tests/              unittest suite, no fixtures on disk
SKILL.md            Claude Code skill wrapper over the MCP tools / CLI
references/         the long-form docs SKILL.md links to
```

## Adding an MCP tool

1. Add the entry to `TOOLS` in `projtruth/mcp_server.py` with a description that
   says **when to call it** - that text is the model's only guidance.
2. Implement it in `call_tool` by delegating to the package; raise `ValueError`
   for user errors so the protocol returns `isError: true` instead of crashing.
3. Add the CLI equivalent if it is useful from a terminal or CI.
4. Extend `tests/test_mcp.py::test_every_tool_is_callable_and_returns_text` -
   every tool must survive an empty/garbage argument object.

## Changing the status model

`report.compute_status` is the contract. Any change there needs:

- a test for each state transition it touches;
- a CHANGELOG entry under "Changed", with the user-visible difference;
- a note in `references/status-model.md` explaining the new rule, not just what
  the code does.

Breaking changes to `.projtruth/requirements.json` must bump `SCHEMA_VERSION`
and keep `store.load` able to read the previous version.

## Evidence in this repo

`projtruth` tracks its own requirements in `.projtruth/` and its own evidence in
`.projtruth/evidence/`. If you change behaviour covered by a requirement, add
the run to that requirement's evidence file - then `projtruth report` on this
repo tells the next contributor what still holds.

## Commit messages

`<area>: <imperative summary>` - `report: show file scope in the table`,
`freshness: treat uncommitted edits as changes`. Body explains *why*, and what
you found that the diff does not show.

## Reporting bugs

Include: the command, the `.projtruth/requirements.json` (redacted), `git status
--short`, and whether the repo is a git work tree. Freshness bugs are almost
always about one of those three.
