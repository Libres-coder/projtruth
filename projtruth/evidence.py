"""projtruth evidence index: find evidence files and link them to criteria.

Two roots are scanned, so the tool is not tied to one agent:

* `.claude/skills/verify-*/evidence/**` - files written by the verify-first
  pipeline (any agent can write there);
* `.projtruth/evidence/**`             - the agent-neutral drop box: point any
  tool, CI step or human at it.

A file is linked by its basename prefix: `R3.1-*.md` feeds criterion R3.1,
`R3-*.md` feeds every criterion of R3. The tier word (measured/inferred/guessed)
is read from the body when present.
"""
import glob
import json
import os
import re
import subprocess

TIER_RE = re.compile(r"measured|inferred|guessed", re.IGNORECASE)
# A tier on its own line is the convention; anywhere else can be a word
# in a test name or a quoted sentence.
TIER_LINE_RE = re.compile(r"^[ 	]*(measured|inferred|guessed)[ 	]*\.?[ 	]*$",
                          re.IGNORECASE | re.MULTILINE)
CRIT_RE = re.compile(r"^(R\d+(?:\.\d+)?)", re.IGNORECASE)
# An explicit link beats the filename: any tool can drop a file and say what it
# proves, without renaming it to our convention.
DIRECTIVE_RE = re.compile(
    r"^[ \t]*(?:<!--[ \t]*)?projtruth[ \t]*:[ \t]*(?P<body>[^\r\n]*?)[ \t]*(?:-->)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE)
ID_RE = re.compile(r"R\d+(?:\.\d+)?", re.IGNORECASE)
INDEX_NAME = "evidence-index.json"

EVIDENCE_ROOTS = (
    os.path.join(".claude", "skills", "verify-*", "evidence"),
    os.path.join(".projtruth", "evidence"),
)


def roots(repo):
    return [os.path.join(repo, r) for r in EVIDENCE_ROOTS]


def declared_ids(body):
    """Ids from an explicit `projtruth: R1.2, R4` line (an HTML comment is fine).

    Explicit beats the filename, so evidence may live under any name - a CI log,
    a doctor note, a screenshot transcript - and still feed exactly the
    requirements it proves.
    """
    m = DIRECTIVE_RE.search(body)
    if not m:
        return []
    ids = []
    for raw in ID_RE.findall(m.group("body")):
        rid = raw.upper()
        if rid not in ids:
            ids.append(rid)
    return ids


def _is_evidence_rel(rel):
    p = rel.replace("\\", "/")
    return p.startswith(".projtruth/evidence/") or (
        p.startswith(".claude/skills/verify-") and "/evidence/" in p)


def _entry(rel, body, mtime):
    tier_m = TIER_LINE_RE.search(body) or TIER_RE.search(body)
    return {"file": rel,
            "tier": (tier_m.group(0).strip().lower() if tier_m else "none"),
            "mtime": mtime}


def _keys_for(rel, body):
    keys = declared_ids(body)
    if not keys:
        m = CRIT_RE.match(os.path.basename(rel))
        if not m:
            return []
        keys = [m.group(1).upper()]
    return keys


def scan_head(repo):
    """Evidence as of HEAD, not the working tree.

    The commit guard judges what HEAD proves: a staged `git rm` of the evidence
    must not make the requirement look like it never had any.
    """
    try:
        p = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only",
                            "-z", "HEAD"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return {}
    if p.returncode != 0:
        return {}
    names = [n for n in p.stdout.decode("utf-8", "surrogateescape").split("\0") if n]
    index = {}
    for rel in names:
        rel = rel.replace("\\", "/")
        if not _is_evidence_rel(rel):
            continue
        try:
            show = subprocess.run(["git", "-C", repo, "show", "HEAD:" + rel],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        if show.returncode != 0:
            continue
        body = show.stdout.decode("utf-8-sig", "replace")
        entry = _entry(rel, body, 0.0)
        for key in _keys_for(rel, body):
            index.setdefault(key, []).append(dict(entry))
    for crit in index:
        index[crit].sort(key=lambda e: e["file"])
    return index


def scan(repo):
    """Return index: {criterion_id: [{file, tier, mtime}]} (sorted oldest->newest)."""
    index = {}
    files = []
    for root in roots(repo):
        files.extend(glob.glob(os.path.join(root, "**", "*"), recursive=True))
    for f in sorted(set(files)):
        if not os.path.isfile(f):
            continue
        try:
            with open(f, "r", encoding="utf-8-sig", errors="replace") as fh:
                body = fh.read()
            mtime = os.path.getmtime(f)
        except OSError:
            continue          # deleted between the glob and the read
        rel = os.path.relpath(f, repo).replace("\\", "/")
        entry = _entry(rel, body, mtime)
        for key in _keys_for(rel, body):
            index.setdefault(key, []).append(dict(entry))
    for crit in index:
        index[crit].sort(key=lambda e: e["mtime"])
    return index


def save_index(repo, index):
    d = os.path.join(repo, ".projtruth")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, INDEX_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return path


def load_index(repo):
    try:
        with open(os.path.join(repo, ".projtruth", INDEX_NAME), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
