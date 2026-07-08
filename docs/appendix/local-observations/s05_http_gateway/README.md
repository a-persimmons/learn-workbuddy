# s05: REST 网关

[返回首页](../../../README.md)

> Harness 层：ACP 负责完整会话，REST 负责管理和自动化。

## 代码架构图

```mermaid
flowchart LR
    A["HTTP Request"] --> B["Local Gateway"]
    B --> C["Route Guard"]
    C --> D["Runtime API"]
    D --> E["JSON Response"]
```

## 问题

并不是所有操作都适合走流式会话协议。列 sessions、查 health、启动后台任务、读文件、看 worker 日志，这些更适合 REST。

## WorkBuddy 观察

CLI 文档列出两套公开接口：

```text
REST API: /api/v1/*
ACP:      /api/v1/acp
```

主要路由族：

```text
/api/v1/health
/api/v1/runs
/api/v1/sessions
/api/v1/pty
/api/v1/process
/api/v1/fs
/api/v1/workers
/api/v1/daemon
/api/v1/plugins
```

## 复刻方式

教学版实现：

```text
GET  /api/v1/health
GET  /api/v1/sessions
POST /api/v1/sessions
POST /api/v1/runs
GET  /api/v1/sessions/:id/history
```

为了模拟 WorkBuddy 的本地请求保护，除了 health 外都需要：

```text
X-Mini-WorkBuddy-Request: 1
```

