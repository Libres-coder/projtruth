"""projtruth guard: refuse a commit that would silently invalidate evidence.

`projtruth hook install` writes this as `.git/hooks/pre-commit`. At commit time
it looks at what is staged:

* for every requirement whose file scope matches a staged file, the commit is
  about to turn `verified` into `stale`;
* if the same commit stages no evidence for that requirement, the commit is
  refused, with the requirement ids and the exact fix.

Already-`stale` or `pending` requirements never block - they are not made worse
by this commit, and blocking them would trap a repository that is catching up.

Escape hatches, both loud: `PROJTRUTH_ALLOW_STALE=1 git commit ...` and
`git commit --no-verify` (the standard hook bypass).
"""
import os
import stat
import sys

from . import evidence, freshness, report, store

MARKER = "projtruth-guard"

HOOK_BODY = """#!/bin/sh
# %s - remove with: projtruth hook uninstall
if ! python -c "import projtruth" >/dev/null 2>&1; then
  if [ -d projtruth ]; then
    export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
  fi
fi
if ! python -c "import projtruth" >/dev/null 2>&1; then
  echo "projtruth: guard skipped - the projtruth package is not importable here" >&2
  echo "projtruth: fix with 'pip install git+https://github.com/Libres-coder/projtruth' or 'projtruth hook uninstall'" >&2
  exit 0
fi
exec python -m projtruth guard
""" % MARKER


def _hook_path(repo):
    """Honour worktrees: the hook lives in the git dir, not necessarily .git/."""
    out = freshness._run(repo, "rev-parse", "--git-path", "hooks/pre-commit")
    if not out:
        return None
    path = out.strip()
    if not os.path.isabs(path):
        path = os.path.join(repo, path)
    return os.path.normpath(path)


def staged_files(repo):
    out = freshness._run(repo, "-c", "core.quotePath=false", "diff", "--cached",
                         "--name-only", "-z", "--diff-filter=ACMRD")
    if out is None:
        return None
    return [p for p in out.split("\0") if p]


def _is_evidence(path):
    p = path.replace("\\", "/")
    return p.startswith(".projtruth/evidence/") or ("/evidence/" in p and
                                                    p.startswith(".claude/skills/verify-"))


def _ids_for(req):
    ids = [req.get("id", "").upper()] + [c.get("id", "").upper()
                                         for c in req.get("criteria", [])]
    return [i for i in ids if i]


def _evidence_ids(repo, rel):
    """Ids this evidence file proves, from its basename or its directive.

    Returns None when the file cannot be read: a staged deletion is not staged
    evidence, and counting it as such used to disarm the guard.
    """
    base = os.path.basename(rel)
    m = evidence.CRIT_RE.match(base)
    ids = set([m.group(1).upper()]) if m else set()
    try:
        with open(os.path.join(repo, rel), encoding="utf-8-sig", errors="replace") as f:
            ids |= set(evidence.declared_ids(f.read()))
    except OSError:
        return None
    return ids


def _staged_evidence_for(repo, req, staged):
    """Evidence staged for this requirement, by exact id or directive.

    Exact, not prefix: `R10-rerun.md` proves R10, not R1.
    """
    ids = set(_ids_for(req))
    for rel in staged:
        if not _is_evidence(rel):
            continue
        found = _evidence_ids(repo, rel)
        if found and ids & found:
            return rel
    return None


def evaluate(repo):
    """[(requirement, [staged files])] that this commit would invalidate."""
    reqs = store.list_requirements(repo)
    if not reqs:
        return []
    staged = staged_files(repo)
    if not staged:
        return []
    idx = evidence.scan_head(repo)              # what HEAD proves, not the worktree
    clock = freshness.Clock(repo, dirty=False)   # judge what HEAD proves
    blocking = []
    for req in reqs:
        hits = freshness.matching_changes(req, staged)
        if not hits:
            continue
        status, _ = report.compute_status(req, idx, clock)
        if status != "verified":
            continue
        if _staged_evidence_for(repo, req, staged):
            continue
        blocking.append((req, hits))
    return blocking


def main(repo, allow=False):
    try:
        blocking = evaluate(repo)
    except store.RegistryUnreadable as e:
        # Fail closed: an unreadable registry is not "no requirements".
        sys.stderr.write("projtruth: %s\n" % e)
        sys.stderr.write("projtruth: commit blocked - the guard cannot read the "
                         "registry\n")
        return 1
    except Exception as e:                     # a guard must never brick commits
        sys.stderr.write("projtruth: guard error (%s) - commit allowed\n" % e)
        return 0
    if not blocking:
        return 0
    lines = ["projtruth: this commit would invalidate proof for %d requirement(s)"
             % len(blocking), ""]
    for req, hits in blocking:
        lines.append("  %s %s" % (req.get("id"), req.get("title", "")))
        for h in hits[:3]:
            lines.append("      <- %s" % h)
        if len(hits) > 3:
            lines.append("      <- +%d more" % (len(hits) - 3))
    lines += ["",
              "The evidence is still valid; committing this change makes it stale.",
              "Re-run the check, then stage the new evidence:",
              "  python -m projtruth report",
              "  git add .projtruth/evidence/",
              "",
              "Or commit anyway: PROJTRUTH_ALLOW_STALE=1 git commit ..."]
    text = "\n".join(lines)
    if allow:
        sys.stderr.write(text + "\n\nprojtruth: allowed (PROJTRUTH_ALLOW_STALE)\n")
        return 0
    sys.stderr.write(text + "\n")
    return 1


def hook_command(repo, action, force=False):
    path = _hook_path(repo)
    if path is None:
        sys.stderr.write("not a git work tree: %s\n" % repo)
        return 1
    exists = os.path.exists(path)
    ours = False
    if exists:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                ours = MARKER in f.read()
        except OSError:
            ours = False
    if action == "status":
        if not exists:
            print("hook not installed (%s)" % path)
        elif ours:
            print("installed: %s" % path)
        else:
            print("a foreign pre-commit hook is installed: %s" % path)
        return 0
    if action == "install":
        if exists and not ours and not force:
            sys.stderr.write("refusing to overwrite %s (not ours); use --force\n" % path)
            return 1
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(HOOK_BODY)
        try:
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass
        print("installed %s" % path)
        return 0
    if action == "uninstall":
        if not exists:
            print("nothing to remove (%s)" % path)
            return 0
        if not ours and not force:
            sys.stderr.write("refusing to remove %s (not ours); use --force\n" % path)
            return 1
        os.remove(path)
        print("removed %s" % path)
        return 0
    return 2
