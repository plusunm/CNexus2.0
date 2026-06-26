# CNexus LAN 双机联调 Checklist（Windows）

> **Step 3 目标：** 在真实局域网验证 `connect → application.phase → hook → gate → confirm → execute` 全链路。  
> **原则：** 先通路、再同步、再诊断、最后人工确认修复。不做 auto-execute。

关联文档：[repair-dual-node-runbook.md](./repair-dual-node-runbook.md)

---

## 0. 角色定义

| 角色 | 职责 | 建议机器 |
|------|------|----------|
| **Node B（Source）** | 持有 chunk blob，已 publish | 笔记本 B |
| **Node A（Repair）** | 有 manifest/commit 索引，缺 chunk | 笔记本 A |

也可在**同一台 PC** 用不同端口 + 数据目录模拟（见 §1.3）。

---

## 1. 环境准备

### 1.1 网络

- [ ] 两台设备连接**同一 Wi‑Fi / 同一网段**（如 `192.168.x.x`）
- [ ] 关闭「公用网络隔离 / AP 隔离」（访客 Wi‑Fi 通常不可用）
- [ ] 记录 Node B 的 LAN IP：`ipconfig` → IPv4（例：`192.168.1.105`）

### 1.2 防火墙（两台都做）

PowerShell（管理员）放行入站 7864：

```powershell
New-NetFirewallRule -DisplayName "CNexus Gateway 7864" -Direction Inbound -Protocol TCP -LocalPort 7864 -Action Allow
```

若 Node B 使用非默认端口，替换 `-LocalPort`。

验证 Node B 端口可达（在 Node A 上）：

```powershell
Test-NetConnection -ComputerName 192.168.1.105 -Port 7864
```

期望：`TcpTestSucceeded : True`

### 1.3 启动 CNexus

**真实双机（推荐）：**

```bat
cd D:\类脑记忆\CNexus2.0
start_cnexus.bat
```

浏览器：`http://127.0.0.1:7864`

**单机模拟双节点（调试）：**

终端 1（Node B，7865）：

```powershell
$env:CNEXUS_PORT="7865"
$env:CNEXUS_DATA_DIR="D:\类脑记忆\CNexus2.0\data-node-b"
python app_v2.py
```

终端 2（Node A，7864）：

```powershell
$env:CNEXUS_PORT="7864"
$env:CNEXUS_DATA_DIR="D:\类脑记忆\CNexus2.0\data-node-a"
python app_v2.py
```

> 两个实例必须使用**不同的** `CNEXUS_DATA_DIR`，否则 identity / 数据会冲突。

### 1.4 获取 PeerID（公钥）

在**各自节点**浏览器或 curl：

```http
GET http://127.0.0.1:7864/api/connectivity/identity
```

记录：

- Node A 的 `pubkey` → 64 hex
- Node B 的 `pubkey` → 64 hex

---

## 2. Node B — 制造「可修复」状态

Node B 必须先有 **chunk truth** + **catalog/cognitive 索引**。

### 方式 A：Application 发布 memory（推荐）

在 Node B 上先有 memory blocks（对话几轮或手动写入），然后：

```powershell
$body = @{
  memory = $true
  topic = "lan/test"
} | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:7865/api/application/publish" `
  -ContentType "application/json" -Body $body
```

确认响应含 `root_hash`、`commit_id`、`graph_id`。

### 方式 B：Cognitive publish（API）

见 [repair-dual-node-runbook.md](./repair-dual-node-runbook.md) 中 publish 示例。

### 验证 Node B 本地完整性

```http
GET http://127.0.0.1:7865/api/application/status
GET http://127.0.0.1:7865/api/cognitive/status
```

期望：catalog + cognitive + chunks 均 ok。

---

## 3. Node A — Connect + 控制面

### 3.1 UI 路径（推荐）

1. 打开 Node A → **连接与邻居发现**（`network-connect` 视图）
2. 粘贴 **Node B 的 PeerID**（64 hex）
3. 点击 **连接并建立信任**
4. 连接成功后应出现 **「完整性诊断与修复控制」** 面板：
   - `phase`: `gate_preview` 或 `diagnosed`（有缺失时）
   - `missing`: ≥ 1
   - `execution_gate`: `require_confirm`
5. 点击 **预览门禁** → gate 决策可见
6. 点击 **确认并执行修复** → 浏览器 confirm → 等待 `repaired >= 1`

Second Brain Connect 页（`SbPeerConnectPanel`）行为相同。

### 3.2 API 路径

```powershell
# Node A 上执行；peer_id = Node B 的 pubkey
$peerB = "<NODE_B_PUBKEY_64_HEX>"
$resp = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:7864/api/connectivity/connect" `
  -ContentType "application/json" -Body (@{ peer_id = $peerB } | ConvertTo-Json)

