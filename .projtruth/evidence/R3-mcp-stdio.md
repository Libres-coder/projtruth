# R3 the MCP server speaks stdio JSON-RPC

_Run at 2026-11-14 06:12:44_

```
$ python -m unittest tests.test_mcp -v   # exit 0
test_every_tool_is_callable_and_returns_text (tests.test_mcp.McpTests)
No tool may raise through the protocol: a bad call is isError, not a crash. ... ok
test_evidence_is_indexed_by_criterion (tests.test_mcp.McpTests) ... ok
test_initialize_and_tools_list (tests.test_mcp.McpTests) ... ok
test_notification_ignored_and_unknown_method (tests.test_mcp.McpTests) ... ok
test_stdio_survives_malformed_messages (tests.test_mcp.McpTests)
The real transport: one bad line must not take the server down. ... ok
test_tool_error_is_not_fatal (tests.test_mcp.McpTests) ... ok
test_tool_flow (tests.test_mcp.McpTests) ... ok
test_utf8_payload_survives (tests.test_mcp.McpTests) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.241s

OK
```

measured
