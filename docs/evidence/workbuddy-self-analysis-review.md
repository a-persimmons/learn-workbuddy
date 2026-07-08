# WorkBuddy 自分析材料审阅

审阅日期：2026-07-08

用户提供的两份材料：

| 文件 | 定位 |
|---|---|
| `[local self-analysis html]` | WorkBuddy 自己生成的 HTML 架构观察报告 |
| `[local draft note]` | 基于分析报告整理的中文传播稿/公众号稿 |

## 总体判断

这两份材料很有价值，但来源和版本要分开看：

- `workbuddy-analysis.html` 明确写明基于本机已安装的 WorkBuddy `5.1.7`。
- 当前教程主证据基于 Downloads 中的 WorkBuddy `本地样本` DMG。
- `110.md` 更像面向读者的二次表达，有不少推断和产品化概括，适合启发教程结构，但不应直接当作可观察证据。

因此合并策略应该是：

```text
本地样本 安装包 / ~/.workbuddy 运行时可复核 -> 可以写入主教程
5.1.7 HTML 报告可复核且 本地样本 也存在 -> 可以补强教程
只在 110.md 中出现、未复核 -> 标注为“推断/待验证”
```

## 可以直接采纳的高置信信息

这些内容已在 本地样本 包体或本机运行时中再次验证。

| 主题 | 材料观点 | 本地样本 / 运行时验证 |
|---|---|---|
| Sidecar ring buffer | 每个 session 有固定大小环形缓冲 | `main/protocol.js` 中 `DEFAULT_RING_BUFFER_BYTES = 8 * 1024 * 1024` |
| Sidecar idle timeout | 空闲一段时间后自动关闭 | `IDLE_TIMEOUT_MS = 1800 * 1000`，即 30 分钟 |
| Sidecar RPC | `session.create`、`session.reconnect`、`session.resize`、`session.kill`、`session.list`、`session.capture`、`sidecar.ping`、`sidecar.shutdown` | `main/sidecar-entry.js` 中可见 |
| 环境变量隔离 | CLI 子进程不能继承部分 Desktop/Node/Electron 变量 | `ENV_BLOCKED_PREFIXES = CODEBUDDY_ / ELECTRON_ / VITE_`，另有 `ENV_BLOCKED_KEYS` |
| 平台差异 | macOS/Linux 使用 PTY，Windows 使用管道模式 | `main/sidecar-entry.js` 注释与实现一致 |
| 沙盒组件 | FileProvider、NetworkExtension、SandboxHelper | `cli/sandbox-config.json` 和 `cli/vendor/sandbox/sandbox-cli` 字符串可见 |
| 审计日志哈希链 | command-safety 日志有 `sequence`、`prevHash`、`hash` | `~/.workbuddy/audit-log/2026-07-05.jsonl` 已验证 |
| SQLite 表 | sessions、workspaces、automations、automation_runs、automation_runtime_state、session_usage、migration_meta | `~/.workbuddy/workbuddy.db` schema 已验证 |
| Agent 名称 | `compact`、`contextSummary`、`memorySelector`、`promptHookEvaluator`、`Explore`、`general-purpose` 等 | `cli/dist/CLI bundle` 中 `AgentNames` 枚举可见 |
| memorySelector | 使用辅助 agent 选择相关记忆 | bundle 中 `MemoryRelevance:AI` 调用 `AgentNames.MEMORY_SELECTOR` |
| 记忆最多筛选 | `selected_memories` JSON 返回，并过滤在 manifest 文件名集合内 | bundle 中可见 `selected_memories` 解析逻辑 |
| 工具延迟加载 | `ToolSearch` 与 `DeferExecuteTool` 两步发现/执行 | bundle 中 `ToolSearch`、`DeferExecuteTool`、`deferLoading` 可见 |
| 压缩阈值 | `tokenUsageThresholds.inputTokens.preMessage/emergency/subAgentEmergency` | bundle 中 `tokenUsageThresholds` 调用链可见 |
| 身份文件 | `persona/core.md`、`persona/identity.md`、`persona/user.md`、`persona/bootstrap.md` | 本地样本 模板与 `~/.workbuddy` 运行时均有证据 |

## 适合补强教程的点

### 1. Sidecar 章节应该更具体

原教程已说明 sidecar 是桌面与 CLI 的边界。自分析材料补充了几个值得写进去的工程细节：

```text
control socket: JSON-RPC 控制面
data stream: PTY/pipe 输出面
ring buffer: 8MB，用于 reconnect/capture
idle timeout: 30min，无会话无控制连接后退出
env isolation: 屏蔽 CODEBUDDY_ / ELECTRON_ / VITE_ 等变量
```

这些对“从 0 复刻”很有帮助，因为它们回答了 sidecar 为什么不是简单 `spawn()`。

### 2. 安全章节可以新增审计哈希链

自分析材料提到的审计链已被运行时验证。可以在 `s09_sandbox_security` 加一节：

```text
AuditLog
  append(event)
  sequence = previous.sequence + 1
  prevHash = previous.hash
  hash = sha256(canonical_json(event_without_hash) + prevHash)
```

最小复刻版不需要真实 sandbox，但可以先做 command audit log。

### 3. 记忆章节可以加入 memorySelector 的实际调用形状

`110.md` 里的描述“用户查询 + 可用记忆文件 manifest -> 返回 selected_memories JSON -> 只注入选中的记忆”与 bundle 证据一致。

推荐教程表达为：

