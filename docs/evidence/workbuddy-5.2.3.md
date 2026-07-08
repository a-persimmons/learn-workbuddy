# WorkBuddy 本地样本 证据索引

分析日期：2026-07-07  
安装包：`[local installer sample]`

## DMG 与 App 元信息

```text
DMG size: 383M
DMG format: UDZO, APFS, read-only compressed image
SHA256: [redacted]
Mounted volume: [redacted local mount]
App bundle: [redacted local app bundle]
App size: 815M
```

`Info.plist` 关键字段：

| 字段 | 值 |
|---|---|
| `CFBundleDisplayName` | `WorkBuddy` |
| `CFBundleExecutable` | `Electron` |
| `CFBundleIdentifier` | `com.workbuddy.workbuddy` |
| `CFBundleShortVersionString` | `本地样本` |
| `CFBundleURLSchemes` | `workbuddy` |
| `LSApplicationCategoryType` | `public.app-category.developer-tools` |
| `NSAllowsLocalNetworking` | `true` |

## 包体结构

```text
WorkBuddy.app/Contents/
  MacOS/Electron
  Frameworks/
    Electron Framework.framework
    WorkBuddy Helper*.app
  Resources/
    桌面包体资源
    unpacked runtime resources/
      cli/
      node_modules/
      resources/
    vendor/
      node.tar.gz
      python.dat
      genie-trash/
```

关键体积：

| 路径 | 大小 |
|---|---:|
| `Resources/桌面包体资源` | 244M |
| `Resources/unpacked runtime resources` | 293M |
| `CLI runtime resources/dist/CLI bundle` | 21.6M |

`桌面包体资源` 文件表大约包含 20428 个条目。顶层结构：

| 顶层目录 | 作用 |
|---|---|
| `main/` | Electron main 进程、app-server、sidecar manager、认证、插件种子、MCP proxy |
| `preload/` | contextBridge IPC 暴露层 |
| `renderer/` | React/Vite 静态前端资源 |
| `resources/` | 被标记 unpacked 的动态资源引用 |
| `cli/` | CLI 相关资源引用 |
| `node_modules/` | Electron main 依赖 |

## CLI Harness

CLI 入口：

```text
CLI runtime resources/bin/codebuddy
CLI runtime resources/dist/CLI bundle
```

`cli/package.json` 关键字段：

| 字段 | 值 |
|---|---|
| `name` | `@genie/agent-cli` |
| `publishConfig.customPackage.name` | `[redacted vendor package]` |
| `publishConfig.customPackage.version` | `2.106.4` |
| `bin` | `codebuddy`, `cbc` |
| `main` | `lib/node/index.js` |

关键依赖显示了 harness 组成：

| 依赖 | 架构含义 |
|---|---|
| `@agentclientprotocol/sdk` | ACP 协议 |
| `@modelcontextprotocol/sdk` | MCP 扩展协议 |
| `@celljs/*` | CLI HTTP 服务和依赖注入框架 |
| `@lydell/node-pty` / `node-pty` | 终端进程 |
| `better-sqlite3` | 本地索引和桌面数据库 |
| `@openai/agents` / `openai` | 模型和 agent SDK 适配 |
| `tree-sitter-bash` / `web-tree-sitter` | Bash 解析与命令安全分析 |
| `ws` / `vscode-jsonrpc` | 流式与 RPC 通信 |
| `ink` / `react` | CLI TUI |

CLI 支持的关键运行模式：

```text
codebuddy --serve --port <port> --host 127.0.0.1
codebuddy --acp
codebuddy --print --output-format stream-json
codebuddy daemon start|status|stop|restart
codebuddy --bg / ps / logs / attach / kill
```

## Desktop Main 关键模块

`桌面包体资源/main/` 中与 harness 关系最密切的文件：

| 文件 | 观察到的职责 |
|---|---|
| `index.js` | Electron 启动入口 |
| `module.app-server.js` | 桌面 app-server、connector、sidecar gateway、REST/ACP 协调 |
| `daemon-app-server-main.js` | daemon app-server 子进程入口 |
| `sidecar-entry.js` | Sidecar 控制 socket、session process、ring buffer |
| `agent bridge` | ACP SDK schema 与客户端/agent 方法 |
| `mcp.js` | MCP SDK 与 Streamable HTTP 相关能力 |
| `workbuddy-auth-product-coordinator.js` | 认证、产品配置、gateway credential |
| `seed-builtin-plugins.js` | 内置插件和资源种子 |
| `desktop-monitor-service.js` | 性能、日志、监控指标 |

关键观察：

