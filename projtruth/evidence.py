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

TIER_RE = re.compile(r"measured|inferred|guessed", re.IGNORECASE)
CRIT_RE = re.compile(r"^(R\d+(?:\.\d+)?)", re.IGNORECASE)
INDEX_NAME = "evidence-index.json"

EVIDENCE_ROOTS = (
    os.path.join(".claude", "skills", "verify-*", "evidence"),
    os.path.join(".projtruth", "evidence"),
)


def roots(repo):
    return [os.path.join(repo, r) for r in EVIDENCE_ROOTS]


def scan(repo):
    """Return index: {criterion_id: [{file, tier, mtime}]} (sorted oldest->newest)."""
    index = {}
    files = []
    for root in roots(repo):
        files.extend(glob.glob(os.path.join(root, "**", "*"), recursive=True))
    for f in sorted(set(files)):
        if not os.path.isfile(f):
            continue
        m = CRIT_RE.match(os.path.basename(f))
        if not m:
            continue
        crit = m.group(1).upper()
        try:
            with open(f, "r", encoding="utf-8-sig", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        tier_m = TIER_RE.search(body)
        index.setdefault(crit, []).append({
            "file": os.path.relpath(f, repo).replace("\\", "/"),
            "tier": (tier_m.group(0).lower() if tier_m else "none"),
            "mtime": os.path.getmtime(f),
        })
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
