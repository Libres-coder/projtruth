# Status model

Five states. The first two are outcomes of evidence; the last three are
declarations by a human or agent.

| status | produced by | meaning |
|---|---|---|
| `verified` | evidence newer than the code it covers | done, and still true |
| `stale` | evidence, but the code changed after it | was true; needs re-verification |
| `unverified` | a declared status evidence cannot back | a claim |
| `implemented` | declared, no evidence yet | a claim reached by a different route |
| `pending` | declared, no evidence yet | not started |

## How `compute_status` decides

```
evidence = files whose basename starts with R<n> or R<n>.<i>
if no evidence:
    pending | implemented  -> keep the declared status  (they are honest claims)
    verified | stale       -> unverified                (evidence outranks words)
else:
    if newest_source_change(requirement) > newest_evidence_change + 1s: stale
    else: verified
```

The one-second tolerance absorbs filesystem timestamp granularity; it is not a
fudge factor for "almost fresh".

## What "newest source change" means

`freshness.Clock` answers per requirement:

1. **git work tree** (the normal case)
   - `git status --porcelain` once. If any file matching the requirement's
     `files` globs is uncommitted → "now".
   - otherwise `git log -1 --format=%ct -- <those files>` → newest commit time.
   - `files` empty → the same computation over the whole repo, excluding
     `.projtruth/`, `.claude/`, `.git/`, `graphify-out/`, `PROGRESS.md`,
     `README*`, `CHANGELOG*`, `CONTRIBUTING*`, `LICENSE*`, `*.lock`.
2. **not a git repo** → newest mtime among matching files (whole tree when no
   scope), same exclusions.

Evidence files get the same treatment (`Clock.file_time`), so a checkout that
rewrites every mtime does not make old evidence look new.

## Why not mtime everywhere

`git clone`, `git checkout` and most archive extractions set every file's mtime
to "now". A mtime-only tool reports *everything changed just now* on first run
in a fresh checkout - the exact opposite of the truth. Commit time plus
dirty-file detection is the only cheap signal that survives that.

## Why scope matters

A requirement with no `files` is scoped to the whole repository: any source edit
marks it stale. That is the honest default before anyone knows which files
matter, and it is wrong the moment a project has more than one feature.

```
R1  POST /todos       -> server.py
R4  create + render   -> index.html, app.js
```

With that, editing `server.py` flips R1-R3 to stale and leaves R4 verified -
which is what a developer would say by hand.

Scope matching nothing (`files: ["future/**/*.py"]`) yields "never stale": a
requirement about code that does not exist yet cannot be invalidated by other
code.

## Declared status is not useless

It answers "has anyone started this?" before evidence exists. `pending` and
`implemented` survive the computation; `verified` and `stale` do not, because
they are claims about evidence and evidence is checked.
