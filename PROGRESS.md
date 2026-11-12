# PROGRESS — projtruth(项目真相 MCP)

## 选题(2026-11-13 调研)
- 记忆类 MCP 红海: Citadel 929★ / projectmem 881★ / storybloq 787★ → 不正面竞争
- 规格/验收追踪近乎空白: spec-harness 0★ / universal-spec-mcp 1★ / agent-acceptance-trace 0★
- 差异化: 存"可判定的验收真相"(需求→标准→证据→新鲜度),而非笔记;跨 agent(MCP);与 verify-first 门禁联动
- 需求风险诚实记录: 该品类普遍低星,可能需求弱。v1 原则 = 零仪式接入(init 一条命令 / import-spec 吃现有 spec.md / scan 自动索引证据)

## 架构
```
projtruth/
  projtruth/
    store.py      # .projtruth/requirements.json + decisions.jsonl 读写
    evidence.py   # 扫描 verify-*/evidence/**,按标准 id 前缀链接,提取档位
    report.py     # status 报告(markdown) + 新鲜度(证据时间 vs 最近源码)
    cli.py        # init / import-spec / req / scan / report / decide / decisions
    mcp_server.py # 手写 JSON-RPC stdio MCP(initialize/tools_list/tools_call)
  tests/
```

## 数据模型
```json
// .projtruth/requirements.json
{"schema_version":1,"requirements":[
  {"id":"R1","title":"待办创建","status":"verified|implemented|pending|stale|unverified",
   "criteria":[{"id":"R1.1","text":"POST 后 GET 可见","judge":"command"}]}
]}
// .projtruth/decisions.jsonl  {"ts":"...","decision":"...","why":"..."}
// .projtruth/evidence-index.json(派生缓存)
```

## MCP 工具面(v1,小即是好)
- req_list / req_add / req_set_status
- evidence_scan(扫描并索引证据,返回每条标准的最新档位/时间)
- status_report(markdown 表:需求→状态→证据→新鲜度)
- decide / decisions_list

## 待办
- [x] core:store / evidence / report / cli + tests
- [x] mcp_server + tests
- [x] 狗粮:demo-todo + demo-todoctl 接入,真实报告
- [x] skill 封装 + 两轮独立审查(P0/P1 全部修复)
- [x] 自举:本项目 5 条需求 + .projtruth/evidence,`report --strict` 退出 0
- [x] 发布:https://github.com/Libres-coder/projtruth (2026-11-13)

## 决策台账
| 时间 | 决策 | 理由 |
|---|---|---|
| 11-13 | 形态=MCP(手写 stdio,零依赖) | 跨 agent 通用;与现有工具同一交付风格 |
| 11-13 | v1 不做代码图谱链接 | 先证核心价值(验收真相可查),v2 再上 graphify 联动 |
| 11-13 | 状态模型五态 | pending/implemented/verified/stale/unverified 覆盖真实生命周期 |
| 11-13 | 只有 pending/implemented 可声明 | verified/stale 是证据的结论,能被一句话改掉就不是结论 |
| 11-13 | 新鲜度以 git 提交时间为主 | clone/checkout 会重写 mtime,"刚克隆全过期"是必现假阳性 |
| 11-13 | 脏文件按自身 mtime 计时 | 用 `now` 会让"改完立刻重跑证据"永远 stale |
| 11-13 | 需求级 files 作用域 | 全仓库作用域在真实项目里等于永久飘红 |
