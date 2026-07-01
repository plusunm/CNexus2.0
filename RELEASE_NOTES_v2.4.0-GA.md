# CNexus 2.0 Personal Edition — v2.4.0-GA 发布说明

> **GA 正式版**：安装稳定性、网关自愈、关系分析全链路、离线自救文档。

**发布日期：** 2026-07-01  
**仓库：** [github.com/plusunm/CNexus2.0](https://github.com/plusunm/CNexus2.0)  
**标签：** [v2.4.0-GA](https://github.com/plusunm/CNexus2.0/releases/tag/v2.4.0-GA)

---

## 一句话介绍

CNexus 2.0 是你电脑上的「第二大脑」——本地网关 `:7864`、桌面悬浮条、关系思考与时间线分析；本版重点解决**安装冲突、网关降级自愈、Tauri 浮窗崩溃**等 GA 阻塞项。

---

## 本版亮点

### 安装与发布门禁
- NSIS 安装脚本对齐 **端口 7864**（修复旧版 :8000 残留逻辑）
- `prebuild:release` 冒烟门禁含 **`POST /api/analyze`**
- `build-tauri-installer.ps1` 默认串联 release gate

### 网关韧性（C1/C2/C5）
- 浮窗/主界面 **降级横幅** + 「重启网关」「查看自救指南」
- 分析失败自动 **深度 → 快速 → 离线** 三级降级
- Tauri `restart_runtime_sidecar` 前端入口

### 关系分析
- 网关 `/api/analyze` 全链路（canonical schema + 卡片存储）
- 前端 **思考 / 时间线 / 卡片** Tab
- 微信聊天记录导入解析

### 路由修复
- Tauri `tauri.localhost` → API 固定 `127.0.0.1:7864`
- 手机 LAN 访问同源 API 修复

---

## 如何获取

### 方式一：从源码构建安装包（推荐开发者）

```powershell
git clone https://github.com/plusunm/CNexus2.0.git
cd CNexus2.0
git checkout v2.4.0-GA
.\scripts\build-tauri-installer.ps1
```

产出：`frontend\src-tauri\target\release\bundle\nsis\CNexus 2.0_2.4.0_x64-setup.exe`

### 方式二：仅运行 Web 网关

```bat
start_cnexus.bat
```

浏览器打开 http://127.0.0.1:7864

---

## 环境要求

| 项目 | 说明 |
|------|------|
| 操作系统 | Windows 10/11 x64 |
| Python | 3.10+（源码/开发模式） |
| 构建安装包 | VS Build Tools、Rust、NSIS、Node 18+ |
| 可选 | Ollama 本地模型 |

---

## 故障自救

见仓库文档：[docs/cnexus-personal-troubleshooting.md](docs/cnexus-personal-troubleshooting.md)

日志目录：`%LOCALAPPDATA%\CNexus\data`

---

## 已知限制（GA 后迭代）

- 关系卡片 server / localStorage 数据分裂（B3）
- Windows 安装包未 Authenticode 签名（C7）
- 外网手机无法直连 `:7864`（可用 LAN 或后续微信 Claw 通道）

---

## License

MIT
