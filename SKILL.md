---
name: projtruth
description: >-
  Answers "what is actually registered as done?" for a codebase - requirements,
  acceptance criteria, the evidence behind each, and whether that evidence still
  holds - via the projtruth MCP tools or the projtruth CLI. Use when asked what
  is finished or left, whether a feature is really verified, which requirements
  have no evidence, why a status went stale, or to append to this project's
  decision log so later sessions do not re-litigate a choice. Also use when a
  spec.md exists but nobody knows which half is implemented and proven
  (需求状态, 哪些需求没验证, 验收证据, 项目真相, 是不是真做完了, 做完了吗,
  完成情况, 还差什么, 证据过期, 上线前核对). Works even when graphify-out/
  exists: graphify answers where code is, this answers what is proven. Not for:
  free-form project notes or memory (use a memory tool), code structure
  questions (use graphify), or producing the verification itself (use
  verify-first).
---

# projtruth

A project promises things. Code drifts. `projtruth` keeps the registered
requirements, their acceptance criteria, the evidence and the decisions in one
place, and computes - never asserts - which of them are still backed by proof.

It answers three questions, and nothing else:

- Which **registered requirements** are verified, which are stale, which have no evidence?
- What evidence backs requirement R3, and when was it written?
- Why was this built this way? (this project's decision log, append-only)

## Setup, once per machine

The skill and the MCP server are the same code. Either is enough:

```bash
pip install git+https://github.com/Libres-coder/projtruth
claude mcp add projtruth -- python -m projtruth.mcp_server
```

Without installing, run it from a checkout: `cd <checkout> && python -m projtruth --repo <project>`.
If neither works, say so instead of guessing - do not hand-edit `.projtruth/`.

## Use it

Prefer the MCP tools when connected (`status_report`, `req_list`, `evidence_scan`,
`req_add`, `decide`, ...). Otherwise shell out - same core:

```bash
python -m projtruth init                     # creates .projtruth/, commit it
python -m projtruth import-spec spec.md      # R<n> headings + 验收/Accept bullets
python -m projtruth report                   # the truth table
```

All three are safe to run repeatedly: `init` only creates what is missing,
`import-spec` skips criteria it already has, `report` writes nothing but the
derived index. None of them deletes a requirement.

## Status is computed, not declared

| status | meaning | what it means for you |
|---|---|---|
| `verified` | evidence exists and the code has not changed since | you may say "done" |
| `stale` | evidence exists but the code changed after it | re-verify before claiming anything |
| `unverified` | no evidence, and the registry says done (legacy or hand-edited) | a claim, not a fact |
| `implemented` | declared done, no evidence | a claim, not a fact |
| `pending` | declared, no evidence yet | expected before work starts |

Only `pending` and `implemented` can be declared (`req_set_status`); the other
three are computed. A declared `verified` is not accepted at all - the tool
points at the evidence route instead. If a user says "it's done", check
`status_report` before agreeing.

## Evidence

Evidence is a file whose basename starts with the criterion or requirement id:

```
.claude/skills/verify-<app>/evidence/<date>/R3.1-post-todos.md   # verify-first writes here
.projtruth/evidence/R3.1-post-todos.md                           # agent-neutral drop box
```

Put the real command output in a fenced block and one of the words `measured`,
`inferred` or `guessed` in the body; `report` shows that tier next to the
freshest evidence. See [references/evidence-format.md](references/evidence-format.md).

Do not hand-write a status to make a report look green. Either produce evidence
or leave the requirement `stale`/`pending` - a report people trust is the whole
product.

## Staleness and scope

Without a scope, **any** source change in the repo marks a requirement stale.
On a real project that is noise. Give each requirement the files it actually
depends on (a plain directory means the whole subtree):

```bash
python -m projtruth req-scope R1 server.py
python -m projtruth req-scope R4 "index.html" "web" "src/**/*.js"
```

Freshness is git-based when the repo is a git work tree: the newest commit that
touched those files, or the file's own mtime if it has uncommitted changes -
never "now", so an edit followed by fresh evidence still counts as verified.
That is deliberate: `git clone` rewrites every mtime, so mtime-only freshness
claims "everything changed just now" on a fresh checkout. Non-git repos fall
back to mtime.

`.projtruth/`, `.claude/`, `.git/`, `.idea/`, `graphify-out/`, `PROGRESS.md`,
`README*`, `CHANGELOG*`, `CONTRIBUTING*`, `LICENSE*` and `*.lock` are never
counted as source changes - `init` alone must not turn a green repo red.

## Acting on a report

- `stale` → re-run that requirement's verification, write new evidence, commit.
- `unverified` (legacy or hand-edited registry) → set it back to `implemented`
  or `pending`, then produce evidence.
- `implemented` → an honest declaration; produce evidence. Do not downgrade it.
- `pending` → work not started. The report lists it under "Needs attention";
  that is a reminder, not a gap, unless the user asked for full coverage.

Report what the table says, including the ugly rows. Suggest `--strict` (exit 1
unless every requirement is verified, and on an empty registry) when the user
wants a release gate.

## Decisions

```bash
python -m projtruth decide "SQLite for storage" --why "single-writer CLI, no server"
```

Append-only. Read it (`decisions_list`) before proposing to change an approach
a previous session already settled - the reason is usually in the `why`.

## Limits, stated honestly

- `import-spec` is a heuristic: 2-4 `#` headings shaped `R<n>` followed by a
  separator and a title, then `- ` or `* ` bullets starting with `验收` or
  `Accept` (optional full-width colon). Check the imported list with `req-list`.
- Evidence is linked by filename prefix, so `R3-foo.md` feeds every `R3.n`
  criterion as well as R3. Name files by criterion when a criterion needs its
  own proof.
- Without `files` scope, one unrelated edit marks everything stale (by design).
- File patterns must be repo-relative; absolute paths and `..` are rejected.
  A pattern that matches nothing means "never stale" - usually a typo.
- It tracks registered requirements only; work nobody wrote down is invisible.
- Inside a git submodule, edits are seen by the submodule's own git, not the
  superproject's - scope requirements to the parent repository's own files.
- MCP reads the repo from `PROJTRUTH_REPO`, else the process cwd - start the
  server from the project root or set the variable.

More: [references/status-model.md](references/status-model.md),
[references/ci-gate.md](references/ci-gate.md).
