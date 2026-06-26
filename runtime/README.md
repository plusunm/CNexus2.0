# CNexus Runtime

本目录是 **CNexus 认知操作系统** 的启动层，不属于 Memory Domain。

## 架构

```text
BOOT
  ↓
Load Constitution     ← runtime/constitution/  → constitution.bin
  ↓
Load Runtime Policy   ← runtime/policy/
  ↓
Load Foundation       ← Memory (用户手册、实战指南)
  ↓
Load Project          ← Memory
  ↓
Conversation Ready
```

## 原则

- **Constitution 不是 Memory** — 不进入 Vector、Recall、Embedding、RAG
- **编译加载** — Gateway 启动时编译为 `data/runtime/constitution.bin`
- **用户上传** — 手册/指南进入 **Foundation Memory**，不是 Constitution

## 目录

| 目录 | 层级 | 说明 |
|------|------|------|
| `constitution/` | L5 | 产品哲学、认知宪法、系统契约 |
| `policy/` | Runtime Policy | 推理、记忆合并、Workflow、安全策略 |

修改源文件后重启 Gateway，或调用 `POST /v1/runtime/recompile`。
