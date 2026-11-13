# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [1.2.3] - 2026-11-14

An adversarial review (2026-11-14) found one P0, three P1s and four P2s; all
fixed, 61 -> 69 tests.

### Fixed
- **P0: deleting or renaming the implementation left the requirement
  verified**, and `report --changed --strict` passed a branch that removed the
  file. A scope that resolves to no file now asks git for the deletion commit
  (a pattern that never matched anything still counts as "nothing to be
  stale"). Covered for deletion, file scope, directory scope and rename.
- **The guard matched evidence by prefix**, so `R10-rerun.md` counted as
  evidence for R1. It matches the exact id from the filename or the
  `projtruth:` directive.
- **A staged deletion of evidence counted as staged evidence.** The guard now
  reads evidence as of HEAD and ignores files that no longer exist.
- **Case-insensitive filesystems**: a scope written `server.py` never matched
  the tracked `Server.py` in git's case-sensitive pathspec. Expansion resolves
  the real spelling, and path matching is case-insensitive on Windows.
- Registry validation: `files` must be a list of strings (a bare string was
  iterated character by character; an int crashed the report); duplicate ids
  and criterion ids that can never be linked are quarantined; id lookups are
  case-normalized.
- An unreadable registry (lock, permissions) no longer looks like an empty one:
  it raises, the CLI exits 2, and the guard **fails closed** instead of letting
  the commit through.
- `PROJTRUTH_ALLOW_STALE=0` no longer enables the bypass.

## [1.2.2] - 2026-11-14

### Added
- `report` ends with an **Evidence quality** section when a *verified*
  requirement's freshest evidence is `guessed` or carries no tier. Status is
  unchanged - a fresh file is still fresh - but "verified by a guess" stops
  being invisible, which is the failure the tier word exists to prevent.
- `report --json` carries `evidence_tier` per requirement, so a consumer can
  gate on quality without parsing the table.

## [1.2.1] - 2026-11-13

### Fixed
- The evidence tier was read as the first `measured|inferred|guessed` anywhere in
  the body, so a test name or a quoted sentence could decide it. A tier on its
  own line now wins; the loose match is only a fallback.

## [1.2.0] - 2026-11-13

### Added
- **Declared evidence.** A file may say what it proves instead of being named
  after it: `projtruth: R1, R4` (an HTML comment works too) links one file to
  several requirements and overrides the filename prefix. A CI log, a doctor
  note or a screenshot transcript can now feed exactly the requirements it
  proves.
- **`report --changed [REF]`** and **`status_report(changed_since=...)`**:
  narrow a report to the requirements a branch touches, with the matched
  changed files per requirement. `--strict --changed` is the PR gate; a PR that
  touches no tracked requirement passes.
- **`guard` + `hook install`**: a git pre-commit hook that refuses a commit
  which would turn a *verified* requirement stale without staging new evidence.
  Already-stale requirements never block. Escapes: `PROJTRUTH_ALLOW_STALE=1` and
  `git commit --no-verify`, both explicit. The hook refuses to overwrite a
  pre-commit hook it did not write, and `hook status` says which is installed.

### Changed
- Path matching is path-aware: `**/` spans directories and `*` stops at a
  slash, so `web/**/*.js` matches `web/app.js` - the pattern people write first.
- `Clock(repo, dirty=False)` answers "what was true at HEAD?", which is what the
  guard needs: at commit time the staged edit is already on disk.

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
