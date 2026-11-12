# projtruth

**Requirements in. Evidence out. No claim without proof.**

`projtruth` is a small MCP server (plus a CLI with the same core) that keeps a
project's promises - requirements, acceptance criteria, the evidence behind
each one, and the decisions that shaped them - and computes which promises are
still true.

It answers three questions, for humans and for agents:

- Which requirements are verified, which went stale, which have no evidence?
- What exactly backs R3, and when was it written?
- Why is it built this way? (append-only decision log)

```
$ projtruth report

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 待办创建(API)      | **verified** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 |
| R2 待办列表(API)      | **verified** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 |
| R3 待办完成切换(API)  | **stale**    | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 |
| R4 前端界面           | **verified** | 1 | 1 | measured | 2 pattern(s) | 2026-11-13 06:54 |

## Needs attention (1 of 4)
- R3 (stale, re-verify): code changed 12m ago, after evidence 2026-11-13 05:50
```

The status is **computed, not declared**. A requirement is `verified` only when
evidence exists and the code it covers has not changed since. There is no
word that grants it: `req_set_status` accepts only `pending` and
`implemented`. A `verified` left in an older or hand-edited registry with no
evidence behind it reports as `unverified`.

## Install

Zero dependencies, Python 3.8+.

```bash
pip install git+https://github.com/Libres-coder/projtruth
```

(Not on PyPI yet - install from the repository, or run `python -m projtruth`
from a checkout.)

As an MCP server (Claude Code, Cursor, any MCP client):

```bash
claude mcp add projtruth -- python -m projtruth.mcp_server
# or point a client at: python /path/to/projtruth/projtruth/mcp_server.py
```

The server reads the repo from `PROJTRUTH_REPO`, else the process cwd - start it
in the project root, or set the variable in the MCP server config.

As a skill (adds the workflow guidance to Claude Code):

```bash
git clone https://github.com/Libres-coder/projtruth ~/.claude/skills/projtruth
```

## Quickstart

```bash
cd your-project
projtruth init                        # .projtruth/  (commit this)
projtruth import-spec spec.md         # reads "### R1 title" + "- 验收: ..." / "- Accept: ..."
projtruth req-scope R1 server.py      # optional but recommended - see below
projtruth report                      # what is actually done
```

No spec file? Register requirements directly:

```bash
projtruth req-add R5 "Rate limit login" "6th attempt within a minute returns 429" \
  --files "app/auth/*.py"
```

## Evidence

Evidence is a file whose basename starts with the criterion or requirement id:

```
.claude/skills/verify-<app>/evidence/<date>/R3.1-post-todos.md   # verify-first writes here
.projtruth/evidence/R3.1-post-todos.md                           # agent-neutral drop box
```

The body should contain the real output and a tier word - `measured`,
`inferred` or `guessed`. See [references/evidence-format.md](references/evidence-format.md).

## Status model

| status | meaning |
|---|---|
| `verified` | evidence exists and is newer than the code it covers |
| `stale` | evidence exists, code changed after it - re-verify |
| `unverified` | declared done, nothing backs it |
| `implemented` | declared done, no evidence yet |
| `pending` | not started |

Only `pending` and `implemented` can be declared; `verified`, `stale` and
`unverified` are computed from evidence.

Details: [references/status-model.md](references/status-model.md).

## Freshness without the mtime lies

`git clone` and `git checkout` rewrite every file's timestamp. A mtime-based
tool therefore reports "everything changed just now" on a fresh checkout - the
opposite of the truth. When the repo is a git work tree, `projtruth` uses the
newest commit that touched the requirement's files, and counts an uncommitted
edit at that file's own mtime - not "now", so a re-run right after an edit
still counts as fresh. Non-git repos fall back to mtime.

`.projtruth/`, `.claude/`, `.git/`, `.idea/`, `graphify-out/`, `PROGRESS.md`,
`README*`, `CHANGELOG*`, `CONTRIBUTING*`, `LICENSE*` and `*.lock` never count as
source changes - `projtruth init` alone must not turn a green repo red. A file
with uncommitted changes counts at its own mtime, not "now", so a fresh re-run
of a check is still newer than the edit it answers.

## Scope: precision beats a repo-wide red

Without a scope, any source change marks a requirement stale. Give each one the
files it depends on and the report matches what a developer would say:

```bash
projtruth req-scope R1 server.py "web/api/**/*.js"
```

Editing `server.py` then flips R1 to stale and leaves the UI requirement
verified.

## MCP tools

| tool | for |
|---|---|
| `status_report` | the truth table - call first when asked what is done |
| `req_list` | requirements, criteria count, declared status, scope |
| `req_add` | register a requirement with criteria and file scope |
| `req_set_status` | declare `pending` / `implemented` (`verified`, `stale`, `unverified` are refused) |
| `req_scope` | restrict staleness to file globs |
| `evidence_scan` | re-index evidence by criterion id |
| `decide` / `decisions_list` | append-only decision log |

Stdio JSON-RPC 2.0, newline-delimited, no dependencies, UTF-8 forced on Windows.

## CI gate

```bash
projtruth report --strict      # exit 1 unless every requirement is verified
```

See [references/ci-gate.md](references/ci-gate.md) for a GitHub Actions job
(use `fetch-depth: 0`, and note what the gate does not prove).

## Design

- **One file of state, meant to be committed.** `.projtruth/requirements.json`
  (promises) and `.projtruth/decisions.jsonl` (reasons). No database, no daemon.
- **Computed over declared.** Words cannot make a requirement verified.
- **Small surface.** Eight MCP tools; every one answerable from the files.
- **Agent-neutral.** Anything that can write a file can leave evidence; anything
  that speaks MCP can read the truth.

## Related work

- [verify-first](https://github.com/Libres-coder/verify-first) - the pipeline
  that produces the evidence this tool reads.
- [skill-audit](https://github.com/Libres-coder/skill-audit) - audits the skills
  a Claude Code install has accumulated.

## Limitations

- `import-spec` is a heuristic over headings and bullet prefixes - check its output.
- Evidence links by filename prefix; `R3-x.md` feeds every `R3.n` criterion.
- A scope glob that matches nothing means "never stale" - a typo fails silently.
- Inside a git submodule, edits are invisible to the superproject's history.
- Unscoped requirements go stale on any source change (by design).
- Only registered requirements are tracked; undocumented work is invisible.
- It does not run anything. It reports what was recorded, and when.

## License

MIT
