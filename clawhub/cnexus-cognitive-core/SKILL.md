---
name: cnexus-cognitive-core
description: CNexus 2.0 — local personal second brain. Chat with memory, document ingest, memory flow graph, federated share across devices, 6-step cognitive loop, REM consolidation, optional Windows installer.
---

# CNexus 2.0 — Personal Cognitive OS

**Repo:** https://github.com/plusunm/CNexus2.0  
**ClawHub:** https://clawhub.ai/plusunm/skills/cnexus-cognitive-core

CNexus 2.0 不是普通聊天机器人，而是**运行在你电脑上的个人第二大脑**：把对话、文档、代码和架构图变成可检索、可关联、可持久化的认知网络。数据默认留在本机；可选与信任设备或局域网内的其他 CNexus 节点共享记忆。

---

## 这个产品解决什么问题？

| 场景 | CNexus 怎么做 |
|------|----------------|
| 聊完就忘 | 每轮对话自动写入结构化记忆，下次对话前按激活度召回相关片段 |
| 资料散落 | 上传 PDF / Word / Markdown / 代码 / 架构图，统一进入记忆库与流图 |
| 想看清「记住了什么」 | 记忆流图、激活分数、语义虫洞，可视化节点与关联 |
| 多设备协作 | 设备 ID + 信任连接 + 记忆共享，在本机 / 组群 / 全网范围检索 |
| 长期运行变乱 | REM 深度整理：空闲时剪枝噪声、压缩碎片、提炼长期节点 |
| 不想依赖云端 | 本地 Ollama 优先；DeepSeek / OpenAI 可选；网关与快照均在本地 JSON |

---

## 应用界面（Second Brain）

| 模块 | 你能做什么 |
|------|------------|
| **对话** | 与 CNexus 聊天；输入框上方切换记忆范围（本机 / 组群 / 全网） |
| **记忆** | 浏览记忆流图、激活扩散、语义虫洞与 REM 状态 |
| **上传记忆** | 批量导入文档，带进度；支持常见办公与文本格式 |
| **记忆共享** | 查看本节点分享统计；检索联邦目录中的记忆图；连接其他设备 |
| **模型** | 配置 Ollama、DeepSeek、OpenAI；本地模型优先 |
| **个人 / 网络** | 设备 ID（Ed25519）、在线节点、拓扑与连接状态 |

---

## 核心能力（应用层）

### 记忆增强

- **结构化记忆单元**：身份、目标、信念、经历等类型，带重要度与关键词
- **记忆流图**：实时展示节点与边，支持按范围（本机 / 组群 / 全网）切换视图
- **激活扩散**：相关记忆随对话上下文自动「升温」，注入下一轮提示
- **语义虫洞**：跨主题的概念通过本地向量相似度建立隐性链接
- **多模态摄入**：文档正文解析；代码 AST 投影；架构图视觉解析（需 Ollama）
- **持久化与清空**：自动写入 `data/cnexus_personal_state.json`；UI 一键清空记忆（可保留模型配置）

### 认知辅助

- **六步闭环**：OBSERVE → COGNIZE → DECIDE → SPEAK → STORE → REFLECT，每轮可追溯
- **决策回放**：通过 trace_id 查看完整执行链与内核记录
- **混合推理**：本地 Ollama 优先，云端 API 可配置为回退
- **可观测状态**：`/api/status` 返回情绪、目标、图谱、激活分数、虫洞链接

### 互联与共享（去中心化）

- **默认分享**：客户端运行时可自动将本机记忆发布到本地目录，供节点间发现
- **本节点统计**：可见记忆图数量、可见分享客户端数（无需中心服务器）
- **客户端发现**：合并信任节点、DHT 与局域网扫描，展示可连接的 CNexus 设备
- **联邦检索**：在「记忆共享」中按范围搜索、拉取远端记忆块

### 记忆层级（简要）

| 层级 | 用途 |
|------|------|
| L0 Scratch | 当前会话草稿 |
| L1–L2 | 临时 / 长期个人记忆 |
| L3 Project | 项目绑定记忆，清空时可保留 |
| L4 Foundation | 官方指南等基础文档（可版本升级） |
| L5 Runtime | 系统策略与宪法（编译加载，非普通聊天记忆） |

---

## 安装与启动

### Windows 安装包（推荐）

运行 `CNexus 2.0_2.4.0_x64-setup.exe`，安装后从开始菜单启动；后台自动拉起网关 **7864** 并打开工作台。

构建安装包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-tauri-installer.ps1
```

### 源码 / 开发

```bash
git clone https://github.com/plusunm/CNexus2.0.git
cd CNexus2.0
pip install pynacl          # 设备 ID（Ed25519）
python app_v2.py
```

浏览器打开 **http://127.0.0.1:7864**，或双击 `start_cnexus.bat`。

| 要求 | 说明 |
|------|------|
| Python | 3.10+ |
| 身份 | `pynacl`（生成设备 ID，用于 P2P 与签名） |
| LLM | 可选 Ollama / DeepSeek / OpenAI |
| 数据目录 | 默认 `./data`，可通过 `CNEXUS_DATA_DIR` 修改 |

---

## 主要 API（网关 7864）

| 端点 | 说明 |
|------|------|
| `GET /` | 静态前端（工作台） |
| `POST /api/converse` | 认知对话 |
| `GET /api/status` | 系统状态 + 记忆图谱 |
| `GET /api/dashboard/status` | 任务控制 / 节点与同步概览 |
| `GET /api/share/stats` | 本节点可见分享统计 |
| `GET /api/peers/discovered` | 发现的 CNexus 客户端 |
| `POST /api/application/publish` | 立即分享本机记忆 |
| `POST /api/ingest/document` | 文档上传与索引 |
| `POST /api/ingest/code` | 代码 AST 投影 |
| `POST /api/ingest/image` | 架构图解析 |
| `POST /api/memory/clear` | 清空记忆 |
| `POST /v1/memory/rem-sleep` | 触发 REM 深度整理 |

---

## OpenClaw 技能安装

本条目为 **应用说明与安装指引**；完整运行时需克隆 GitHub 仓库或安装桌面包。

```bash
openclaw skills install @plusunm/cnexus-cognitive-core
```

---

## 典型使用路径

1. **个人知识库**：上传笔记与文档 → 在「记忆」查看流图 → 对话时自动引用  
2. **本地 AI 工作台**：配置 Ollama → 对话 + 记忆增强，数据不出本机  
3. **双机协作**：两台设备互加信任 → 切换「组群」记忆范围 → 共享检索与同步  
4. **长期维护**：定期 REM 整理；需要时一键清空记忆重新开始  

---

**CNexus remembers what you think, and understands how you think.**