- `sidecar-entry.js` 中存在 `session.create`、`session.reconnect` 等控制 socket 方法。
- Sidecar 为 session 构造 `http://127.0.0.1:<port>/api/v1/acp` endpoint。
- macOS/Linux 使用 PTY 启动 session process，Windows 可退到 child process。
- 注释显示历史上本地 gateway auth 曾是风险点，新版本用进程内随机请求凭证缓解。

## Renderer 与 Preload

Renderer 入口：

```text
桌面包体资源/renderer/index.html
桌面包体资源/renderer/assets/index-*.js
```

前端资源名显示了主要页面：

| 资源名线索 | 可能页面/能力 |
|---|---|
| `colleague-chat-page-*` | 多 agent / colleague chat |
| `connector-*` | MCP connector 管理 |
| `automation-panel-*` | 自动化任务 |
| `agent-chat-pane-*` | 会话面板 |
| `expert-picker-*` | Expert / agent persona 选择 |
| `claw-workspace-*` | 工作区 |
| `FileTabs-*` / `codeEditor-*` | 文件和代码查看 |

Preload 暴露的桥：

| 桥 | 作用 |
|---|---|
| `__workbuddyStartDragLocalFile` | renderer 发起本地文件拖拽 |
| `__datongIpc` | 遥测 SDK 所需的最小 IPC 子集 |

## 运行时目录

本机运行时目录：`~/.workbuddy/`

重要文件：

| 路径 | 作用 |
|---|---|
| `settings.json` | 用户设置、插件开关、sandbox 额外写入白名单 |
| `.mcp.json` | MCP server 聚合配置，含 connector-proxy |
| `workbuddy.db` | Desktop 级 SQLite：sessions、workspaces、automations、usage |
| `projects/<project>/<session>.jsonl` | 会话 transcript |
| `projects/<project>/<session>/tool-results/*.txt` | 大工具输出外部化文件 |
| `tasks/<session>/*.json` | Todo/task 状态 |
| `artifact-index/<session>.json` | artifact 和文件变更索引 |
| `memory/<uid>_memory.md` | 用户/云记忆本地材料 |
| `logs/` | main、startup、sandbox、team、update 等日志 |

SQLite 表：

```text
sessions
workspaces
automations
automation_runs
automation_runtime_state
session_usage
migration_meta
```

## 上下文管理常量

CLI bundle 中可观察到的环境变量/阈值：

| 名称 | 含义 |
|---|---|
| `BASH_MAX_OUTPUT_LENGTH` / default bash output length | Bash 输出截断/外部化阈值 |
| `CODEBUDDY_TOOL_RESULT_THRESHOLD_KB` | 非 Bash 工具结果外部化阈值，默认可观察为 50KB |
| `CODEBUDDY_PRE_MESSAGE_COMPACT_PCT` | 用户消息前预压缩水位 |
| `CODEBUDDY_AUTOCOMPACT_PCT_OVERRIDE` | 自动压缩水位覆盖 |
| `CODEBUDDY_SESSION_MAX_ITEMS` | session 恢复时最多回放 item 数，默认可观察为 1000 |
| `CODEBUDDY_BASH_ASSISTANT_BUDGET_MS` | Bash 前台/后台预算 |

## 协议层

ACP 方法名来自 `@agentclientprotocol/sdk` schema：

| 方向 | 方法 |
|---|---|
| Client -> Agent | `initialize`, `session/new`, `session/load`, `session/prompt`, `session/resume`, `session/cancel`, `mcp/message` |
| Agent -> Client | `session/update`, `session/request_permission`, `terminal/create`, `terminal/output`, `terminal/kill`, `mcp/message`, `fs/read_text_file`, `fs/write_text_file` |

REST API 公开文档位于：

```text
CLI runtime resources/dist/web-ui/docs/cn/cli/http-api.md
CLI runtime resources/dist/web-ui/docs/cn/cli/acp.md
```

公开路由族：

```text
/api/v1/health
/api/v1/runs
/api/v1/sessions
/api/v1/pty
/api/v1/process
/api/v1/fs
/api/v1/files
/api/v1/workers
/api/v1/daemon
/api/v1/channels
/api/v1/plugins
/api/v1/acp
```

## 扩展系统

包内可观察到：

```text
unpacked runtime resources/resources/builtin-skills/
unpacked runtime resources/resources/builtin-plugins/
unpacked runtime resources/resources/builtin-mcp-apps/
```

运行时可观察到：

```text
~/.workbuddy/plugins/
~/.workbuddy/connectors/
~/.workbuddy/.mcp.json
```

抽象关系：

```text
Skill = 给模型看的说明、参考材料、脚本
Plugin = 打包 skill + MCP server + hook + assets 的分发单位
MCP connector = 把外部系统统一暴露成 tools/resources/prompts
ToolSearch/defer loading = 工具很多时，只把摘要放进上下文，需要时再加载 schema
```
