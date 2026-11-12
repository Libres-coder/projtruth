# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-13

### Added
- `freshness.Clock`: git-backed staleness. Compares the newest commit that
  touched a requirement's files against the evidence file's commit, and counts
  uncommitted edits at the file's own mtime. Fixes the fresh-checkout false
  positive where every mtime is rewritten by `git clone`/`checkout`; non-git
  repos still fall back to mtime.
- Per-requirement file scope: `files` on `req_add`, `req-scope` in the CLI,
  `req_scope` over MCP. Unscoped requirements keep the repo-wide behaviour.
- `.projtruth/evidence/` is scanned alongside
  `.claude/skills/verify-*/evidence/`, so any tool - not just verify-first -
  can leave evidence.
- `report --strict` (exit 1 unless every requirement is verified, and on an
  empty registry - an empty registry cannot be green) for CI.
- `report --json` now carries each requirement's file scope and criterion text.
- Decision log survives a corrupt line instead of returning an empty list.
- Requirement ids are validated (`R<n>`), and requirement writes are atomic
  (unique temp file + `os.replace`).

### Changed
- `req_set_status` only accepts `pending` and `implemented`. `verified` and
  `stale` were already computed; declaring them is now refused with a message
  pointing at the evidence route.
- Status table gained `tier` and `scope` columns; "needs attention" rows now say
  *why* (stale, unverified, pending) and when the code changed.
- `.projtruth/`, `.claude/`, `PROGRESS.md`, `README*`, `CHANGELOG*`,
  `CONTRIBUTING*`, `LICENSE*`, `*.lock` never count as source changes.
- Every MCP tool description now states when to call it; `status_report` is
  first so agents reach for it before `req_list`.

### Fixed
- `projtruth init` writing an untracked `.projtruth/requirements.json` marked
  every requirement stale on the next report (found by dogfooding on demo-todo).
- Writing a new evidence file could itself mark the project stale.
- An uncommitted source edit counted as "changed now", so evidence written after
  the edit was always stale and `--strict` could never pass before a commit.
  Dirty files now count at their own mtime.
- New files inside a brand-new untracked directory were invisible to scope
  matching (`git status` collapsed them to `dir/`); now `-uall`.
- Paths with spaces or CJK characters were mangled by git's default quoting and
  never matched a scope; now `-z` + `core.quotePath=false`.
- A change that arrived through a merge could be hidden by git's history
  simplification; `git log` now uses `--full-history`.
- A requirement with **no criteria** could never link `R5-*.md` evidence and sat
  at `pending` forever.
- `files: ["src"]` (a directory, not a glob) matched nothing and made a
  requirement permanently verified; a directory now means the whole subtree.
- `import-spec` duplicated every criterion when run twice.
- A malformed JSON-RPC line (`[]`, `null`, non-object `params`) could kill the
  MCP server; bad messages now get an error response and the loop continues.
- A damaged `requirements.json` was silently replaced on the next write; it is
  now kept as `requirements.json.corrupt-<ts>`.
- Absolute and `..` file patterns are rejected instead of reading outside the
  repo.
- Concurrent writers shared one fixed temp filename; writes now use `mkstemp`.
- An evidence file deleted between the glob and the read could crash `scan`.

## [1.0.0] - 2026-11-13

### Added
- Initial release: requirement registry (`.projtruth/requirements.json`),
  append-only decision log (`.projtruth/decisions.jsonl`), evidence index over
  `verify-*/evidence/**`, computed status (`verified`/`stale`/`unverified`/
  `implemented`/`pending`), `import-spec` heuristic, markdown and JSON reports,
  zero-dependency stdio MCP server (8 tools), CLI, and test suite.
