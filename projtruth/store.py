"""projtruth store: requirements registry + decision log under <repo>/.projtruth/.

Two files, both plain text, both meant to be committed:

    .projtruth/requirements.json   what the project promises, and to which files
    .projtruth/decisions.jsonl     why it is the way it is (append-only)

Nothing here is derived. Deleting .projtruth loses the promises, not the code.
"""
import json
import os
import re
import tempfile
import time

STATE_DIR = ".projtruth"
SCHEMA_VERSION = 1

VALID_STATUS = ("pending", "implemented", "verified", "stale", "unverified")
# verified/stale are computed from evidence; only these three can be declared.
DECLARABLE_STATUS = ("pending", "implemented")
REQ_ID_RE = re.compile(r"^R\d+$")


def state_dir(repo):
    return os.path.join(repo, STATE_DIR)


def _req_path(repo):
    return os.path.join(state_dir(repo), "requirements.json")


def _dec_path(repo):
    return os.path.join(state_dir(repo), "decisions.jsonl")


def init(repo):
    d = state_dir(repo)
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(_req_path(repo)):
        with open(_req_path(repo), "w", encoding="utf-8") as f:
            json.dump({"schema_version": SCHEMA_VERSION, "requirements": []},
                      f, ensure_ascii=False, indent=2)
    return d


def load(repo):
    """Read the registry. A damaged file is moved aside, never silently lost."""
    try:
        with open(_req_path(repo), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"schema_version": SCHEMA_VERSION, "requirements": []}
    except (ValueError, UnicodeDecodeError, OSError):
        _quarantine(repo)
        return {"schema_version": SCHEMA_VERSION, "requirements": []}
    if not isinstance(data, dict) or not isinstance(data.get("requirements", []), list):
        _quarantine(repo)
        return {"schema_version": SCHEMA_VERSION, "requirements": []}
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("requirements", [])
    return data


def _quarantine(repo):
    """Keep a damaged registry for inspection instead of overwriting it."""
    path = _req_path(repo)
    if not os.path.exists(path):
        return
    try:
        os.replace(path, path + ".corrupt-%s" % time.strftime("%Y%m%d-%H%M%S"))
    except OSError:
        pass


def _as_list(value):
    """A single string is one item, not a sequence of characters."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _unsafe_files(files):
    bad = []
    for f in files or []:
        p = str(f).replace("\\", "/")
        if os.path.isabs(p) or p.startswith("/") or ".." in p.split("/"):
            bad.append(f)
    return bad


def save(repo, data):
    """Write atomically: a unique temp file in the same directory, then rename."""
    os.makedirs(state_dir(repo), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".requirements-", suffix=".tmp",
                               dir=state_dir(repo))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _req_path(repo))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _norm_id(req_id):
    return str(req_id or "").strip().upper()


def add_requirement(repo, req_id, title, criteria=None, files=None):
    """Register a requirement.

    criteria: list of {id?, text, judge?} or plain strings (auto-numbered R<n>.<i>).
    files:    repo-relative globs whose changes make this requirement stale, e.g.
              ["server.py", "web/**/*.js"]. Empty means "any source change".
    """
    req_id = _norm_id(req_id)
    if not REQ_ID_RE.match(req_id):
        return False, "invalid requirement id %r (expected R1, R2, ...)" % req_id
    files = _as_list(files)
    criteria = _as_list(criteria)
    bad = _unsafe_files(files)
    if bad:
        return False, "file patterns must stay inside the repo: %s" % ", ".join(map(str, bad))
    data = load(repo)
    for r in data["requirements"]:
        if r.get("id") == req_id:
            return False, "requirement %s already exists" % req_id
    crit = []
    for i, c in enumerate(criteria or [], 1):
        if isinstance(c, str):
            crit.append({"id": "%s.%d" % (req_id, i), "text": c, "judge": "command"})
        else:
            c = dict(c)
            c.setdefault("id", "%s.%d" % (req_id, i))
            c.setdefault("judge", "command")
            crit.append(c)
    data["requirements"].append({"id": req_id, "title": title, "status": "pending",
                                 "files": [str(f) for f in (files or [])],
                                 "criteria": crit})
    save(repo, data)
    return True, "added %s" % req_id


def set_status(repo, req_id, status):
    if status in VALID_STATUS and status not in DECLARABLE_STATUS:
        return False, ("%s is computed from evidence, not declared - write an "
                       "evidence file for this requirement instead" % status)
    if status not in VALID_STATUS:
        return False, "invalid status: %s (valid: %s)" % (status, ", ".join(DECLARABLE_STATUS))
    req_id = _norm_id(req_id)
    data = load(repo)
    for r in data["requirements"]:
        if r.get("id") == req_id:
            r["status"] = status
            save(repo, data)
            return True, "%s -> %s" % (req_id, status)
    return False, "no such requirement: %s" % req_id


def set_files(repo, req_id, files):
    files = _as_list(files)
    bad = _unsafe_files(files)
    if bad:
        return False, "file patterns must stay inside the repo: %s" % ", ".join(map(str, bad))
    req_id = _norm_id(req_id)
    data = load(repo)
    for r in data["requirements"]:
        if r.get("id") == req_id:
            r["files"] = [str(f) for f in files]
            save(repo, data)
            return True, "%s now scoped to %d pattern(s)" % (req_id, len(files))
    return False, "no such requirement: %s" % req_id


def list_requirements(repo):
    return load(repo)["requirements"]


def append_decision(repo, decision, why=""):
    os.makedirs(state_dir(repo), exist_ok=True)
    row = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
           "decision": decision, "why": why}
    with open(_dec_path(repo), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def list_decisions(repo):
    try:
        with open(_dec_path(repo), encoding="utf-8") as f:
            out = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue          # one corrupt line must not hide the rest
            return out
    except OSError:
        return []
