#!/usr/bin/env python3
"""Generate new app_ui.py with replacement SHELL_HTML and FLOAT_HTML."""

with open("D:/类脑记忆/CNexus2.0/app_ui.py", "r", encoding="utf-8") as f:
    full = f.read()

# Extract JS logic
shell_start_marker = "SHELL_HTML = r'''"
shell_start = full.find(shell_start_marker)
shell_content_start = shell_start + len(shell_start_marker)
idx_float_marker = full.find("FLOAT_HTML = r'''")
shell_content_end = full.rfind("'''", shell_content_start, idx_float_marker)
shell_content = full[shell_content_start:shell_content_end-3]

js_start = shell_content.find("<script>")
js_content_start = js_start + len("<script>")
js_end = shell_content.find("</script>", js_content_start)
js_logic = shell_content[js_content_start:js_end]

# Extract old float JS
idx_float_marker_inner = idx_float_marker + len("FLOAT_HTML = r'''")
float_content_end = full.find("'''", idx_float_marker_inner)
old_float = full[idx_float_marker_inner:float_content_end]

float_js_start = old_float.find("<script>")
float_js_content_start = float_js_start + len("<script>")
float_js_end = old_float.find("</script>", float_js_content_start)
float_js = old_float[float_js_content_start:float_js_end]

# Build new SHELL_HTML
# Based on original CNexus Platform rendered HTML, stripped of Next.js/RSC boilerplate
new_shell = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CNexus · 记忆流图</title>
<style>
/* CNexus2.0 UI styles — adapted from original CNexus Platform */
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#070b14;--surface:#111827;--surface2:#0c1220;--border:#243047;--text:#f1f5f9;--textMuted:#94a3b8;--textLight:#64748b;--accent:#3b82f6;--blue:#3b82f6;--blueSoft:rgba(59,130,246,0.18);--green:#22c55e;--greenSoft:rgba(34,197,94,0.12);--red:#f87171;--orange:#f59e0b;--orangeSoft:rgba(245,158,11,0.12);--purple:#a78bfa;--purpleSoft:rgba(167,139,250,0.12);--teal:#5eead4;--tealSoft:rgba(94,234,212,0.12);--chatBg:#0c1220;--fontMono:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;--fontSans:'PingFang SC','Noto Sans SC',Inter,system-ui,sans-serif}
html,body{height:100%}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px}
body{font-family:var(--fontSans);background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;font-size:13px;line-height:1.5}
a{text-decoration:none;color:inherit}
button{border:none;background:none;cursor:pointer;font-family:inherit;color:inherit}
input{font-family:inherit}