```text
Memory manifest:
  filename
  description
  type
  recently_used_tools

memorySelector output:
  {"selected_memories": ["a.md", "b.md"]}
```

这比“加载所有记忆”更贴近 WorkBuddy 的设计重点。

### 4. 多 Agent 章节可以新增“辅助 Agent 零工具化”

bundle 中可见 `compact`、`contextSummary`、`memorySelector`、`promptHookEvaluator` 都被归为 auxiliary trace。`110.md` 对它们“用 lite/default/craft 分层”的表述很适合教学，但模型槽位需要标成推断或来自产品配置，不能只凭传播稿断言。

可以写成：

```text
主 Agent：面向用户，持有写文件、bash、MCP 等工具。
辅助 Agent：只做分类/摘要/标题/Hook 评估，通常不需要文件系统工具。
asTool 子 Agent：作为工具被主 Agent 调用，只返回摘要结果。
团队/协作 Agent：通过 message/notification/plan 状态协作。
```

## 需要谨慎或待验证的点

这些内容在材料中出现，但当前没有完整 本地样本 本地证据，写入教程时应标注来源或降级为推断。

| 观点 | 风险 |
|---|---|
| “多类内置 Agent” | bundle 中有 AgentNames 枚举，但具体“16 种”需要完整产品配置枚举后再确认 |
| “主 Agent 多种工具” | 工具数量依赖模式、MCP、插件、产品配置和 deferred 状态，不能写死 |
| “云端画像 v40” | 运行时 memory 文件版本为 0，服务端具体版本无法从本地包完全确认 |
| `history_search` | 110.md 提到，但 本地样本 未直接命中该字符串，可能是服务端工具或另一个版本能力 |
| “30 天后蒸馏日志” | 传播稿中有产品化规则，但本地未找到明确实现证据 |
| “TaskList 而不是消息队列” | Task/Todo/plan 工具有证据，但“黑板架构”是合理解释，不是源码注释级证据 |
| “模型槽位 lite/default/craft 的具体分配” | Agent 名称和辅助分类有证据，具体模型分配需解析 product config 后确认 |

## 与现有教程的差异

当前教程更偏 `本地样本` 的 clean-room harness 复刻。WorkBuddy 自分析材料补了三个方向：

1. **产品外壳更完整**：RPC domain、技能市场、专家、IM、分享、inspiration 等。
2. **sidecar 细节更扎实**：ring buffer、socket 路径、idle timeout、env isolation。
3. **安全系统更完整**：sandbox-cli、FileProvider/NetworkExtension、审计哈希链、文件版本管理。

建议后续合并顺序：

1. 先更新 `s03_sidecar_gateway`：ring buffer、idle timeout、env isolation。
2. 再更新 `s09_sandbox_security`：sandbox-cli 和 audit hash chain。
3. 再更新 `s07_context_memory`：memorySelector manifest -> selected_memories。
4. 最后新增一个 `s13_multi_agent_coordination`：AgentNames、auxiliary/asTool/team、TaskList 黑板模式。

## 给公众号稿的反馈

`110.md` 可读性很好，适合作为“为什么 WorkBuddy 值得研究”的传播稿。它的优势是把工程机制讲成了几个清晰主题：

- 六层架构与安全控制
- 多 Agent 分工
- SubAgent 上下文隔离
- 三层记忆和 memorySelector
- 工具延迟加载与压缩
- Skills / Plugins / MCP 扩展

但如果作为技术教程发布，建议补三类标注：

1. 明确版本：哪些来自 `5.1.7`，哪些来自 `本地样本`。
2. 区分证据与解释：“黑板模式”“信息收费站”是解释，不是内部名。
3. 避免写死数量：工具数、Agent 数、连接器数会随插件和版本变化。

## 2026-07-08 二次复核记录

本次复核重新阅读了用户提供的 HTML 分析报告和中文稿件，并把它们与当前教程正文、代码、测试一起对照。处理原则如下：

| 类别 | 处理 |
|---|---|
| Sidecar、RPC、环形缓冲、环境隔离 | 保留为架构模式，用教学实现表达 |
| `memorySelector`、工具延迟加载、压缩、上下文摘要 | 保留为 harness 关键机制，并在对应章节给出最小实现 |
| 多 Agent、TaskList 黑板、模型分层 | 作为合理架构解释写入，不写死具体产品数量 |
| 私有文件路径、包体尺寸、精确工具/Agent 数量 | 从公开教程正文移除或泛化 |
| 未在当前本地样本中复核的服务端能力 | 不作为教程事实，只在 evidence 中记录为待验证 |

本次还新增了“公开教程正文过度具体化扫描”，专门避免把可变的内部数量、私有 bundle 路径、文件尺寸、未确认接口名写进公开教程正文。这样 evidence 可以保留观察线索，主教程保持 clean-room 教学表达。

验证结果：

```text
python3 -m pytest -q
29 passed

python3 scripts/verify.py
ok syntax: 39 Python files
ok project shape
ok smoke: mini_workbuddy HTTP run
ok clean-room scan
ok public doc specificity scan
all checks passed
```

当前判断：教程可以继续朝“learn claude code”式开源教程推进。主线足够完整，覆盖 agent loop、工具分发、权限、Electron shell、Sidecar、会话、模型路由、JSONL、记忆、压缩、prompt 组装、Skills、MCP、专家、可视化、结果呈现、SQLite、自动化、安全审计和综合 harness；公开表达上也已把源码观察和教学实现分开。
