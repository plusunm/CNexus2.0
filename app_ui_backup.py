#!/usr/bin/env python3
"""CNexus 2.0 Web UI -- full Shell + Float frontend"""

import os, sys, json, time, math, traceback, cgi, tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src import CNexusOSCoreEngine

_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = CNexusOSCoreEngine()
        _engine.initialize()
    return _engine

def api_status():
    e = get_engine(); k = e.kernel
    st = k.status() if hasattr(k, "status") else {"active": False}
    st["engine_initialized"] = e.is_initialized
    st["memory_count"] = k.state.get("memory_count", 0)
    st["execution_count"] = k.state.get("execution_count", 0)
    st["current_iteration"] = k.cog.get("iteration", 0)
    return st

def api_converse(text):
    e = get_engine()
    try:
        reply = e.handle_request(text)
    except Exception as ex:
        reply = '[stub] 已收到: ' + text[:80]
        # Still try to write to memory_store directly so memory_dump works
        k = e.kernel
        import hashlib
        mem_id = hashlib.md5(text.encode()).hexdigest()[:8]
        k.memory_store[mem_id] = {
            'block_id': mem_id, 'type': 'memory_block',
            'skill': 'upload', 'input': text,
            'content': {'input': text, 'skill': 'upload', 'output_hash': ''},
            'metadata': {'timestamp_boot': k.state.get('boot_time', 0), 'iteration': k.cog.get('iteration', 0), 'strategy': 'upload'},
            'weight': 0.7, 'decay_factor': 1.0, 'reference_count': 0
        }
        k.state['memory_count'] = k.state.get('memory_count', 0) + 1
    k = e.kernel
    return {'reply':reply,'cog_state':k.cog.get('cog_state',{}),
        'memory_count':k.state.get('memory_count',0),
        'execution_count':k.state.get('execution_count',0),
        'iteration':k.cog.get('iteration',0),
        'trace':k.cog.get('trace',[]),
        'execution_history':k.execution_history[-5:] if hasattr(k,'execution_history') else []}

def api_memory_dump(limit=20):
    e = get_engine(); k = e.kernel
    if hasattr(k,'memory_dump'): return k.memory_dump(limit)
    keys=sorted(k.memory_store.keys(),key=lambda kk:kk,reverse=True); entries=[]
    for kk in keys[:limit]:
        blk=k.memory_store[kk]; entries.append({
            'block_id':blk.get('block_id',kk),'type':blk.get('type',''),
            'skill':blk.get('content',{}).get('skill',''),
            'input':blk.get('content',{}).get('input','')[:60],
            'weight':blk.get('weight',0),
            'iteration':blk.get('metadata',{}).get('iteration',0)})
    return {'total_entries':len(k.memory_store),'entries':entries}

def api_exec_trace(limit=30):
    e=get_engine(); k=e.kernel
    h=getattr(k,'execution_history',[]); return {'traces':h[-limit:],'total':len(h)}

def api_cog_state():
    e=get_engine(); k=e.kernel
    return {'cog_state':k.cog.get('cog_state',{}),
        'state':k.state,'iteration':k.cog.get('iteration',0),
        'skills_loaded':len(getattr(k,'skills',{})),
        'skill_registry':list(getattr(k,'skill_registry',{}).keys())[:12],
        'execution_history_count':len(getattr(k,'execution_history',[]))}

def api_skill_graph():
    e=get_engine(); k=e.kernel
    return {'skills':list(k.skills.keys()),
        'skill_graph':k.skill_graph,'classification':k.classification}

def api_reset():
    e=get_engine(); k=e.kernel
    return k.reset() if hasattr(k,'reset') else {'status':'error'}

# === SHELL_HTML ===


