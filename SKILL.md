---
name: projtruth
description: Answers "what is actually done?" for a codebase - requirements, acceptance criteria, the evidence behind each, and whether that evidence still holds - via the projtruth MCP tools or the `projtruth` CLI. Use when asked what is finished or left, whether a feature is really verified, which requirements have no evidence, why a status went stale, or to record a decision so later sessions do not re-litigate it. Also use when a spec.md exists but nobody knows which half is implemented and proven (需求状态/哪些需求没验证/验收证据/项目真相/是不是真做完了/上线前核对). Not for: free-form project notes or memory (use a memory tool), code structure questions (use graphify), or producing the verification itself (use verify-first).
---

# projtruth

A project promises things. Code drifts. `projtruth` keeps the promises, the
acceptance criteria, the evidence and the decisions in one place, and computes -
never asserts - which promises are still backed by proof.

Three questions it answers, and nothing else:

- Which requirements are **verified**, which are **stale**, which have **no evidence**?
- What evidence backs requirement R3, and when was it written?
- Why was this built this way? (decision log, append-only)

## Use it

Prefer the MCP tools when they are connected (`status_report`, `req_list`,
`evidence_scan`, `req_add`, `decide`, ...). Otherwise shell out - same core:

```bash
python -m projtruth init                     # creates .projtruth/, commit it
python -m projtruth import-spec spec.md      # R<n> headings + 验收/Accept bullets
python -m projtruth report                   # the truth table
```

`init`, `import-spec` and `report` are safe to run repeatedly; none of them
deletes or rewrites an existing requirement.

## Status is computed, not declared

| status | meaning | what it means for you |
|---|---|---|
| `verified` | evidence exists and the code has not changed since | you may say "done" |
| `stale` | evidence exists but the code changed after it | re-verify before claiming anything |
| `unverified` | declared done, no evidence behind it | a claim, not a fact |
| `implemented` | declared done, no evidence | a claim, not a fact |
| `pending` | declared, no evidence yet | expected before work starts |

A declared `verified` never overrides missing evidence. If a user says "it's
done", check `status_report` before agreeing.

## Evidence

Evidence is a file whose basename starts with the criterion or requirement id:

```
.claude/skills/verify-<app>/evidence/<date>/R3.1-post-todos.md   # verify-first writes here
.projtruth/evidence/R3.1-post-todos.md                           # agent-neutral drop box
```

Write the real command output in a fenced block and one of the words
`measured` / `inferred` / `guessed` for how it was obtained. See
[references/evidence-format.md](references/evidence-format.md).

Do not hand-write a status to make a report look green. Either produce evidence
or leave the requirement `stale`/`pending` - a report people trust is the whole
product.

## Staleness and scope

Without a scope, **any** source change in the repo marks a requirement stale.
On a real project that is noise. Give each requirement the files it actually
depends on:

```bash
python -m projtruth req-scope R1 server.py
python -m projtruth req-scope R4 "index.html" "web/**/*.js"
```

Freshness is git-based when the repo is a git work tree: the newest commit that
touched those files, bumped to "now" if any of them is uncommitted. That is
deliberate - `git clone` rewrites every mtime, so mtime-only freshness claims
"everything changed just now" on a fresh checkout. Non-git repos fall back to
mtime.

`PROGRESS.md`, README/CHANGELOG/LICENSE, `.claude/`, `.projtruth/` and evidence
files are never counted as source changes.

## Acting on a report

- `stale` → re-run that requirement's verification, write new evidence, commit.
- `unverified` / `implemented` → either produce evidence or set the status back
  to `pending` and say so.
- `pending` → work not started; do not report it as a gap unless the user asked
  for full coverage.

Report what the table says, including the ugly rows. Suggest `--strict` (exit 1
unless every requirement is verified) when the user wants a release gate.

## Decisions

```bash
python -m projtruth decide "SQLite for storage" --why "single-writer CLI, no server"
```

Append-only. Read it (`decisions_list`) before proposing to change an approach
that a previous session already settled - the reason is usually in the `why`.

## Limits, stated honestly

- `import-spec` is a heuristic over `### R<n>` headings and `- 验收:` / `- Accept:`
  bullets. Check the imported list before trusting it.
- Evidence is linked by filename prefix, so `R3-foo.md` also feeds every `R3.n`
  criterion. Name files by criterion when a criterion needs its own proof.
- Without `files` scope, one unrelated edit marks everything stale (by design,
  see above).
- It tracks registered requirements only; work nobody wrote down is invisible.
- MCP reads the repo from `PROJTRUTH_REPO`, else the process cwd - start the
  server from the project root or set the variable.

More: [references/status-model.md](references/status-model.md),
[references/ci-gate.md](references/ci-gate.md).
