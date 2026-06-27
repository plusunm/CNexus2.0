# 11_semantic_control_plane — Semantic Control Plane (SCP)

**层级：L1（执行层规格）+ L2（稳定性环）**  
**Status:** Architecture Freeze Candidate v1.0  
**Depends on:** `04_recall_context.md`, `02_identity_correction.md`, `cognitive_constitution.md`

---

## 一、定义

CNexus SCP 是 Memory OS 之上的 **语义控制面（control plane）**，对 cognition injection 做 bounded multi-source routing。

```text
Memory OS (Block / Chunk / STORE)     ← data plane
Semantic Control Plane (SCP)          ← control plane
Expert Plugin                           ← optional candidate producer (hot-plug)
```

**工程定义：**

> A constraint-driven semantic control system with bounded multi-source cognition injection.

**类比：** Kubernetes admission controller × LLM memory governance × multi-source injection router.

---

## 二、L0 不变量（SSS + SCP）

| ID | 不变量 | 范围 |
|----|--------|------|
| SSS-01 | 每个 semantic dimension 有且仅有一个主生产者 | 单轮 |
| SSS-02 | R_style ⟂ P_style（跨路径 decorrelation） | 单轮 |
| SSS-03 | LLM 输出 ≠ 记忆写入依据（除非 fact-confirm） | 跨轮 |
| SSS-04 | fact > decision > activation > style > persona_summary | 单轮 |
| SSS-05 | Constitution / L4 不参与 Arbitration 竞争 | 永久 |
| SCP-06 | E[style_weight]_session ≤ α | 跨轮 |
| SCP-07 | ΔEMA_d / Δt ≤ β_d | 跨轮 |
| SCP-08 | SBSL correction 单向收敛（只减 entanglement） | 跨轮 |

---

## 三、六层栈

```text
L0  OS Invariants
L1  Semantic Arbitration Layer (SAL)
L2  Context Composer
L3  Provenance Gate
    → LLM Context
L4  Drift Observation (turn-level)
L5  Semantic Budget Stability Loop (SBSL)
    ↓ feedback → 下轮 ArbitrationRequest
```

| 组件 | 解决 |
|------|------|
| SAL | 语义冲突（空间） |
| SBSL | 语义时间漂移（时间） |
| SCP | 统一 admission 面 |

---

## 四、语义维度模型

| Dimension | 唯一主源 | Provenance |
|-----------|----------|------------|
| fact | Recall | local-full / remote-preview |
| decision | Recall | audit-preview |
| activation | Recall | local-full |
| style | Prompt **OR** Recall（互斥） | persona-synthetic |
| persona_summary | Prompt | persona-synthetic |
| procedure | Prompt | policy-layer |

`persona_summary` 禁止进入向量索引与 activation graph。

---

## 五、SCP Admission API

### 5.1 请求 / 响应

```python
SCPRequest(
    query, turn_profile,
    recall_candidates, prompt_candidates, activation_candidates,
    activation_context,          # OS 已组装的 memory 层（P0 pass-through）
    budget_state,
    compose_llm_context,           # callback → 最终 LLM context
)

SCPResponse(
    llm_context, decision, observation,
    budget_state, correction, admitted, reject_reason,
)
```

### 5.2 调用顺序（强约束）

```text
pipeline.prepare_turn()
  → 收集 activation + recall 候选
  → SCP.admit()          # mandatory when CNEXUS_SCP_ENABLED=1
  → llm_context
pipeline.commit_turn()
  → AntiLoopGate         # P2+
```

Expert Plugin **仅**注册 candidate producers；**禁止**直连 `compose_llm_context`。

---

## 六、SAL（L1 摘要）

- Phase A：维度冲突检测（dual style → exclude）
- Phase B：单轮权重归一化（Σ w_d = 1.0；Precision: w_fact+w_decision ≥ 0.75）
- Phase C：Source dominance 裁剪

---

## 七、SBSL（L5）

### 7.1 状态

`SemanticBudgetState` 持久化于 `data/semantic_budget_state.json`（atomic replace）。

### 7.2 EMA

```text
EMA_d(t) = α · EMA_d(t-1) + (1-α) · w_d(t)     default α=0.9
```

### 7.3 触发器

| ID | 条件 |
|----|------|
| SBSL-T1 | ema[style] > STYLE_EMA_MAX (0.08) |
| SBSL-T2 | ema[style] 连续 N 轮上升且 Δ > 0.01 |
| SBSL-T3 | ema[fact] < FACT_EMA_FLOOR (0.45) |
| SBSL-T4 | cumulative[style]/turns > STYLE_MEAN_MAX |
| SBSL-T5 | fact_miss_streak ≥ 3 且 ema[style] > 0.05 |

### 7.4 Restoration（单向收敛）

| Level | 动作 |
|-------|------|
| 1 | style_weight_max ↓；fact_floor ↑ |
| 2 | style_source=off 1 turn；force MMR rebalance |
| 3 | style_source=off 3 turns；audit correction |

`BudgetCorrection` 回灌下轮 `ArbitrationRequest`；SAL 必须 honor。

---

## 八、配置

```powershell
CNEXUS_SCP_ENABLED=0              # P0 默认 OFF，零回归
CNEXUS_EXPERT_DISTILL=0
CNEXUS_EXPERT_STYLE_SOURCE=prompt
CNEXUS_SAL_STYLE_WEIGHT_MAX=0.15
CNEXUS_SBS_EMA_ALPHA=0.9
CNEXUS_SBS_STYLE_EMA_MAX=0.08
CNEXUS_SBS_FACT_EMA_FLOOR=0.45
CNEXUS_SEMANTIC_BUDGET_FILE=...   # optional override
```

---

## 九、代码布局

```text
src/semantic/
  scp.py
  arbitration.py
  composer.py
  stability_loop.py
  budget_store.py
  drift_observation.py
  provenance_gate.py
  anti_loop.py
  mmr.py
  types.py
  dimensions.py

src/plugins/expert_distill/
  producer.py
```

---

## 十、落地阶段

| Phase | 内容 |
|-------|------|
| P0 | SCP 骨架 + types + SBSL + atomic persist + pipeline hook |
| P1 | Composer slot isolation + persona-synthetic provenance + anti-loop + status |
| P2 | SAL MMR rebalance + expert candidate producer + drift L4 + converse expert_mode |
| P3 | Expert distill jobs + fact-confirm API |
| P4 | SBSL 100-turn creep 门禁 |
| P5 | Expert Plugin producers |

**Freeze 门槛：P0–P4。**

---

## 十一、PR Gate

- [ ] 无 bypass SCP 的 context 路径（SCP_ENABLED=1 时）
- [ ] style 单源；Σw=1
- [ ] SBSL correction 只收紧
- [ ] 100-turn style=0.12 → T1 在 ≤15 turn 触发
- [ ] 重启后 EMA 从 persist 恢复
- [ ] SCP_ENABLED=0 → baseline 零 diff

---

*CNexus Expert Distillation = Single-Source Semantic Control System, not multi-channel augmentation.*
