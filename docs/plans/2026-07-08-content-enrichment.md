# WorkBuddy Tutorial Content Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich every chapter with stronger fundamentals, clean-room architecture notes, and a clearer reading path while preserving the 24-step learn-by-building structure.

**Architecture:** Keep the 24 existing chapters because each chapter maps to one harness mechanism and already has runnable code. Add shared documentation for chapter grouping and further reading, then insert consistent learning scaffolding into every README without changing code behavior.

**Tech Stack:** Markdown, Python verification scripts, SVG diagrams, pytest.

---

### Task 1: Fix Chapter Numbering

**Files:**
- Modify: `s08_model_routing/README.md`
- Modify: `s09_jsonl_transcript/README.md`
- Modify: `s13_output_externalization/README.md`

**Steps:**
1. Correct title numbers so directory number and README title match.
2. Run a title consistency check.
3. Keep existing chapter names and code paths unchanged.

### Task 2: Add Chapter Map

**Files:**
- Create: `docs/chapter-map.md`
- Modify: `README.md`

**Steps:**
1. Group 24 chapters into five modules: Agent Core, Desktop Runtime, Context & Memory, Extension System, Production Harness.
2. Explain why chapters are not merged.
3. Link the map from the root README.

### Task 3: Add Further Reading Map

**Files:**
- Create: `docs/further-reading.md`
- Modify: `README.md`

**Steps:**
1. Map uploaded resource-list references to tutorial chapters.
2. Include Anthropic harness/context/tool/eval resources, learn-claude-code style projects, memory systems, MCP/ACP/A2A, and observability resources.
3. Keep external resources as optional reading, not dependencies.

### Task 4: Enrich Every Chapter README

**Files:**
- Modify: `s01_*` through `s24_*` README files.

**Steps:**
1. Add a concise `学习前置知识` section to each chapter.
2. Add a concise `本章抓住的 WorkBuddy-style 机制` section to each chapter.
3. Add a concise `常见误区` section to each chapter.
4. Avoid private file names, exact tool/agent counts, and unverified service names.

### Task 5: Integrate 110.md Architecture Insights

**Files:**
- Modify: `s04_permission_hooks/README.md`
- Modify: `s07_session_management/README.md`
- Modify: `s12_cloud_memory/README.md`
- Modify: `s14_context_compact/README.md`
- Modify: `s16_skills_system/README.md`
- Modify: `s17_mcp_connectors/README.md`
- Modify: `s23_audit_sandbox/README.md`
- Modify: `s24_comprehensive/README.md`
- Modify: `docs/evidence/workbuddy-self-analysis-review.md`

**Steps:**
1. Add clean-room summaries for six-layer architecture, tiered trust, multi-agent roles, context isolation, TaskList blackboard, memorySelector, deferred tools, compact/contextSummary, Skills/Plugins/MCP/Hooks.
2. Downgrade exact counts and private claims to generalized patterns.
3. Record the source-handling decision in evidence docs.

### Task 6: Expand Verification

**Files:**
- Modify: `tests/test_project_structure.py`
- Modify: `scripts/verify.py`

**Steps:**
1. Check README title number matches directory number.
2. Check every chapter has the new learning sections.
3. Run existing Python, image, clean-room, and HTTP smoke checks.

### Task 7: Final Multi-Round Validation

**Commands:**
- `python3 -m pytest -q`
- `python3 scripts/verify.py`
- targeted `rg` clean-room scan

**Expected:** All checks pass and no generated artifacts remain.