/* Layout */
.min-h-screen{min-height:100vh}
.flex{display:flex}
.flex-1{flex:1 1 0%}
.flex-col{flex-direction:column}
.shrink-0{flex-shrink:0}
.items-center{align-items:center}
.justify-center{justify-content:center}
.justify-between{justify-content:space-between}
.gap-1{gap:4px}.gap-1\\.5{gap:6px}.gap-2{gap:8px}.gap-2\\.5{gap:10px}.gap-3{gap:12px}.gap-5{gap:20px}
.px-2{padding-left:8px;padding-right:8px}
.px-2\\.5{padding-left:10px;padding-right:10px}
.px-3{padding-left:12px;padding-right:12px}
.px-4{padding-left:16px;padding-right:16px}
.py-2{padding-top:8px;padding-bottom:8px}
.py-2\\.5{padding-top:10px;padding-bottom:10px}
.py-3{padding-top:12px;padding-bottom:12px}
.py-4{padding-top:16px;padding-bottom:16px}
.py-5{padding-top:20px;padding-bottom:20px}
.p-0\\.5{padding:2px}.p-2{padding:8px}.p-2\\.5{padding:10px}.p-3{padding:12px}
.pl-3{padding-left:12px}.pr-4{padding-right:16px}
.mb-1{margin-bottom:4px}.mb-2{margin-bottom:8px}.mt-1{margin-top:4px}
.mt-auto{margin-top:auto}
.border{border:1px solid var(--border)}
.border-r{border-right:1px solid var(--border)}
.border-t{border-top:1px solid var(--border)}
.rounded-lg{border-radius:8px}
.rounded-xl{border-radius:12px}
.overflow-hidden{overflow:hidden}
.overflow-y-auto{overflow-y:auto}
.overflow-auto{overflow:auto}
.min-w-0{min-width:0}
.min-h-0{min-height:0}
.w-2{width:8px}.w-2\\.5{width:10px}.w-3\\.5{width:14px}.w-4{width:16px}.w-5{width:20px}.w-8{width:32px}.w-full{width:100%}
.h-2{height:8px}.h-2\\.5{height:10px}.h-3\\.5{height:14px}.h-4{height:16px}.h-5{height:20px}.h-8{height:32px}.h-full{height:100%}
.max-h-screen{max-height:100vh}
.block{display:block}
.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.text-\\[9px\\]{font-size:9px}.text-\\[10px\\]{font-size:10px}.text-\\[11px\\]{font-size:11px}
.text-xs{font-size:12px}.text-sm{font-size:13px}.text-lg{font-size:18px}
.font-medium{font-weight:500}.font-semibold{font-weight:600}.font-bold{font-weight:700}
.leading-tight{line-height:1.25}.leading-relaxed{line-height:1.5}
.uppercase{text-transform:uppercase}
.tracking-wider{letter-spacing:0.05em}
.text-left{text-align:left}
.relative{position:relative}
.absolute{position:absolute}
.top-4{top:16px}.left-4{left:16px}
.z-10{z-index:10}
.pointer-events-none{pointer-events:none}
.touch-none{touch-action:none}
.opacity-80{opacity:0.8}
.transition{transition:all 0.12s}
.shrink-0{flex-shrink:0}
.cursor-pointer{cursor:pointer}
.disabled\\:opacity-50:disabled{opacity:0.5}
.active\\:scale-95:active{transform:scale(0.95)}
.grid{display:grid}
.grid-cols-1{grid-template-columns:1fr}
.grid-cols-2{grid-template-columns:1fr 1fr}
.grid-rows-2{grid-template-rows:1fr 1fr}
.accent-cyan-400{accent-color:#22d3ee}

/* Mobile hide sidebar */
@media(max-width:1023px){.hidden\\.lg\\:flex{display:none}}
@media(min-width:1024px){
  .lg\\:flex{display:flex}
  .lg\\:hidden{display:none}
  .lg\\:h-full{height:100%}
  .lg\\:min-h-0{min-height:0}
  .lg\\:border-t-0{border-top:none}
  .lg\\:border-l{border-left:1px solid var(--border)}
  .lg\\:py-5{padding-top:20px;padding-bottom:20px}
  .lg\\:pl-4{padding-left:16px}
  .lg\\:pr-6{padding-right:24px}
  .lg\\:grid-cols-\\[minmax\\(0\\,1fr\\)_var\\(--graph-controls-w\\)\\]{grid-template-columns:minmax(0,1fr) var(--graph-controls-w)}
}
@media(min-width:640px){
  .sm\\:flex-row{flex-direction:row}
  .sm\\:items-start{align-items:flex-start}
  .sm\\:justify-between{justify-content:space-between}
}

/* Sidebar nav items */
.nav-item{background-color:transparent;color:#94a3b8;border:1px solid transparent}
.nav-item:hover{opacity:1}

/* Graph view shell */
.graph-view-shell{display:grid;grid-template-columns:minmax(0,1fr) min(480px,calc(min(68vh,600px)*0.75));border:1px solid var(--border);border-radius:12px;overflow:hidden;height:min(68vh,600px);width:100%}
@media(max-width:1023px){.graph-view-shell{grid-template-columns:1fr;height:auto}}
.graph-view-shell canvas{width:100%;height:100%;display:block}

/* Controls panel sections */
.gv-section{border:1px solid var(--border);border-radius:8px;padding:8px;display:flex;flex-direction:column;overflow:hidden;background:#0c1220}
.gv-sec-hdr{width:100%;display:flex;align-items:center;gap:4px;text-align:left;font-size:10px;font-weight:600;margin-bottom:4px;flex-shrink:0;cursor:pointer;color:var(--text);border:none;background:none;padding:0}
.gv-chev{display:inline-block;transition:transform .2s;width:10px;font-size:8px}
.gv-chev.open{transform:rotate(0deg)}
.gv-sec-body{flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;justify-content:center;gap:2px}
.gv-search{width:100%;padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:9px;outline:none;margin-bottom:6px}
.gv-toggle{display:flex;align-items:center;justify-content:space-between;font-size:9px;padding:3px 0;cursor:pointer;color:var(--textMuted)}
.gv-switch{width:28px;height:14px;border-radius:7px;position:relative;flex-shrink:0;border:none;cursor:pointer;background:var(--border);padding:0;transition:background .2s}
.gv-switch.on{background:#3b82f6}
.gv-switch span{position:absolute;top:1.5px;width:11px;height:11px;border-radius:50%;background:#fff;left:1.5px;transition:left .2s}
.gv-switch.on span{left:14.5px}
.gv-groups{list-style:none;padding:0;margin:0;flex:1;overflow-y:auto}
.gv-groups li{display:flex;align-items:center;gap:4px;font-size:9px;color:var(--textMuted);padding:2px 0}
.gv-groups li span:nth-child(2){flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text)}
.gv-swatch{width:8px;height:8px;border-radius:50%;flex-shrink:0;display:inline-block}
.gv-gcount{margin-left:auto;flex-shrink:0}
.gv-slider-row{display:block;margin-bottom:6px;font-size:9px}
.gv-slider-row:last-child{margin-bottom:0}
.gv-slider-labels{display:flex;justify-content:space-between;margin-bottom:2px;color:var(--textMuted);font-size:9px}
.gv-slider-labels span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:4px}
.gv-slider-labels span:last-child{flex-shrink:0}
.gv-slider-row input[type=range]{width:100%;accent-color:#22d3ee;height:3px;margin:2px 0}
.gv-anim-btn{width:100%;padding:5px 0;border-radius:6px;border:none;font-size:9px;font-weight:500;cursor:pointer;margin-top:2px}

/* Flex helpers for controls panel */
.gv-grid{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:8px;min-width:0;width:100%;height:100%;grid-template-areas:'f g' 'd r'}
</style>
</head>
<body style="background-color:#070b14;color:#f1f5f9;font-family:'PingFang SC','Noto Sans SC',Inter,system-ui,sans-serif;">
<div class="min-h-screen flex" style="background-color:#070b14;color:#f1f5f9;background-image:radial-gradient(at 100% 0%,rgba(167,139,250,0.14) 0%,transparent 40%),radial-gradient(at 0% 100%,rgba(59,130,246,0.14) 0%,transparent 35%);">

<!-- Sidebar - desktop only -->
<aside class="hidden lg:flex w-full max-w-[220px] shrink-0 flex-col border-r px-4 py-5 gap-5 overflow-y-auto max-h-screen" style="border-color:#243047;background-color:#111827;">
  <div class="flex items-center gap-3">
    <div class="rounded-xl flex items-center justify-center shrink-0" style="width:40px;height:40px;background:linear-gradient(135deg,#3b82f6,#a78bfa);box-shadow:0 6px 20px rgba(47,107,255,0.35);">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:21px;height:21px;color:#fff;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
    </div>
    <div>
      <p class="text-sm font-semibold" style="color:#f1f5f9;">CNexus</p>
      <p class="text-[11px]" style="color:#94a3b8;">运行时观测</p>
    </div>
  </div>

  <div class="rounded-xl p-3 border" style="border-color:#243047;background-color:#0c1220;">
    <div class="flex items-center gap-1.5 min-w-0 mb-2 overflow-hidden">
      <span class="w-2 h-2 rounded-full shrink-0" id="sidebar-dot" style="background-color:#22c55e;"></span>
      <span class="text-xs font-medium shrink-0" style="color:#f1f5f9;" id="sidebar-status">就绪</span>
      <span class="text-[10px] shrink-0" style="color:#64748b;">·</span>
      <span class="font-medium truncate text-[10px]" style="color:#94a3b8;" id="sidebar-llm">Ollama</span>
    </div>
    <p class="text-[11px] leading-relaxed" style="color:#94a3b8;" id="sidebar-health">系统状态: 运行中</p>
  </div>

  <div class="space-y-2">
    <p class="text-[10px] uppercase tracking-wider" style="color:#64748b;">视图</p>
    <div class="space-y-1">
      <a class="nav-item w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" href="#" onclick="switchView('overview');return false" style="border:1px solid transparent;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0"><path d="M12 7v14"></path><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"></path></svg>
        <span class="min-w-0"><span class="block text-xs leading-tight">认知教学</span><span class="block text-[10px] leading-tight" style="color:#94a3b8;">人类叙事</span></span>
      </a>
      <a class="nav-item w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" href="#" onclick="switchView('debugger');return false" style="border:1px solid transparent;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"></path></svg>
        <span class="min-w-0"><span class="block text-xs leading-tight">旧版调试器</span><span class="block text-[10px] leading-tight" style="color:#94a3b8;">GTBS 兼容视图</span></span>
      </a>
      <a class="nav-item w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition font-medium" id="nav-flow-btn" href="#" onclick="switchView('flow');return false" style="background-color:rgba(59,130,246,0.18);color:#5eead4;border:1px solid #243047;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0"><line x1="6" x2="6" y1="3" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>
        <span class="min-w-0"><span class="block text-xs leading-tight" style="color:#5eead4;">记忆流图</span><span class="block text-[10px] leading-tight" style="color:#94a3b8;">关联网络</span></span>
      </a>
      <a class="nav-item w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" href="#" onclick="switchView('token');return false" style="border:1px solid transparent;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0"><circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h1v4"></path><path d="m16.71 13.88.7.71-2.82 2.82"></path></svg>
        <span class="min-w-0"><span class="block text-xs leading-tight">算力观测</span><span class="block text-[10px] leading-tight" style="color:#94a3b8;">总览 · 事件 · 分布 · 归因</span></span>
      </a>
      <a class="nav-item w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" href="#" onclick="switchView('summary');return false" style="border:1px solid transparent;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
        <span class="min-w-0"><span class="block text-xs leading-tight">运行摘要</span><span class="block text-[10px] leading-tight" style="color:#94a3b8;">CSE 叙事 · 运行脉搏</span></span>
      </a>
      <a class="nav-item w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" href="#" onclick="switchView('workbench');return false" style="border:1px solid transparent;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" x2="20" y1="19" y2="19"></line></svg>
        <span class="min-w-0"><span class="block text-xs leading-tight">工作台</span><span class="block text-[10px] leading-tight" style="color:#94a3b8;">对话 · 建议 · 上传</span></span>
      </a>
    </div>
  </div>
  <div class="mt-auto flex items-start gap-2 text-[11px]" style="color:#64748b;">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5 shrink-0 mt-0.5" style="color:#5eead4;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
    <span>记忆关联网络 · 图谱视图</span>
  </div>
</aside>

<!-- Main content -->
<div class="flex-1 flex flex-col min-w-0">
  <!-- Mobile header -->
  <header class="lg:hidden flex items-center justify-between px-4 py-3 border-b shrink-0" style="border-color:#243047;background-color:#111827;">
    <div>
      <p class="text-sm font-semibold" style="color:#f1f5f9;">CNexus Neural Flow · 记忆流图</p>
      <p class="text-[11px]" style="color:#94a3b8;">关联网络 · 力导向图 · 参数可调</p>
    </div>
    <button type="button" id="mobile-refresh-btn" class="p-2 rounded-lg border transition active:scale-95" style="border-color:#243047;">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path><path d="M8 16H3v5"></path></svg>
    </button>
  </header>

  <main class="flex-1 overflow-auto w-full py-4 lg:py-5 pl-3 pr-4 lg:pl-4 lg:pr-6 max-w-none">
    <!-- Flow view content -->
    <div class="space-y-4 w-full min-w-0 max-w-none">
      <header class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5" style="color:#a78bfa;"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"></path></svg>
            <h1 class="text-xl font-bold" style="color:#f1f5f9;">Neural Flow · 记忆流图</h1>
          </div>
          <p class="text-sm mt-1" style="color:#94a3b8;">Graph view · force-directed memory network / 力导向记忆网络 · 右侧可调参数</p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button type="button" id="sync-btn" class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border" style="border-color:#3b82f6;color:#3b82f6;background-color:rgba(59,130,246,0.14);">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path><path d="M8 16H3v5"></path></svg>
            Sync / 同步
          </button>
        </div>
      </header>

      <!-- Graph view shell -->
      <div class="graph-view-shell" style="--graph-panel-h:min(68vh,600px);--graph-controls-w:min(480px,calc(min(68vh,600px)*0.75));">
        <!-- Canvas area -->
        <div class="relative" style="background-color:#070b14;min-height:300px;">
          <div class="absolute top-4 left-4 z-10 pointer-events-none">
            <p class="text-lg font-semibold" style="color:#f1f5f9;">Graph view</p>
            <p class="text-xs" style="color:#94a3b8;">Neural flow · memory factor network / 记忆流图 · 关联网络</p>
          </div>
          <canvas id="flow-canvas" class="touch-none" style="width:100%;height:100%;display:block;"></canvas>
        </div>
        <!-- Controls panel -->
        <div class="min-h-[240px] border-t lg:border-t-0 lg:border-l" style="border-color:#243047;">
          <aside id="flow-controls" style="min-width:0;width:100%;height:100%;padding:10px;overflow:hidden;box-sizing:border-box;background-color:rgba(17,24,39,0.933);"></aside>
        </div>
      </div>
    </div>
  </main>
</div>
</div>

<script>
""" + js_logic + r"""
</script>
</body>
</html>"""

# Build new FLOAT_HTML (keep existing, slightly cleaned)
new_float = r"""<!DOCTYPE html>
<html lang=zh-CN>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>CNexus 浮标</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#060912;--surface:#0d1117;--surface2:#161b22;--border:#21262d;--text:#e1e4e8;--textMuted:#8b