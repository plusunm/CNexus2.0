/** Execution Spine UI — bilingual labels (EN / 中文). */

import type { LanguageProjectionMode } from "@/lib/sibt/projectionMode";

export type BilingualLabel = { en: string; zh: string };

/** Project label to single language or bilingual per SIBT UI mode. */
export function projectLabel(label: BilingualLabel, mode: LanguageProjectionMode = "both"): string {
  if (mode === "en") return label.en;
  if (mode === "zh") return label.zh;
  return `${label.en} / ${label.zh}`;
}

/** Section heading with projection mode. */
export function projectBiSection(label: BilingualLabel, mode: LanguageProjectionMode = "both"): string {
  if (mode === "en") return label.en;
  if (mode === "zh") return label.zh;
  return `${label.en} · ${label.zh}`;
}

/** Render as "English / 中文" */
export function bi(label: BilingualLabel): string {
  return `${label.en} / ${label.zh}`;
}

/** Section heading: English · 中文 */
export function biSection(label: BilingualLabel): string {
  return `${label.en} · ${label.zh}`;
}

/** Bilingual template: replace {key} in both en and zh */
export function biFmt(label: BilingualLabel, vars: Record<string, string | number>): string {
  let en = label.en;
  let zh = label.zh;
  for (const [key, val] of Object.entries(vars)) {
    const token = `{${key}}`;
    en = en.split(token).join(String(val));
    zh = zh.split(token).join(String(val));
  }
  return `${en} / ${zh}`;
}

