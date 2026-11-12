# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-13

### Added
- `freshness.Clock`: git-backed staleness. Compares the newest commit that
  touched a requirement's files against the evidence file's commit, and treats
  uncommitted edits to those files as "changed now". Fixes the fresh-checkout
  false positive where every mtime is rewritten by `git clone`/`checkout`;
  non-git repos still fall back to mtime.
- Per-requirement file scope: `files` on `req_add`, `req-scope` in the CLI,
  `req_scope` over MCP. Unscoped requirements keep the repo-wide behaviour.
- `.projtruth/evidence/` is scanned alongside
  `.claude/skills/verify-*/evidence/`, so any tool - not just verify-first -
  can leave evidence.
- `report --strict` (exit 1 unless every requirement is verified) for CI.
- `report --json` now carries each requirement's file scope and criterion text.
- Decision log survives a corrupt line instead of returning an empty list.
- Requirement ids are validated (`R<n>`), and requirement writes are atomic
  (`.tmp` + `os.replace`).

### Changed
- Status table gained a `scope` column; "needs attention" rows now say *why*
  (stale, unverified, pending) and when the code changed.
- `.projtruth/`, `.claude/`, `PROGRESS.md`, `README*`, `CHANGELOG*`,
  `CONTRIBUTING*`, `LICENSE*`, `*.lock` never count as source changes.
- Every MCP tool description now states when to call it; `status_report` is
  first so agents reach for it before `req_list`.

### Fixed
- `projtruth init` writing an untracked `.projtruth/requirements.json` marked
  every requirement stale on the next report (found by dogfooding on demo-todo).
- Writing a new evidence file could itself mark the project stale.

## [1.0.0] - 2026-11-13

### Added
- Initial release: requirement registry (`.projtruth/requirements.json`),
  append-only decision log (`.projtruth/decisions.jsonl`), evidence index over
  `verify-*/evidence/**`, computed status (`verified`/`stale`/`unverified`/
  `implemented`/`pending`), `import-spec` heuristic, markdown and JSON reports,
  zero-dependency stdio MCP server (8 tools), CLI, and test suite.
