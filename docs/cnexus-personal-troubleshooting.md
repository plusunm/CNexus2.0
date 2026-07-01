# CNexus 2.0 Personal — 故障自救与日志提取手册

> GA 临时支持文档 · 适用于 Windows 安装版与 `start_cnexus.bat` 浏览器模式  
> 网关默认端口：**7864**

---

## 1. 快速判断：我现在是什么状态？

| 现象 | 可能原因 | 优先操作 |
|------|----------|----------|
| 顶部黄色/红色横幅「本地网关未连接」 | sidecar 未启动或端口被占用 | 桌面版点 **重启网关**；或运行 `CNexus-restart.bat` |
| 横幅「分析已降级」 | 深度思考失败，已自动切换规则分析 | 可继续使用；若需深度分析，先恢复网关 |
| 浏览器能打开页面但 API 无数据 | 网关未运行或访问了错误端口 | 确认地址为 `http://127.0.0.1:7864` |
| 手机 LAN 能开页但无推理 | PC 防火墙拦截 7864 | 允许 `cnexus-runtime` / Python 通过防火墙 |
| 安装/升级失败提示端口冲突 | 旧版 :8000 或残留 Python 占 7864 | 见 [§3 清理残留进程](#3-清理残留进程) |
| 思考 tab 一直「分析中」 | 网关挂起或 LLM 超时 | 重启网关；检查 Ollama 是否运行 |

---

## 2. 一键恢复流程（推荐顺序）

### 2.1 桌面安装版（Tauri）

1. 打开悬浮条 → **本地服务** 面板  
2. 点击 **重启本地网关**（或顶部降级横幅中的 **重启网关**）  
3. 等待 5–10 秒后点 **重新检测**  
4. 仍失败 → 完全退出 CNexus（托盘/任务管理器结束 `cnexus-product.exe`）  
5. 双击安装目录或桌面的 **`CNexus-restart.bat`**（若存在）

### 2.2 浏览器 / 开发模式

1. 关闭所有 CNexus 窗口  
2. 在项目根目录运行：

```bat
start_cnexus.bat
```

3. 浏览器访问：`http://127.0.0.1:7864`

### 2.3 强制清理后冷启动

在 PowerShell 中（项目根目录）：

```powershell
.\scripts\kill-cnexus-runtime.ps1
# 然后重新启动桌面版或 start_cnexus.bat
```

---

## 3. 清理残留进程

安装程序与 `kill-cnexus-runtime.ps1` 会终止以下目标：

- **UI**：`CNexus.exe`、`cnexus-product.exe`、`cnexus-runtime.exe`
- **网关 Python**：命令行含 `app_v2.py`、`runtime-bundle` 或 `CNexus2.0`
- **端口**：**7864**（网关）、**3000**（开发前端，若存在）

手动检查端口占用：

```powershell
Get-NetTCPConnection -LocalPort 7864 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Get-Process -Id $_.OwningProcess }
```

---

## 4. 日志位置（提交工单时请附上）

| 文件 | 路径 | 内容 |
|------|------|------|
| 运行时冲突监控 | `%LOCALAPPDATA%\CNexus\data\runtime-conflict-monitor.log` | 安装/杀进程/端口冲突事件 |
| 网关 stderr | `%LOCALAPPDATA%\CNexus\data\runtime-api.stderr.log` | Python 网关启动与崩溃栈 |
| 用户数据目录 | `%LOCALAPPDATA%\CNexus\data\` | blocks、关系卡片等 |
| 预构建烟测报告 | `packaging\prebuild-rc\LATEST_SMOKE.txt` | 构建机 smoke gate 结果 |

打包日志给支持：

```powershell
$dest = "$env:USERPROFILE\Desktop\cnexus-logs-$(Get-Date -Format 'yyyyMMdd-HHmm')"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item "$env:LOCALAPPDATA\CNexus\data\runtime-*.log" $dest -ErrorAction SilentlyContinue
Copy-Item "$env:LOCALAPPDATA\CNexus\data\runtime-conflict-monitor.log" $dest -ErrorAction SilentlyContinue
Compress-Archive -Path "$dest\*" -DestinationPath "$dest.zip" -Force
Write-Host "已打包: $dest.zip"
```

---

## 5. 常见问题

### Q1：升级后一启动就闪退

- 原因多为旧进程占 **7864** 或残留 **:8000** 时代码冲突（已在 2.4.0+ 修复）  
- 操作：先 `kill-cnexus-runtime.ps1`，再覆盖安装或运行 `CNexus-restart.bat`

### Q2：`Failed to fetch` / 思考 tab 报错

- 确认网关：`http://127.0.0.1:7864/api/status` 应返回 JSON  
- Tauri 浮窗 API 固定走 `127.0.0.1:7864`（与 `tauri.localhost` 页面源无关）

### Q3：深度思考变慢或降级为规则分析

- 属 **C5 自动降级**，非致命错误  
- 恢复 Ollama + 网关后重试「开始思考」

### Q4：构建/发布前自检

```powershell
cd frontend
npm run prebuild:release
npm run tauri:build
# 或一键：
..\scripts\build-tauri-installer.ps1
```

---

## 6. 联系支持时请提供

1. 版本号（关于对话框或安装包文件名，如 `2.4.0`）  
2. 使用方式：桌面安装版 / 浏览器 / 手机 LAN  
3. §4 打包的日志 zip  
4. 复现步骤与截图（含顶部降级横幅文案）

---

*文档版本：与 CNexus 2.0 Personal GA 审计修复批次同步（B2/B1/C1/C5/C2）*