export const spineL = {
  appTitle: { en: "Execution Spine", zh: "执行观测" } satisfies BilingualLabel,
  eivTitle: { en: "Execution Identity Viewer", zh: "执行标识视图" } satisfies BilingualLabel,
  eivSubtitle: {
    en: "Identity class · trace instance · causal structure · state diff",
    zh: "执行标识 · 追踪实例 · 因果链 · 状态变更",
  } satisfies BilingualLabel,
  appSubtitle: {
    en: "One trace · trigger → causal → state → control → explain",
    zh: "单次追踪 · 触发 → 因果 → 状态 → 管控 → 解释",
  } satisfies BilingualLabel,

  trace: { en: "TRACE", zh: "追踪" } satisfies BilingualLabel,
  status: { en: "STATUS", zh: "状态" } satisfies BilingualLabel,
  source: { en: "SOURCE", zh: "来源" } satisfies BilingualLabel,
  mode: { en: "MODE", zh: "模式" } satisfies BilingualLabel,
  events: { en: "events", zh: "事件" } satisfies BilingualLabel,
  semantic: { en: "semantic", zh: "语义关联" } satisfies BilingualLabel,

  statusLive: { en: "LIVE", zh: "实时" } satisfies BilingualLabel,
  statusReplay: { en: "REPLAY", zh: "回放" } satisfies BilingualLabel,
  statusOffline: { en: "OFFLINE", zh: "离线" } satisfies BilingualLabel,
  statusStale: { en: "STALE", zh: "已过期" } satisfies BilingualLabel,

  query: { en: "QUERY", zh: "查询" } satisfies BilingualLabel,
  queryPlaceholder: {
    en: "TRACE <id> EXPLAIN causal",
    zh: "TRACE <id> EXPLAIN causal",
  } satisfies BilingualLabel,
  runtimeRequired: {
    en: "Runtime not connected — spine_events.jsonl required",
    zh: "未连接运行时，需可读的 spine_events.jsonl",
  } satisfies BilingualLabel,

  streamLive: { en: "STREAM LIVE", zh: "执行流已订阅" } satisfies BilingualLabel,
  streamConnecting: { en: "SUBSCRIBING…", zh: "正在订阅执行流…" } satisfies BilingualLabel,
  stream: { en: "STREAM", zh: "推送" } satisfies BilingualLabel,
  streamOff: { en: "STREAM OFF", zh: "推送关闭" } satisfies BilingualLabel,
  liveSpineStream: { en: "Live Spine Stream", zh: "实时解释流" } satisfies BilingualLabel,
  waitingFrames: {
    en: "Waiting for explanation frames…",
    zh: "等待解释更新…",
  } satisfies BilingualLabel,
  openLiveStream: { en: "Open live stream", zh: "打开实时流" } satisfies BilingualLabel,
  frameCount: { en: "frames", zh: "条更新" } satisfies BilingualLabel,

  loading: { en: "Loading execution spine…", zh: "正在加载执行数据…" } satisfies BilingualLabel,
  liveStreamError: { en: "Live stream", zh: "实时流异常" } satisfies BilingualLabel,
  emptyPrompt: {
    en: "Enter TRACE <id> and QUERY to load an execution record.",
    zh: "输入 TRACE <id> 与查询语句以加载执行记录",
  } satisfies BilingualLabel,
  queryFailed: { en: "Query failed", zh: "查询失败" } satisfies BilingualLabel,

  timeline: { en: "Execution Spine Timeline", zh: "执行时序" } satisfies BilingualLabel,
  noExecutionEvents: {
    en: "No execution events in this trace.",
    zh: "该追踪暂无执行事件",
  } satisfies BilingualLabel,
  stateDelta: { en: "Δ state", zh: "状态变化" } satisfies BilingualLabel,
  triggeredBy: { en: "triggered_by from", zh: "触发来源" } satisfies BilingualLabel,

  causalLens: { en: "Causal Lens", zh: "因果分析" } satisfies BilingualLabel,
  noCausal: { en: "No causal chain from backend.", zh: "暂无因果链数据" } satisfies BilingualLabel,
  rootCause: { en: "Root cause", zh: "根因" } satisfies BilingualLabel,

  stateEvolution: { en: "State Evolution", zh: "状态演变" } satisfies BilingualLabel,
  noStateTrajectory: {
    en: "No state trajectory in contract.",
    zh: "暂无状态变更记录",
  } satisfies BilingualLabel,

  controlDecision: { en: "Control & Decision", zh: "管控决策" } satisfies BilingualLabel,
  noControl: {
    en: "No control decisions in this trace.",
    zh: "该追踪暂无管控记录",
  } satisfies BilingualLabel,
  entry: { en: "entry", zh: "入口" } satisfies BilingualLabel,
  caller: { en: "caller", zh: "调用方" } satisfies BilingualLabel,

  explanation: { en: "Explanation", zh: "解释" } satisfies BilingualLabel,
  noExplanation: {
    en: "No explanation from backend for this trace.",
    zh: "该追踪暂无解释内容",
  } satisfies BilingualLabel,
  path: { en: "path", zh: "路径" } satisfies BilingualLabel,

  executionMode: { en: "execution_spine_v1", zh: "execution_spine_v1" } satisfies BilingualLabel,
  executionSource: { en: "execution_spine", zh: "execution_spine" } satisfies BilingualLabel,

  driftPanel: { en: "Runtime ↔ Spine Drift", zh: "运行时与日志偏差" } satisfies BilingualLabel,
  driftScore: { en: "DRIFT SCORE", zh: "偏差指数" } satisfies BilingualLabel,
  driftMissing: { en: "Missing", zh: "缺失" } satisfies BilingualLabel,
  driftExtra: { en: "Extra", zh: "冗余" } satisfies BilingualLabel,
  driftMismatch: { en: "Mismatch", zh: "不匹配" } satisfies BilingualLabel,
  driftSync: { en: "Spine sync", zh: "日志同步" } satisfies BilingualLabel,
  driftConfidence: { en: "confidence", zh: "置信度" } satisfies BilingualLabel,
  driftStatusOk: { en: "OK", zh: "一致" } satisfies BilingualLabel,
  driftStatusMissing: { en: "MISSING", zh: "缺失" } satisfies BilingualLabel,
  driftStatusExtra: { en: "EXTRA", zh: "冗余" } satisfies BilingualLabel,
  driftStatusSuspect: { en: "SUSPECT", zh: "存疑" } satisfies BilingualLabel,
  noDriftData: {
    en: "No drift report — query with engine v2 in Runtime mode",
    zh: "暂无偏差报告，请在运行时模式下使用 v2 引擎查询",
  } satisfies BilingualLabel,

  epistemicScore: { en: "Epistemic confidence", zh: "解释可信度" } satisfies BilingualLabel,
  explainCaveats: { en: "Drift caveats", zh: "偏差说明" } satisfies BilingualLabel,

  identityPanel: { en: "Execution Identity", zh: "执行标识" } satisfies BilingualLabel,
  identityHash: { en: "IDENTITY", zh: "执行标识" } satisfies BilingualLabel,
  identityEquivalent: { en: "Equivalent traces", zh: "等价追踪" } satisfies BilingualLabel,
  identityDriftVariants: { en: "Drift variants", zh: "偏差变体" } satisfies BilingualLabel,
  identityDrift: { en: "Identity drift", zh: "标识偏差" } satisfies BilingualLabel,
  noIdentity: { en: "No identity — query with engine v3", zh: "暂无标识信息，请使用 v3 引擎查询" } satisfies BilingualLabel,

  identityHeader: { en: "Identity Header", zh: "标识概览" } satisfies BilingualLabel,
  identityStability: { en: "Identity stability", zh: "标识稳定性" } satisfies BilingualLabel,
  identityDriftFlag: { en: "Drift", zh: "偏差" } satisfies BilingualLabel,
  equivalentCount: { en: "Equivalent traces", zh: "等价追踪数" } satisfies BilingualLabel,
  yes: { en: "YES", zh: "是" } satisfies BilingualLabel,
  no: { en: "NO", zh: "否" } satisfies BilingualLabel,
  traceInstance: { en: "Trace instance", zh: "追踪实例" } satisfies BilingualLabel,

  traceTimeline: { en: "Trace Timeline", zh: "执行时序" } satisfies BilingualLabel,
  causalSubgraph: { en: "Causal Subgraph", zh: "因果链路" } satisfies BilingualLabel,
  causalEdges: { en: "edges", zh: "关联" } satisfies BilingualLabel,
  stateDiffStream: { en: "State Diff Stream", zh: "状态变更" } satisfies BilingualLabel,

  identityPanelDetail: { en: "Identity Panel", zh: "标识详情" } satisfies BilingualLabel,
  sigGraph: { en: "graph_hash", zh: "图结构指纹" } satisfies BilingualLabel,
  sigState: { en: "state_hash", zh: "状态指纹" } satisfies BilingualLabel,
  sigControl: { en: "control_hash", zh: "管控指纹" } satisfies BilingualLabel,
  sigCausal: { en: "causal_hash", zh: "因果指纹" } satisfies BilingualLabel,
  identityExplanation: { en: "Identity explanation", zh: "标识说明" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const tokenL = {
  title: { en: "Token Observatory", zh: "算力观测" } satisfies BilingualLabel,
  consoleTitle: { en: "Token Observatory Console", zh: "算力观测台" } satisfies BilingualLabel,
  consoleSubtitle: {
    en: "Cost · Binding · Gravity Field · Influence · Identity",
    zh: "消耗统计 · 执行归因 · 热力分布 · 因果权重 · 执行标识",
  } satisfies BilingualLabel,
  loading: { en: "Loading Token Graph...", zh: "正在加载用量数据…" } satisfies BilingualLabel,
  totalTokens: { en: "Total Tokens", zh: "Token 总量" } satisfies BilingualLabel,
  tokensIn: { en: "Tokens In", zh: "输入量" } satisfies BilingualLabel,
  tokensOut: { en: "Tokens Out", zh: "输出量" } satisfies BilingualLabel,
  activeTraces: { en: "Active Traces", zh: "活跃追踪" } satisfies BilingualLabel,
  spikeCount: { en: "Spikes", zh: "突增次数" } satisfies BilingualLabel,
  highCostCount: { en: "High Cost", zh: "高消耗" } satisfies BilingualLabel,
  spikes: { en: "Token Spikes", zh: "消耗异常" } satisfies BilingualLabel,
  noAnomalies: { en: "No anomalies detected", zh: "未发现异常消耗" } satisfies BilingualLabel,
  distribution: { en: "Token Distribution", zh: "用量排行" } satisfies BilingualLabel,
  modeCostMap: { en: "Mode Cost Map", zh: "按模式统计" } satisfies BilingualLabel,
  gravityField: { en: "Token Cost Gravity Field", zh: "消耗热力分布" } satisfies BilingualLabel,
  totalCost: { en: "Total Cost", zh: "总消耗" } satisfies BilingualLabel,
  identityOverlay: { en: "Identity", zh: "执行标识" } satisfies BilingualLabel,
  costTimeline: { en: "Cost Timeline", zh: "消耗时序" } satisfies BilingualLabel,
  noFieldData: { en: "No token field data", zh: "暂无分布数据" } satisfies BilingualLabel,
  hotPaths: { en: "Hot Paths (token influence)", zh: "高消耗因果路径" } satisfies BilingualLabel,
  byPhase: { en: "By Phase", zh: "分阶段统计" } satisfies BilingualLabel,
  loadingField: { en: "Loading token field...", zh: "正在加载追踪数据…" } satisfies BilingualLabel,
  tabOverview: { en: "Overview", zh: "总览" } satisfies BilingualLabel,
  tabEvents: { en: "Events", zh: "消耗事件" } satisfies BilingualLabel,
  tabField: { en: "Field", zh: "热力分布" } satisfies BilingualLabel,
  tabBinding: { en: "Binding", zh: "执行归因" } satisfies BilingualLabel,
  tabInfluence: { en: "Influence", zh: "因果权重" } satisfies BilingualLabel,
  tabIdentity: { en: "Identity", zh: "执行标识" } satisfies BilingualLabel,
  tracePlaceholder: { en: "trace_id", zh: "输入 trace_id" } satisfies BilingualLabel,
  loadTrace: { en: "LOAD", zh: "查询" } satisfies BilingualLabel,
  refresh: { en: "Refresh", zh: "刷新" } satisfies BilingualLabel,
  traceList: { en: "Trace List", zh: "追踪列表" } satisfies BilingualLabel,
  traceCount: { en: "traces", zh: "条追踪" } satisfies BilingualLabel,
  noTraces: { en: "No traces", zh: "暂无追踪记录" } satisfies BilingualLabel,
  noEvents: { en: "No token events", zh: "暂无消耗事件" } satisfies BilingualLabel,
  noBindings: { en: "No bindings", zh: "暂无归因记录" } satisfies BilingualLabel,
  noHotPaths: { en: "No hot paths", zh: "暂无高消耗路径" } satisfies BilingualLabel,
  bindings: { en: "bindings", zh: "条归因" } satisfies BilingualLabel,
  weightedEdges: { en: "Weighted Causal Edges", zh: "加权因果链" } satisfies BilingualLabel,
  selectTrace: {
    en: "Select a trace from the list or enter trace_id",
    zh: "从左侧选择追踪，或输入 trace_id 查询",
  } satisfies BilingualLabel,
  selectEventHint: {
    en: "Click an event to inspect token binding",
    zh: "点击事件可查看消耗归因详情",
  } satisfies BilingualLabel,
  inspector: { en: "Token Inspector", zh: "事件详情" } satisfies BilingualLabel,
  whatHappened: { en: "What happened", zh: "消耗概况" } satisfies BilingualLabel,
  whoTriggered: { en: "Who triggered", zh: "触发来源" } satisfies BilingualLabel,
  whatChanged: { en: "What changed", zh: "关联执行" } satisfies BilingualLabel,
  dimension: { en: "Dimension", zh: "字段" } satisfies BilingualLabel,
  value: { en: "Value", zh: "数值" } satisfies BilingualLabel,
  identityCostBreakdown: { en: "Identity Cost Breakdown", zh: "分阶段消耗明细" } satisfies BilingualLabel,
  nodeCount: { en: "nodes", zh: "个节点" } satisfies BilingualLabel,
  maxWeight: { en: "max weight", zh: "最大权重" } satisfies BilingualLabel,
  consumedSummary: {
    en: "{source} used {total} tokens ({in} in / {out} out)",
    zh: "{source} 消耗 {total} Token（输入 {in} / 输出 {out}）",
  } satisfies BilingualLabel,
  boundToSpine: {
    en: "bound to spine event {id}",
    zh: "归因至脊柱事件 {id}",
  } satisfies BilingualLabel,
  boundEdge: { en: "causal edge {id}", zh: "因果边 {id}" } satisfies BilingualLabel,
  runtimeFallback: { en: "runtime", zh: "运行时" } satisfies BilingualLabel,
  traceSummary: { en: "trace", zh: "追踪" } satisfies BilingualLabel,
  eventsCount: { en: "events", zh: "事件数" } satisfies BilingualLabel,
  gradDelta: { en: "gradient", zh: "梯度" } satisfies BilingualLabel,
  weightShort: { en: "weight", zh: "权重" } satisfies BilingualLabel,
  severityHigh: { en: "HIGH", zh: "高" } satisfies BilingualLabel,
  severityMid: { en: "MEDIUM", zh: "中" } satisfies BilingualLabel,
  baseWeight: { en: "base", zh: "基准" } satisfies BilingualLabel,
  spineEvent: { en: "spine event", zh: "脊柱事件" } satisfies BilingualLabel,
  tokensInOut: { en: "in / out", zh: "输入 / 输出" } satisfies BilingualLabel,
  traceIoLine: {
    en: "{in} in · {out} out · {mode}",
    zh: "输入 {in} · 输出 {out} · {mode}",
  } satisfies BilingualLabel,
  eventSpineLine: {
    en: "spine {id} · {in} in / {out} out",
    zh: "脊柱事件 {id} · 输入 {in} / 输出 {out}",
  } satisfies BilingualLabel,
  hotPathWeight: {
    en: "weight {w} · {sev}",
    zh: "权重 {w} · {sev}",
  } satisfies BilingualLabel,
  edgeWeightLine: {
    en: "base {base} · weight {w}",
    zh: "基准 {base} · 权重 {w}",
  } satisfies BilingualLabel,
  guideTitle: { en: "How to record real token usage", zh: "如何记录真实 Token 消耗" } satisfies BilingualLabel,
  guideIntro: {
    en: "The observatory shows provider-reported usage only when chat goes through an external LLM. The built-in L0 kernel uses character-based estimates.",
    zh: "算力观测台在外部大模型参与对话时，显示服务商返回的真实 Token；使用内置 L0 认知内核时，显示按字数估算的参考值。",
  } satisfies BilingualLabel,
  guideStep1Title: { en: "Open model settings", zh: "打开模型接口配置" } satisfies BilingualLabel,
  guideStep1Body: {
    en: "Sidebar → Model API (LLM). Pick DeepSeek, OpenAI-compatible, or Ollama local.",
    zh: "左侧导航 →「模型接口」。选择 DeepSeek、OpenAI 兼容接口，或 Ollama 本地。",
  } satisfies BilingualLabel,
  guideStep2Title: { en: "Fill connection details", zh: "填写连接信息" } satisfies BilingualLabel,
  guideStep2Body: {
    en: "Cloud: Base URL + Model ID + API Key (e.g. DeepSeek https://api.deepseek.com, deepseek-v4-flash).\nOllama: Base URL http://localhost:11434, model name e.g. llama3.2 — no API Key. Start Ollama service first.",
    zh: "云端：Base URL + Model ID + API Key（例：DeepSeek 填 https://api.deepseek.com，模型 deepseek-v4-flash）。\nOllama：Base URL 填 http://localhost:11434，模型名如 llama3.2，无需 Key；需先启动 Ollama 服务。",
  } satisfies BilingualLabel,
  guideStep3Title: { en: "Save and test", zh: "保存并测试连通" } satisfies BilingualLabel,
  guideStep3Body: {
    en: "Click Save. The backend runs a connectivity test. Fix API Key or URL if the test fails, then save again.",
    zh: "点击「保存配置」，后端会执行连通性测试。若失败请检查 Key / Base URL / 模型名，修正后重新保存。",
  } satisfies BilingualLabel,
  guideStep4Title: { en: "Select model in workbench", zh: "在工作台选用该模型" } satisfies BilingualLabel,
  guideStep4Body: {
    en: "After a successful save, the model becomes default. Chat from Workbench must use that external model (not CNexus Local only) so each turn reports real usage.",
    zh: "保存成功后该模型会设为默认。请在「工作台」对话，并确保当前选用的是已配置的外部模型（而非仅 CNexus Local），每次对话才会写入真实 Token。",
  } satisfies BilingualLabel,
  guideStep5Title: { en: "Refresh observatory", zh: "回到观测台刷新" } satisfies BilingualLabel,
  guideStep5Body: {
    en: "Return here and click Refresh. Traces tagged provider show API usage; estimated traces are from the offline kernel.",
    zh: "返回本页点击「刷新」。列表中标记「真实」的为服务商回报；标记「估算」的为内置内核按字数推算的参考值。",
  } satisfies BilingualLabel,
  guideNoteEstimated: {
    en: "Tip: L0 kernel-only chat ≈ 0.75 tokens per character (reference). External LLM chat uses prompt_tokens / completion_tokens from the provider.",
    zh: "提示：仅走内置 L0 内核时，Token ≈ 字数 × 0.75（估算参考）。走外部大模型时，使用接口返回的 prompt_tokens / completion_tokens（真实计量）。",
  } satisfies BilingualLabel,
  guideOpenLlmConfig: { en: "Open Model API settings", zh: "前往模型接口配置" } satisfies BilingualLabel,
  traceSourceProvider: { en: "provider", zh: "真实" } satisfies BilingualLabel,
  traceSourceEstimated: { en: "estimated", zh: "估算" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const navL = {
  executionSpine: { en: "Execution Spine", zh: "执行观测" } satisfies BilingualLabel,
  executionSpineSub: {
    en: "Identity · Trace · Causal · State",
    zh: "标识 · 追踪 · 因果 · 状态",
  } satisfies BilingualLabel,
  debuggerLegacy: { en: "Debugger (legacy)", zh: "旧版调试器" } satisfies BilingualLabel,
  debuggerSub: {
    en: "GTBS projection fallback",
    zh: "GTBS 兼容视图",
  } satisfies BilingualLabel,
  flow: { en: "Neural Flow", zh: "记忆流图" } satisfies BilingualLabel,
  flowSub: { en: "Factor chain graph", zh: "关联网络" } satisfies BilingualLabel,
  workbench: { en: "Workbench", zh: "工作台" } satisfies BilingualLabel,
  workbenchSub: {
    en: "Chat · Suggestions · Upload",
    zh: "对话 · 建议 · 上传",
  } satisfies BilingualLabel,
  summaryMode: { en: "Value Summary", zh: "运行摘要" } satisfies BilingualLabel,
  summaryModeSub: {
    en: "CSE narrative · runtime pulse",
    zh: "CSE 叙事 · 运行脉搏",
  } satisfies BilingualLabel,
  summaryHint: {
    en: "Auto-synthesized runtime summary from CSE",
    zh: "CSE 自动归纳的运行摘要与观测卡片",
  } satisfies BilingualLabel,
  summaryPageTitle: { en: "CNexus Value Summary", zh: "CNexus 运行摘要" } satisfies BilingualLabel,
  summaryPageHint: {
    en: "Narrative summary · goal · identity · belief · focus",
    zh: "叙事摘要 · 目标 · 身份 · 信念 · 工作焦点",
  } satisfies BilingualLabel,
  learnMode: { en: "Learn Mode", zh: "认知教学" } satisfies BilingualLabel,
  learnModeSub: {
    en: "Human narrative",
    zh: "人类叙事",
  } satisfies BilingualLabel,
  learnHint: {
    en: "Turn ExecutionRecord into beginner-friendly AI behavior stories",
    zh: "把 ExecutionRecord 翻译成初学者能理解的 AI 行为故事",
  } satisfies BilingualLabel,
  learnPageTitle: { en: "CNexus Learn Mode", zh: "CNexus 认知教学" } satisfies BilingualLabel,
  learnPageHint: {
    en: "Beginner · intermediate · expert views from one trace",
    zh: "初学者 · 进阶 · 工程视角，基于单次执行记录",
  } satisfies BilingualLabel,
  debuggerHint: {
    en: "Legacy GTBS projection — prefer Learn Mode",
    zh: "旧版视图，建议使用认知教学",
  } satisfies BilingualLabel,
  debuggerTitle: { en: "CNexus Debugger (legacy)", zh: "CNexus 旧版调试器" } satisfies BilingualLabel,
  debuggerPageHint: {
    en: "GTBS fallback — not truth source",
    zh: "GTBS 兼容层，非权威数据源",
  } satisfies BilingualLabel,
  runtimeReader: { en: "Cognitive execution reader", zh: "运行时观测" } satisfies BilingualLabel,

  demoMode: { en: "Demo mode", zh: "演示模式" } satisfies BilingualLabel,
  connectedRuntime: { en: "Runtime connected", zh: "运行时已连接" } satisfies BilingualLabel,
  notConnected: { en: "Not connected", zh: "未连接" } satisfies BilingualLabel,
  warmingUp: { en: "Starting…", zh: "正在启动" } satisfies BilingualLabel,
  systemHealth: { en: "System health", zh: "系统状态" } satisfies BilingualLabel,
  views: { en: "Views", zh: "视图" } satisfies BilingualLabel,
  networkSection: { en: "Network topology", zh: "网络拓扑" } satisfies BilingualLabel,
  missionControl: { en: "Mission Control", zh: "网络驾驶舱" } satisfies BilingualLabel,
  networkConnect: { en: "Connect & DHT", zh: "连接与寻址" } satisfies BilingualLabel,
  networkConnectSub: { en: "ICE · STUN · Kademlia", zh: "打洞 · STUN · DHT" } satisfies BilingualLabel,
  networkOps: { en: "Network ops", zh: "网络操作" } satisfies BilingualLabel,
  networkOpsSub: { en: "Replay · index · queue", zh: "回放 · 索引 · 队列" } satisfies BilingualLabel,
  networkAssets: { en: "Cognitive assets", zh: "认知资产" } satisfies BilingualLabel,
  networkAssetsSub: { en: "Upload · CLIP · reflect", zh: "上传 · 向量 · 反思" } satisfies BilingualLabel,
  networkOpsPageTitle: { en: "Network operations", zh: "网络操作中心" } satisfies BilingualLabel,
  networkOpsPageHint: {
    en: "One-click actions that previously required curl or shell env vars",
    zh: "将原先需要 curl / 环境变量的操作改为一键执行",
  } satisfies BilingualLabel,
  networkConnectPageTitle: { en: "Connectivity & discovery", zh: "连接与邻居发现" } satisfies BilingualLabel,
  networkConnectPageHint: {
    en: "DHT lookup, ICE path probe, and network firewall",
    zh: "DHT 寻址、ICE 路径探测与网络防火墙",
  } satisfies BilingualLabel,
  networkAssetsPageTitle: { en: "Cognitive assets & metacognition", zh: "认知资产与元认知" } satisfies BilingualLabel,
  networkAssetsPageHint: {
    en: "Asset ingest, semantic index, and self-reflection over AuditLog",
    zh: "资产入库、语义索引与基于 AuditLog 的元认知反思",
  } satisfies BilingualLabel,
  networkOpReplayTitle: { en: "Log replay (cognitive resurrection)", zh: "记忆重塑 / Log Replay" } satisfies BilingualLabel,
  networkOpReplayHint: {
    en: "Snapshot + incremental replay from AuditLog. Use after Genesis sync or node wipe.",
    zh: "从 AuditLog 快照+增量回放认知态。Genesis 同步后或节点清空后执行。",
  } satisfies BilingualLabel,
  networkOpReplayRun: { en: "Run replay (force)", zh: "强制回放" } satisfies BilingualLabel,
  networkOpReindexTitle: { en: "Rebuild vector index", zh: "重建向量索引" } satisfies BilingualLabel,
  networkOpReindexHint: {
    en: "Re-embed all assets (CLIP direct image + text). Equivalent to POST /api/asset/reindex.",
    zh: "对所有资产重新嵌入向量（含 CLIP 图片直嵌）。等同 /api/asset/reindex。",
  } satisfies BilingualLabel,
  networkOpReindexRun: { en: "Reindex assets", zh: "重建索引" } satisfies BilingualLabel,
  networkOpPushQueueTitle: { en: "Process push retry queue", zh: "处理推送重试队列" } satisfies BilingualLabel,
  networkOpPushQueueHint: {
    en: "Retry failed asset pushes to trusted peers with exponential backoff.",
    zh: "对失败的邻居资产推送进行指数退避重试。",
  } satisfies BilingualLabel,
  networkOpPushQueueEnv: {
    en: "Auto-push on upload is enabled by default; set CNEXUS_ASSET_PEER_PUSH=0 to disable",
    zh: "上传后自动推送已默认开启；设置 CNEXUS_ASSET_PEER_PUSH=0 可关闭",
  } satisfies BilingualLabel,
  networkOpPushQueueRun: { en: "Process queue now", zh: "立即处理队列" } satisfies BilingualLabel,
  networkOpReflectTitle: { en: "Metacognitive reflection", zh: "元认知反思" } satisfies BilingualLabel,
  networkOpReflectHint: {
    en: "Analyze last 100 audit events for cognitive bias and domain fixation.",
    zh: "分析最近 100 条审计记录，检测认知偏差与领域固着。",
  } satisfies BilingualLabel,
  networkOpReflectRun: { en: "Run reflection", zh: "开始反思" } satisfies BilingualLabel,
  networkOpRemHint: {
    en: "Deep sleep consolidation — prune weak memory and synthesize facts.",
    zh: "深度睡眠整合 — 修剪弱记忆并合成语义事实。",
  } satisfies BilingualLabel,
  networkEnvSection: { en: "Server env (restart required)", zh: "服务端环境变量（需重启）" } satisfies BilingualLabel,
  networkEnvHint: {
    en: "Set in PowerShell before python app_v2.py. Copy and paste into your terminal.",
    zh: "在运行 python app_v2.py 前的 PowerShell 中设置，可复制下方命令。",
  } satisfies BilingualLabel,
  networkEnvRestart: {
    en: "After changing env vars, restart app_v2.py and rebuild UI: npm run build:personal → copy to CNexus2.0/ui/",
    zh: "修改环境变量后需重启 app_v2.py；前端更新需 npm run build:personal 并同步到 CNexus2.0/ui/",
  } satisfies BilingualLabel,
  networkEnvPeerPush: { en: "Auto-push assets to peers after index", zh: "索引后自动推送到邻居" } satisfies BilingualLabel,
  networkEnvEmbed: { en: "Ollama embedding model for text vectors", zh: "Ollama 文本向量模型" } satisfies BilingualLabel,
  networkEnvBind: { en: "Listen on all interfaces for cross-network P2P", zh: "监听所有网卡以支持跨网段 P2P" } satisfies BilingualLabel,
  networkEnvDht: { en: "Bootstrap DHT peer URL(s)", zh: "DHT 引导节点地址" } satisfies BilingualLabel,
  networkEnvClip: { en: "CLIP ONNX model paths for true image embed", zh: "CLIP ONNX 模型路径（图片直嵌）" } satisfies BilingualLabel,
  networkConnectIce: { en: "NAT type", zh: "NAT 类型" } satisfies BilingualLabel,
  networkFirewall: { en: "Firewall bans", zh: "防火墙封禁" } satisfies BilingualLabel,
  networkConnectPeerTitle: { en: "Connect by PeerID", zh: "按 PeerID 连接" } satisfies BilingualLabel,
  networkConnectPeerHint: {
    en: "Paste the other device's ID — CNexus will auto-discover it on your local network and complete the secure handshake.",
    zh: "粘贴对方设备 ID 即可 — 系统会自动在局域网内寻址并完成安全握手，无需额外配置。",
  } satisfies BilingualLabel,
  networkConnectPeerRun: { en: "Connect & trust", zh: "连接并建立信任" } satisfies BilingualLabel,
  networkConnectOk: { en: "Trusted peer connected", zh: "已建立信任连接" } satisfies BilingualLabel,
  networkConnectHandshakeOk: {
    en: "P2P handshake complete — both sides may sync",
    zh: "P2P 握手完成 — 双方可同步",
  } satisfies BilingualLabel,
  networkConnectHandshakeSkip: {
    en: "Path ok — identity disabled, handshake skipped",
    zh: "路径已通 — 身份模块未启用，跳过握手",
  } satisfies BilingualLabel,
  repairControlTitle: {
    en: "Integrity & repair control",
    zh: "完整性诊断与修复控制",
  } satisfies BilingualLabel,
  repairControlHint: {
    en: "System detected missing chunks after connect. Review the gate decision before executing repair.",
    zh: "连接后系统检测到缺失 chunk。执行修复前请审阅门禁决策。",
  } satisfies BilingualLabel,
  repairControlIntegrityOk: {
    en: "Local chunk store matches manifest — no repair needed.",
    zh: "本地 chunk 与 manifest 一致 — 无需修复。",
  } satisfies BilingualLabel,
  repairControlPhase: { en: "Control phase", zh: "控制面阶段" } satisfies BilingualLabel,
  repairControlMissing: { en: "Missing chunks", zh: "缺失 chunk" } satisfies BilingualLabel,
  repairControlPlans: { en: "Repair plans", zh: "修复计划" } satisfies BilingualLabel,
  repairControlGate: { en: "Execution gate", zh: "执行门禁" } satisfies BilingualLabel,
  repairControlSources: { en: "Suggested sources", zh: "候选来源" } satisfies BilingualLabel,
  repairControlPreviewGate: { en: "Preview gate", zh: "预览门禁" } satisfies BilingualLabel,
  repairControlConfirm: {
    en: "Confirm & execute repair",
    zh: "确认并执行修复",
  } satisfies BilingualLabel,
  repairControlConfirmPrompt: {
    en: "Execute verified chunk repair from the connected peer? This will pull and verify blobs locally.",
    zh: "从已连接节点拉取并验证缺失 chunk？数据将在本地校验后写入。",
  } satisfies BilingualLabel,
  repairControlExecuteOk: {
    en: "Repair executed — chunks verified locally.",
    zh: "修复已执行 — chunk 已在本地校验写入。",
  } satisfies BilingualLabel,
  repairControlExecuteDenied: {
    en: "Execution denied — probe evidence or policy blocked repair.",
    zh: "执行被拒绝 — probe 证据不足或策略不允许。",
  } satisfies BilingualLabel,
  repairControlConfirmRequired: {
    en: "User confirmation required before execute.",
    zh: "执行前需要用户确认。",
  } satisfies BilingualLabel,
  networkErrorNoViablePath: {
    en: "No viable path (no_viable_path) — ensure the other device is running CNexus and on the same network, then retry.",
    zh: "无法建立连接路径（no_viable_path）— 请确认对方 CNexus 已启动且与您在同一网络，然后重试。",
  } satisfies BilingualLabel,
  networkErrorPeerOffline: {
    en: "Peer not found — ensure the other device is online on the same Wi‑Fi/LAN and CNexus is running.",
    zh: "未找到对方设备 — 请确认对方 CNexus 已启动，且与您连接同一 Wi‑Fi/局域网。",
  } satisfies BilingualLabel,
  networkErrorHostUnreachable: {
    en: "Peer unreachable — check that CNexus is running on the other device and your firewall allows port 7864.",
    zh: "对方设备不可达 — 请确认对方 CNexus 正在运行，且防火墙未拦截 7864 端口。",
  } satisfies BilingualLabel,
  networkErrorMissingPeerId: {
    en: "Missing peer ID — paste the other node's Ed25519 pubkey in the field above before connecting.",
    zh: "未填写对方 ID — 请先在上方输入框粘贴对方的节点公钥，再点击连接。",
  } satisfies BilingualLabel,
  networkErrorConnectivityUnavailable: {
    en: "Connectivity manager unavailable — restart CNexus or enable network stack.",
    zh: "连接管理器不可用 — 请重启 CNexus 或启用网络栈。",
  } satisfies BilingualLabel,
  networkErrorDhtUnavailable: {
    en: "DHT unavailable — set CNEXUS_DHT_BOOTSTRAP and restart the gateway.",
    zh: "DHT 不可用 — 请配置 CNEXUS_DHT_BOOTSTRAP 后重启网关。",
  } satisfies BilingualLabel,
  networkErrorFirewallBlocked: {
    en: "Connection blocked by firewall or low trust score.",
    zh: "连接被防火墙拦截或信誉分过低。",
  } satisfies BilingualLabel,
  networkErrorHandshakeFailed: {
    en: "P2P handshake failed — verify the peer ID and that both nodes use compatible identity keys.",
    zh: "P2P 握手失败 — 请核对对方 ID 是否正确，并确认双方身份密钥可用。",
  } satisfies BilingualLabel,
  networkConnectPeerPlaceholder: {
    en: "Other node's ID — 64-char Ed25519 hex pubkey",
    zh: "对方节点 ID（64 位 Ed25519 十六进制公钥）",
  } satisfies BilingualLabel,
  networkTrustedPeersTitle: { en: "Trusted peers", zh: "信任邻居" } satisfies BilingualLabel,
  networkTrustedPeersEmpty: {
    en: "No trusted peers yet — connect by Peer ID above",
    zh: "暂无信任邻居 — 请在上方输入 Peer ID 连接",
  } satisfies BilingualLabel,
  networkBanTitle: { en: "Ban malicious peer", zh: "封禁恶意节点" } satisfies BilingualLabel,
  networkBanHint: {
    en: "Remove from routing table and reputation registry. Blocks gossip/DHT before consensus.",
    zh: "从路由表与信誉库剔除，在共识层之前于物理层阻断。",
  } satisfies BilingualLabel,
  networkBanRun: { en: "Ban peer", zh: "封禁节点" } satisfies BilingualLabel,
  networkBanConfirm: { en: "Ban this peer from the network?", zh: "确认封禁该节点？" } satisfies BilingualLabel,
  networkBanDone: { en: "Peer banned and removed from registry", zh: "已封禁并从邻居表移除" } satisfies BilingualLabel,
  missionControlSub: {
    en: "Peers · sync · topology",
    zh: "邻居 · 同步 · 拓扑",
  } satisfies BilingualLabel,
  missionControlPageTitle: { en: "CNexus Mission Control", zh: "CNexus 网络驾驶舱" } satisfies BilingualLabel,
  missionControlPageHint: {
    en: "Distributed peers · audit sync · live topology",
    zh: "分布式邻居 · 审计链同步 · 实时拓扑",
  } satisfies BilingualLabel,
  missionControlHint: {
    en: "Monitor trusted peers, hash alignment, and gossip sync health",
    zh: "监控信任邻居、哈希对齐与 Gossip 同步状态",
  } satisfies BilingualLabel,
  missionControlUptime: { en: "Uptime", zh: "运行时间" } satisfies BilingualLabel,
  missionControlResources: { en: "CPU / RAM", zh: "CPU / 内存" } satisfies BilingualLabel,
  missionControlPsutilHint: {
    en: "Install psutil for host metrics",
    zh: "安装 psutil 可启用主机指标",
  } satisfies BilingualLabel,
  missionControlChain: { en: "Audit head", zh: "审计链头" } satisfies BilingualLabel,
  missionControlPeers: { en: "Peers online", zh: "邻居在线" } satisfies BilingualLabel,
  missionControlAligned: { en: "aligned", zh: "已对齐" } satisfies BilingualLabel,
  missionControlTopology: { en: "Topology", zh: "拓扑视图" } satisfies BilingualLabel,
  missionControlSyncLog: { en: "Sync log", zh: "同步日志" } satisfies BilingualLabel,
  missionControlSyncEmpty: { en: "No sync events yet", zh: "暂无同步记录" } satisfies BilingualLabel,
  missionControlPeerMap: { en: "Peer map", zh: "邻居列表" } satisfies BilingualLabel,
  missionControlPeersEmpty: {
    en: "No trusted peers — complete P2P handshake first",
    zh: "暂无信任邻居 — 完成 P2P 握手后显示",
  } satisfies BilingualLabel,
  missionControlRem: { en: "REM sleep", zh: "REM 睡眠" } satisfies BilingualLabel,
  missionControlRemLast: { en: "Last REM cycle", zh: "上次 REM 周期" } satisfies BilingualLabel,
  missionControlRemNever: { en: "Not run yet", zh: "尚未执行" } satisfies BilingualLabel,
  missionControlRemRunning: { en: "Consolidating…", zh: "正在整合…" } satisfies BilingualLabel,
  missionControlConsensus: { en: "Consensus negotiation", zh: "共识协商" } satisfies BilingualLabel,
  missionControlConsensusMode: { en: "Mode", zh: "协商模式" } satisfies BilingualLabel,
  missionControlConsensusOptimistic: { en: "Optimistic", zh: "乐观" } satisfies BilingualLabel,
  missionControlConsensusConservative: { en: "Conservative", zh: "谨慎" } satisfies BilingualLabel,
  missionControlConsensusTrust: { en: "Min trust", zh: "最低信任" } satisfies BilingualLabel,
  missionControlConsensusQuorum: { en: "Quorum", zh: "法定人数" } satisfies BilingualLabel,
  missionControlConsensusReputation: { en: "Reputation peers", zh: "信誉邻居" } satisfies BilingualLabel,
  missionControlConsensusRecent: { en: "Recent negotiations", zh: "近期协商" } satisfies BilingualLabel,
  missionControlConsensusRecentEmpty: {
    en: "No fork negotiations yet",
    zh: "暂无分叉协商记录",
  } satisfies BilingualLabel,
  missionControlConsensusReorg: { en: "Chain reorg", zh: "链重组" } satisfies BilingualLabel,
  missionControlConsensusFailed: { en: "Negotiation failed", zh: "协商失败" } satisfies BilingualLabel,
  missionControlConsensusAligned: { en: "Aligned", zh: "已对齐" } satisfies BilingualLabel,
  missionControlConsensusBlacklisted: { en: "Blacklisted", zh: "已拉黑" } satisfies BilingualLabel,
  missionControlCognitiveAudit: { en: "Cognitive audit console", zh: "认知审计台" } satisfies BilingualLabel,
  missionControlCognitiveAuditHint: {
    en: "Inspect negotiation forks, memory pairs, and emergent synthesis conclusions",
    zh: "检视协商分叉、原始记忆对与涌现消解结论",
  } satisfies BilingualLabel,
  missionControlCognitiveAuditEmpty: {
    en: "No auto-resolved negotiation conflicts yet",
    zh: "尚无自动消解的协商冲突",
  } satisfies BilingualLabel,
  missionControlCognitiveAuditLocal: { en: "Local memory", zh: "本地记忆" } satisfies BilingualLabel,
  missionControlCognitiveAuditRemote: { en: "Remote memory", zh: "远端记忆" } satisfies BilingualLabel,
  missionControlCognitiveAuditSynthesis: { en: "Emergent synthesis", zh: "涌现消解" } satisfies BilingualLabel,
  missionControlCognitiveAuditForked: { en: "Forked narrative", zh: "分叉叙事" } satisfies BilingualLabel,
  missionControlCognitiveAuditMerged: { en: "Merged", zh: "已合并" } satisfies BilingualLabel,
  missionControlCognitiveAuditEntropy: { en: "Consensus entropy", zh: "共识熵" } satisfies BilingualLabel,
  missionControlCognitiveAuditView: { en: "View audit", zh: "查看审计" } satisfies BilingualLabel,
  missionControlCognitiveAuditConflicts: { en: "Conflicts", zh: "冲突" } satisfies BilingualLabel,
  missionControlCognitiveAuditLlmAuto: {
    en: "LLM auto-resolve on negotiation failure",
    zh: "协商失败时 LLM 自动消解",
  } satisfies BilingualLabel,
  missionControlCognitiveAuditLlmHeuristic: {
    en: "Heuristic auto-resolve (fast)",
    zh: "启发式自动消解（快速）",
  } satisfies BilingualLabel,
  missionControlCognitivePruning: { en: "Cognitive pruning", zh: "认知修剪" } satisfies BilingualLabel,
  missionControlCognitivePruningHint: {
    en: "Archive cold unreferenced blocks and summarize recurring dispute points",
    zh: "归档冷记忆块，并将反复争议点压缩为知识结论",
  } satisfies BilingualLabel,
  missionControlCognitivePruningRun: { en: "Run prune cycle", zh: "执行修剪" } satisfies BilingualLabel,
  missionControlCognitivePruningPreview: { en: "Preview prune", zh: "预览修剪" } satisfies BilingualLabel,
  missionControlEntropy: { en: "Consensus entropy", zh: "共识熵" } satisfies BilingualLabel,
  missionControlEntropyHint: {
    en: "Mesh-wide XOR entropy seed drives emergent inference temperature",
    zh: "全网 XOR 熵种子驱动涌现推理温度",
  } satisfies BilingualLabel,
  missionControlReplayRun: { en: "Force replay", zh: "强制回放" } satisfies BilingualLabel,
  missionControlReplayDue: { en: "Replay due", zh: "待回放" } satisfies BilingualLabel,
  missionControlAuditApply: { en: "Apply synthesis", zh: "应用消解" } satisfies BilingualLabel,
  missionControlAuditResolve: { en: "Re-resolve", zh: "重新消解" } satisfies BilingualLabel,
  missionControlAuditDiscuss: { en: "Discuss in emergent chat", zh: "涌现模式讨论" } satisfies BilingualLabel,
  missionControlAutoConflict: {
    en: "Auto conflict resolution on negotiation failure",
    zh: "协商失败自动冲突消解",
  } satisfies BilingualLabel,
  missionControlPeerConnect: { en: "Connect", zh: "连接" } satisfies BilingualLabel,
  missionControlPeerSync: { en: "Force sync", zh: "强制同步" } satisfies BilingualLabel,
  missionControlPeerGenesis: { en: "Genesis sync", zh: "Genesis 同步" } satisfies BilingualLabel,
  missionControlReputationBlacklist: { en: "Blacklist", zh: "拉黑" } satisfies BilingualLabel,
  missionControlReputationRestore: { en: "Restore trust", zh: "恢复信任" } satisfies BilingualLabel,
  missionControlAwakeningRetryReplay: { en: "Retry replay", zh: "重试回放" } satisfies BilingualLabel,
  missionControlAwakeningRetryReindex: { en: "Retry vector index", zh: "重建向量" } satisfies BilingualLabel,
  missionControlAssets: { en: "Cognitive assets", zh: "认知资产入口" } satisfies BilingualLabel,
  missionControlAssetsHint: {
    en: "Store blobs locally; AuditLog keeps hash pointers + summaries",
    zh: "物理文件存本地，AuditLog 仅记录哈希指针与摘要",
  } satisfies BilingualLabel,
  missionControlAssetCode: { en: "Code snippet", zh: "代码片段" } satisfies BilingualLabel,
  missionControlAssetImage: { en: "Image upload", zh: "图片上传" } satisfies BilingualLabel,
  missionControlAssetSearch: { en: "Search assets", zh: "搜索资产" } satisfies BilingualLabel,
  missionControlAssetProject: { en: "Also project to graph", zh: "同时投射到图谱" } satisfies BilingualLabel,
  missionControlAssetIndexed: { en: "Indexed", zh: "已索引" } satisfies BilingualLabel,
  missionControlAssetEmpty: { en: "No matching assets", zh: "无匹配资产" } satisfies BilingualLabel,
  missionControlAssetSemantic: { en: "Semantic search (CLIP)", zh: "语义搜索 (向量)" } satisfies BilingualLabel,
  missionControlAssetImageSearchHint: {
    en: "Second picker: image-to-image CLIP search (semantic mode)",
    zh: "下方第二个选择器：图片直嵌相似搜索（需开启语义）",
  } satisfies BilingualLabel,
  missionControlAssetPeerPush: { en: "Auto-push to peers", zh: "自动推送到邻居" } satisfies BilingualLabel,
  missionControlAssetPeerPushScheduled: { en: "Peer push scheduled", zh: "已调度邻居推送" } satisfies BilingualLabel,
  missionControlAssetPeerPull: { en: "Pull from peer", zh: "从邻居拉取" } satisfies BilingualLabel,
  missionControlAssetPeerPullDone: { en: "Asset pulled locally", zh: "已拉取到本地" } satisfies BilingualLabel,
  missionControlAssetRemotePreview: { en: "Remote preview only", zh: "仅远程预览" } satisfies BilingualLabel,
  missionControlResilience: { en: "Network resilience", zh: "网络健壮性" } satisfies BilingualLabel,
  missionControlResilienceFortress: { en: "Fortress", zh: "堡垒级" } satisfies BilingualLabel,
  missionControlResilienceStrong: { en: "Strong", zh: "强健" } satisfies BilingualLabel,
  missionControlResilienceRecovering: { en: "Recovering", zh: "恢复中" } satisfies BilingualLabel,
  missionControlResilienceCritical: { en: "Critical", zh: "脆弱" } satisfies BilingualLabel,
  missionControlAwakening: { en: "Awakening", zh: "生命唤醒" } satisfies BilingualLabel,
  missionControlAwakeningAlive: { en: "Alive", zh: "在线" } satisfies BilingualLabel,
  missionControlAwakeningHint: {
    en: "Genesis sync → log replay → vector warmup",
    zh: "基因同步 → 记忆重塑 → 向量热身",
  } satisfies BilingualLabel,
  missionControlAwakeningGenesis: { en: "Phase 1: Genesis", zh: "阶段 1: 基因同步" } satisfies BilingualLabel,
  missionControlAwakeningReplay: { en: "Phase 2: Log Replay", zh: "阶段 2: 记忆重塑" } satisfies BilingualLabel,
  missionControlAwakeningVector: { en: "Phase 3: Vector Index", zh: "阶段 3: 向量热身" } satisfies BilingualLabel,
  missionControlMetaReflection: { en: "Metacognition", zh: "元认知反思" } satisfies BilingualLabel,
  missionControlMetaReflectionHint: {
    en: "Reflect on cognitive biases from AuditLog + vector index",
    zh: "基于 AuditLog 与向量索引，反思认知偏差与领域倾斜",
  } satisfies BilingualLabel,
  missionControlMetaReflectionRun: { en: "Run reflection", zh: "开始反思" } satisfies BilingualLabel,
  missionControlMetaReflectionLlm: { en: "Use LLM synthesis", zh: "LLM 深度综合" } satisfies BilingualLabel,
  missionControlMetaReflectionSource: { en: "Source", zh: "来源" } satisfies BilingualLabel,
  missionControlGenesis: { en: "Genesis sync", zh: "全量创世同步" } satisfies BilingualLabel,
  remSleepTrigger: { en: "Run REM now", zh: "手动触发 REM" } satisfies BilingualLabel,
  remSleepBusy: { en: "REM running…", zh: "REM 执行中…" } satisfies BilingualLabel,
  remSleepConfirm: {
    en: "Force a REM consolidation cycle? Low-value memories may be pruned and summaries generated.",
    zh: "确定手动触发 REM 深度睡眠？系统将修剪低价值记忆并尝试生成语义摘要。",
  } satisfies BilingualLabel,
  remSleepSkipped: { en: "REM skipped", zh: "REM 已跳过" } satisfies BilingualLabel,
  quickActions: { en: "Quick actions", zh: "快捷操作" } satisfies BilingualLabel,
  refresh: { en: "Refresh", zh: "刷新" } satisfies BilingualLabel,
  clearMemory: { en: "Clear memory", zh: "一键清空" } satisfies BilingualLabel,
  clearMemoryConfirm: {
    en: "Clear memory blocks, graph nodes, and chat history? Foundation / constitution memories are preserved.",
    zh: "确定清空记忆、图谱节点与对话记录？认知宪法与系统基石记忆将保留。",
  } satisfies BilingualLabel,
  clearMemoryBusy: { en: "Clearing…", zh: "清空中…" } satisfies BilingualLabel,
  switchDataSource: { en: "Switch data source", zh: "切换数据源" } satisfies BilingualLabel,

  flowHint: {
    en: "Memory factor chain · Obsidian-style graph view",
    zh: "记忆关联网络 · 图谱视图",
  } satisfies BilingualLabel,
  workbenchHint: {
    en: "Chat with the system, view suggestions, and upload files",
    zh: "系统对话、今日建议与文件上传",
  } satisfies BilingualLabel,
  workbenchOffline: {
    en: "Runtime not connected — start API or switch to Demo",
    zh: "未连接运行时，请先启动 API 或切换演示模式",
  } satisfies BilingualLabel,
  workbenchWarming: {
    en: "Waking core runtime — chat unlocks when ready; document upload available via Gateway",
    zh: "正在唤醒核心…对话就绪后开放；文档上传经 Gateway 可用",
  } satisfies BilingualLabel,

  flowPageTitle: { en: "CNexus Neural Flow", zh: "CNexus 记忆流图" } satisfies BilingualLabel,
  flowPageHint: {
    en: "Factor chain · Graph view · Adjustable forces",
    zh: "关联网络 · 力导向图 · 参数可调",
  } satisfies BilingualLabel,
  workbenchPageTitle: { en: "CNexus Workbench", zh: "CNexus 工作台" } satisfies BilingualLabel,
  workbenchDemoHint: { en: "Demo", zh: "演示数据" } satisfies BilingualLabel,
  workbenchConnectedHint: { en: "Connected", zh: "已连接" } satisfies BilingualLabel,
  workbenchOfflineHint: { en: "Not connected", zh: "未连接" } satisfies BilingualLabel,

  tokenObservatory: { en: "Token Observatory", zh: "算力观测" } satisfies BilingualLabel,
  tokenObservatorySub: {
    en: "Console · Events · Field · Influence",
    zh: "总览 · 事件 · 分布 · 归因",
  } satisfies BilingualLabel,
  tokenPageTitle: { en: "CNexus Token Observatory", zh: "CNexus 算力观测" } satisfies BilingualLabel,
  tokenPageHint: {
    en: "Token cost physics · binding · gravity field · causal influence",
    zh: "消耗归因 · 热力分布 · 因果权重 · 执行标识对照",
  } satisfies BilingualLabel,

  llmConfig: { en: "LLM API", zh: "模型接口" } satisfies BilingualLabel,
  llmConfigSub: {
    en: "Cloud APIs · Ollama local",
    zh: "云端 API · Ollama 本地",
  } satisfies BilingualLabel,
  llmConfigHint: {
    en: "Configure DeepSeek, OpenAI-compatible APIs, and local Ollama",
    zh: "配置 DeepSeek、OpenAI 兼容接口与本地 Ollama",
  } satisfies BilingualLabel,
  llmConfigPageTitle: { en: "CNexus LLM Configuration", zh: "CNexus 模型接口配置" } satisfies BilingualLabel,
  llmConfigPageHint: {
    en: "Provider · Base URL · Model · API Key · Ollama service",
    zh: "服务商 · 接口地址 · 模型 · API Key · Ollama 服务",
  } satisfies BilingualLabel,

  debuggerHeader: { en: "CNexus Debugger", zh: "CNexus 调试器" } satisfies BilingualLabel,
  debuggerHeaderSub: {
    en: "Event Spine · Causal Graph · Control + State Inspector",
    zh: "事件流 · 因果图 · 管控与状态",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const homeL = {
  valueSummary: { en: "Value Summary", zh: "运行摘要" } satisfies BilingualLabel,
  example: { en: "Example", zh: "示例" } satisfies BilingualLabel,
  valueLoadError: { en: "Failed to load value summary", zh: "摘要加载失败" } satisfies BilingualLabel,
  valueEmptyLive: {
    en: "Connect Runtime and use Ask, Capture, or Analyze to build a summary.",
    zh: "连接运行时后，通过提问、记录或分析，系统会自动归纳运行摘要",
  } satisfies BilingualLabel,
  valueEmptyIdle: {
    en: "No summary yet — it will appear as you use the system.",
    zh: "暂无摘要，使用系统后会自动生成",
  } satisfies BilingualLabel,
  neuralFlow: { en: "Memory Flow", zh: "记忆流图" } satisfies BilingualLabel,
  neuralFlowSub: {
    en: "Factor Graph — memory anchor topology from dialogue & documents",
    zh: "因子网络图 — 由对话与文档编织的记忆锚点拓扑",
  } satisfies BilingualLabel,
  neuralFlowVitals: {
    en: "Nodes from /api/status memory_items. Each chat or upload crystallizes new neurons on the right.",
    zh: "数据来自 memory_items 记忆锚点。每次对话或上传，右侧将结晶出新神经元节点与连线。",
  } satisfies BilingualLabel,
  flowLayerTitle: { en: "Cognitive flow", zh: "认知流动层" } satisfies BilingualLabel,
  workbenchLink: { en: "Workbench", zh: "工作台" } satisfies BilingualLabel,
  dashboard: { en: "Dashboard", zh: "运行面板" } satisfies BilingualLabel,
  sync: { en: "Sync", zh: "同步" } satisfies BilingualLabel,
  recentPulse: { en: "Recent pulse", zh: "最近动态" } satisfies BilingualLabel,
  graphEmpty: {
    en: "No memory anchors yet — chat or upload on Workbench to grow the network",
    zh: "暂无记忆锚点，请在工作台对话或上传文档，网络将从右侧结晶生长",
  } satisfies BilingualLabel,
  graphTitle: { en: "Factor Graph", zh: "因子网络图" } satisfies BilingualLabel,
  graphNodeCount: {
    en: "{n} anchors · {e} links",
    zh: "{n} 个锚点 · {e} 条连线",
  } satisfies BilingualLabel,
  tabTrace: { en: "Trace log", zh: "运行记录" } satisfies BilingualLabel,
  tabSettings: { en: "Runtime mode", zh: "运行模式" } satisfies BilingualLabel,
  tabModel: { en: "Model API", zh: "大模型 API" } satisfies BilingualLabel,
  traceStats: {
    en: "{logs} events · {traces} traces",
    zh: "共 {logs} 条事件 · {traces} 条追踪",
  } satisfies BilingualLabel,
  refreshing: { en: "Refreshing…", zh: "刷新中…" } satisfies BilingualLabel,
  noTraceLogs: { en: "No trace logs yet", zh: "暂无运行记录" } satisfies BilingualLabel,
  logLevelError: { en: "Error", zh: "错误" } satisfies BilingualLabel,
  logLevelWarn: { en: "Warn", zh: "警告" } satisfies BilingualLabel,
  logLevelOk: { en: "OK", zh: "正常" } satisfies BilingualLabel,
  runtimeModeHint: {
    en: "Pick a runtime mode for your machine (local config, safe to revert)",
    zh: "选择适合本机的运行模式（本地配置，可随时改回）",
  } satisfies BilingualLabel,
  concurrencyMax: { en: "Concurrency (max 2)", zh: "并发数（最大 2）" } satisfies BilingualLabel,
  autoSynth: { en: "Auto-update cognitive summary", zh: "自动更新认知结论" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const footerL = {
  dataFlowGuide: { en: "Data flow", zh: "数据流向" } satisfies BilingualLabel,
  chatFlow: {
    en: "Chat → Goal/Belief/Memory → Reflection",
    zh: "对话流：对话 → 目标/信念/记忆 → 反思",
  } satisfies BilingualLabel,
  browseFlow: {
    en: "Memory → Identity/Goal/Belief → Governance",
    zh: "浏览流：记忆 → 身份/目标/信念 → 治理",
  } satisfies BilingualLabel,
  importFlow: {
    en: "Upload → Episodic → Synthesis → Goal Layer",
    zh: "导入流：上传 → 情景记忆 → 综合 → 目标层",
  } satisfies BilingualLabel,
  corePrinciples: { en: "Core principles", zh: "核心设计原则" } satisfies BilingualLabel,
  p4Loop: { en: "P4 closed loop", zh: "P4 闭环支撑" } satisfies BilingualLabel,
  health: { en: "health", zh: "健康" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const bootL = {
  config: { en: "Loading config", zh: "加载配置" } satisfies BilingualLabel,
  hydrating: { en: "Starting", zh: "正在启动" } satisfies BilingualLabel,
  sync: { en: "Connecting runtime", zh: "连接运行时" } satisfies BilingualLabel,
  runtimeStarting: { en: "Starting runtime…", zh: "正在启动运行时…" } satisfies BilingualLabel,
  floatPending: { en: "Preparing float bar", zh: "准备悬浮条" } satisfies BilingualLabel,
  float: { en: "Ready", zh: "就绪" } satisfies BilingualLabel,
  degraded: { en: "Degraded mode", zh: "降级模式" } satisfies BilingualLabel,
  runtimeBundleMissing: {
    en: "Runtime bundle missing — run bundle:runtime",
    zh: "未找到 Runtime 包 — 请先执行 bundle:runtime",
  } satisfies BilingualLabel,
  runtimeInitFailed: { en: "Runtime init failed", zh: "Runtime 初始化失败" } satisfies BilingualLabel,
  runtimeSpawnFailed: { en: "Failed to start runtime process", zh: "无法启动 Runtime 进程" } satisfies BilingualLabel,
  initProduct: { en: "Starting CNexus…", zh: "正在启动 CNexus…" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const floatL = {
  factorGraph: { en: "Factor network", zh: "因子词网络" } satisfies BilingualLabel,
  factorGraphHint: {
    en: "Force-directed · same graph as main window",
    zh: "力导向 · 与大窗同源",
  } satisfies BilingualLabel,
  tokenStrip: { en: "Token usage", zh: "算力消耗" } satisfies BilingualLabel,
  tokenEmpty: { en: "No token data yet", zh: "暂无消耗数据" } satisfies BilingualLabel,
  tokenEmptyLive: {
    en: "Runtime live — no token usage yet. Send a chat message to record costs.",
    zh: "运行时已连接，暂无 Token 消耗。发送一条对话后即可显示。",
  } satisfies BilingualLabel,
  tokenOffline: {
    en: "Connect Runtime to load token usage",
    zh: "请先连接运行时以加载 Token 数据",
  } satisfies BilingualLabel,
  tokenLoading: { en: "Loading…", zh: "加载中…" } satisfies BilingualLabel,
  openTokenConsole: { en: "Open Token Observatory", zh: "打开算力观测" } satisfies BilingualLabel,
  importPanel: { en: "Import memory", zh: "导入记忆" } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const debuggerL = {
  selectEvent: {
    en: "Select an event in Timeline or Graph",
    zh: "请在时序或图谱中选择事件",
  } satisfies BilingualLabel,
  inspectHint: {
    en: "View Control · Intent · State Diff",
    zh: "查看管控、意图与状态变更",
  } satisfies BilingualLabel,
  noSpineEvents: {
    en: "No Spine events — connect Runtime or switch Demo",
    zh: "暂无脊柱事件，请连接运行时或切换演示模式",
  } satisfies BilingualLabel,
  noSpineEventsLive: {
    en: "Runtime is live — no GTBS events yet. Send a chat message or run Analyze to generate traces.",
    zh: "运行时已连接，暂无脊柱事件。发送对话或点击分析以生成追踪。",
  } satisfies BilingualLabel,
  spineOffline: {
    en: "Runtime not connected — connect services or switch Demo",
    zh: "运行时未连接 — 请连接服务或切换演示模式",
  } satisfies BilingualLabel,
  waitForTrace: {
    en: "Select a trace or wait for events",
    zh: "请选择追踪或等待事件",
  } satisfies BilingualLabel,
  causalProjection: {
    en: "parent_event_id · causal_links projection",
    zh: "基于 parent_event_id 与 causal_links 投影",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;

export const connectionL = {
  ollamaRunning: { en: "Ollama running", zh: "Ollama 已运行" } satisfies BilingualLabel,
  ollamaConnected: { en: "Ollama connected", zh: "Ollama 已连接" } satisfies BilingualLabel,
  ollamaDisconnected: { en: "Ollama not connected", zh: "Ollama 未连接" } satisfies BilingualLabel,
  ollamaStopped: { en: "Ollama not started", zh: "Ollama 未启动" } satisfies BilingualLabel,
  ollamaMissing: { en: "Ollama not installed", zh: "未安装 Ollama" } satisfies BilingualLabel,
  ollamaLocal: { en: "Ollama running (local)", zh: "Ollama 已运行（本机）" } satisfies BilingualLabel,
  ollamaNotFound: { en: "Ollama not detected", zh: "未检测到 Ollama" } satisfies BilingualLabel,
  ollamaProbing: { en: "Detecting Ollama…", zh: "正在检测 Ollama…" } satisfies BilingualLabel,
  runtimeStartHint: {
    en: "Run in terminal: python -m api.main (port 8000)",
    zh: "请在终端执行：python -m api.main（端口 8000）",
  } satisfies BilingualLabel,
  runtimeNotReadyDev: {
    en: "Runtime not ready. Start API in brain-memory-ui, or restart CNexus.",
    zh: "运行时未就绪。请在 brain-memory-ui 目录启动 API，或重启 CNexus",
  } satisfies BilingualLabel,
  runtimeNotReadyLocal: {
    en: "Runtime not ready. Ensure 127.0.0.1:8000 is running.",
    zh: "运行时未就绪，请确认本机 127.0.0.1:8000 已启动",
  } satisfies BilingualLabel,
  connectRuntimeFirst: {
    en: "Connect Runtime before starting Ollama via API.",
    zh: "请先连接运行时，再通过 API 启动 Ollama",
  } satisfies BilingualLabel,
  runtimeConnected: { en: "Runtime connected", zh: "运行时已连接" } satisfies BilingualLabel,
  runtimeConnectedSuccess: {
    en: "Runtime connected — closing panel…",
    zh: "运行时已连接，正在关闭…",
  } satisfies BilingualLabel,
  runtimeConnecting: { en: "Connecting…", zh: "正在连接…" } satisfies BilingualLabel,
  runtimeWarming: { en: "Runtime starting…", zh: "正在启动…" } satisfies BilingualLabel,
  runtimeDisconnected: { en: "Runtime disconnected", zh: "运行时未连接" } satisfies BilingualLabel,
  connectServices: { en: "Connect services", zh: "连接服务" } satisfies BilingualLabel,
  localServices: { en: "Local services", zh: "本地服务" } satisfies BilingualLabel,
  localServicesSub: { en: "Runtime API · Ollama", zh: "运行时 API · Ollama 模型" } satisfies BilingualLabel,
  reconnectRuntime: { en: "Probe Runtime", zh: "重新探测运行时" } satisfies BilingualLabel,
  connectRuntime: { en: "Connect Runtime", zh: "连接运行时" } satisfies BilingualLabel,
  ollamaOfflineProbe: {
    en: "Runtime offline — local port probe only",
    zh: "运行时离线，仅探测本机端口",
  } satisfies BilingualLabel,
  ollamaAlreadyRunning: { en: "Ollama already running", zh: "Ollama 已在运行" } satisfies BilingualLabel,
  ollamaStarting: { en: "Starting…", zh: "正在启动…" } satisfies BilingualLabel,
  startOllama: { en: "Start Ollama", zh: "启动 Ollama" } satisfies BilingualLabel,
  ollamaNeedsRuntime: {
    en: "Port 11434 responds, but Runtime is required for chat and embeddings.",
    zh: "11434 端口有响应，但对话与向量需先连接运行时",
  } satisfies BilingualLabel,
  devSidecarHint: {
    en: "Dev mode won't auto-start sidecar. Run API manually in brain-memory-ui.",
    zh: "开发模式不会自动拉起 sidecar，请在 brain-memory-ui 目录手动启动 API",
  } satisfies BilingualLabel,
} satisfies Record<string, BilingualLabel>;
