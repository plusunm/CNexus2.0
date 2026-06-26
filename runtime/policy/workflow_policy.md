# Workflow Policy

## 工具路由

- 文档导入 → Foundation Memory（非 Constitution）
- Constitution 变更 → 仅通过 `runtime/constitution/` 编译
- 项目 Workflow → Project Memory

## Agent 约束

Agent 不得将用户对话内容写入 Constitution 源文件或编译产物。

## 升级路径

1. 修改 `runtime/constitution/` 或 `runtime/policy/`
2. `POST /v1/runtime/recompile` 或重启 Gateway
3. Foundation 内容通过 `/v1/memory/foundation/upgrade` 版本链升级
