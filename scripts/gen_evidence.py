"""Regenerate the evidence for requirements a code change touched.

Each entry names the evidence file, its title and the commands whose real
output proves the requirement now. Run it from anywhere; it writes into
.projtruth/evidence/ with fresh mtimes, which is what the commit guard reads.
"""
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, ".projtruth", "evidence")

PLAN = [
    ("R1-status-report.md",
     "R1 Status is computed from evidence and real code changes",
     [["python", "-m", "unittest", "tests.test_core.GitFreshnessTests", "-v"]]),
    ("R4-cli.md",
     "R4 CLI mirrors the core and gates CI",
     [["python", "-m", "unittest", "tests.test_core.ScopeReportTests", "-v"],
      ["python", "-m", "projtruth", "scopes"]]),
    ("R7-changed.md",
     "R7 report --changed scopes the report to touched requirements",
     [["python", "-m", "unittest",
       "tests.test_guard.GitRepoTest.test_changed_files_sees_commits_and_worktree",
       "tests.test_guard.GitRepoTest.test_changed_report_scopes_to_touched_requirements",
       "-v"]]),
    ("R8-guard.md",
     "R8 The commit guard refuses to invalidate verified evidence",
     [["python", "-m", "unittest", "tests.test_guard", "-v"]]),
]


def run(argv):
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    os.makedirs(EVIDENCE, exist_ok=True)
    failed = False
    for name, title, commands in PLAN:
        lines = ["# %s" % title, "",
                 "_Run at %s_" % datetime.datetime.now().strftime(
                     "%Y-%m-%d %H:%M:%S"), ""]
        ok = True
        for argv in commands:
            code, out = run(argv)
            lines += ["```", "$ %s   # exit %d" % (" ".join(argv), code),
                      out.rstrip(), "```", ""]
            ok = ok and code == 0
        lines.append("measured")
        with open(os.path.join(EVIDENCE, name), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        print("%s %s" % ("wrote" if ok else "WROTE (a command failed)", name))
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
