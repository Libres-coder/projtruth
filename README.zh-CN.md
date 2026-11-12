# projtruth

**需求进屋，证据出门，没有证据不算完成。**

`projtruth` 是一个很小的 MCP 服务器（外加同一套核心的 CLI），把项目的承诺——需求、验收标准、每条需求背后的证据、以及做过的决定——放在一处，并**计算**哪些承诺现在还成立。

它只回答三个问题，对人类和对 agent 都一样：

- 哪些需求已验证、哪些已过期、哪些根本没有证据？
- R3 背后到底是什么证据，什么时候写的？
- 为什么这么设计？（只追加的决策台账）

```
$ projtruth report

| requirement | status | criteria | evidence | tier | scope | freshest evidence |
|---|---|---|---|---|---|---|
| R1 待办创建(API)      | **verified** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 |
| R2 待办列表(API)      | **verified** | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 |
| R3 待办完成切换(API)  | **stale**    | 1 | 1 | measured | 1 pattern(s) | 2026-11-13 05:50 |
| R4 前端界面           | **verified** | 1 | 1 | measured | 2 pattern(s) | 2026-11-13 06:54 |
```

状态是**算出来的，不是声明的**。只有证据存在、且它覆盖的代码在那之后没变，需求才是 `verified`；没有证据却声明 `verified`，报告里显示 `unverified`。

## 安装

零依赖，Python 3.8+。

```bash
pip install git+https://github.com/Libres-coder/projtruth
```

（尚未发布到 PyPI，请从仓库安装；或者克隆后直接在仓库里跑 `python -m projtruth`。）

作为 MCP 服务器（Claude Code、Cursor 或任何 MCP 客户端）：

```bash
claude mcp add projtruth -- python -m projtruth.mcp_server
# 或让客户端直接指向 python /路径/projtruth/projtruth/mcp_server.py
```

服务器按 `PROJTRUTH_REPO` 找仓库，没有则用进程 cwd——在项目根目录启动，或在 MCP 配置里设好变量。

作为技能（给 Claude Code 补上使用流程）：

```bash
git clone https://github.com/Libres-coder/projtruth ~/.claude/skills/projtruth
```

## 接入

```bash
cd 你的项目
projtruth init                        # 生成 .projtruth/（请提交进 git）
projtruth import-spec spec.md         # 识别 "### R1 标题" 与 "- 验收: ..." / "- Accept: ..."
projtruth req-scope R1 server.py      # 可选但强烈建议，见下
projtruth report                      # 现在到底做完了什么
```

没有 spec 文件？直接登记：

```bash
projtruth req-add R5 "登录限流" "一分钟内第 6 次尝试返回 429" --files "app/auth/*.py"
```

## 证据

文件名以需求或标准 id 开头的文件即为证据：

```
.claude/skills/verify-<app>/evidence/<日期>/R3.1-post-todos.md   # verify-first 写这里
.projtruth/evidence/R3.1-post-todos.md                           # 中立投放箱，任何工具都能写
```

正文里应该放真实输出，以及 `measured` / `inferred` / `guessed` 三档之一。详见 [references/evidence-format.md](references/evidence-format.md)。

## 状态模型

| 状态 | 含义 |
|---|---|
| `verified` | 有证据，且证据比它覆盖的代码新 |
| `stale` | 有证据，但代码在那之后改过——需要重新验证 |
| `unverified` | 声称完成，但没有东西支撑 |
| `implemented` | 已声明完成，尚无证据 |
| `pending` | 还没开始 |

只有 `pending` 和 `implemented` 可以手动声明；`verified`、`stale`、`unverified` 都由证据算出来。

细节：[references/status-model.md](references/status-model.md)。

## 不被 mtime 骗的新鲜度

`git clone` 和 `git checkout` 会重写所有文件的时间戳，只看 mtime 的工具在全新 checkout 上会报"所有代码刚刚都改过"——和事实正好相反。当仓库是 git 工作区时，`projtruth` 用的是**最后一次改到该需求文件的提交时间**，并且把"这些文件有未提交修改"直接当作"刚刚改过"；非 git 仓库才退回 mtime。

`.projtruth/`、`.claude/`、`.git/`、`.idea/`、`graphify-out/`、`PROGRESS.md`、`README*`、`CHANGELOG*`、`CONTRIBUTING*`、`LICENSE*`、`*.lock` 都不算源码变更——否则光是 `projtruth init` 就能把整个项目刷成红色。有未提交修改的文件按**它自己的 mtime** 计算，而不是"现在"，所以改完代码立刻重跑一次证据，仍然是新证据。

## 作用域：精确胜过全仓库飘红

不设作用域时，任何源码改动都会把需求标成 stale。给每条需求写上它依赖的文件，报告就和你手工判断一致：

```bash
projtruth req-scope R1 server.py "web/api/**/*.js"
```

此后改 `server.py` 只会让 R1 变 stale，前端需求保持 verified。

## MCP 工具

| 工具 | 用途 |
|---|---|
| `status_report` | 真相表——被问"做完没有"时先调它 |
| `req_list` | 需求列表、标准数、声明状态、作用域 |
| `req_add` | 登记需求、验收标准与文件作用域 |
| `req_set_status` | 声明 `pending` / `implemented`（`verified` 会被拒绝） |
| `req_scope` | 用文件通配符限定 staleness 范围 |
| `evidence_scan` | 按标准 id 重建证据索引 |
| `decide` / `decisions_list` | 只追加的决策台账 |

stdio JSON-RPC 2.0，按行分隔，无依赖，Windows 下强制 UTF-8。

## CI 门禁

```bash
projtruth report --strict      # 只要还有未验证需求就 exit 1
```

GitHub Actions 示例见 [references/ci-gate.md](references/ci-gate.md)（记得 `fetch-depth: 0`，也请读一下门禁**不能**证明什么）。

## 设计取向

- **状态就一个文件，用来提交。** `.projtruth/requirements.json`（承诺）与 `.projtruth/decisions.jsonl`（理由）。没有数据库，没有常驻进程。
- **计算优先于声明。** 写一个词不能让需求变成已验证。
- **接口小。** 八个 MCP 工具，每一个都能从文件回答。
- **面向任何 agent。** 能写文件的就能留证据；会说 MCP 的就能读到真相。

## 相关项目

- [verify-first](https://github.com/Libres-coder/verify-first) —— 产出这里所读证据的流水线。
- [skill-audit](https://github.com/Libres-coder/skill-audit) —— 审计 Claude Code 里堆积的技能。

## 局限

- `import-spec` 是按标题与列表前缀的启发式解析，请核对导入结果。
- 证据按文件名前缀关联；`R3-x.md` 会喂给 R3 的每一个标准。
- 作用域通配符如果什么都没匹配到，等于"永不 stale"——写错一个字符不会报错。
- 在 git 子模块里改动，父仓库的历史看不到。
- 没有作用域的需求，任何源码改动都会 stale（这是设计）。
- 只追踪已登记的需求；没写下来的工作它看不见。
- 它不执行任何东西，只报告被记录了什么、以及何时记录的。

## 许可证

MIT
