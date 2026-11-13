"""projtruth CLI - the same core the MCP server exposes, for terminals and CI.

  projtruth init                       create .projtruth/
  projtruth import-spec spec.md        import R<n> headings + 验收/Accept bullets
  projtruth req-list
  projtruth req-add R9 "title" "criterion" --files "src/api/*.py"
  projtruth req-set R9 implemented|pending
  projtruth req-scope R9 "server.py" "web/**"
  projtruth scan                       refresh the evidence index
  projtruth report [--json] [--strict]
  projtruth decide "text" --why "reason"
  projtruth decisions

Exit codes: 0 ok, 1 gate/command failure, 2 usage.
`report --strict` exits 1 when any requirement is not verified, and when the
registry is empty - usable as a CI gate or a pre-release check.
"""
import argparse
import json
import os
import re
import sys

from . import evidence, freshness, report, store

HEADING_RE = re.compile(r"^#{2,4}\s*(R\d+)[.:)\s]\s*(.+)$", re.IGNORECASE)
CRIT_RE = re.compile(r"^\s*[-*]\s*(?:验收|Accept)[:：]?\s*(.+)$", re.IGNORECASE)


def import_spec(repo, path):
    """Heuristic spec.md import: headings 'R<n> title' + bullets starting with 验收/Accept."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        return False, "cannot read %s: %s" % (path, e)
    added = 0
    for line in lines:
        m = HEADING_RE.match(line.strip())
        if m:
            ok, _ = store.add_requirement(repo, m.group(1).upper(), m.group(2).strip())
            if ok:
                added += 1
    data = store.load(repo)
    by_id = {r["id"]: r for r in data["requirements"]}
    cur = None
    crit_added = 0
    for line in lines:
        m = HEADING_RE.match(line.strip())
        if m:
            cur = m.group(1).upper()
            continue
        cm = CRIT_RE.match(line)
        if cm and cur and cur in by_id:
            crit = by_id[cur].setdefault("criteria", [])
            text = cm.group(1).strip()
            if any(c.get("text") == text for c in crit):
                continue          # re-running import-spec must not duplicate criteria
            crit.append({"id": "%s.%d" % (cur, len(crit) + 1),
                         "text": text, "judge": "command"})
            crit_added += 1
    store.save(repo, data)
    return True, "imported %d new requirement(s), %d new criterion/criteria from %s" % (
        added, crit_added, os.path.basename(path))


def _utf8_stdout():
    rec = getattr(sys.stdout, "reconfigure", None)
    if rec:
        try:
            rec(encoding="utf-8")
        except Exception:
            pass


def main(argv=None):
    try:
        return _main(argv)
    except store.RegistryUnreadable as exc:
        sys.stderr.write("projtruth: %s\n" % exc)
        return 2


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="projtruth")
    ap.add_argument("--repo", default=os.getcwd(),
                    help="repository to read/write (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    p = sub.add_parser("import-spec"); p.add_argument("path")
    sub.add_parser("req-list")
    p = sub.add_parser("req-add")
    p.add_argument("id"); p.add_argument("title")
    p.add_argument("criteria", nargs="*")
    p.add_argument("--files", nargs="*", default=[],
                   help="globs whose change makes this requirement stale")
    p = sub.add_parser("req-set"); p.add_argument("id"); p.add_argument("status")
    p = sub.add_parser("req-scope"); p.add_argument("id"); p.add_argument("files", nargs="*")
    sub.add_parser("scan")
    p = sub.add_parser("report")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true",
                   help="exit 1 unless every requirement is verified (empty registry fails too)")
    p.add_argument("--changed", nargs="?", const="HEAD", default=None, metavar="REF",
                   help="only requirements touched by changes since REF (default HEAD)")
    p = sub.add_parser("decide"); p.add_argument("decision"); p.add_argument("--why", default="")
    sub.add_parser("decisions")
    p = sub.add_parser("guard")
    p.add_argument("--allow", action="store_true",
                   help="report but never block (same as PROJTRUTH_ALLOW_STALE=1)")
    p = sub.add_parser("hook")
    p.add_argument("action", choices=["install", "uninstall", "status"])
    p.add_argument("--force", action="store_true",
                   help="overwrite or remove a pre-commit hook that is not ours")

    args = ap.parse_args(argv)
    repo = os.path.abspath(args.repo)

    if args.cmd == "init":
        store.init(repo)
        print("initialized %s" % store.state_dir(repo))
        return 0
    if args.cmd == "import-spec":
        ok, msg = import_spec(repo, args.path)
        print(msg)
        return 0 if ok else 1
    if args.cmd == "req-list":
        reqs = store.list_requirements(repo)
        for r in reqs:
            scope = " -> %s" % ", ".join(r["files"]) if r.get("files") else ""
            print("%s  %s  [%d criteria]  status=%s%s"
                  % (r["id"], r.get("title", ""), len(r.get("criteria", [])),
                     r.get("status"), scope))
        if not reqs:
            print("(no requirements)")
        return 0
    if args.cmd == "req-add":
        ok, msg = store.add_requirement(repo, args.id.upper(), args.title,
                                        args.criteria, args.files)
        print(msg)
        return 0 if ok else 1
    if args.cmd == "req-set":
        ok, msg = store.set_status(repo, args.id.upper(), args.status)
        print(msg)
        return 0 if ok else 1
    if args.cmd == "req-scope":
        ok, msg = store.set_files(repo, args.id.upper(), args.files)
        print(msg)
        return 0 if ok else 1
    if args.cmd == "scan":
        idx = evidence.scan(repo)
        path = evidence.save_index(repo, idx)
        total = sum(len(v) for v in idx.values())
        print("indexed %d criteria, %d evidence file(s) -> %s"
              % (len(idx), total, os.path.relpath(path, repo)))
        return 0
    if args.cmd == "report":
        idx = evidence.scan(repo)
        evidence.save_index(repo, idx)
        clock = freshness.Clock(repo)
        all_reqs = reqs = store.list_requirements(repo)
        note, matched = "", None
        if args.changed:
            changed = freshness.changed_files(repo, args.changed)
            if changed is None:
                print("cannot read git changes since %r - is this a git work tree?"
                      % args.changed, file=sys.stderr)
                return 1
            pairs = report.changed_subset(reqs, idx, clock, changed)
            reqs = [r for r, _ in pairs]
            matched = dict((r["id"], hits) for r, hits in pairs)
            note = "changes since %s: %d file(s), %d requirement(s) in scope" % (
                args.changed, len(changed), len(reqs))
        if args.json:
            _utf8_stdout()
            print(json.dumps(report.as_json(reqs, idx, clock), ensure_ascii=False, indent=2))
        else:
            _utf8_stdout()
            print(report.render(reqs, idx, clock, note=note, matched=matched))
        if args.strict:
            if not all_reqs:
                print("strict: no requirements registered - nothing to gate on",
                      file=sys.stderr)
                return 1
            if args.changed and not reqs:
                print("strict: no requirement is touched by these changes",
                      file=sys.stderr)
                return 0
            bad = [r["id"] for r in reqs
                   if report.compute_status(r, idx, clock)[0] != "verified"]
            if bad:
                print("strict: not verified: %s" % ", ".join(bad), file=sys.stderr)
                return 1
        return 0
    if args.cmd == "guard":
        from . import guard
        allow = args.allow or str(os.environ.get("PROJTRUTH_ALLOW_STALE", "")) \
            .strip().lower() in ("1", "true", "yes", "on")
        return guard.main(repo, allow=allow)
    if args.cmd == "hook":
        from . import guard
        return guard.hook_command(repo, args.action, force=args.force)
    if args.cmd == "decide":
        row = store.append_decision(repo, args.decision, args.why)
        print("decided: %s" % row["decision"])
        return 0
    if args.cmd == "decisions":
        _utf8_stdout()
        rows = store.list_decisions(repo)
        for d in rows:
            print("%s  %s%s" % (d.get("ts", ""), d.get("decision", ""),
                                ("  (why: %s)" % d["why"]) if d.get("why") else ""))
        if not rows:
            print("(no decisions)")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