SHELL_HTML = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CNexus · 记忆流图</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#070b14;--surface:#111827;--surface2:#0c1220;--border:#243047;--text:#f1f5f9;--textMuted:#94a3b8;--textLight:#64748b;--accent:#3b82f6;--blue:#3b82f6;--blueSoft:rgba(59,130,246,0.18);--green:#22c55e;--greenSoft:rgba(34,197,94,0.12);--red:#f87171;--orange:#f59e0b;--orangeSoft:rgba(245,158,11,0.12);--purple:#a78bfa;--purpleSoft:rgba(167,139,250,0.12);--teal:#5eead4;--tealSoft:rgba(94,234,212,0.12);--chatBg:#0c1220;--fontMono:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;--fontSans:'PingFang SC','Noto Sans SC',Inter,system-ui,sans-serif}
html,body{height:100%}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px}
body{font-family:var(--fontSans);background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;font-size:13px;line-height:1.5}
a{text-decoration:none;color:inherit}
button{cursor:pointer;font-family:inherit}
input{font-family:inherit}
.hidden{display:none}
.flex{display:flex}
.flex-1{flex:1 1 0%}
.flex-col{flex-direction:column}
.shrink-0{flex-shrink:0}
.items-center{align-items:center}
.justify-center{justify-content:center}
.justify-between{justify-content:space-between}
.gap-1{gap:4px}.gap-1\\.5{gap:6px}.gap-2{gap:8px}.gap-2\\.5{gap:10px}.gap-3{gap:12px}.gap-5{gap:20px}
.px-2\\.5{padding-left:10px;padding-right:10px}.px-3{padding-left:12px;padding-right:12px}
.px-4{padding-left:16px;padding-right:16px}
.py-2{padding-top:8px;padding-bottom:8px}.py-2\\.5{padding-top:10px;padding-bottom:10px}
.py-3{padding-top:12px;padding-bottom:12px}.py-4{padding-top:16px;padding-bottom:16px}
.py-5{padding-top:20px;padding-bottom:20px}
.p-2{padding:8px}.p-2\\.5{padding:10px}.p-3{padding:12px}
.pl-3{padding-left:12px}.pr-4{padding-right:16px}
.mb-1{margin-bottom:4px}.mb-2{margin-bottom:8px}.mt-1{margin-top:4px}.mt-auto{margin-top:auto}
.border{border:1px solid var(--border)}.border-r{border-right:1px solid var(--border)}.border-t{border-top:1px solid var(--border)}
.rounded-lg{border-radius:8px}.rounded-xl{border-radius:12px}
.overflow-hidden{overflow:hidden}.overflow-y-auto{overflow-y:auto}.overflow-auto{overflow:auto}
.min-w-0{min-width:0}.min-h-0{min-height:0}
.w-2{width:8px}.w-2\\.5{width:10px}.w-3\\.5{width:14px}.w-4{width:16px}.w-5{width:20px}.w-8{width:32px}.w-full{width:100%}
.h-2{height:8px}.h-2\\.5{height:10px}.h-3\\.5{height:14px}.h-4{height:16px}.h-5{height:20px}.h-8{height:32px}.h-full{height:100%}
.max-h-screen{max-height:100vh}
.block{display:block}
.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.text-\\[9px\\]{font-size:9px}.text-\\[10px\\]{font-size:10px}.text-\\[11px\\]{font-size:11px}
.text-xs{font-size:12px}.text-sm{font-size:13px}.text-lg{font-size:18px}
.font-medium{font-weight:500}.font-semibold{font-weight:600}.font-bold{font-weight:700}
.leading-tight{line-height:1.25}.leading-relaxed{line-height:1.5}
.uppercase{text-transform:uppercase}.tracking-wider{letter-spacing:0.05em}
.relative{position:relative}.absolute{position:absolute}
.top-4{top:16px}.left-4{left:16px}.z-10{z-index:10}
.pointer-events-none{pointer-events:none}.touch-none{touch-action:none}
.opacity-80{opacity:0.8}.transition{transition:all 0.12s}
.grid{display:grid}.grid-cols-1{grid-template-columns:1fr}.grid-cols-2{grid-template-columns:1fr 1fr}.grid-rows-2{grid-template-rows:1fr 1fr}
.accent-cyan-400{accent-color:#22d3ee}
@media(min-width:640px){
  .sm\\:flex-row{flex-direction:row}.sm\\:items-start{align-items:flex-start}.sm\\:justify-between{justify-content:space-between}
}
@media(min-width:1024px){
  .lg\\:flex{display:flex}.lg\\:hidden{display:none}.lg\\:h-full{height:100%}
  .lg\\:min-h-0{min-height:0}.lg\\:border-t-0{border-top:none}.lg\\:border-l{border-left:1px solid var(--border)}
  .lg\\:py-5{padding-top:20px;padding-bottom:20px}.lg\\:pl-4{padding-left:16px}.lg\\:pr-6{padding-right:24px}
}
@media(max-width:1023px){.hidden\\.lg\\:flex{display:none}}

.graph-view-shell{border:1px solid var(--border);border-radius:12px;overflow:hidden;width:100%}
.gv-section{border:1px solid var(--border);border-radius:8px;padding:8px;display:flex;flex-direction:column;overflow:hidden;background:#0c1220}
.gv-sec-hdr{width:100%;display:flex;align-items:center;gap:4px;text-align:left;font-size:10px;font-weight:600;margin-bottom:4px;flex-shrink:0;cursor:pointer;color:var(--text);border:none;background:none;padding:0}
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
.gv-grid{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:8px;min-width:0;width:100%;height:100%}
</style>
</head>
<body style="background-color:#070b14;color:#f1f5f9;font-family:'PingFang SC','Noto Sans SC',Inter,system-ui,sans-serif;">
<div class="flex" style="min-height:100vh;background-color:#070b14;background-image:radial-gradient(at 100% 0%,rgba(167,139,250,0.14) 0%,transparent 40%),radial-gradient(at 0% 100%,rgba(59,130,246,0.14) 0%,transparent 35%);">

<!-- Sidebar -->
<aside class="hidden lg:flex flex-col" style="width:220px;flex-shrink:0;border-right:1px solid #243047;padding:20px 16px;gap:20px;overflow-y:auto;max-height:100vh;background-color:#111827;">
  <!-- Brand -->
  <div class="flex items-center gap-3">
    <div style="width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0;background:linear-gradient(135deg,#3b82f6,#a78bfa);box-shadow:0 6px 20px rgba(47,107,255,0.35);">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:21px;height:21px;color:#fff;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
    </div>
    <div>
      <p style="font-size:13px;font-weight:600;color:#f1f5f9;">CNexus</p>
      <p style="font-size:11px;color:#94a3b8;">运行时观测</p>
    </div>
  </div>

  <!-- Status card -->
  <div style="border-radius:12px;padding:12px;border:1px solid #243047;background-color:#0c1220;">
    <div style="display:flex;align-items:center;gap:6px;min-width:0;margin-bottom:8px;overflow:hidden;">
      <span id="sidebar-dot" style="width:8px;height:8px;border-radius:50%;flex-shrink:0;background-color:#22c55e;"></span>
      <span style="font-size:12px;font-weight:500;flex-shrink:0;color:#f1f5f9;" id="sidebar-status">就绪</span>
      <span style="font-size:10px;color:#64748b;">·</span>
      <span style="font-size:10px;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" id="sidebar-llm">Ollama</span>
    </div>
    <p style="font-size:11px;line-height:1.5;color:#94a3b8;" id="sidebar-health">系统状态: 运行中</p>
  </div>

  <!-- Nav -->
  <div style="gap:8px;">
    <p style="font-size:10px;text-transform:uppercase;letter-spacing:0.05em;color:#64748b;margin-bottom:8px;">视图</p>
    <div style="gap:4px;">
      <a href="#" onclick="switchView('overview');return false" class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" style="border:1px solid transparent;color:#94a3b8;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;flex-shrink:0;"><path d="M12 7v14"></path><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"></path></svg>
        <span style="min-width:0;"><span class="block text-xs leading-tight">认知教学</span><span style="font-size:10px;color:#94a3b8;">人类叙事</span></span>
      </a>
      <a href="#" onclick="switchView('debugger');return false" class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" style="border:1px solid transparent;color:#94a3b8;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;flex-shrink:0;"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"></path></svg>
        <span style="min-width:0;"><span class="block text-xs leading-tight">旧版调试器</span><span style="font-size:10px;color:#94a3b8;">GTBS 兼容视图</span></span>
      </a>
      <a href="#" onclick="switchView('flow');return false" id="nav-flow-btn" class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition font-medium" style="background-color:rgba(59,130,246,0.18);color:#5eead4;border:1px solid #243047;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;flex-shrink:0;"><line x1="6" x2="6" y1="3" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><path d="M18 9a9 9 0 0 1-9 9"></path></svg>
        <span style="min-width:0;"><span class="block text-xs leading-tight" style="color:#5eead4;">记忆流图</span><span style="font-size:10px;color:#94a3b8;">关联网络</span></span>
      </a>
      <a href="#" onclick="switchView('token');return false" class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" style="border:1px solid transparent;color:#94a3b8;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;flex-shrink:0;"><circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h1v4"></path><path d="m16.71 13.88.7.71-2.82 2.82"></path></svg>
        <span style="min-width:0;"><span class="block text-xs leading-tight">算力观测</span><span style="font-size:10px;color:#94a3b8;">总览 · 事件 · 分布 · 归因</span></span>
      </a>
      <a href="#" onclick="switchView('summary');return false" class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" style="border:1px solid transparent;color:#94a3b8;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;flex-shrink:0;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
        <span style="min-width:0;"><span class="block text-xs leading-tight">运行摘要</span><span style="font-size:10px;color:#94a3b8;">CSE 叙事 · 运行脉搏</span></span>
      </a>
      <a href="#" onclick="switchView('workbench');return false" class="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition opacity-80" style="border:1px solid transparent;color:#94a3b8;">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;flex-shrink:0;"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" x2="20" y1="19" y2="19"></line></svg>
        <span style="min-width:0;"><span class="block text-xs leading-tight">工作台</span><span style="font-size:10px;color:#94a3b8;">对话 · 建议 · 上传</span></span>
      </a>
    </div>
  </div>

  <div class="flex items-start gap-2" style="margin-top:auto;font-size:11px;color:#64748b;">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;flex-shrink:0;margin-top:2px;color:#5eead4;"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"></path><path d="M20 3v4"></path><path d="M22 5h-4"></path><path d="M4 17v2"></path><path d="M5 18H3"></path></svg>
    <span>记忆关联网络 · 图谱视图</span>
  </div>
</aside>

<!-- Main content -->
<div class="flex-1 flex flex-col" style="min-width:0;">
  <!-- Mobile header -->
  <header class="lg:hidden flex items-center justify-between" style="padding:12px 16px;border-bottom:1px solid #243047;flex-shrink:0;background-color:#111827;">
    <div>
      <p style="font-size:13px;font-weight:600;color:#f1f5f9;">CNexus Neural Flow · 记忆流图</p>
      <p style="font-size:11px;color:#94a3b8;">关联网络 · 力导向图 · 参数可调</p>
    </div>
    <button type="button" id="mobile-refresh-btn" style="padding:8px;border-radius:8px;border:1px solid #243047;">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px;"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path><path d="M8 16H3v5"></path></svg>
    </button>
  </header>

  <main style="flex:1;overflow:auto;padding:16px 16px 20px 12px;">
    <div style="gap:16px;">
      <!-- Header row -->
      <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between" style="gap:12px;">
        <div>
          <div class="flex items-center gap-2" style="flex-wrap:wrap;">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:20px;height:20px;color:#a78bfa;"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"></path></svg>
            <h1 style="font-size:20px;font-weight:700;color:#f1f5f9;">Neural Flow · 记忆流图</h1>
          </div>
          <p style="font-size:13px;margin-top:4px;color:#94a3b8;">Graph view · force-directed memory network / 力导向记忆网络 · 右侧可调参数</p>
        </div>
        <div class="flex items-center gap-2" style="flex-shrink:0;">
          <button type="button" id="sync-btn" style="display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:8px;font-size:11px;border:1px solid #3b82f6;color:#3b82f6;background-color:rgba(59,130,246,0.14);">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path><path d="M8 16H3v5"></path></svg>
            Sync / 同步
          </button>
        </div>
      </div>

      <!-- Graph view shell -->
      <div class="graph-view-shell" style="display:grid;grid-template-columns:minmax(0,1fr) min(480px,calc(min(68vh,600px)*0.75));height:min(68vh,600px);">
        <!-- Canvas area -->
        <div class="relative" style="background-color:#070b14;min-height:0;">
          <div style="position:absolute;top:16px;left:16px;z-index:10;pointer-events:none;">
            <p style="font-size:18px;font-weight:600;color:#f1f5f9;">Graph view</p>
            <p style="font-size:12px;color:#94a3b8;">Neural flow · memory factor network / 记忆流图 · 关联网络</p>
          </div>
          <canvas id="flow-canvas" class="touch-none" style="width:100%;height:100%;display:block;"></canvas>
        </div>
        <!-- Controls panel -->
        <div style="border-left:1px solid #243047;min-height:240px;overflow:hidden;">
          <aside id="flow-controls" style="padding:10px;overflow:hidden;height:100%;box-sizing:border-box;background-color:rgba(17,24,39,0.933);"></aside>
        </div>
      </div>
    </div>
  </main>
</div>
</div>

<script>

var API='';
var VIEW='overview',TOK_TAB='overview',WB_MODE='ask',DU_LAYER='experience',DU_FILES=[];
function esc(s){if(!s)return'';var d=document.createElement('div');d.textContent=typeof s==='string'?s:JSON.stringify(s);return d.innerHTML}
function $(id){return document.getElementById(id)}
async function api(path){try{var r=await fetch(API+path);return await r.json()}catch(e){return null}}
function switchView(v){
  VIEW=v;
  document.querySelectorAll('.nav-item').forEach(function(n){n.classList.toggle('active',n.dataset.view===v)});
  document.querySelectorAll('.panel').forEach(function(p){p.classList.toggle('active',p.id==='panel-'+v)});
  var titles={overview:['总览','引擎状态 · 实时监控'],debugger:['诊断器','Spine 事件 · 内核诊断'],flow:['记忆流图','因子链图 · 记忆图谱'],token:['算力观测','消耗统计 · 执行归因'],summary:['运行摘要','CSE 叙事 · 状态观测'],workbench:['工作台','对话 · 建议 · 上传']};
  $('page-title').textContent=titles[v][0];$('page-hint').textContent=titles[v][1];
  var hints={overview:'认知教学 · 探索系统能力',debugger:'诊断内核状态 · 查看认知追踪',flow:'记忆流图 · 因子关联可视化',token:'算力消耗与执行归因分析',summary:'CSE 叙事 · 人格意向观测',workbench:'对话 · 今日建议 · 批量上传'};
  $('sidebar-hint-text').textContent=hints[v];
  $('sidebar-status').textContent='活跃';
  $('sidebar-dot').className='status-dot green';
  if(v==='debugger')loadDebugger();if(v==='flow')drawFlowGraph();if(v==='token')loadTokenData();
  if(v==='summary')loadSummaryData();if(v==='workbench')loadRecommendations();
}
function refreshAll(){pollStatus();if(VIEW==='token')loadTokenData();if(VIEW==='flow')drawFlowGraph();if(VIEW==='debugger')loadDebugger();if(VIEW==='summary')loadSummaryData();if(VIEW==='workbench')loadRecommendations();}
function switchDataSrc(){$('sidebar-status').textContent='切换中';$('sidebar-dot').className='status-dot orange';setTimeout(refreshAll,500)}

async function pollStatus(){
  var d=await api('/api/status');
  if(!d){$('sidebar-dot').className='status-dot red';$('sidebar-status').textContent='断开';$('sidebar-health').textContent='系统状态: 离线';return}
  $('sidebar-dot').className='status-dot green';
  $('sidebar-status').textContent='就绪';
  var s=d.status||d.engine_status||'运行中';
  $('sidebar-health').textContent='系统状态: '+s;
  var cs=d.cog_state||d;
  if(cs.accumulated_weight!==undefined)$('cog-belief').textContent=parseFloat(cs.accumulated_weight).toFixed(3);
  if(cs.active_intent)$('cog-intent').textContent=cs.active_intent;
  if(cs.iteration!==undefined)$('cog-iter').textContent=cs.iteration;
  if(cs.execution_count!==undefined)$('cog-exec').textContent=cs.execution_count;
  if(d.memory_count!==undefined)$('cog-memory').textContent=d.memory_count;
  if(VIEW==='overview')renderOverview(d);
}

function renderOverview(d){
  if(!d)return;
  var memCount=d.memory_count||d.memories||0, execCount=d.execution_count||0, iter=d.cog_state?.iteration||0;
  var uptime=d.uptime||d.runtime_seconds||0;
  var h=Math.floor(uptime/3600),m=Math.floor((uptime%3600)/60),s=Math.floor(uptime%60);
  var uptimeStr=h+'h '+m+'m '+s+'s';
  var items=[
    ['引擎','Engine',d.engine_status||'Active','green'],
    ['内核活跃','Kernel','活跃 ('+(d.active_skills||d.skills_loaded||0)+'/10)','blue'],
    ['技能加载','Skills',(d.skills_loaded||0)+'/'+(d.skills_total||10),'orange'],
    ['执行次数','Execs',execCount,'purple'],
    ['记忆块数','Memory',memCount,'teal'],
    ['当前迭代','Iter',iter,'blue'],
    ['运行时间','Uptime',uptimeStr,'green']
  ];
  $('overview-stats').innerHTML=items.map(function(it){return '<div class="stat-card"><div class="stat-label">'+it[0]+'<br><span style="color:#555">'+it[1]+'</span></div><div class="stat-value '+it[3]+'">'+it[2]+'</div></div>'}).join('');
}

async function loadDebugger(){
  var d=await api('/api/cog_state');
  $('cog-debug').textContent=d?JSON.stringify(d,null,2):'No data';
  filterDebug();
}
function filterDebug(){
  var q=$('debug-filter').value.toLowerCase();
  if(!q){$('cog-debug').style.display='block';return}
  $('cog-debug').style.display='block';
}

/* GraphViewCanvas 1:1 复刻 — 来自原始 CNexus Platform (GraphViewCanvas.tsx + graphViewModel.ts + GraphViewControlsPanel.tsx) */

/* ===== Settings (DEFAULT_GRAPH_SETTINGS) ===== */
var GV_SETTINGS = {
  centerForce: 0.08,
  repelForce: 120,
  linkForce: 0.04,
  linkDistance: 72,
  nodeSize: 1,
  linkThickness: 1,
  textFade: 0.35,
  animate: true,
  showArrows: false,
  search: '',
  tagsOnly: true,
  orphansOnly: false
};

/* ===== Data model ===== */
var GV_SIMS=[],GV_NODES=[],GV_LINKS=[],GV_RAF=0;
var GV_ZOOM=1,GV_PANX=0,GV_PANY=0,GV_DRAG=null;

function gvGroupColor(group){
  var m={'goal':'#3fb950','belief':'#c9a227','episode':'#6b8cae','identity':'#f85149','insight':'#3fb950','term':'#8b949e','halo':'#8b949e55'};
  return m[group]||'#8b949e';
}

function gvNodeRadius(weight,sizeMul){
  return (4+weight*5.5)*sizeMul;
}

function gvFilterNodes(settings){
  var nodes=GV_SIMS.slice();
  var q=(settings.search||'').trim().toLowerCase();
  if(q)nodes=nodes.filter(function(n){return(n.label||'').toLowerCase().indexOf(q)>=0||n.group.indexOf(q)>=0});
  if(settings.orphansOnly){
    var linked={};
    for(var i=0;i<GV_LINKS.length;i++){linked[GV_LINKS[i].source]=1;linked[GV_LINKS[i].target]=1}
    nodes=nodes.filter(function(n){return n.group==='halo'||!linked[n.id]});
  }
  if(settings.tagsOnly)nodes=nodes.filter(function(n){return n.group==='halo'||n.group!=='term'});
  var ids={};for(var i=0;i<nodes.length;i++)ids[nodes[i].id]=1;
  var links=[];for(var i=0;i<GV_LINKS.length;i++){if(ids[GV_LINKS[i].source]&&ids[GV_LINKS[i].target])links.push(GV_LINKS[i])}
  return {nodes:nodes,links:links};
}

/* ===== Build Graph View Model (1:1 from graphViewModel.ts) ===== */
function gvBuildGraphViewModel(){
  var gv_n=[],gv_l=[];
  GV_SIMS.forEach(function(s,i){
    var angle=(i/Math.max(GV_SIMS.length,1))*Math.PI*2;
    var onRing=s.weight<1.05||i%3===0;
    var r=onRing?220+(i%5)*18:40+Math.random()*80;
    gv_n.push({
      id:s.block_id||s.id||('node-'+i),
      label:s.label||s.input_hint||s.text||s.input||'[无标题]',
      group:s.group||'episode',
      weight:s.weight||0.5,
      x:Math.cos(angle)*r,
      y:Math.sin(angle)*r,
      vx:0,vy:0
    });
  });
  // Chain edges
  for(var i=0;i<gv_n.length-1;i++){
    gv_l.push({id:'chain-'+gv_n[i].id+'-'+gv_n[i+1].id,source:gv_n[i].id,target:gv_n[i+1].id,strength:0.92});
  }
  // Tag group edges (within same group, connect nearby)
  var byGroup={};
  for(var i=0;i<gv_n.length;i++){
    var g=gv_n[i].group;
    if(!byGroup[g])byGroup[g]=[];
    byGroup[g].push(gv_n[i].id);
  }
  var gKeys=Object.keys(byGroup);
  for(var gi=0;gi<gKeys.length;gi++){
    var ids=byGroup[gKeys[gi]];
    for(var i=0;i<ids.length-1;i++){
      for(var j=i+1;j<Math.min(i+3,ids.length);j++){
        var a=ids[i],b=ids[j];
        var dup=false;
        for(var li=0;li<gv_l.length;li++){if((gv_l[li].source===a&&gv_l[li].target===b)||(gv_l[li].source===b&&gv_l[li].target===a)){dup=true;break}}
        if(dup)continue;
        gv_l.push({id:'tag-'+a+'-'+b,source:a,target:b,strength:0.35});
      }
    }
  }
  // Halo nodes (fill up to 28 if less)
  if(gv_n.length<28){
    var haloCount=Math.max(12,28-gv_n.length);
    for(var i=0;i<haloCount;i++){
      var angle=(i/haloCount)*Math.PI*2;
      var id='halo-'+i;
      gv_n.push({id:id,label:'',group:'halo',weight:0.35+(i%3)*0.08,x:Math.cos(angle)*(260+(i%4)*12),y:Math.sin(angle)*(260+(i%4)*12),vx:0,vy:0});
      var anchor=gv_n[i%Math.max(GV_SIMS.length,1)]&&gv_n[i%Math.max(GV_SIMS.length,1)].id;
      if(anchor)gv_l.push({id:'halo-link-'+i,source:id,target:anchor,strength:0.06});
      var nextHalo='halo-'+(i+1)%haloCount;
      if(i<haloCount-1)gv_l.push({id:'halo-ring-'+i,source:id,target:nextHalo,strength:0.04});
    }
  }
  GV_NODES.length=0;GV_LINKS.length=0;
  GV_NODES.push.apply(GV_NODES,gv_n);
  GV_LINKS.push.apply(GV_LINKS,gv_l);
}

/* ===== Draw/Animation loop (1:1 from GraphViewCanvas.tsx) ===== */
async function drawFlowGraph(){
  var c=$('flow-canvas');if(!c)return;
  cancelAnimationFrame(GV_RAF);
  GV_NODES.length=0;GV_LINKS.length=0;GV_SIMS.length=0;
  try{
    var d=await api('/api/memory_dump?limit=20');
    var entries=d&&(d.entries||d.data||[]);
    if(entries&&entries.length){
      entries.forEach(function(e){
        GV_SIMS.push({id:e.block_id||e.id,label:e.input_hint||e.text||e.input||'[无标题]',weight:e.weight||0.5,group:e.type==='skill_execution_trace'?'insight':'episode'});
      });
    }else{
      // Fallback: build from /api/status
      var st=await api('/api/status');
      var cs=st&&st.cog_state||{};
      if(cs.active_intent)GV_SIMS.push({id:'intent',label:'intent: '+cs.active_intent,weight:0.6,group:'goal'});
      if(cs.last_strategy)GV_SIMS.push({id:'strate',label:'strategy: '+cs.last_strategy,weight:0.5,group:'belief'});
      if(cs.accumulated_weight!==undefined)GV_SIMS.push({id:'weight',label:'belief: '+cs.accumulated_weight.toFixed(3),weight:0.8,group:'belief'});
      if(cs.recall_strength!==undefined)GV_SIMS.push({id:'recall',label:'recall: '+cs.recall_strength.toFixed(3),weight:0.4,group:'insight'});
      if(st&&st.uptime)GV_SIMS.push({id:'uptime',label:'uptime: '+Math.floor(st.uptime)+'s',weight:0.3,group:'episode'});
      if(st&&st.skills_loaded)GV_SIMS.push({id:'skills',label:'skills: '+st.skills_loaded,weight:0.55,group:'identity'});
      if(st&&st.execution_count)GV_SIMS.push({id:'execs',label:'exec: '+st.execution_count,weight:0.45,group:'episode'});
      if(GV_SIMS.length<3)GV_SIMS.push({id:'cx',label:'CNexus 2.0',weight:0.5,group:'identity'},{id:'stub',label:'stub mode',weight:0.25,group:'episode'});
    }
  }catch(e){
    GV_SIMS.push({id:'err',label:'API unavailable',weight:0.5,group:'episode'},{id:'retry',label:'retry...',weight:0.4,group:'episode'});
  }
  gvBuildGraphViewModel();

  var p=c.parentElement;
  var w=Math.max(p.clientWidth||400,300);
  var h=Math.max(p.clientHeight||400,window.innerHeight-200,300);
  c.width=w;c.height=h;
  var ctx=c.getContext('2d');
  var cx=w/2,cy=h/2;
  var view={scale:1,panX:0,panY:0};
  GV_ZOOM=1;GV_PANX=0;GV_PANY=0;

  var screenToWorld=function(cx2,cy2){
    var rect=c.getBoundingClientRect();
    var sx=cx2-rect.left,sy=cy2-rect.top;
    return {x:(sx-w/2-view.panX)/view.scale,y:(sy-h/2-view.panY)/view.scale};
  };

  function tick(){
    var filtered=gvFilterNodes(GV_SETTINGS);
    var n=filtered.nodes,l=filtered.links;
    var nm={};for(var i=0;i<n.length;i++)nm[n[i].id]=n[i];
    if(!c.parentNode){cancelAnimationFrame(GV_RAF);return}

    // Physics (1:1 from GraphViewCanvas.tsx)
    if(GV_SETTINGS.animate){
      for(var i=0;i<n.length;i++){
        if(n[i].fixed)continue;
        n[i].vx+=(0-n[i].x)*GV_SETTINGS.centerForce*0.002;
        n[i].vy+=(0-n[i].y)*GV_SETTINGS.centerForce*0.002;
      }
      for(var i=0;i<n.length;i++){
        for(var j=i+1;j<n.length;j++){
          var a=n[i],b=n[j];
          var dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(Math.hypot(dx,dy),1);
          var force=GV_SETTINGS.repelForce/(dist*dist);
          var fx=(dx/dist)*force,fy=(dy/dist)*force;
          if(!a.fixed){a.vx-=fx;a.vy-=fy}
          if(!b.fixed){b.vx+=fx;b.vy+=fy}
        }
      }
      for(var li=0;li<l.length;li++){
        var a=nm[l[li].source],b=nm[l[li].target];
        if(!a||!b)continue;
        var dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(Math.hypot(dx,dy),1);
        var delta=dist-GV_SETTINGS.linkDistance;
        var force=delta*GV_SETTINGS.linkForce*l[li].strength;
        var fx=(dx/dist)*force,fy=(dy/dist)*force;
        if(!a.fixed){a.vx+=fx;a.vy+=fy}
        if(!b.fixed){b.vx-=fx;b.vy-=fy}
      }
      for(var i=0;i<n.length;i++){
        if(n[i].fixed)continue;
        n[i].vx*=0.88;n[i].vy*=0.88;n[i].x+=n[i].vx;n[i].y+=n[i].vy;
      }
    }

    // Draw background
    ctx.fillStyle='#0d1117';ctx.fillRect(0,0,w,h);
    var grad=ctx.createRadialGradient(cx,cy,20,cx,cy,Math.max(w,h)*0.55);
    grad.addColorStop(0,'#1a1f2c44');grad.addColorStop(1,'#0d1117');
    ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);

    ctx.save();
    ctx.translate(cx+view.panX,cy+view.panY);
    ctx.scale(view.scale,view.scale);

    // Draw links
    for(var li=0;li<l.length;li++){
      var a=nm[l[li].source],b=nm[l[li].target];
      if(!a||!b)continue;
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
      ctx.strokeStyle='#8b949e44';
      ctx.lineWidth=GV_SETTINGS.linkThickness*(0.6+l[li].strength*0.6);
      ctx.stroke();
      if(GV_SETTINGS.showArrows){
        var ang=Math.atan2(b.y-a.y,b.x-a.x);
        var mx=(a.x+b.x)/2,my=(a.y+b.y)/2;
        ctx.beginPath();
        ctx.moveTo(mx,my);
        ctx.lineTo(mx-Math.cos(ang-0.4)*6,my-Math.sin(ang-0.4)*6);
        ctx.lineTo(mx-Math.cos(ang+0.4)*6,my-Math.sin(ang+0.4)*6);
        ctx.closePath();
        ctx.fillStyle='#8b949e66';ctx.fill();
      }
    }

    // Draw nodes
    for(var i=0;i<n.length;i++){
      var r=gvNodeRadius(n[i].weight,GV_SETTINGS.nodeSize);
      var col=gvGroupColor(n[i].group);
      ctx.beginPath();ctx.arc(n[i].x,n[i].y,r,0,Math.PI*2);
      ctx.fillStyle=col;
      ctx.globalAlpha=n[i].group==='halo'?0.35:0.92;
      ctx.fill();ctx.globalAlpha=1;
      if(n[i].label&&GV_SETTINGS.textFade>0.05){
        ctx.font='500 '+Math.max(7,9*GV_SETTINGS.nodeSize)+'px sans-serif';
        ctx.textAlign='center';ctx.fillStyle='#c9d1d9';
        ctx.globalAlpha=Math.min(1,GV_SETTINGS.textFade);
        var maxLen=10;
        var short=n[i].label.length>maxLen?n[i].label.slice(0,maxLen-1)+'...':n[i].label;
        ctx.fillText(short,n[i].x,n[i].y+r+10);
        ctx.globalAlpha=1;
      }
    }

    ctx.restore();

    // Empty state
    if(!n.length){
      ctx.font='500 14px sans-serif';
      ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillStyle='#8b949e';
      ctx.fillText('暂无记忆词条',cx,cy);
    }

    GV_RAF=requestAnimationFrame(tick);
  }

  // Input handling (1:1 from GraphViewCanvas.tsx)
  var pickNode=function(cx2,cy2){
    var pt=screenToWorld(cx2,cy2);
    var filtered=gvFilterNodes(GV_SETTINGS);
    for(var i=filtered.nodes.length-1;i>=0;i--){
      var n=filtered.nodes[i];
      var r=gvNodeRadius(n.weight,GV_SETTINGS.nodeSize)+4;
      if(Math.hypot(n.x-pt.x,n.y-pt.y)<=r)return n;
    }
    return null;
  };

  c.onwheel=function(e){
    e.preventDefault();
    var factor=e.deltaY>0?0.92:1.08;
    view.scale=Math.min(2.5,Math.max(0.35,view.scale*factor));
    GV_ZOOM=view.scale;
  };

  c.onpointerdown=function(e){
    var hit=pickNode(e.clientX,e.clientY);
    if(hit){
      hit.fixed=true;
      GV_DRAG={kind:'node',nodeId:hit.id,lastX:e.clientX,lastY:e.clientY};
    }else{
      GV_DRAG={kind:'pan',lastX:e.clientX,lastY:e.clientY};
    }
    c.setPointerCapture(e.pointerId);
  };

  c.onpointermove=function(e){
    if(!GV_DRAG)return;
    var dx=e.clientX-GV_DRAG.lastX,dy=e.clientY-GV_DRAG.lastY;
    GV_DRAG.lastX=e.clientX;GV_DRAG.lastY=e.clientY;
    if(GV_DRAG.kind==='pan'){view.panX+=dx;view.panY+=dy;GV_PANX=view.panX;GV_PANY=view.panY;return}
    var node=null;
    var filtered=gvFilterNodes(GV_SETTINGS);
    for(var i=0;i<filtered.nodes.length;i++){if(filtered.nodes[i].id===GV_DRAG.nodeId){node=filtered.nodes[i];break}}
    if(!node)return;
    node.x+=dx/view.scale;node.y+=dy/view.scale;node.vx=0;node.vy=0;
  };

  c.onpointerup=function(e){
    if(GV_DRAG&&GV_DRAG.kind==='node'&&GV_DRAG.nodeId){
      var node=null;
      var filtered=gvFilterNodes(GV_SETTINGS);
      for(var i=0;i<filtered.nodes.length;i++){if(filtered.nodes[i].id===GV_DRAG.nodeId){node=filtered.nodes[i];break}}
      if(node)node.fixed=false;
    }
    GV_DRAG=null;
    try{c.releasePointerCapture(e.pointerId)}catch(ex){}
  };

  tick();

  // Reinitialize on settings change
  window._gvSettingsApply=function(key,val){
    GV_SETTINGS[key]=val;
    // Rebuild graph view model if search/tags/orphans changed to reset highlight
  };
}

/* ===== Controls Panel (1:1 from GraphViewControlsPanel.tsx) ===== */
function gvInitControls(){
  var panel=$('flow-controls');
  if(!panel)return;
  var tagLabels={'goal':'目标因子','belief':'信念因子','episode':'情景因子','identity':'身份因子','insight':'洞察因子','term':'术语因子'};
  var groupSwatch={'goal':'#34D399','belief':'#c9a227','episode':'#6b8cae','identity':'#F87171','insight':'#34D399','term':'#64748B'};
  
  function renderPanel(){
    // Count groups from GV_SIMS
    var gCounts={};
    for(var i=0;i<GV_SIMS.length;i++){
      var g=GV_SIMS[i].group||'episode';
      gCounts[g]=(gCounts[g]||0)+1;
    }
    var gKeys=Object.keys(gCounts);
    
    panel.innerHTML=
      '<div class="gv-grid">'+
      '  <div class="gv-section" style="grid-area:f"><div class="gv-sec-hdr" onclick="var e=this.nextElementSibling;e.style.display=e.style.display===\'none\'?\'block\':\'none\';this.querySelector(\'.gv-chev\').classList.toggle(\'open\')"><span class="gv-chev open">▼</span> Filters</div><div class="gv-sec-body">'+
      '    <input class="gv-search" id="gv-search" placeholder="Search..." value="'+esc(GV_SETTINGS.search)+'" oninput="gvSetSearch(this.value)">'+
      '    <label class="gv-toggle"><span>Tags</span><button class="gv-switch'+(GV_SETTINGS.tagsOnly?' on':'')+'" onclick="gvToggle(\'tagsOnly\')"><span></span></button></label>'+
      '    <label class="gv-toggle"><span>Orphans</span><button class="gv-switch'+(GV_SETTINGS.orphansOnly?' on':'')+'" onclick="gvToggle(\'orphansOnly\')"><span></span></button></label>'+
      '  </div></div>'+
      '  <div class="gv-section" style="grid-area:g"><div class="gv-sec-hdr" onclick="var e=this.nextElementSibling;e.style.display=e.style.display===\'none\'?\'block\':\'none\';this.querySelector(\'.gv-chev\').classList.toggle(\'open\')"><span class="gv-chev open">▼</span> Groups</div><div class="gv-sec-body">'+
      '    <ul class="gv-groups">'+
        gKeys.map(function(g){return '<li><span class="gv-swatch" style="background:'+(groupSwatch[g]||'#8b949e')+'"></span><span>'+esc(tagLabels[g]||g)+'</span><span class="gv-gcount">'+gCounts[g]+'</span></li>'}).join('')+
      '    </ul>'+
      '  </div></div>'+
      '  <div class="gv-section" style="grid-area:d"><div class="gv-sec-hdr" onclick="var e=this.nextElementSibling;e.style.display=e.style.display===\'none\'?\'block\':\'none\';this.querySelector(\'.gv-chev\').classList.toggle(\'open\')"><span class="gv-chev open">▼</span> Display</div><div class="gv-sec-body">'+
      '    <label class="gv-toggle"><span>Arrows</span><button class="gv-switch'+(GV_SETTINGS.showArrows?' on':'')+'" onclick="gvToggle(\'showArrows\')"><span></span></button></label>'+
      '    '+gvSliderRow('Text fade','textFade',0,1,0.05)+
      '    '+gvSliderRow('Node size','nodeSize',0.5,2,0.1)+
      '    '+gvSliderRow('Link width','linkThickness',0.3,3,0.1)+
      '    <button class="gv-anim-btn" id="gv-anim-btn">'+(GV_SETTINGS.animate?'Animate ON':'Animate')+'</button>'+
      '  </div></div>'+
      '  <div class="gv-section" style="grid-area:r"><div class="gv-sec-hdr" onclick="var e=this.nextElementSibling;e.style.display=e.style.display===\'none\'?\'block\':\'none\';this.querySelector(\'.gv-chev\').classList.toggle(\'open\')"><span class="gv-chev open">▼</span> Forces</div><div class="gv-sec-body">'+
      '    '+gvSliderRow('Center','centerForce',0,0.3,0.01)+
      '    '+gvSliderRow('Repel','repelForce',20,300,5)+
      '    '+gvSliderRow('Link','linkForce',0.01,0.15,0.005)+
      '    '+gvSliderRow('Distance','linkDistance',30,160,2)+
      '  </div></div>'+
      '</div>';
      
    document.getElementById('gv-anim-btn').onclick=function(){
      GV_SETTINGS.animate=!GV_SETTINGS.animate;
      document.getElementById('gv-anim-btn').textContent=GV_SETTINGS.animate?'Animate ON':'Animate';
      document.getElementById('gv-anim-btn').style.backgroundColor=GV_SETTINGS.animate?'#5eead4':'#21262d';
      document.getElementById('gv-anim-btn').style.color=GV_SETTINGS.animate?'#0f172a':'#8b949e';
    };
  }
  
  renderPanel();
}

function gvSliderRow(label,key,min,max,step){
  var val=GV_SETTINGS[key];
  return '<label class="gv-slider-row"><div class="gv-slider-labels"><span>'+label+'</span><span>'+Number(val).toFixed(2).replace(/\.00$/,'')+'</span></div><input type="range" min="'+min+'" max="'+max+'" step="'+step+'" value="'+val+'" oninput="gvSetSlider(\''+key+'\',this.value,this)"></label>';
}

function gvSetSlider(key,val,inp){
  GV_SETTINGS[key]=Number(val);
  var lbl=inp.parentElement.querySelector('.gv-slider-labels span:last-child');
  if(lbl)lbl.textContent=Number(val).toFixed(2).replace(/\.00$/,'');
}

function gvSetSearch(val){
  GV_SETTINGS.search=val;
}

function gvToggle(key){
  GV_SETTINGS[key]=!GV_SETTINGS[key];
  gvInitControls(); // re-render
}

async function loadTokenData(){
  var d=await api('/api/exec_trace?limit=50');
  var traces=d.traces||d.entries||d.data||[];
  var totalCost=0;traces.forEach(function(t){totalCost+=t.cost||t.weight||0});
  $('token-stats').innerHTML='<div class="stat-card"><div class="stat-label">轨迹记录</div><div class="stat-value blue">'+traces.length+'</div></div><div class="stat-card"><div class="stat-label">算力消耗</div><div class="stat-value orange">'+totalCost.toFixed(2)+'</div></div>';
  if(traces.length){
    var html='<table><thead><tr><th>#</th><th>Trace ID</th><th>类型</th><th>消耗</th><th>时间</th></tr></thead><tbody>';
    traces.slice(0,50).forEach(function(t,i){
      html+='<tr><td>'+(i+1)+'</td><td style="font-family:var(--fontMono);font-size:10px">'+esc(t.trace_id||t.id||'—')+'</td><td>'+esc(t.type||t.kind||'—')+'</td><td>'+(typeof t.cost==='number'?t.cost.toFixed(3):typeof t.weight==='number'?t.weight.toFixed(3):'—')+'</td><td>'+esc(t.timestamp||t.time||'—')+'</td></tr>';
    });
    html+='</tbody></table>';$('token-table').innerHTML=html;
  }else $('token-table').innerHTML='<div style="padding:16px;text-align:center;color:var(--textMuted);font-size:12px">暂无执行轨迹数据</div>';
}

async function loadSummaryData(){
  var d=await api('/api/status');if(!d)return;
  var cs=d.cog_state||d;
  var narrative=cs.narrative||cs.cse_narrative||'';
  if(narrative){$('vsp-body').innerHTML='<div class="narrative-text">'+esc(narrative)+'</div>'}
  else{$('vsp-body').innerHTML='<div class="narrative-empty">等待 Runtime 连接 · CSE 叙事数据尚未就绪</div>'}
}

async function loadRecommendations(){
  var d=await api('/api/status');var ov=d&&d.overview||{};
  var acts=ov.top_actions||ov.recommendations||[];
  if(acts.length){
    var top=acts[0];
    $('rec-hero-title').textContent=top.title||top.action||'分析当前状态';
    $('rec-hero-sub').textContent=top.description||'检查系统认知状态，寻找优化机会';
    var tags='';if(top.priority){tags+='<span class="rec-tag" style="background:var(--orangeSoft);color:var(--orange)">优先级: '+top.priority+'</span>'}
    if(top.reversibility){tags+='<span class="rec-tag" style="background:var(--blueSoft);color:var(--blue)">可逆性: '+top.reversibility+'</span>'}
    $('rec-tags').innerHTML=tags;
    $('rec-why-text').innerHTML=top.rationale||top.reason||'基于当前认知状态分析';
    $('rec-why').style.display='block';$('rec-apply-btn').style.display='block';$('rec-error').style.display='none';
    if(acts.length>1){$('rec-other-list').style.display='block';$('rec-other-items').innerHTML=acts.slice(1).map(function(a){return '<div class="rec-other-item">'+(a.title||a.action||'')+'</div>'}).join('')}
  }else{$('rec-error').style.display='block';$('rec-hero-title').textContent='—';$('rec-hero-sub').textContent='暂无建议'}
}

async function wbSend(){
  var inp=$('wb-input'),t=inp.value.trim();if(!t)return;inp.value='';
  var area=$('wb-reply-area');area.innerHTML='<div class="it-reply-text">正在思考...</div>';
  try{
    var d=await api('/api/converse?text='+encodeURIComponent(t));
    var reply=typeof d.reply==='object'?JSON.stringify(d.reply,null,2):d.reply||'无回复';
    area.innerHTML='<div style="font-size:11px;color:var(--textLight);margin-bottom:8px;text-align:right">> '+esc(t)+'</div><div class="it-reply-text">'+esc(reply)+'</div>';
  }catch(e){area.innerHTML='<div class="it-reply-text" style="color:var(--red)">请求失败</div>'}
}

function switchWBMode(m,btn){
  WB_MODE=m;
  document.querySelectorAll('.it-mode-btn').forEach(function(b){b.classList.toggle('active',b.dataset.mode===m)});
  var hints={ask:'向 CNexus 引擎提出问题或命令...',record:'记录当前观察或想法到记忆...',analyze:'选择数据进行分析...',recall:'搜索记忆中的相关信息...'};
  $('wb-hint').textContent=hints[m];
  $('wb-reply-area').innerHTML='<div class="it-placeholder">'+hints[m]+'</div>';
}

function switchDULayer(l,btn){DU_LAYER=l;document.querySelectorAll('.du-layer-btn').forEach(function(b){b.classList.toggle('active',b.dataset.layer===l)})}
function handleFileDrop(files){
  for(var i=0;i<files.length;i++){if(!DU_FILES.find(function(f){return f.name===files[i].name}))DU_FILES.push(files[i])}
  renderDUFiles();
  var dz=document.getElementById('du-dropzone');if(dz)dz.classList.remove('dragging');
}
function renderDUFiles(){
  if(DU_FILES.length){
    $('du-file-list').innerHTML=DU_FILES.map(function(f,i){return '<div class="du-file-item"><span class="du-file-name">'+esc(f.name)+'</span><button class="du-file-remove" onclick="DU_FILES.splice('+i+',1);renderDUFiles()">✕</button></div>'}).join('');
    $('du-import-btn').textContent='📥 导入 ('+DU_FILES.length+')';$('du-import-btn').disabled=false;
  }else{$('du-file-list').innerHTML='';$('du-import-btn').textContent='📥 导入 (0)';$('du-import-btn').disabled=true}
}
function duClear(){DU_FILES=[];renderDUFiles();$('du-note').className='du-note';$('du-note').textContent=''}
async function duImport(){
  if(!DU_FILES.length)return;
  $('du-note').className='du-note loading';
  $('du-note').textContent='正在上传 '+DU_FILES.length+' 个文件...';
  $('du-import-btn').disabled=true;
  var fd=new FormData();
  for(var i=0;i<DU_FILES.length;i++)fd.append('files',DU_FILES[i]);
  try{
    var r=await fetch(API+'/api/upload',{method:'POST',body:fd});
    var d=await r.json();
    if(d.ok||d.status==='success'||d.imported_blocks_count){
      var ok=d.imported_blocks_count||d.count||DU_FILES.length;
      $('du-note').className='du-note success';
      $('du-note').textContent='✅ 已导入 '+ok+' 条记忆 ('+DU_LAYER+')';
      DU_FILES=[];renderDUFiles();
      // Refresh memory flow graph
      if(VIEW==='flow')drawFlowGraph();
    }else{
      $('du-note').className='du-note error';
      $('du-note').textContent='❌ 导入失败: '+(d.error||d.message||'未知错误');
    }
  }catch(e){
    $('du-note').className='du-note error';
    $('du-note').textContent='❌ 网络错误: '+e.message;
  }
  $('du-import-btn').disabled=false;
}

// Init
// Expose all functions to window for onclick bindings
window.pollStatus=pollStatus;window.switchView=switchView;
window.drawFlowGraph=drawFlowGraph;window.loadTokenData=loadTokenData;
window.loadSummaryData=loadSummaryData;window.loadRecommendations=loadRecommendations;
window.wbSend=wbSend;window.switchWBMode=switchWBMode;
window.handleFileDrop=handleFileDrop;window.duImport=duImport;
window.duClear=duClear;
window.gvInitControls=gvInitControls;

pollStatus();setInterval(pollStatus,3000);
if($('flow-canvas')){drawFlowGraph();gvInitControls();}
setInterval(drawFlowGraph,5000);

</script>
</body>
</html>

'''


# === FLOAT ===
FLOAT_HTML = r'''
<!DOCTYPE html>
<html lang=zh-CN>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>CNexus 浮标</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#060912;--surface:#0d1117;--surface2:#161b22;--border:#21262d;--text:#e1e4e8;--textMuted:#8b949e;--textLight:#6e7681;--accent:#58a6ff;--blue:#58a6ff;--blueSoft:rgba(88,166,255,0.12);--green:#3fb950;--greenSoft:rgba(63,185,80,0.12);--red:#f85149;--orange:#d29922;--orangeSoft:rgba(210,153,34,0.12);--purple:#bc8cff;--teal:#5eead4;--chatBg:#0d1117;--fontMono:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;--fontSans:-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif}
body{font-family:var(--fontSans);background:transparent;color:var(--text);overflow:hidden;font-size:12px;line-height:1.4;width:340px;min-height:100vh}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:2px}
.float-wrap{display:flex;flex-direction:column;min-height:100vh;background:var(--bg);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.float-header{display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:var(--surface);border-bottom:1px solid var(--border)}
.float-header .name{font-size:11px;font-weight:600;background:linear-gradient(135deg,var(--purple),var(--blue));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.float-header .dot{width:7px;height:7px;border-radius:50%}
.dot.green{background:var(--green);box-shadow:0 0 4px rgba(63,185,80,0.5)}
.dot.red{background:var(--red);box-shadow:0 0 4px rgba(248,81,73,0.5)}
.state-row{display:flex;align-items:center;gap:4px;padding:4px 10px;border-bottom:1px solid var(--border);font-size:9px;color:var(--textMuted);flex-wrap:wrap}
.state-row .tag{padding:1px 5px;border-radius:3px;font-size:8px;font-weight:600;font-family:var(--fontMono)}
.float-body{flex:1;overflow-y:auto;padding:6px 8px}
.float-section{margin-bottom:6px}
.float-section-title{font-size:9px;color:var(--textLight);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px}
.float-chat{padding:6px 8px}
.float-chat .fmsg{font-size:11px;line-height:1.4;padding:4px 8px;border-radius:6px;margin-bottom:4px}
.float-chat .fmsg.bot{background:var(--border);color:var(--text)}
.float-chat .fmsg.user{background:var(--blueSoft);color:var(--blue);text-align:right}
.float-input-row{display:flex;gap:4px;margin-top:6px}
.float-input-row input{flex:1;padding:4px 8px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text);font-size:11px;outline:none;font-family:var(--fontSans)}
.float-input-row button{padding:4px 10px;border:none;border-radius:6px;background:var(--blue);color:#fff;font-size:10px;cursor:pointer;white-space:nowrap}
.float-canvas{width:100%;height:100px;border-radius:6px;border:1px solid var(--border);background:var(--surface);margin-bottom:6px}
.float-canvas canvas{width:100%;height:100%;display:block}
.float-status{display:grid;grid-template-columns:1fr 1fr;gap:2px;padding:4px;font-size:9px}
.float-status .fs{display:flex;justify-content:space-between;color:var(--textMuted)}
.float-status .fs .val{color:var(--text);font-weight:500}
</style>
</head>
<body>
<div class="float-wrap" id="app">
<div class="float-header">
<div class="name">CNexus 浮标</div>
<span class="dot green" id="float-dot"></span>
</div>
<div class="state-row" id="state-row">
<span id="float-status-text">就绪 · 运行中</span>
<span class="tag" id="float-belief" style="background:var(--greenSoft);color:var(--green)">信念 0.000</span>
<span class="tag" id="float-mem" style="background:var(--tealSoft);color:var(--teal)">记忆 0</span>
</div>
<div class="float-body">
<div class="float-section">
<div class="float-section-title">📝 迷你对话</div>
<div class="float-chat">
<div class="fmsg bot" id="float-chat">连接中...</div>
<div class="float-input-row"><input id="float-msg" placeholder="..." onkeydown="if(event.key==='Enter')floatSend()"><button onclick="floatSend()">➤</button></div>
</div>
</div>
<div class="float-section">
<div class="float-section-title">🔀 记忆流</div>
<div class="float-canvas"><canvas id="float-flow"></canvas></div>
</div>
<div class="float-section">
<div class="float-section-title">⚡ 实时状态</div>
<div class="float-status">
<div class="fs"><span>引擎</span><span class="val" id="fs-engine">—</span></div>
<div class="fs"><span>技能</span><span class="val" id="fs-skills">—</span></div>
<div class="fs"><span>执行</span><span class="val" id="fs-exec">0</span></div>
<div class="fs"><span>迭代</span><span class="val" id="fs-iter">0</span></div>
</div>
</div>
<div class="float-section">
<button style="width:100%;padding:4px;border:1px solid var(--border);border-radius:6px;font-size:10px;background:transparent;color:var(--textMuted);cursor:pointer" onclick="floatRefresh()">🔄 刷新</button>
</div>
</div>
</div>
<script>
var API='';
function $(id){return document.getElementById(id)}
function esc(s){if(!s)return'';var d=document.createElement('div');d.textContent=s;return d.innerHTML}
async function api(path){try{var r=await fetch(API+path);return await r.json()}catch(e){return null}}
async function pollFloat(){
  var d=await api('/api/status');
  if(!d){$('float-dot').className='dot red';$('float-status-text').textContent='离线';return}
  $('float-dot').className='dot green';
  $('float-status-text').textContent=(d.engine_status||'运行中')+' · '+(d.status||'Active');
  var cs=d.cog_state||d;
  if(cs.accumulated_weight!==undefined)$('float-belief').textContent='信念 '+parseFloat(cs.accumulated_weight).toFixed(3);
  if(d.memory_count!==undefined)$('float-mem').textContent='记忆 '+d.memory_count;
  if(d.engine_status)$('fs-engine').textContent=d.engine_status;
  if(d.skills_loaded!==undefined)$('fs-skills').textContent=d.skills_loaded+'/'+(d.skills_total||'?');
  if(cs.execution_count!==undefined)$('fs-exec').textContent=cs.execution_count;
  if(cs.iteration!==undefined)$('fs-iter').textContent=cs.iteration;
  drawFloatFlow();
}
async function floatSend(){
  var inp=$('float-msg'),t=inp.value.trim();if(!t)return;
  inp.value='';$('float-chat').innerHTML='<div class="fmsg user">'+esc(t)+'</div><div class="fmsg bot">正在思考...</div>';
  try{
    var r=await api('/api/converse?text='+encodeURIComponent(t));
    var reply=r.reply||'无响应';
    $('float-chat').innerHTML='<div class="fmsg user">'+esc(t)+'</div><div class="fmsg bot">'+esc(typeof reply==='object'?JSON.stringify(reply):reply)+'</div>';
  }catch(e){$('float-chat').innerHTML=$('float-chat').innerHTML.replace('正在思考...','请求失败')}
}
function drawFloatFlow(){
  var c=$('float-flow');if(!c)return;
  var p=c.parentElement;c.width=p.clientWidth||300;c.height=100;
  var ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);
  var cx=c.width/2,cy=c.height/2,count=8;
  for(var i=0;i<count;i++){
    var a=2*Math.PI*i/count;
    var x=cx+Math.cos(a)*(c.width/2-20),y=cy+Math.sin(a)*(c.height/2-10);
    var grad=ctx.createRadialGradient(x,y,0,x,y,4);
    grad.addColorStop(0,'rgba(88,166,255,0.8)');grad.addColorStop(1,'rgba(88,166,255,0.1)');
    ctx.fillStyle=grad;ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill();
    if(i>0){var pa=2*Math.PI*(i-1)/count;var px=cx+Math.cos(pa)*(c.width/2-20),py=cy+Math.sin(pa)*(c.height/2-10);ctx.strokeStyle='rgba(48,54,61,0.4)';ctx.lineWidth=0.5;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(x,y);ctx.stroke()}
  }
}
function floatRefresh(){pollFloat()}
pollFloat();setInterval(pollFloat,3000);setInterval(drawFloatFlow,5000);
</script>
</body>
</html>

'''


# === HTTP Handler ===
class CNexusUIHandler(BaseHTTPRequestHandler):
    def _json(self, data, st=200):
        self.send_response(st)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        self.wfile.write(json.dumps(data,ensure_ascii=False,default=str).encode('utf-8'))

    def _html(self, s, st=200):
        self.send_response(st)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin','*')
        self.end_headers()
        self.wfile.write(s.encode('utf-8'))

    def do_POST(self):
        p = urlparse(self.path); path = p.path.rstrip('/') or '/'
        try:
            length = int(self.headers.get('Content-Length',0))
            body = self.rfile.read(length) if length else b'{}'
            if path == '/api/upload':
                ct = self.headers.get('Content-Type','')
                if 'multipart/form-data' in ct:
                    # Parse multipart manually — simpler than cgi.FieldStorage
                    import re
                    results = []; ok = 0
                    boundary = ct.split('boundary=')[-1].strip().strip('"')
                    parts = body.split(('--' + boundary).encode())
                    for part in parts:
                        if not part or part == b'--\r\n' or part == b'--' or part == b'\r\n':
                            continue
                        # Split headers from body at first \r\n\r\n
                        hdr_end = part.find(b'\r\n\r\n')
                        if hdr_end < 0: continue
                        hdrs_raw = part[:hdr_end].decode('utf-8', errors='replace')
                        data_raw = part[hdr_end+4:]
                        # Strip trailing \r\n--\r\n etc
                        if data_raw.endswith(b'\r\n'):
                            data_raw = data_raw[:-2]
                        if data_raw.endswith(b'--'):
                            data_raw = data_raw[:-2]
                        if data_raw.endswith(b'\r\n'):
                            data_raw = data_raw[:-2]
                        # Get filename from Content-Disposition
                        fn_match = re.search(r'filename="([^"]*)"', hdrs_raw)
                        if not fn_match:
                            continue
                        filename = fn_match.group(1)
                        try:
                            text_data = data_raw.decode('utf-8')[:5000]
                        except:
                            text_data = '[binary file: ' + filename + ' — size: ' + str(len(data_raw)) + ' bytes]'
                        text_content = '-- file: ' + filename + ' --\n' + text_data
                        try:
                            resp = api_converse(text_content.strip())
                            ok += 1
                            results.append({'file': filename, 'status': 'ok', 'reply_len': len(str(resp.get('reply',''))) if isinstance(resp,dict) else 0})
                        except Exception as e:
                            results.append({'file': filename, 'status': 'error', 'message': str(e)})
                    return self._json({'ok':True,'count':ok,'imported_blocks_count':ok,'results':results})
                else:
                    text = body.decode('utf-8',errors='replace')
                    try:
                        resp = api_converse(text)
                        return self._json({'ok':True,'status':'success','reply':resp.get('reply','') if isinstance(resp,dict) else str(resp)})
                    except Exception as e:
                        return self._json({'ok':False,'error':str(e)},500)
            if path == '/api/converse':
                t = json.loads(body).get('text','')
                return self._json({'error':'missing text'},400) if not t else self._json(api_converse(t))
            return self._json({'error':'not found','path':path},404)
        except Exception as e:
            return self._json({'error':str(e),'trace':traceback.format_exc()},500)
    def do_GET(self):
        p = urlparse(self.path); path = p.path.rstrip('/') or '/'; qs = parse_qs(p.query)
        try:
            if path in ('/','/shell'): return self._html(SHELL_HTML)
            if path == '/float': return self._html(FLOAT_HTML)
            if path == '/api/status': return self._json(api_status())
            if path == '/api/converse':
                t = qs.get('text',[''])[0]
                return self._json({'error':'missing text'},400) if not t else self._json(api_converse(t))
            if path == '/api/memory_dump':
                return self._json(api_memory_dump(int(qs.get('limit',['20'])[0])))
            if path == '/api/exec_trace':
                return self._json(api_exec_trace(int(qs.get('limit',['30'])[0])))
            if path == '/api/cog_state': return self._json(api_cog_state())
            if path == '/api/skill_graph': return self._json(api_skill_graph())
            if path == '/api/reset': return self._json(api_reset())
            self.send_response(404); self.end_headers(); self.wfile.write(b'404')
        except Exception as e:
            self._json({'error':str(e),'trace':traceback.format_exc()},500) if path.startswith('/api') else self._html('404 not found')

    def log_message(self, *a): pass

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',default='127.0.0.1')
    ap.add_argument('--port',type=int,default=7862)
    ap.add_argument('--no-engine',action='store_true')
    args = ap.parse_args()

    if not args.no_engine:
        print('[CNexus 2.0] init kernel...')
        try:
            get_engine()
            e = get_engine()
            print(f'[CNexus 2.0] ready | memory: {len(e.kernel.memory_store)} | exec: {e.kernel.state["execution_count"]}')
        except Exception as ex:
            print(f'[CNexus 2.0] init failed (UI still works): {ex}')

    server = HTTPServer((args.host,args.port),CNexusUIHandler)
    print(f'\n  CNexus 2.0 Console -> http://{args.host}:{args.port}')
    print(f'  Float -> http://{args.host}:{args.port}/float')
    print()
    try: server.serve_forever()
    except KeyboardInterrupt: print('\n[CNexus 2.0] shutdown'); server.server_close()
