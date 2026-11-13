"""projtruth freshness: when did a requirement's source last change?

`git clone` and `git checkout` rewrite every file's mtime, so mtime alone says
"everything changed just now" on a fresh checkout and "nothing changed" after
touching a file with a preserved timestamp. That is the difference between a
report people trust and one they learn to ignore.

When the repo is a git work tree we ask git instead:

* newest commit that touched the requirement's files (`git log --full-history`),
  one call per requirement, cached;
* a file with uncommitted changes counts at its **own mtime**, not "now" - an
  edit at 10:00 and a fresh piece of evidence at 10:05 means the evidence is
  newer, and returning "now" would call it stale forever;
* `--full-history` so a change that arrived through a merge is still seen;
* `-z` + `core.quotePath=false` so paths with spaces or CJK characters are not
  mangled.

Non-git repos, and requirements with no `files:` globs, fall back to mtimes.
"""
import fnmatch
import glob
import os
import re
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
MAX_PATHSPECS = 100
MAX_EXPANDED = 20000
_WIN_ABS = re.compile(r"^[A-Za-z]:[\\/]")


def _ignored_path(path):
    p = path.replace("\\", "/")
    if p.startswith(STATE_PREFIXES):
        return True
    return any(fnmatch.fnmatch(os.path.basename(p), ig) for ig in DEFAULT_IGNORES)


def _safe_pattern(pattern):
    """Repo-relative only: an absolute path or '..' can point outside the repo.

    `C:/x` is not absolute on POSIX, so the drive-letter form is checked
    explicitly - a registry written on Windows must behave the same everywhere.
    """
    p = str(pattern).replace("\\", "/")
    if os.path.isabs(p) or p.startswith("/") or _WIN_ABS.match(p):
        return False
    return ".." not in p.split("/")


def _files_under(directory):
    """Every file below directory, skipping build/VCS dirs. One walk, no re-glob
    per matched subdirectory, and dotfiles included (glob's '*' skips them)."""
    out = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            out.append(os.path.join(root, f))
            if len(out) >= MAX_EXPANDED:
                return out
    return out


def _match_case(pattern, rel):
    """Case-sensitive, path-aware glob match: `*` and `?` stay inside a segment,
    `**` spans directories. Python's glob is case-insensitive on Windows; git's
    pathspec is not, and neither is CI."""
    def walk(pp, ss):
        if not pp:
            return not ss
        head = pp[0]
        if head == "**":
            return walk(pp[1:], ss) or (bool(ss) and walk(pp, ss[1:]))
        if not ss:
            return False
        return fnmatch.fnmatchcase(ss[0], head) and walk(pp[1:], ss[1:])
    pat = pattern.replace("\\", "/")
    while pat.startswith("./"):
        pat = pat[2:]
    return walk(pat.split("/"), rel.replace("\\", "/").split("/"))


def describe_scope(repo, patterns):
    """How each scope pattern resolves - including the ways it resolves to
    nothing, or only on a case-insensitive filesystem.

    A scope that matches nothing means "never stale", so a typo fails silently;
    a wrong-case path works on Windows and matches nothing on Linux/CI. This is
    the check for both, without changing what the scope means.
    """
    out = []
    for pattern in patterns or []:
        p = str(pattern).replace("\\", "/")
        entry = {"pattern": p, "kind": "", "files": 0, "note": ""}
        if not _safe_pattern(p):
            entry.update(kind="unsafe",
                         note="absolute path or '..' - ignored by every check")
            out.append(entry)
            continue
        if any(ch in p for ch in "*?["):
            full = os.path.join(repo, p)
            matches = glob.glob(full, recursive=True)
            exact = [f for f in matches
                     if _match_case(p, os.path.relpath(f, repo).replace("\\", "/"))]
            entry.update(kind="glob", files=len(exact))
            if not exact:
                if matches:
                    entry["note"] = ("matches %d path(s) only case-insensitively; "
                                     "Linux and CI will match nothing" % len(matches))
                else:
                    entry["note"] = "matches nothing - a typo fails silently"
            out.append(entry)
            continue
        real = _existing_case(repo, p)
        if real is None:
            entry.update(kind="missing",
                         note="does not exist at this spelling - a typo fails silently")
        else:
            rel = os.path.relpath(real, repo).replace("\\", "/")
            is_dir = os.path.isdir(real)
            entry.update(kind="dir" if is_dir else "file",
                         files=len(_files_under(real)) if is_dir else 1)
            if rel != os.path.normpath(p).replace("\\", "/"):
                entry["note"] = ("spelled %r on disk; git and CI match "
                                 "case-sensitively" % rel)
        out.append(entry)
    return out


