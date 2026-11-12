# Evidence format

Evidence is a file. Its name links it to a requirement; its body should let a
skeptic re-check the claim.

## Where

Both roots are scanned; use whichever fits the tool that produced the proof.

```
.claude/skills/verify-<app>/evidence/<date>/<id>-<slug>.md    # verify-first output
.projtruth/evidence/<id>-<slug>.md                            # anything else
```

`.projtruth/evidence/` exists so a Makefile, a pytest plugin, a CI step or a
Cursor agent can drop proof without knowing anything about verify-first.

## Name

```
R3-open.md          feeds requirement R3 (all of its criteria)
R3.1-post-201.md    feeds criterion R3.1 only
notes.md            ignored - no id prefix
```

Prefix match is case-insensitive (`r3-open.md` works). The id must start the
basename.

## Body

Minimum: something a human can re-run or re-read.

````markdown
# R3.1 POST /todos returns 201

```
$ curl -s -o /dev/null -w '%{http_code}' -X POST localhost:8765/todos -d '{"title":"x"}'
201
```

measured
````

Rules that matter:

- Put the **actual output** in a fenced block. A sentence saying "it works" is
  not evidence.
- Include the tier word - `measured`, `inferred` or `guessed` - somewhere in the
  body. `report` shows the tier of the freshest evidence per requirement,
  `evidence_scan` lists it per criterion, and verify-first's gate rejects
  evidence without one.
  - `measured` - a real run, real output, pasted.
  - `inferred` - read from code or a log, not executed.
  - `guessed` - an assumption with no run behind it.
- Record the date and the exact command when the command is not obvious.
- One file per criterion keeps scope tight; one file per requirement is fine
  when the check covers all of them.

## Anti-patterns

| smell | why it fails |
|---|---|
| `R3-ok.md` containing "tested, works" | nothing to re-check; will be trusted until it is wrong |
| evidence written before running the check | the file exists, the claim does not |
| editing the evidence file to bump its date | commit time is compared for tracked files; an uncommitted edit counts at its mtime, so commit the re-run |
| one giant `R1-R9.md` | links to nothing specific; every criterion inherits it |

## Refreshing

When a requirement goes `stale`, re-run the check and **write a new file** (or
replace the body with a new run). The mtime/commit time of the file is what
proves freshness, so a re-run has to actually touch it after the code change.
