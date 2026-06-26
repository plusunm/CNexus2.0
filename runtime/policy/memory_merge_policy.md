# Memory Merge Policy

## 优先级

```text
Constitution > Runtime Policy > Foundation > Project > Long-term > Conversation
```

## 检索边界

- **禁止** 将 Constitution / Runtime Policy 纳入 Vector Search、Recall、Embedding。
- Foundation 在 Memory 召回中享有加权优先，但不替代 Constitution 直注。

## 清空策略

- L0/L1 可清空
- L2 Core / L4 Foundation 保留
- Constitution 不在 Memory Store，不受 memory.clear 影响

## 版本合并

Foundation 升级采用 append-only 版本链；禁止覆盖，只能 supersede。
