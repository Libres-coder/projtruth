"""projtruth MCP server (stdio, newline-delimited JSON-RPC 2.0, zero deps).

Register with Claude Code:
  claude mcp add projtruth -- python D:/path/to/projtruth/mcp_server.py
(or point at this file from any MCP client). Repo under analysis:
  env PROJTRUTH_REPO, else the process cwd.

Tools: req_list, req_add, req_set_status, req_scope, evidence_scan,
       status_report, decide, decisions_list.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # make the package importable

from projtruth import evidence, freshness, report, store  # noqa: E402

SERVER_INFO = {"name": "projtruth", "version": "1.1.0"}
PROTOCOL = "2025-03-26"

TOOLS = [
    {
        "name": "status_report",
        "description": ("Where the project actually stands: every requirement with its "
                        "computed status (verified/stale/unverified/pending) and the "
                        "evidence behind it. Call this first when asked what is done, "
                        "what is left, or whether a feature is really finished. Pass "
                        "changed_since to narrow it to what a branch or PR touches."),
        "inputSchema": {"type": "object",
                        "properties": {
                            "changed_since": {
                                "type": "string",
                                "description": "git ref (e.g. origin/main); report only requirements touched by changes since it"}}},
    },
    {
        "name": "req_list",
        "description": "List registered requirements, their criteria count, declared status and file scope.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "req_add",
        "description": ("Register a requirement with acceptance criteria. Use when the user "
                        "states a feature or a promise the project should keep. Criteria are "
                        "auto-numbered R<n>.<i>; they are what evidence files link to."),
        "inputSchema": {"type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "e.g. R9"},
                            "title": {"type": "string"},
                            "criteria": {"type": "array", "items": {"type": "string"},
                                         "description": "testable statements, one per criterion"},
                            "files": {"type": "array", "items": {"type": "string"},
                                      "description": "globs whose change makes this stale, e.g. ['server.py','web/**/*.js']"}},
                        "required": ["id", "title"]},
    },
    {
        "name": "req_set_status",
        "description": ("Declare a requirement's status: pending or implemented. verified, stale "
                        "and unverified are computed from evidence and are rejected here - "
                        "write an evidence file instead."),
        "inputSchema": {"type": "object",
                        "properties": {"id": {"type": "string"},
                                       "status": {"type": "string"}},
                        "required": ["id", "status"]},
    },
    {
        "name": "req_scope",
        "description": ("Restrict a requirement's staleness to specific file globs. Without "
                        "scope, any source change in the repo marks it stale; with scope, only "
                        "changes to matching files do."),
        "inputSchema": {"type": "object",
                        "properties": {"id": {"type": "string"},
                                       "files": {"type": "array", "items": {"type": "string"}}},
                        "required": ["id", "files"]},
    },
    {
        "name": "evidence_scan",
        "description": ("Re-read the evidence folders and index them by criterion id. "
                        "Sources: .claude/skills/verify-*/evidence/** and .projtruth/evidence/**."),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "decide",
        "description": ("Append a decision with its reason to the project's decision log. "
                        "Use when a non-obvious choice is made (library, data model, trade-off) "
                        "so a later session does not re-litigate it."),
        "inputSchema": {"type": "object",
                        "properties": {"decision": {"type": "string"},
                                       "why": {"type": "string"}},
                        "required": ["decision"]},
    },
    {
        "name": "decisions_list",
        "description": "Read the project decision log (newest last) before re-opening a settled question.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def repo_dir():
    return os.path.abspath(os.environ.get("PROJTRUTH_REPO", os.getcwd()))


def call_tool(name, args):
    repo = repo_dir()
    if name == "status_report":
        idx = evidence.scan(repo)
        evidence.save_index(repo, idx)
        clock = freshness.Clock(repo)
        reqs = store.list_requirements(repo)
        since = args.get("changed_since")
        if not since:
            return report.render(reqs, idx, clock)
        changed = freshness.changed_files(repo, since)
        if changed is None:
            raise ValueError("cannot read git changes since %r - not a git work tree "
                             "or unknown ref" % since)
        pairs = report.changed_subset(reqs, idx, clock, changed)
        matched = dict((r["id"], hits) for r, hits in pairs)
        note = "changes since %s: %d file(s), %d requirement(s) in scope" % (
            since, len(changed), len(pairs))
        return report.render([r for r, _ in pairs], idx, clock, note=note, matched=matched)
    if name == "req_list":
        reqs = store.list_requirements(repo)
        if not reqs:
            return "(no requirements registered)"
        idx = evidence.scan(repo)
        clock = freshness.Clock(repo)
        rows = []
        for r in reqs:
            st, detail = report.compute_status(r, idx, clock)
            scope = (" -> %s" % ", ".join(r["files"])) if r.get("files") else ""
            rows.append("%s  %s  [%d criteria]  status=%s (%s)%s"
                        % (r["id"], r.get("title", ""), len(r.get("criteria", [])),
                           st, detail, scope))
        return "\n".join(rows)
    if name == "req_add":
        ok, msg = store.add_requirement(repo, args.get("id", ""), args.get("title", ""),
                                        args.get("criteria", []), args.get("files", []))
        if not ok:
            raise ValueError(msg)
        return msg
    if name == "req_set_status":
        ok, msg = store.set_status(repo, args.get("id", ""), args.get("status", ""))
        if not ok:
            raise ValueError(msg)
        return msg
    if name == "req_scope":
        ok, msg = store.set_files(repo, args.get("id", ""), args.get("files", []))
        if not ok:
            raise ValueError(msg)
        return msg
    if name == "evidence_scan":
        idx = evidence.scan(repo)
        evidence.save_index(repo, idx)
        total = sum(len(v) for v in idx.values())
        if not idx:
            return ("no evidence found - write files named R<n>[-slug].md under "
                    ".claude/skills/verify-<app>/evidence/ or .projtruth/evidence/")
        rows = ["%s: %d file(s), newest tier=%s"
                % (crit, len(evs), evs[-1]["tier"]) for crit, evs in sorted(idx.items())]
        return ("indexed %d criteria, %d evidence file(s)\n" % (len(idx), total)
                + "\n".join(rows))
    if name == "decide":
        row = store.append_decision(repo, args.get("decision", ""), args.get("why", ""))
        return "logged decision at %s" % row["ts"]
    if name == "decisions_list":
        rows = store.list_decisions(repo)
        return "\n".join("%s  %s%s" % (d.get("ts", ""), d.get("decision", ""),
                                       ("  (why: %s)" % d["why"]) if d.get("why") else "")
                         for d in rows) or "(no decisions)"
    raise ValueError("unknown tool: %s" % name)


def handle(msg):
    """Return a response dict for a request message, or None for notifications."""
    if not isinstance(msg, dict):
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": "invalid request: expected an object"}}
    method = msg.get("method", "")
    mid = msg.get("id")
    if mid is None:
        return None  # notification
    if not isinstance(method, str):
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32600, "message": "invalid request: method must be a string"}}
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"protocolVersion": PROTOCOL,
                           "capabilities": {"tools": {}},
                           "serverInfo": SERVER_INFO}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params")
        if not isinstance(params, dict):
            params = {}
        name = params.get("name")
        args = params.get("arguments")
        if not isinstance(args, dict):
            args = {}
        try:
            text = call_tool(name, args)
            return {"jsonrpc": "2.0", "id": mid,
                    "result": {"content": [{"type": "text", "text": text}], "isError": False}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": mid,
                    "result": {"content": [{"type": "text", "text": "error: %s" % e}],
                               "isError": True}}
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": "method not found: %s" % method}}


def main():
    # MCP stdio is UTF-8; Windows defaults to the OEM code page (cp936 etc.).
    for stream in (sys.stdin, sys.stdout):
        rec = getattr(stream, "reconfigure", None)
        if rec is not None:
            try:
                rec(encoding="utf-8")
            except Exception:
                pass
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": "parse error"}}
        else:
            try:
                resp = handle(msg)
            except Exception as e:          # one bad message must not kill the server
                rid = msg.get("id") if isinstance(msg, dict) else None
                resp = {"jsonrpc": "2.0", "id": rid,
                        "error": {"code": -32603, "message": "internal error: %s" % e}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