$resp.application.phase          # gate_preview | diagnosed | connected
$resp.application.missing_count   # via repair_hook
$resp.repair_hook.executed       # 必须为 false
```

或使用自动化脚本（§6）。

---

## 4. 验证修复结果

在 **Node A** 上：

```http
GET  /api/application/status
GET  /api/storage/chunk/state?hash=<CHUNK_HASH>
POST /api/storage/manifest/verify
POST /api/application/diagnose        → missing_total 应为 0
```

UI 面板应变为：

- `phase`: `repair_complete` 或 `connected`
- 绿色「本地 chunk 与 manifest 一致」

---

## 5. 失败场景速查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `no_viable_path` | LAN 不通 / B 未启动 / 防火墙 | §1.2 `Test-NetConnection` |
| `peer_offline` / DHT 找不到 | AP 隔离、不同网段 | 换同一 Wi‑Fi；可设 `host` hint |
| `handshake_failed` | identity 未初始化 | 重启 gateway；查 identity status |
| connect ok 但 `missing_count=0` | B 未 publish；A 已有 chunk | 在 B 重新 publish；或 A 删 `data/chunks/` 对应文件 |
| gate `deny` | probe 失败 | 确认 B 的 `/api/storage/chunk/state?hash=` 返回 `exists:true` |
| execute `409` | 未 confirm | UI confirm 或 API `confirm:true` |
| execute `403` | probe 证据不足 | 先 connect（触发 hook+probe），再 execute |
| 同源双实例 identity 冲突 | 共用 `CNEXUS_DATA_DIR` | §1.3 分离数据目录 |

### 5.1 手动制造缺失（仅调试）

在 Node A 上，catalog 已同步但需强制 missing：

1. 记下 manifest 中的 chunk hash
2. 删除 `data-node-a/chunks/{aa}/{full_hash}` 文件（保留 manifests.json）
3. `POST /api/application/diagnose` → 应出现 plan
4. 重新 connect → repair 流程

---

## 6. 自动化 Smoke 脚本

Node A 已启动、已知 Node B PeerID 时：

```powershell
cd D:\类脑记忆\CNexus2.0

# 仅 connect + gate 预览（不 execute）
python scripts/lan_dual_node_smoke.py --peer-id <NODE_B_PUBKEY>

# 含远程可达性探测
python scripts/lan_dual_node_smoke.py --peer-id <NODE_B_PUBKEY> --remote-host http://192.168.1.105:7864

# 完整修复（显式 confirm）
python scripts/lan_dual_node_smoke.py --peer-id <NODE_B_PUBKEY> --confirm-repair
```

退出码：`0` = 全部通过，`1` = 有失败项。

---

## 7. 联调签字表（发布前）

| # | 检查项 | Node A | Node B | 通过 |
|---|--------|--------|--------|------|
| 1 | 同网段 + 7864 可达 | | | ☐ |
| 2 | identity 可用 | | | ☐ |
| 3 | B publish 成功 | | ✓ | ☐ |
| 4 | A connect + handshake ok | ✓ | | ☐ |
| 5 | `application.phase` 正确 | ✓ | | ☐ |
| 6 | `repair_hook.executed=false` | ✓ | | ☐ |
| 7 | gate `require_confirm` | ✓ | | ☐ |
| 8 | UI 确认后 execute ok | ✓ | | ☐ |
| 9 | A chunk verify ok | ✓ | | ☐ |
| 10 | diagnose missing=0 | ✓ | | ☐ |

---

## 8. 禁止事项（联调时）

- ❌ 不要在 connect 路径开启 auto-repair
- ❌ 不要跳过 UI/API confirm 直接 curl execute（除非 `--confirm-repair` 明确意图）
- ❌ 不要两台机器共用同一 `CNEXUS_DATA_DIR`
- ❌ 联调阶段不要跑 `npm run tauri:build`（installer 非本阶段目标）

---

## 9. 通过标准（Step 3 Done）

满足以下即视为 LAN 双机验证完成：

```text
✔ Node B publish → chunk truth 存在
✔ Node A connect → catalog + cognitive 同步
✔ application.phase 进入 gate_preview
✔ 人工 confirm → execute → chunk verify 本地通过
✔ diagnose 无 missing
```

下一步（可选）：Mission Control 批量 connect 复用同一 RepairGatePanel；或 P6 replica 设计。
