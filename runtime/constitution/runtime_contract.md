# CNexus Runtime Contract

## BOOT Sequence

```text
BOOT → Constitution → Runtime Policy → Foundation → Project → Conversation Ready
```

## 编译契约

- 源：`runtime/constitution/*.md` + `runtime/policy/*.md`
- 产物：`data/runtime/constitution.bin`
- 校验：SHA-256 content signature

## Memory 边界

| 组件 | 域 | Vector | Recall |
|------|-----|--------|--------|
| Constitution | Runtime | 否 | 否 |
| Runtime Policy | Runtime | 否 | 否 |
| Foundation | Memory | 可选 | 是 |
| Project | Memory | 是 | 是 |
| Conversation | Memory | 否 | 局部 |

## 版本策略

Foundation 支持分支版本链：`v1 → v1.1 → v1.2 → v2`，历史保留，不硬删。
