---
name: cnexus-cognitive-core
description: CNexus 2.0 Personal Cognitive OS — local second brain with 6-step loop, spreading activation, REM sleep, wormhole links, code/vision projection, JSON persistence, and memory clear API.
---

# CNexus 2.0 — Personal Cognitive OS

**GitHub:** https://github.com/plusunm/CNexus2.0

CNexus 2.0 is a **local-first personal second brain**, not a generic RAG chatbot. It turns conversations, documents, codebases, and architecture diagrams into a **living cognitive network** that persists, self-organizes, and evolves on your machine.

---

## What You Get (Application Layer)

### 🧠 Memory Augmentation

- **Structured memory units** — identity, goal, belief, episode tags instead of flat chat logs
- **Memory flow graph** — Canvas 2D factor network with activation glow and wormhole dashed links
- **Spreading activation** — after each turn, related nodes warm up; high-score fragments inject into the next reply
- **Wormhole protocol** — semantic cosine bridges between nodes without explicit physical links (Ollama / cloud embedding fallback)
- **REM deep sleep** — idle watchdog triggers synaptic pruning, LLM/heuristic compaction, causality re-anchor
- **Multimodal projection** — `POST /api/ingest/code` (stdlib AST) and `POST /api/ingest/image` (Ollama vision)
- **JSON persistence** — auto-save to `data/cnexus_personal_state.json`, restore on boot, graceful shutdown flush
- **One-click clear** — UI button + `POST /api/memory/clear` wipes memory while keeping model registry

### 🧭 Cognitive Companion

- **6-step loop** — OBSERVE → COGNIZE → DECIDE → SPEAK → STORE → REFLECT on every `/api/converse`
- **Trace replay** — `GET /v1/kernel/record/{trace_id}` for full decision chain
- **Hybrid inference** — Ollama local first; optional DeepSeek / OpenAI when keys are set
- **Live observability** — `GET /api/status` exposes emotion, goals, memory_items, activation scores, consolidation state

---

## Quick Start

```bash
git clone https://github.com/plusunm/CNexus2.0.git
cd CNexus2.0
python app_v2.py
# open http://127.0.0.1:7864
```

Windows: double-click `start_cnexus.bat`

**Requirements:** Python 3.10+. Core gateway uses **stdlib only**. Ollama is optional for chat, vision, and embeddings.

---

## Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/converse` | Cognitive dialogue loop |
| `GET /api/status` | System + memory graph + persistence |
| `POST /api/memory/clear` | Wipe memory snapshot |
| `POST /v1/memory/rem-sleep` | Trigger REM consolidation |
| `POST /api/ingest/code` | AST code graph projection |
| `POST /api/ingest/image` | Vision architecture projection |
| `GET /v1/kernel/record/{trace_id}` | Execution trace replay |

---

## Why CNexus 2.0?

If you want a **sovereign, local second brain** that:

- remembers *how* you think, not just *what* you said
- visualizes memory as a living graph
- compacts itself like sleep instead of bloating forever
- runs without cloud lock-in

…CNexus 2.0 is built for that.

---

## Install via OpenClaw

```bash
openclaw skills install @plusunm/cnexus-cognitive-core
```

Then clone the GitHub repo above for the full runtime + UI.

---

## Links

- **GitHub:** https://github.com/plusunm/CNexus2.0
- **Runtime:** http://127.0.0.1:7864
- **Stack:** Python stdlib gateway + Next.js static UI + Canvas 2D graph + Ollama (optional)

**CNexus 2.0 — Sovereign memory. Living metabolism. Your thoughts, persisted.**
