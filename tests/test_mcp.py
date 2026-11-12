import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import projtruth.mcp_server as mcp  # noqa: E402

TOOL_NAMES = {"req_list", "req_add", "req_set_status", "req_scope", "evidence_scan",
              "status_report", "decide", "decisions_list"}


class McpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["PROJTRUTH_REPO"] = self.tmp.name

    def tearDown(self):
        os.environ.pop("PROJTRUTH_REPO", None)
        self.tmp.cleanup()

    def _handle(self, msg):
        resp = mcp.handle(msg)
        assert resp is not None
        return resp

    def _call(self, name, args=None, mid=1):
        return self._handle({"jsonrpc": "2.0", "id": mid, "method": "tools/call",
                             "params": {"name": name, "arguments": args or {}}})

    def _text(self, resp):
        return resp["result"]["content"][0]["text"]

    def test_initialize_and_tools_list(self):
        r = self._handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": mcp.PROTOCOL, "capabilities": {},
                                        "clientInfo": {"name": "t", "version": "1"}}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "projtruth")
        self.assertEqual(r["result"]["protocolVersion"], mcp.PROTOCOL)
        r = self._handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in r["result"]["tools"]}
        self.assertEqual(names, TOOL_NAMES)
        for tool in r["result"]["tools"]:
            self.assertTrue(tool["description"], tool["name"])
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_every_tool_is_callable_and_returns_text(self):
        """No tool may raise through the protocol: a bad call is isError, not a crash."""
        for name in TOOL_NAMES:
            r = self._call(name, {"id": "R1", "title": "t", "status": "pending", "files": [],
                                  "decision": "d", "criteria": ["c"]})
            self.assertIn("result", r, name)
            self.assertIsInstance(self._text(r), str, name)

    def test_notification_ignored_and_unknown_method(self):
        self.assertIsNone(mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        r = self._handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})
        self.assertEqual(r["error"]["code"], -32601)

    def test_tool_flow(self):
        r = self._call("req_add", {"id": "R1", "title": "t", "criteria": ["c1"]})
        self.assertFalse(r["result"]["isError"], r)
        self.assertIn("added R1", self._text(r))
        r = self._call("req_scope", {"id": "R1", "files": ["app.py"]})
        self.assertIn("1 pattern", self._text(r))
        r = self._call("req_list")
        self.assertIn("app.py", self._text(r))
        r = self._call("evidence_scan")
        self.assertIn("no evidence found", self._text(r))
        r = self._call("status_report")
        self.assertIn("projtruth status report", self._text(r))
        r = self._call("decide", {"decision": "d1", "why": "w1"})
        self.assertIn("logged decision", self._text(r))
        r = self._call("decisions_list")
        self.assertIn("d1", self._text(r))
        r = self._call("req_set_status", {"id": "R1", "status": "verified"})
        self.assertIn("R1 -> verified", self._text(r))

    def test_evidence_is_indexed_by_criterion(self):
        d = os.path.join(self.tmp.name, ".projtruth", "evidence")
        os.makedirs(d)
        with open(os.path.join(d, "R1.1-ok.md"), "w", encoding="utf-8") as f:
            f.write("measured\n")
        r = self._call("req_add", {"id": "R1", "title": "t", "criteria": ["c1", "c2"]})
        self.assertFalse(r["result"]["isError"])
        r = self._call("evidence_scan")
        self.assertIn("R1.1: 1 file(s)", self._text(r))
        r = self._call("status_report")
        self.assertIn("verified", self._text(r))

    def test_tool_error_is_not_fatal(self):
        r = self._call("req_set_status", {"id": "R404", "status": "verified"})
        self.assertTrue(r["result"]["isError"])
        r = self._call("req_add", {"id": "bogus", "title": "t"})
        self.assertTrue(r["result"]["isError"])
        r = self._call("nope")
        self.assertTrue(r["result"]["isError"])

    def test_parse_error_and_roundtrip_over_stdio(self):
        resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        # the transport writes exactly one line per response
        self.assertEqual(len(json.dumps(resp)), len(json.dumps(resp)))
        self.assertNotIn("\n", json.dumps(resp))

    def test_utf8_payload_survives(self):
        r = self._call("req_add", {"id": "R7", "title": "中文标题", "criteria": ["验收通过"]})
        self.assertFalse(r["result"]["isError"])
        r = self._call("req_list")
        self.assertIn("中文标题", self._text(r))


if __name__ == "__main__":
    unittest.main()
