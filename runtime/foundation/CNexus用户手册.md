# CNexus 2.0 Personal Edition — 用户手册

> **版本：** v2.4.0  
> **层级：** Foundation Memory（L4）— 可版本升级，非系统宪法  
> **适用：** Windows 桌面安装包 / 本机 Web 网关

---

## 一句话介绍

**CNexus 2.0 是你电脑上的「第二大脑」**：可以聊天、上传文档、记住重要内容，并在下次对话时自动把相关记忆拿出来参考。数据默认都在本机，不上传云端。

---

## 安装与启动

### 方式一：桌面版（推荐）

1. 运行安装包 `CNexus 2.0_2.4.0_x64-setup.exe`
2. 安装完成后从开始菜单或桌面快捷方式启动 **CNexus 2.0**
3. 首次启动会自动在后台拉起网关（端口 **7864**），并打开工作台界面

### 方式二：源码 / 压缩包

1. 确认已安装 **Python 3.10+**（命令行输入 `python --version`）
2. 双击项目根目录的 `start_cnexus.bat`
3. 浏览器打开 **http://127.0.0.1:7864**

### 退出程序

- **桌面版：** 关闭浮动窗口，或在系统托盘退出
- **脚本版：** 双击 `stop_cnexus.bat`，或在任务管理器结束 `python app_v2.py` / `pythonw.exe`

> 仅关闭浏览器标签页**不会**停止后台网关。

---

## 3 分钟上手

