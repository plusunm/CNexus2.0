# 🧠 CNexus 2.0 — Personal Cognitive OS

> CNexus turns your conversations into a living second brain — and your decisions into a traceable cognitive system.

**CNexus 不是一个 AI 聊天工具，而是一个"会进化的个人第二大脑系统"。**  
它只解决两件事：**记忆增强** × **认知辅助**。

---

## 🧩 ① 认知记忆增强 — Memory Augmentation

> 你的所有信息不会再"散掉"

CNexus 把你的输入变成：

- 📌 **结构化记忆** — 不再是文本，而是记忆单元
- 📌 **可检索知识节点** — 关键事件、抽象概念、决策背景
- 📌 **自动关联网络** — 信息和信息之间自动建立链接
- 📌 **长期演化认知** — 系统持续学习你关注什么

### 它替你做了什么？

**🧠 自动记住"你说过什么"**  
不只是保存聊天记录，而是提取关键事件、抽象概念、记录决策背景、保留上下文状态。

**🔗 自动建立"知识关联"**  
CNexus 会自动帮你回答：这件事和你之前说过的什么有关？这个决策和你过去的选择有什么模式？

**🧭 自动构建"你的认知地图"**  
你关注的主题结构、反复思考的领域、长期兴趣的演化路径 → 你的认知地图自动生长。

**🔁 自动压缩与整理记忆**  
类似大脑睡眠机制 —— 去重、提炼长期知识、删除噪声、强化重要概念。第二大脑不会爆炸，而是自我整理。

---

## 🧠 ② 认知辅助决策 — Cognitive Assistant

> 它不仅记住你，还"理解你怎么思考"

**🧭 决策过程可回放**  
每一次回答都有完整链路：输入 → 理解 → 判断 → 决策 → 输出 → 反思。  
你可以看到：我为什么这样判断？有没有更优路径？AI 从"黑箱"变成"思维记录器"。

**🧠 思维模式识别**  
系统逐渐识别你的重复决策模式、思维偏差、信息盲区。它帮你"看见自己"，而不是"回答问题"。

**⚡ 上下文持续增强**  
传统 AI 每次对话清空大脑。CNexus 每一次对话累积认知状态。你问的问题越来越贴合你，系统越来越懂你。

**🧩 长期目标辅助执行**  
当前目标状态、历史决策路径、相关记忆节点 → 帮你拆解复杂目标、追踪执行路径、避免重复决策。

---

## 🔥 一句话收敛

> **CNexus remembers what you think, and understands how you think.**

| 维度 | 能力 |
|---|---|
| 🧠 Personal Memory OS | 自动结构化信息、构建知识网络、防止碎片化 |
| 🧭 Cognitive Companion | 记录决策过程、识别思维模式、增强上下文、辅助目标执行 |

---

## 🚀 快速启动

```bash
pip install -r requirements.txt
python app_v2.py
```

默认访问 `http://localhost:7865`

---

## 📡 API

| 端点 | 说明 |
|---|---|
| `POST /api/converse` | 认知循环对话 |
| `GET /api/status` | 系统状态 + 记忆图谱 |
| `GET /v1/kernel/record/{trace_id}` | 执行追踪回放 |

---

## 🧱 项目结构

```
CNexus2.0/
├── app_v2.py          # HTTP Server (zero framework deps)
├── src/kernel/        # 6-step cognitive pipeline
│   ├── observe_reducer.py
│   ├── cognize_reducer.py
│   ├── decide_reducer.py
│   ├── speak_reducer.py
│   ├── store_reducer.py
│   ├── reflect_reducer.py
│   ├── block_store.py
│   └── state_snapshot.py
├── ui/                # Next.js static export (personal edition)
├── core_essence/      # Architecture design docs
└── specs/             # Full specification suite
```

---

## 📜 License

MIT License — free to use, modify, and extend.