def _existing_case(repo, rel):
    """The path as it exists on disk, resolving spelling on a case-insensitive
    filesystem. A registry written as `server.py` must find `Server.py`; git's
    pathspec matching is case-sensitive even where Windows is not."""
    cur = repo
    parts = [p for p in str(rel).replace("\\", "/").split("/") if p not in ("", ".")]
    for part in parts:
        try:
            names = os.listdir(cur)
        except OSError:
            return None
        if part in names:
            cur = os.path.join(cur, part)
            continue
        if os.name != "nt":
            return None
        hit = next((n for n in names if n.lower() == part.lower()), None)
        if hit is None:
            return None
        cur = os.path.join(cur, hit)
    return cur


def expand(repo, patterns):
    """Resolve repo-relative globs to existing files (absolute paths, deduped).

    A pattern that names a directory means the whole subtree - `files: ["src/api"]`
    would otherwise match nothing and make the requirement permanently verified.
    """
    out = []
    for p in patterns:
        if not _safe_pattern(p):
            continue
        full = os.path.join(repo, p)
        if any(ch in p for ch in "*?["):
            for f in glob.glob(full, recursive=True):
                if os.path.isfile(f):
                    out.append(f)
                elif os.path.isdir(f) and not _ignored_dir(f, repo):
                    out.extend(_files_under(f))
            continue
        real = _existing_case(repo, p)
        if real and os.path.isfile(real):
            out.append(real)
        elif real and os.path.isdir(real) and not _ignored_dir(real, repo):
            out.extend(_files_under(real))
    return sorted(set(out))


def _ignored_dir(path, repo):
    """A scope that names a build/VCS directory by hand is a mistake, not a file list."""
    parts = os.path.relpath(path, repo).replace("\\", "/").split("/")
    return any(part in IGNORE_DIRS for part in parts)


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


def _parse_status(out):
    """Paths from `git status --porcelain -z` output.

    The field order for a rename is destination first, origin second (and the
    origin is its own NUL field) - so the origin must be skipped, or it would be
    read as a file named after the old path.
    """
    paths = []
    fields = out.split("\0") if out else []
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if "R" in status or "C" in status:
            i += 1
        paths.append(path.replace("\\", "/"))
    return paths


def changed_files(repo, since="HEAD"):
    """Repo-relative files changed since a git ref, plus uncommitted changes.

    Returns None when git cannot answer (not a repo, unknown ref) - the caller
    must not treat that as "nothing changed".
    """
    committed = []
    if str(since).upper() != "HEAD":
        out = _run(repo, "diff", "--name-only", "-z", "%s...HEAD" % since)
        if out is None:
            return None
        committed = [p for p in out.split("\0") if p]
    status = _run(repo, "-c", "core.quotePath=false", "status", "--porcelain",
                  "-z", "--untracked-files=all")
    if status is None:
        return None
    return sorted(set(committed) | set(_parse_status(status)))


def _glob_to_re(pattern):
    """Path-aware glob: `*` stops at a slash, `**/` spans directories.

    fnmatch's `*` crosses slashes, so `web/**/*.js` would miss `web/app.js` -
    the exact pattern people write first.
    """
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i:i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
            elif pattern[i:i + 2] == "**":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            j = pattern.find("]", i + 1)
            if j == -1:
                out.append(re.escape(c))
                i += 1
            else:
                out.append(pattern[i:j + 1])
                i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


_GLOB_CACHE = {}


def _glob_match(rel, pattern):
    rx = _GLOB_CACHE.get(pattern)
    if rx is None:
        rx = _GLOB_CACHE[pattern] = _glob_to_re(pattern)
    return rx.match(rel) is not None


def path_matches(rel, pattern):
    """Does a repo-relative path fall under a requirement's file pattern?

    Compared case-insensitively on Windows: the filesystem is, and git is not,
    so `Server.py` edited against a `server.py` scope must still match.
    """
    rel = rel.replace("\\", "/")
    p = str(pattern).replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    if not _safe_pattern(p):
        return False
    if os.name == "nt":
        rel, p = rel.lower(), p.lower()
    if any(ch in p for ch in "*?["):
        return _glob_match(rel, p)
    p = p.rstrip("/")
    return rel == p or rel.startswith(p + "/")


