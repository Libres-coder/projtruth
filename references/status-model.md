# Status model

Five states. `verified` and `stale` are outcomes of evidence. `pending` and
`implemented` are declarations a human or agent makes. `unverified` is what the
registry shows when it claims done with nothing behind it - reachable through an
older or hand-edited registry, not through the API: `req_set_status` accepts
only `pending` and `implemented`, and refuses the other three.

| status | produced by | meaning |
|---|---|---|
| `verified` | evidence newer than the code it covers | done, and still true |
| `stale` | evidence, but the code changed after it | was true; needs re-verification |
| `unverified` | no evidence, registry says done (legacy or hand-edited) | a claim |
| `implemented` | declared, no evidence yet | a claim reached by a different route |
| `pending` | declared, no evidence yet | not started |

## How `compute_status` decides

```
evidence = files whose basename starts with R<n> or R<n>.<i>
if no evidence:
    pending | implemented  -> keep the declared status  (they are honest claims)
    verified | stale       -> unverified                (evidence outranks words;
                                                         not reachable through
                                                         req_set_status)
else:
    if newest_source_change(requirement) > newest_evidence_change + 1s: stale
    else: verified
```

The one-second tolerance absorbs filesystem timestamp granularity; it is not a
fudge factor for "almost fresh".

## What "newest source change" means

`freshness.Clock` answers per requirement:

1. **git work tree** (the normal case)
   - `git status --porcelain -z -uall` once, with `core.quotePath=false` so
     paths with spaces or CJK characters are not mangled. A file with
     uncommitted changes counts at **its own mtime** - never "now", or an edit
     at 10:00 followed by evidence at 10:05 would be stale forever.
   - otherwise `git log -1 --format=%ct --full-history -- <those files>` →
     newest commit time. `--full-history` keeps changes that arrived through a
     merge; without it git's history simplification can hide them.
   - `files` empty → the same computation over the whole repo, excluding
     `.projtruth/`, `.claude/`, `.git/`, `.idea/`, `graphify-out/`,
     `PROGRESS.md`, `README*`, `CHANGELOG*`, `CONTRIBUTING*`, `LICENSE*`, `*.lock`.
   - a plain directory in `files` means the whole subtree.
   - more than 100 matched files are queried in batches, not dropped.
2. **not a git repo** → newest mtime among matching files. With no scope it
   walks the whole tree and applies the same exclusions; a scoped mtime check
   reads only the matched files.

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
code. That also means a typo in a glob fails silently - `req-scope` prints the
pattern count, not the match count, and `report` never complains.

Three things scope cannot see: files inside a **git submodule** (the
submodule's own history holds those commits), evidence **authored before** a code
change but committed after it in the same commit (both sides use commit time),
and an uncommitted edit whose mtime was restored by `cp -p` / `touch -d` - the
mtime is the only timestamp a dirty file has, so commit the edit to be judged by
commit time.

## Declared status is not useless

It answers "has anyone started this?" before evidence exists. `pending` and
`implemented` survive the computation. Everything else is either computed from
evidence or refused at write time - `store.DECLARABLE_STATUS` is the whole list.
