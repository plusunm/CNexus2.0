# CNexus 双节点 Repair 联调 Runbook

> **推荐入口（P5.3）：** 优先使用 `/api/application/*` 统一语义 API，而非直接拼装底层 protocol 路由。

本文档描述 Node A（本地缺失 chunk）与 Node B（持有 chunk）之间的完整 repair 流程。  
**原则：Hook 只观察，Gate 只许可，Execute 必须显式 confirm。**

---

## Application Facade（统一控制面）

| 方法 | 路径 | 语义 |
|------|------|------|
| GET | `/api/application/status` | 控制面状态 + 各层 health |
| POST | `/api/application/publish` | memory blocks 或 graph/commit 发布 |
| POST | `/api/application/find` | catalog 检索 |
| POST | `/api/application/sync` | catalog + cognitive pull（无 handshake） |
| POST | `/api/application/diagnose` | 本地 diff + plan（无 peer） |
| POST | `/api/application/repair` | `action`: hook / gate / execute |

Connect 响应新增 `application` 字段，吸收 `repair_hook` + `execution_gate` 到统一 phase 状态机。

---

## 前置条件

- Node A、Node B 均运行 CNexus 2.0（默认端口 `7864`）
- 已完成 P2 Catalog + P3 Cognitive 同步（connect 后 catalog/cognitive 正常）
- Node B 已通过 `POST /api/cognitive/publish` 发布含 chunk 的 graph
- Node A 有对应 Manifest 索引，但本地 ChunkStore 缺失 blob

---

## 流程总览

```text
1. POST /api/connectivity/connect          → handshake + catalog + cognitive + repair_hook
2. 审阅 repair_hook（missing / plans / probe / execution_gate）
3. POST /api/storage/repair/gate           → 可选，单独预览门禁
4. POST /api/storage/repair/execute        → confirm:true 才执行
```

---

## Step 1 — Connect（Node A → Node B）

```http
POST http://NODE_A:7864/api/connectivity/connect
Content-Type: application/json

{
  "peer_id": "<NODE_B_PUBKEY_64_HEX>",
  "host": "http://NODE_B:7864"
}
```

关键响应字段 `repair_hook`：

| 字段 | 含义 |
|------|------|
| `missing` | 本地缺失的 chunk hashes |
| `repair_plans` | 结构化修复意图 |
| `suggested_sources` | 候选来源 + probe 证据 |
| `execution_gate` | 门禁预览（通常 `require_confirm`） |
| `executed` | 必须为 `false` |

---

## Step 2 — 审阅 Gate（可选独立调用）

```http
POST http://NODE_A:7864/api/storage/repair/gate
Content-Type: application/json

{
  "plans": [ ... 来自 repair_hook.repair_plans ... ],
  "suggested_sources": [ ... 来自 repair_hook.suggested_sources ... ],
  "confirm": false
}
```

期望：

- `gate: "require_confirm"` — 需要用户确认
- `decisions[].detail` — 每项可审计（probe 是否通过、source reason 等）

再次提交 `confirm: true` 预览 ALLOW 状态（仍不 pull）：

```json
{ "plans": [...], "suggested_sources": [...], "confirm": true }
```

---

## Step 3 — Execute（显式确认）

```http
POST http://NODE_A:7864/api/storage/repair/execute
Content-Type: application/json

{
  "plans": [ ... repair_hook.repair_plans ... ],
  "suggested_sources": [ ... repair_hook.suggested_sources ... ],
  "confirm": true
}
```

成功响应：

- `repaired >= 1`
- `gate.gate == "allow"`
- 本地 `GET /api/storage/chunk/state?hash=<CHUNK_HASH>` → `exists: true`

失败码：

| HTTP | 含义 |
|------|------|
| `409` | 未传 `confirm: true` |
| `403` | probe 证据不足或 source 不在 allowed_sources |

---

## Step 4 — 验证

```http
GET http://NODE_A:7864/api/storage/chunk/verify?hash=<CHUNK_HASH>
GET http://NODE_A:7864/api/storage/manifest/verify
```

---

## 执行策略（可选调整）

```http
GET  http://NODE_A:7864/api/storage/repair/policy
POST http://NODE_A:7864/api/storage/repair/policy
```

默认策略：

```json
{
  "mode": "manual",
  "allowed_sources": ["connected_peer", "trusted_registry_peer", "descriptor_provenance"],
  "require_probe": true,
  "require_user_confirm": true,
  "max_concurrency": 2,
  "max_plans": 32
}
```

持久化路径：`data/execution_policy.json`（环境变量 `CNEXUS_EXECUTION_POLICY_FILE`）

---

## 禁止事项（协议级）

- 不要跳过 hook 直接 execute（会缺 probe 证据 → 403）
- 不要在 connect 路径上自动 execute
- 不要关闭 `require_probe` 用于生产默认（仅测试环境可临时关闭）

---

## 自动化测试

```bash
python -m pytest tests/test_repair_integration_flow.py -q
```

覆盖：hook → gate(require_confirm) → gate(allow) → execute → 本地 verify

---

## LAN 双机实操

见 **[lan-dual-node-checklist.md](./lan-dual-node-checklist.md)** — Windows 防火墙、双实例模拟、UI/API 联调签字表。

快速 smoke（在 Node A 运行）：

```powershell
python scripts/lan_dual_node_smoke.py --peer-id <NODE_B_PUBKEY> --remote-host http://192.168.x.x:7864
```