def matching_changes(req, changed):
    """The subset of `changed` (repo-relative) this requirement depends on."""
    rels = [c.replace("\\", "/") for c in changed if not _ignored_path(c)]
    patterns = req.get("files") or []
    if not patterns:
        return rels                      # unscoped: any source change counts
    out = []
    for rel in rels:
        if any(path_matches(rel, p) for p in patterns):
            out.append(rel)
    return out


class Clock(object):
    """Answers: when was this requirement's code last changed?"""

    def __init__(self, repo, dirty=True):
        """dirty=False answers "what was true at HEAD?" - uncommitted edits are
        ignored. The commit guard needs that: at commit time the staged edit is
        already on disk, so the working-tree answer is always "changed". """
        self.repo = os.path.abspath(repo)
        self.use_dirty = dirty
        self._is_git = None
        self._dirty = None
        self._dirty_all = None
        self._log_cache = {}
        self._file_cache = {}

    # -- git plumbing -----------------------------------------------------
    def is_git(self):
        if self._is_git is None:
            out = _run(self.repo, "rev-parse", "--is-inside-work-tree")
            self._is_git = bool(out) and out.strip() == "true"
        return self._is_git

    def _dirty_paths(self, filtered=True):
        """Paths with uncommitted changes.

        filtered=True drops tool state and bookkeeping (what "the code changed"
        means). file_time needs the unfiltered list: re-running a check edits an
        existing evidence file, and that edit is newer than its commit.
        """
        if self._dirty is None:
            # -z: NUL-separated, no quoting; -uall: an untracked directory is
            # otherwise collapsed to "dir/", which no file path can match.
            out = _run(self.repo, "-c", "core.quotePath=false", "status",
                       "--porcelain", "-z", "--untracked-files=all")
            every = _parse_status(out)
            self._dirty_all = every
            self._dirty = [p for p in every if not _ignored_path(p)]
        return (self._dirty or []) if filtered else (self._dirty_all or [])

    def _mtime_of(self, rel):
        try:
            return os.path.getmtime(os.path.join(self.repo, rel))
        except OSError:
            return 0.0

    def _changed_time(self, rel):
        """When an uncommitted file actually changed: its mtime, not "now"."""
        return self._mtime_of(rel) or time.time()

    def _log_time(self, pathspecs):
        key = tuple(pathspecs) if pathspecs else ()
        if key in self._log_cache:
            return self._log_cache[key]
        args = ["log", "-1", "--format=%ct", "--full-history"]
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
            # The scope resolves to nothing: the implementation may have been
            # deleted or renamed. Git still remembers the deletion commit; a
            # pattern that never matched anything returns 0.0, which is
            # "nothing that could be stale". Returning 0.0 for a deleted file
            # used to keep the requirement verified after `git rm`.
            specs = [str(p).replace("\\", "/").rstrip("/") for p in patterns]
            return self._log_time(specs)
        dirty = self._dirty_paths() if self.use_dirty else []
        if patterns:
            rels = [os.path.relpath(f, self.repo).replace("\\", "/") for f in files]
            newest = 0.0
            for d in dirty:
                for rel in rels:
                    if rel == d or fnmatch.fnmatch(rel, d):
                        newest = max(newest, self._changed_time(rel))
            if newest:
                return newest
            if len(rels) > MAX_PATHSPECS:       # keep the argv short, stay correct
                best = 0.0
                for i in range(0, len(rels), MAX_PATHSPECS):
                    best = max(best, self._log_time(rels[i:i + MAX_PATHSPECS]))
                return best
            return self._log_time(rels)
        # whole repo: the newest uncommitted change, at its own mtime
        newest = max((self._changed_time(d) for d in dirty), default=0.0)
        if newest:
            return newest
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
        elif self.use_dirty and any(rel == d or fnmatch.fnmatch(rel, d)
                                    for d in self._dirty_paths(filtered=False)):
            ts = self._changed_time(rel)
        else:
            ts = self._log_time([rel])
            if ts == 0.0:                     # untracked: only mtime is available
                ts = self._mtime_of(rel)
        self._file_cache[rel] = ts
        return ts


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
    # surrogateescape: git emits raw bytes for non-UTF-8 names on POSIX, and
    # Python's os layer decodes paths the same way - only then do they compare.
    return proc.stdout.decode("utf-8", "surrogateescape")
