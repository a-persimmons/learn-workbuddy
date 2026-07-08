# s04: ACP 会话协议

[返回首页](../../../README.md)

> Harness 层：UI 和 agent core 用协议解耦。

## 代码架构图

```mermaid
flowchart LR
    A["Client Message"] --> B["JSON-RPC Envelope"]
    B --> C["Session Method"]
    C --> D["Runtime Handler"]
    D --> E["Protocol Reply"]
```

## 问题

一个完整 agent UI 不只需要“发一段 prompt，拿一段文本”。它需要会话创建、恢复、取消、权限请求、工具调用、终端输出、MCP 消息和流式增量。

## WorkBuddy 观察

WorkBuddy CLI 支持 `--acp` 和 `--serve`。包内 ACP 文档说明 `CodeBuddy Code` 可作为 ACP server。

核心方法形状：

| 方向 | 方法 |
|---|---|
| Client -> Agent | `initialize`, `session/new`, `session/load`, `session/prompt` |
| Agent -> Client | `session/update`, `session/request_permission`, `terminal/create`, `terminal/output`, `mcp/message` |

WorkBuddy 桌面端使用的是 HTTP endpoint 上的 ACP：

```text
/api/v1/acp
```

## 复刻方式

教学版只实现 4 个方法：

```text
initialize
session/new
session/load
session/prompt
```

启动：

```bash
python3 -m mini_workbuddy.server --port 8765
```

调用：

```bash
curl --noproxy '*' -s -X POST http://127.0.0.1:8765/api/v1/acp \
  -H 'Content-Type: application/json' \
  -H 'X-Mini-WorkBuddy-Request: 1' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```
