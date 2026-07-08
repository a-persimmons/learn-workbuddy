# s08: Skills / Plugins / MCP

[返回首页](../../../README.md)

> Harness 层：能力越多，越需要延迟加载。

## 代码架构图

```mermaid
flowchart LR
    A["Extension Directory"] --> B["Manifest Reader"]
    B --> C["Tool/Skill Loader"]
    C --> D["Capability Index"]
    D --> E["Agent Runtime"]
```

## 问题

一个 agent 产品会接入几十个工具、连接器和领域技能。如果全部塞进系统提示，上下文会被工具说明吃光。

## WorkBuddy 观察

包内资源：

```text
unpacked runtime resources/resources/builtin-skills/
unpacked runtime resources/resources/builtin-plugins/
unpacked runtime resources/resources/builtin-mcp-apps/
```

运行时资源：

```text
~/.workbuddy/plugins/
~/.workbuddy/connectors/
~/.workbuddy/.mcp.json
```

抽象：

| 类型 | 作用 |
|---|---|
| Skill | 给模型看的领域知识、流程、脚本 |
| Plugin | 分发单位，可包含 skill、MCP、hooks、assets |
| MCP Connector | 把外部系统统一成 tools/resources/prompts |
| ToolSearch | 只先加载摘要，需要时再加载完整 schema |

## 复刻方式

教学版的 `tool_search` 只搜索内置工具，但接口形状与真实 deferred loading 一致：

```text
query -> matching tool summaries -> model chooses exact tool
```

