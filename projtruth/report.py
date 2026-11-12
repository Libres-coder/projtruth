"""projtruth report: computed verification status per requirement.

Status is computed, never asserted: evidence exists -> is it newer than the code?
Five states, and only two of them mean "done":

    verified    evidence exists and the code has not changed since
    stale       evidence exists but the code changed after it
    unverified  a declared status that evidence cannot back
    pending     declared, no evidence yet (expected before work starts)
    implemented declared done, no evidence (a claim, shown as such)
"""
import time

STATUS_NOTE = {
    "verified": "fresh evidence",
    "stale": "re-verify",
    "unverified": "no evidence behind claim",
    "pending": "not started",
    "implemented": "claimed, unproven",
}


def _req_evidence(req, index):
    """Evidence for a requirement: its own criterion ids (R1.1) plus the
    requirement id itself (R1) - files are commonly named r1-<slug>.md, and a
    requirement without criteria still owns whatever is named after it."""
    rid = req.get("id", "").upper()
    seen = {}
    keys = [c.get("id", "").upper() for c in req.get("criteria", [])] + [rid]
    for key in keys:
        for e in index.get(key, []):
            seen[e["file"]] = e
    return sorted(seen.values(), key=lambda e: e["mtime"])


def _times(req, evidences, clock):
    """(newest_evidence_time, newest_evidence, newest_source_time)."""
    if hasattr(clock, "file_time"):          # freshness.Clock
        stamped = [(clock.file_time(e["file"]), e) for e in evidences]
        src = clock.for_requirement(req)
    else:                                     # float: global source time, raw mtimes
        stamped = [(e["mtime"], e) for e in evidences]
        src = float(clock or 0.0)
    if not stamped:
        return 0.0, {}, src
    ts, ev = max(stamped, key=lambda t: (t[0], t[1]["file"]))
    return ts, ev, src


def compute_status(req, index, clock):
    """Return (status, detail) where status is one of store.VALID_STATUS."""
    evidences = _req_evidence(req, index)
    if not evidences:
        declared = req.get("status", "pending")
        return (declared if declared in ("pending", "implemented") else "unverified",
                "no evidence")
    newest_ev, ev, src = _times(req, evidences, clock)
    if src > newest_ev + 1:
        return ("stale", "code changed %s, after evidence %s (%s)"
                % (_ago(src), _stamp(newest_ev), ev.get("file", "?")))
    scope = "%d file pattern(s)" % len(req["files"]) if req.get("files") else "whole repo"
    return ("verified", "evidence newer than %s" % scope)


def _stamp(mtime):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)) if mtime else "-"


def _ago(then):
    delta = time.time() - then
    if delta < 0:
        return "just now"
    if delta < 3600:
        return "%dm ago" % int(delta // 60)
    if delta < 86400:
        return "%dh ago" % int(delta // 3600)
    return "%dd ago" % int(delta // 86400)


def render(requirements, index, clock):
    lines = ["# projtruth status report (%s)" % time.strftime("%Y-%m-%d %H:%M"), ""]
    if not requirements:
        lines.append("No requirements registered yet. "
                     "Run `projtruth import-spec spec.md` or add one with req_add.")
        return "\n".join(lines)
    lines.append("| requirement | status | criteria | evidence | tier | scope "
                 "| freshest evidence |")
    lines.append("|---|---|---|---|---|---|---|")
    for req in requirements:
        status, _ = compute_status(req, index, clock)
        evs = _req_evidence(req, index)
        freshest, ev, _ = _times(req, evs, clock) if evs else (0.0, {}, 0.0)
        scope = "%d pattern(s)" % len(req["files"]) if req.get("files") else "repo"
        lines.append("| %s %s | **%s** | %d | %d | %s | %s | %s |"
                     % (req.get("id", "?"), req.get("title", ""), status,
                        len(req.get("criteria", [])), len(evs),
                        ev.get("tier", "-"), scope,
                        _stamp(freshest) if evs else "-"))
    lines.append("")
    attention = []
    for r in requirements:
        st, detail = compute_status(r, index, clock)
        if st != "verified":
            attention.append("- %s (%s, %s): %s"
                             % (r.get("id"), st, STATUS_NOTE.get(st, ""), detail))
    if attention:
        lines.append("## Needs attention (%d of %d)" % (len(attention), len(requirements)))
        lines.extend(attention)
    else:
        lines.append("All %d requirement(s) verified with fresh evidence."
                     % len(requirements))
    return "\n".join(lines)


def as_json(requirements, index, clock):
    out = []
    for req in requirements:
        status, detail = compute_status(req, index, clock)
        out.append({"id": req.get("id"), "title": req.get("title"),
                    "status": status, "detail": detail,
                    "files": req.get("files", []),
                    "criteria": [{"id": c.get("id"), "text": c.get("text")}
                                 for c in req.get("criteria", [])]})
    return out