1. 左侧进入 **「对话」**，输入问题开始聊天  
2. 进入 **「上传记忆」**，导入 PDF、Word、Markdown、TXT 等文档  
3. 到 **「模型」** 页配置 DeepSeek、OpenAI API Key，或安装 [Ollama](https://ollama.com) 使用本地模型  
4. 对话时输入框上方可选择 **记忆范围**：本机 / 组群 / 全网  

---

## 界面导览（Second Brain）

| 菜单 | 用途 |
|------|------|
| **对话** | 与 CNexus 聊天，自动参考相关记忆 |
| **记忆** | 浏览记忆流图、激活分数、语义虫洞 |
| **上传记忆** | 批量导入文档，支持进度显示 |
| **记忆共享** | 在本机 / 信任设备 / 全网范围检索 |
| **模型** | 配置 DeepSeek、OpenAI、Ollama |
| **个人** | 身份、节点公钥、基础设置 |

---

## 记忆层级（重要）

CNexus 按保护级别组织记忆，从低到高：

| 层级 | 名称 | 说明 |
|------|------|------|
| L0 | Scratch | 当前会话草稿，不长期保留 |
| L1 | Temporary | 临时记忆，可清理 |
| L2 | Long-term | 普通长期记忆 |
| L3 | Project | 项目绑定记忆，清空时保留 |
| L4 | Foundation | **本手册所在层级** — 官方指南、实战文档，只追加版本链 |
| L5 | Runtime | 系统宪法与策略，编译加载，**不是**普通记忆 |

### 本手册的定位

《用户手册》《实战指南》属于 **Foundation Memory（L4）**：

- 安装时自动写入记忆库，对话时可被检索引用  
- 可通过新版本升级（保留历史版本链）  
- **不是** Constitution，修改本文件不会直接改变系统规则  

在记忆面板中，L4 记忆标记为 **基石**，支持查看版本树。

---

## 对话设置

输入框上方与侧栏提供以下选项：

| 选项 | 说明 |
|------|------|
| **记忆范围** | 本机 / 组群 / 全网 — 决定参考哪里的记忆 |
| **快速 / 深度** | 控制推理深度与响应速度 |
| **准确 / 深入思考** | 控制回答风格（precision / emergent） |
| **不参考记忆** | 纯模型回答，不注入记忆上下文 |

未配置 AI 模型时，系统会提示如何配置，**不会**复读你的输入。

---

## 上传与导入

**入口：** Second Brain → **上传记忆**

支持格式：PDF、Markdown、TXT、Word 等常见文档。

- 单文件上传已优化为秒级响应  
- 支持批量上传并显示进度  
- 文件名含「手册」「指南」「manual」等关键词时，自动识别为 Foundation 层级  

**代码与架构图：**

- `POST /api/ingest/code` — Python AST 代码投影  
- `POST /api/ingest/image` — 架构图视觉解析（需 Ollama 视觉模型）  

---

## L3 项目绑定（v2.4 新功能）

可将记忆锁定到当前项目上下文：

- 在 UI 中设置 **活动项目**（Active Project）  
- 带 `project_id` 的记忆在清空普通记忆时保留  
- 适合多项目并行时隔离认知上下文  

---

## Runtime BOOT（v2.4 新功能）

启动时 Gateway 自动执行 **BOOT** 流程：

1. 编译 `runtime/constitution/` → `data/runtime/constitution.bin`  
2. 加载 `runtime/policy/` 推理与合并策略  
3. 注入 Foundation 预置文档（含本手册）  
4. 准备对话引擎  

查看状态：`GET /v1/runtime/boot`

重新编译宪法（高级）：`POST /v1/runtime/recompile`

---

## 记忆整理与清空

| 操作 | 入口 / API | 说明 |
|------|------------|------|
| REM 深度睡眠 | `POST /v1/memory/rem-sleep` 或 UI | 空闲时剪枝噪声、压缩碎片 |
| 手动清空 | 侧栏 / `POST /api/memory/clear` | 默认保留 L3+ 与 Foundation |
| 提升到 L4 | 记忆面板「提升为基石」 | 将重要记忆升级为 Foundation |

清空记忆时，`keep_models: true` 可保留已配置的模型 API Key。

---

## 模型配置

### DeepSeek / OpenAI（云端）

1. 进入 **模型** 页  
2. 填入 API Key 与模型 ID（如 `deepseek-chat`）  
3. 保存后回到对话页测试  

### Ollama（本地，推荐隐私场景）

1. 安装 Ollama 并拉取模型（如 `ollama pull qwen2.5`）  
2. 默认地址 `127.0.0.1:11434`  
3. 可选环境变量 `OLLAMA_HOST` 修改地址  

---

## 数据存储位置

| 路径 | 内容 |
|------|------|
| `data/cnexus_personal_state.json` | 记忆快照与引擎状态 |
| `data/identity.key` | Ed25519 节点身份（勿泄露） |
| `data/runtime/constitution.bin` | 编译后的 Runtime 宪法 |

桌面版数据目录通常在用户配置目录下，由安装程序管理。

> 以上路径已在 `.gitignore` 中排除，**不会**随代码推送到 GitHub。

---

## 常见问题

**Q：一定要联网吗？**  
基础功能可离线使用；云端 AI 需要网络和 API Key。

**Q：代理软件导致连不上 AI？**  
关闭失效的系统代理，或在 Clash 等工具中关闭「系统代理」后重试。

**Q：聊天窗口滚动异常？**  
v2.3+ 已修复：消息在聊天区域内滚动，输入框固定在底部。

**Q：如何更新本手册？**  
安装新版本时，若 `runtime/foundation/` 中文件有更新，启动时会自动升级 Foundation 版本链；也可手动上传新版 Markdown。

**Q：桌面版与 Web 版区别？**  
功能相同；桌面版通过 Tauri 打包，自带嵌入式 Python 运行时，无需单独安装 Python。

---

## 快捷键与 API（开发者）

| 端点 | 说明 |
|------|------|
| `GET /api/status` | 系统状态 + 记忆图谱 |
| `POST /api/converse` | 六步认知对话 |
| `GET /v1/kernel/record/{trace_id}` | 决策回放 |
| `GET /v1/memory/foundation/versions` | Foundation 版本列表 |
| `POST /v1/memory/foundation/upgrade` | 手动升级 Foundation 文档 |

完整 API 见仓库 `README.md`。

---

## 版本历史摘要

| 版本 | 要点 |
|------|------|
| v2.3.0 | 修复聊天复读；记忆范围选择；上传加速；聊天区滚动修复 |
| v2.4.0 | Runtime BOOT；L3 项目绑定；L4 Foundation 版本链；桌面安装包；Ed25519 签名 |

---

## 支持与反馈

- 仓库：https://github.com/plusunm/CNexus2.0  
- 问题反馈：GitHub Issues  
- OpenClaw 技能：cnexus-cognitive-core  

感谢使用 CNexus 2.0 — **CNexus remembers what you think, and understands how you think.**
