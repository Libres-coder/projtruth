"""projtruth freshness: when did a requirement's source last change?

`git clone` and `git checkout` rewrite every file's mtime, so mtime alone says
"everything changed just now" on a fresh checkout and "nothing changed" after
touching a file with a preserved timestamp. That is the difference between a
report people trust and one they learn to ignore.

When the repo is a git work tree we ask git instead:

* newest commit that touched the requirement's files (`git log -1 --format=%ct`),
  one call per requirement, cached;
* bumped to "now" when any of those files is uncommitted (`git status --porcelain`),
  because an uncommitted edit is by definition newer than the evidence.

Non-git repos, and requirements with no `files:` globs, fall back to mtimes over
the whole tree (the v1 behaviour).
"""
import fnmatch
import glob
import os
import subprocess
import time

IGNORE_DIRS = {".git", "node_modules", "__pycache__", "graphify-out", ".venv", "venv",
               "dist", "build", "target", ".next", ".projtruth", ".claude", ".idea"}
DEFAULT_IGNORES = ("PROGRESS.md", "README*", "LICENSE*", "CHANGELOG*",
                   "CONTRIBUTING*", ".gitignore", "*.lock")
# Tool state and bookkeeping never count as "the code changed": projtruth's own
# .projtruth/ writes, a new evidence file, a README edit. Without this every
# `init` marks the whole project stale.
STATE_PREFIXES = (".projtruth/", ".claude/", ".git/", ".idea/", "graphify-out/")
EXCLUDES = [":(exclude).projtruth", ":(exclude).claude", ":(exclude).git",
            ":(exclude).idea", ":(exclude)graphify-out",
            ":(exclude,glob)**/PROGRESS.md", ":(exclude,glob)**/README*",
            ":(exclude,glob)**/CHANGELOG*", ":(exclude,glob)**/CONTRIBUTING*",
            ":(exclude,glob)**/LICENSE*", ":(exclude,glob)**/*.lock"]
MAX_PATHSPECS = 200


def _ignored_path(path):
    p = path.replace("\\", "/")
    if p.startswith(STATE_PREFIXES):
        return True
    return any(fnmatch.fnmatch(os.path.basename(p), ig) for ig in DEFAULT_IGNORES)


def _run(repo, *args):
    """Run git in repo; return stdout on exit 0, else None (never raises)."""
    try:
        proc = subprocess.run(["git", "-C", repo] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def expand(repo, patterns):
    """Resolve repo-relative globs to existing files (absolute paths, deduped)."""
    out = []
    for p in patterns:
        full = os.path.join(repo, p)
        if any(ch in p for ch in "*?["):
            out.extend(f for f in glob.glob(full, recursive=True) if os.path.isfile(f))
        elif os.path.isfile(full):
            out.append(full)
    return sorted(set(out))


def _mtime_newest(repo, patterns=None):
    if patterns:
        newest = 0.0
        for f in expand(repo, patterns):
            try:
                newest = max(newest, os.path.getmtime(f))
            except OSError:
                pass
        return newest
    newest = 0.0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if any(fnmatch.fnmatch(f, ig) for ig in DEFAULT_IGNORES):
                continue
            try:
                newest = max(newest, os.path.getmtime(os.path.join(root, f)))
            except OSError:
                continue
    return newest


class Clock(object):
    """Answers: when was this requirement's code last changed?"""

    def __init__(self, repo):
        self.repo = os.path.abspath(repo)
        self._is_git = None
        self._dirty = None
        self._log_cache = {}
        self._file_cache = {}

    # -- git plumbing -----------------------------------------------------
    def is_git(self):
        if self._is_git is None:
            out = _run(self.repo, "rev-parse", "--is-inside-work-tree")
            self._is_git = bool(out) and out.strip() == "true"
        return self._is_git

    def _dirty_paths(self):
        if self._dirty is None:
            out = _run(self.repo, "status", "--porcelain")
            paths = []
            if out:
                for line in out.splitlines():
                    if len(line) < 4:
                        continue
                    path = line[3:]
                    if " -> " in path:          # rename: take the new path
                        path = path.split(" -> ", 1)[1]
                    path = path.strip().strip('"').replace("\\", "/")
                    if not _ignored_path(path):
                        paths.append(path)
            self._dirty = paths
        return self._dirty

    def _log_time(self, pathspecs):
        key = tuple(pathspecs) if pathspecs else ()
        if key in self._log_cache:
            return self._log_cache[key]
        args = ["log", "-1", "--format=%ct"]
        if pathspecs:
            args += ["--"] + list(pathspecs)
        else:
            args += ["--", "."] + EXCLUDES
        out = _run(self.repo, *args)
        try:
            ts = float(out.strip()) if out and out.strip() else 0.0
        except ValueError:
            ts = 0.0
        self._log_cache[key] = ts
        return ts

    # -- public -----------------------------------------------------------
    def latest_change(self, patterns=None):
        """Epoch seconds of the newest change to files matching patterns.

        patterns=None means the whole source tree (bookkeeping files ignored).
        Returns 0.0 when nothing matches, i.e. nothing that could be stale.
        """
        if not self.is_git():
            return _mtime_newest(self.repo, patterns)
        files = expand(self.repo, patterns) if patterns else []
        if patterns and not files:
            return 0.0
        dirty = self._dirty_paths()
        if patterns:
            rels = [os.path.relpath(f, self.repo).replace("\\", "/") for f in files]
            for d in dirty:
                for rel in rels:
                    if rel == d or fnmatch.fnmatch(rel, d):
                        return time.time()
            if len(rels) > MAX_PATHSPECS:
                return self._log_time(None)
            return self._log_time(rels)
        # whole repo: an uncommitted change anywhere counts as "now"
        if dirty:
            return time.time()
        return self._log_time(None)

    def for_requirement(self, req):
        return self.latest_change(req.get("files") or None)

    def file_time(self, rel_path):
        """When the *content* of this file last changed (git) or its mtime."""
        rel = rel_path.replace("\\", "/")
        if rel in self._file_cache:
            return self._file_cache[rel]
        if not self.is_git():
            ts = self._mtime_of(rel)
        elif any(rel == d or fnmatch.fnmatch(rel, d) for d in self._dirty_paths()):
            ts = time.time()
        else:
            ts = self._log_time([rel])
            if ts == 0.0:                     # untracked-but-clean is impossible; be safe
                ts = self._mtime_of(rel)
        self._file_cache[rel] = ts
        return ts

    def _mtime_of(self, rel):
        try:
            return os.path.getmtime(os.path.join(self.repo, rel))
        except OSError:
            return 0.0
