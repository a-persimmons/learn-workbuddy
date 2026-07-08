# Chapter Map

This tutorial keeps 24 chapters on purpose. The chapters are not separate products; each one isolates one harness mechanism so a reader can build, run, and understand it before the next layer appears. The machine-checkable version of that ladder lives in [Progression Contract](./progression-contract.md).

## Should Any Chapters Be Merged?

Not now. Some topics are adjacent, but merging them would make the learning curve worse:

| Adjacent Chapters | Why Keep Separate |
|---|---|
| s05 Electron Shell / s06 Sidecar / s07 Session | UI process isolation, sidecar control plane, and session lifecycle are three different failure domains. |
| s10 Workspace Memory / s11 User Memory / s12 Cloud Memory | The storage location, ownership, update policy, and retrieval timing are different. |
| s16 Skills / s17 MCP / s18 Experts | Skills add instructions, MCP adds external tools, Experts package persona + memory + tools. |
| s21 SQLite / s22 Automation / s23 Audit | Persistence, scheduling, and security governance share infrastructure but answer different production questions. |

The right improvement is enrichment, not compression: better prerequisites, clearer architecture notes, and stronger cross-chapter links.

## Module 1: Agent Core

| Chapter | Mechanism | Build Outcome |
|---|---|---|
| s01 Agent Loop | ReAct-style loop with tool calls | A minimal agent loop. |
| s02 Tool Dispatch | Tool registry and handler dispatch | Add tools without changing the loop. |
| s03 Deferred Loading | Tool discovery before schema loading | Keep startup prompt small. |
| s04 Permission & Hooks | Tiered trust and hook gates | Let the agent act inside safe boundaries. |

## Module 2: Desktop Runtime

| Chapter | Mechanism | Build Outcome |
|---|---|---|
| s05 Electron Shell | Main/renderer/preload process split | Understand desktop app boundaries. |
| s06 Sidecar Server | JSON-RPC control plane and ring buffer | Keep agent work outside the UI process. |
| s07 Session Management | Per-session process lifecycle | Run isolated work sessions. |
| s08 Model Routing | Cheap model for routing, stronger model for reasoning | Match model cost to task complexity. |
| s09 JSONL Transcript | Append-only event stream | Recover and replay sessions. |

## Module 3: Context & Memory

| Chapter | Mechanism | Build Outcome |
|---|---|---|
| s10 Workspace Memory | Project-local logs and curated memory | Remember current project work. |
| s11 User Memory | Cross-project preferences and identity | Carry stable user context. |
| s12 Cloud Memory | Server-side profile and history recall | Retrieve long-horizon context. |
| s13 Output Externalization | Swap large tool output to disk | Keep context small. |
| s14 Context Compact | Structured compression before overflow | Continue long sessions. |
| s15 Prompt Assembly | Runtime prompt composition | Assemble exactly the context needed. |

## Module 4: Extension System

| Chapter | Mechanism | Build Outcome |
|---|---|---|
| s16 Skills System | Instruction packages with optional scripts/assets | Add capabilities without changing core code. |
| s17 MCP Connectors | External tool protocol and trust model | Connect third-party services safely. |
| s18 Experts System | Domain bundles of persona, memory, and tools | Switch working modes cleanly. |
| s19 Visualizer | Structured output to diagrams/UI artifacts | Turn agent output into inspectable views. |
| s20 Result Presentation | Prioritized deliverables | Present work as files, summaries, and diffs. |

## Module 5: Production Harness

| Chapter | Mechanism | Build Outcome |
|---|---|---|
| s21 SQLite Database | Durable metadata and usage tracking | Persist sessions and usage. |
| s22 Automation Scheduler | Timed and recurring agent runs | Wake the harness without a user prompt. |
| s23 Audit & Sandbox | Command policy and tamper-evident logs | Make autonomous work governable. |
| s24 Comprehensive | End-to-end mini harness | See how all layers fit together. |

## The Mental Model

The tutorial is a ladder:

```text
agent loop
  + tool dispatch
  + permissions
  + desktop process boundary
  + sidecar/session runtime
  + memory/context compression
  + extension protocols
  + persistence/scheduling/audit
  = WorkBuddy-style harness
```

Each chapter should answer three questions:

1. What problem appears when the previous chapter gets real users?
2. What minimal mechanism fixes it?
3. How would a production desktop agent harden that mechanism?
