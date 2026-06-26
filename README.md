# 🧠 CNexus 2.0 — Personal Cognitive OS

> **CNexus remembers what you think, and understands how you think.**

CNexus 2.0 不是又一个聊天机器人，而是一个**本地运行的个人第二大脑**：把对话、文档、代码和架构图，变成可检索、可关联、可演化的认知网络。

本仓库为 **Personal Edition（纯净个人版）** — 单文件网关 `app_v2.py` + 静态 UI，零重型框架依赖，数据默认落在本地 JSON。

**当前开发版：v2.4.0**（构建前优化：Runtime BOOT、L3 项目绑定、Conversation Scratch、Ed25519 签名）  
**已发布：[v2.3.0](https://github.com/plusunm/CNexus2.0/releases/tag/v2.3.0)** — [小白向发布说明](RELEASE_NOTES_v2.3.0.md)

---

## 最新版本 v2.3.0 亮点（小白版）

| 你关心的事 | 这版的变化 |
|------------|------------|
| 聊天像复读机 | 已修复；未配模型时会提示，配好 DeepSeek/Ollama 后正常对话 |
| 记忆从哪来 | 输入框上方可选 **本机 / 组群 / 全网** 记忆范围 |
| 上传很慢 | 单文件上传从十几秒降到秒级；支持批量进度 |
| 聊天窗口乱滚 | 消息在框内滚动，不再把整页顶出浏览器 |
| 怎么开始 | 双击 `start_cnexus.bat` → 浏览器打开即可 |

详细图文说明见 **[RELEASE_NOTES_v2.3.0.md](RELEASE_NOTES_v2.3.0.md)**。

---

## 应用能做什么？

### ① 认知记忆增强 — Memory Augmentation

| 能力 | 你得到什么 |
|------|-----------|
| **结构化记忆** | 每次对话 / 上传 / 捕获 → 记忆单元（身份 / 目标 / 信念 / 经历） |
| **关联网络** | 记忆流图实时展示节点与边；激活扩散让相关记忆自动「升温」 |
| **语义虫洞** | 未显式链接的概念，通过本地向量余弦相似度建立跨域共振 |
| **REM 深度睡眠** | 空闲时自动剪枝噪声、压缩碎片、提炼长期语义节点 |
| **多模态摄入** | Python AST 代码投影 + Ollama 视觉架构图解析 |
| **持久化** | 自动写入 `data/cnexus_personal_state.json`，重启恢复 |
| **一键清空** | UI 侧栏 / 记忆面板 → 清空记忆与快照（保留模型配置） |

### ② 认知辅助决策 — Cognitive Companion

| 能力 | 你得到什么 |
|------|-----------|
| **六步认知闭环** | OBSERVE → COGNIZE → DECIDE → SPEAK → STORE → REFLECT，每轮可追溯 |
| **阈值即时回忆** | 对话前自动注入高激活记忆片段，上下文越用越准 |
| **决策回放** | `/v1/kernel/record/{trace_id}` 查看完整执行链 |
| **混合推理** | 本地 Ollama 优先，可选 DeepSeek / OpenAI 云端回退 |
| **可观测** | `/api/status` 返回情绪、目标、记忆图谱、激活分数、虫洞链接 |

---

## 快速启动

**Windows（推荐）**

```bat
start_cnexus.bat
```

**手动**

```bash
python app_v2.py
# 浏览器打开 http://127.0.0.1:7864
```

**环境变量（可选）**

| 变量 | 说明 | 默认 |
|------|------|------|
| `OLLAMA_HOST` | Ollama 地址 | `127.0.0.1:11434` |
| `CNEXUS_DATA_DIR` | 持久化目录 | `./data` |
| `CNEXUS_PERSIST_FILE` | 快照文件路径 | `./data/cnexus_personal_state.json` |
| `CNEXUS_REM_IDLE_SECONDS` | REM 触发空闲秒数 | `1800` |

> Python 3.10+，核心网关**无第三方 Python 依赖**。Ollama 为可选本地 LLM / 视觉 / Embedding 后端。

---

## 构建（所筑即所测）

**Web 网关（推荐）**

```powershell
cd CNexus2.0
powershell -ExecutionPolicy Bypass -File scripts/prepare-build.ps1
python app_v2.py
# 浏览器 http://127.0.0.1:7864
```

**分步**

```powershell
python -m pytest tests/ -q
cd frontend
npm ci
npm run typecheck
npm run build:personal   # 导出到 ../ui/
```

**桌面安装包（Tauri，需 VS Build Tools + Rust + NSIS）**

```powershell
cd frontend
npm run prebuild:release   # toolchain + gate + smoke
npm run tauri:build
```

---

## 主要 API

| 端点 | 说明 |
|------|------|
| `GET /` | 静态前端（工作台 / 记忆流图 / 模型配置） |
| `GET /api/status` | 系统状态 + 记忆图谱 + 持久化信息 |
| `POST /api/converse` | 六步认知对话 `{ "text": "..." }` |
| `POST /api/memory/clear` | 一键清空记忆 `{ "keep_models": true }` |
| `POST /v1/memory/capture` | 手动写入记忆 |
| `POST /v1/memory/rem-sleep` | 触发 REM 深度睡眠整理 |
| `POST /api/ingest/code` | AST 代码空间投影 |
| `POST /api/ingest/image` | 架构图视觉投影 |
| `GET /v1/kernel/record/{trace_id}` | 执行追踪回放 |

---

## 项目结构

```
CNexus2.0/
├── app_v2.py              # 统一 HTTP 网关（7864）
├── start_cnexus.bat       # Windows 一键启动
├── stop_cnexus.bat        # Windows 停止网关
├── RELEASE_NOTES_v2.3.0.md # 当前版本发布说明（小白向）
├── frontend/              # Next.js 前端源码（build:personal → ui/）
├── src/gateway/           # 模块化网关服务
├── src/kernel/            # 六步认知 reducer + BlockStore
├── ui/                    # Next.js 静态导出（个人版前端）
├── clawhub/               # ClawHub 技能发布包
├── tests/                 # 内核与网关测试
└── specs/v2_final/        # 架构与运行时规格文档
```

---

## ClawHub

OpenClaw 技能页：[cnexus-cognitive-core](https://clawhub.ai/plusunm/skills/cnexus-cognitive-core)

```bash
openclaw skills install @plusunm/cnexus-cognitive-core
```

---

## License

MIT — free to use, modify, and extend.
