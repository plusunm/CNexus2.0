/**
 * cnexus_v2.adapter.ts — Pure Functional Adapter (ACL Layer)
 *
 * Translates CNexus 2.0 Personal Backend responses into Old Frontend's MindOverview
 * and related data structures.
 *
 * Purity contract:
 *   - 100% pure functions (no side effects, no localStorage, no routing, no global state)
 *   - All enterprise fields that no longer exist are mocked with safe defaults
 *   - Types are strict — no `any` escape hatches
 *
 * @see Old Schema: lib/runtimeTypes.ts (MindOverview, RuntimeState)
 * @see New Backend: src/kernel.py (CNexusOSKernel.run())
 */

import type {
  MindOverview,
  MindOverviewCard,
  MindOverviewFeedRow,
  MindOverviewMemoryItem,
  MindOverviewPersonality,
  MindOverviewIntent,
  MindOverviewIntentGoal,
  MindOverviewDnaTrait,
} from "@/lib/runtimeTypes";

// ─────────────────────────────────────────────────────────────
// CNexus 2.0 Backend Type Definitions
// ─────────────────────────────────────────────────────────────

/** Full response from CNexusOSKernel.run() */
export interface V2RunResponse {
  response: V2SpeakResult;
  state: V2StateSnapshot;
  store_result: V2StoreResult;
  reflect_result: V2ReflectResult;
  drift_results: V2DriftCheck[];
  degradation_level: string;
  in_refuge: boolean;
}

export interface V2SpeakResult {
  text: string;
  inference_type: string;
  confidence: number;
  latency_ms: number;
  metadata: Record<string, unknown>;
}

export interface V2StateSnapshot {
  emotion: V2Emotion;
  relationship: V2Relationship;
  goal: V2Goal;
  attention: V2Attention;
  meta: V2Meta;
}

export interface V2Emotion {
  val: number;
  arousal: number;
  dominance: number;
}

/** /api/status may emit `valence` instead of internal `val`. */
function normalizeEmotion(raw?: Partial<V2Emotion> & { valence?: number } | null): V2Emotion {
  const arousal = Number(raw?.arousal ?? 0.5);
  const dominance = Number(raw?.dominance ?? 0.5);
  const val = Number(raw?.val ?? raw?.valence ?? 0);
  return { val, arousal, dominance };
}

export interface V2Relationship {
  tone: number;
  trust: number;
  familiarity: number;
}

export interface V2Goal {
  current: string;
  progress: number;
}

export interface V2Attention {
  focus: string;
  level: number;
}

export interface V2Meta {
  session_count: number;
  total_interactions: number;
}

export interface V2StoreResult {
  blocks_written: Record<string, number>;
  total_blocks: number;
  failed_writes: string[];
  decay_activated: boolean;
  eviction_triggered: boolean;
  timestamp: number;
}

export interface V2ReflectResult {
  narrative_written: boolean;
  reflective_written: boolean;
  belief_delta: number;
  belief_after: number;
  state_oscillation_detected: boolean;
  anomaly_signal_sent: boolean;
  iteration: number;
  timestamp: number;
}

export interface V2DriftCheck {
  assertion: string;
  passed: boolean;
}

/** /api/converse response from app_ui.py */
export interface V2ConverseResponse {
  reply: string;
  cog_state: V2CogState;
  memory_count: number;
  execution_count: number;
  iteration: number;
  trace: V2TraceEntry[];
  execution_history: V2ExecHistoryEntry[];
}

export interface V2CogState {
  active_intent: string;
  last_content_hash: string;
  accumulated_weight: number;
  recall_strength: number;
  total_observations: number;
  last_intent: string;
  consecutive_same_intent: number;
}

export interface V2TraceEntry {
  step: string;
  type?: string;
  raw?: string;
  normalized?: string;
  is_empty?: boolean;
  timestamp?: number;
  strategy?: string;
  context_hash?: string;
  note?: string;
}

export interface V2ExecHistoryEntry {
  input: string;
  iteration: number;
  strategy: string;
  skills: string[];
  latency_ms: number;
}

/** /api/status response from app_ui.py */
export interface V2StatusResponse {
  active: boolean;
  engine_initialized?: boolean;
  memory_count?: number;
  execution_count?: number;
  current_iteration?: number;
  running?: boolean;
  booted?: boolean;
  total_interactions?: number;
  session_count?: number;
  degradation_level?: string;
  in_refuge?: boolean;
  block_store_size?: number;
  emotion?: V2Emotion;
  cog_state?: V2CogState;
  goal?: { current?: string; progress?: number };
  generated_at?: string;
  schema_version?: string;
  cards?: MindOverview["cards"];
  feeds?: MindOverview["feeds"];
  system?: Partial<MindOverview["system"]>;
  chat_context?: MindOverview["chat_context"];
  memory_items?: MindOverviewMemoryItem[];
  wormhole_links?: MindOverview["wormhole_links"];
  projection_links?: MindOverview["projection_links"];
}

// ─────────────────────────────────────────────────────────────
// Pure Helper Functions (no side effects)
// ─────────────────────────────────────────────────────────────

function _emotionLabel(val: number, arousal: number): string {
  if (val > 0.5 && arousal > 0.6) return "joyful";
  if (val > 0.3 && arousal > 0.5) return "happy";
  if (val > 0 && arousal > 0.3) return "content";
  if (val < -0.5 && arousal > 0.6) return "angry";
  if (val < -0.3 && arousal > 0.4) return "frustrated";
  if (val < -0.3 && arousal < 0.3) return "sad";
  if (val < 0 && arousal < 0.4) return "melancholic";
  if (arousal < 0.3) return "calm";
  if (arousal > 0.7) return "alert";
  return "neutral";
}

function _pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

function _ago(): string {
  return "now";
}

// ─────────────────────────────────────────────────────────────
// Pure Adapter Functions
// ─────────────────────────────────────────────────────────────

export function toPersonality(state: V2StateSnapshot): MindOverviewPersonality {
  const e = state.emotion;
  const primaryEmotion = _emotionLabel(e.val, e.arousal);
  const intensity = Math.min(1, Math.abs(e.val) + e.arousal / 2);
  return {
    emotion: {
      primary_emotion: primaryEmotion,
      primary_emotion_label: primaryEmotion,
      intensity,
      intensity_label: _pct(intensity),
      valence: e.val,
      valence_label: e.val >= 0 ? "positive" : "negative",
      arousal: e.arousal,
      arousal_label: _pct(e.arousal),
      dominance: e.dominance,
      dominance_label: _pct(e.dominance),
      last_updated_ago: _ago(),
    },
    dna: {
      traits: [] as MindOverviewDnaTrait[],
      version: "2.0.0",
      mutation_count: 0,
      self_consistency: 0.85,
      self_consistency_label: "85%",
      overall_stability: state.goal.progress,
      overall_stability_label: _pct(state.goal.progress),
      last_updated_ago: _ago(),
    },
    identity: {
      summary: "Personal Agent Identity - CNexus 2.0",
      stability: 0.7,
      stability_label: "70%",
      consistency: 0.8,
      consistency_label: "80%",
      updated_ago: _ago(),
    } as MindOverviewCard,
    belief: {
      content: state.goal.current,
      confidence: 0.65,
      confidence_label: "65%",
      evidence_count: state.meta.total_interactions,
      conflict_count: 0,
    } as MindOverviewCard,
  };
}

export function toIntent(
  cogState: V2CogState | null,
  state: V2StateSnapshot,
  iteration: number,
): MindOverviewIntent {
  const goalId = `g:it${iteration}`;
  const goal: MindOverviewIntentGoal = {
    goal_id: goalId,
    description: state.goal.current,
    priority: 0.6,
    priority_label: "60%",
    motivation: 0.7,
    motivation_label: "70%",
    alignment_score: 0.8,
    alignment_label: "80%",
    progress: state.goal.progress,
    progress_label: _pct(state.goal.progress),
    status: state.goal.progress >= 1.0 ? "completed" : "active",
  };
  return {
    current_focus_id: goalId,
    current_focus_label: state.goal.current.slice(0, 40),
    motivation_baseline: 0.6,
    motivation_baseline_label: "60%",
    active_goal_count: 1,
    goals: [goal],
    proactive: {
      should_trigger: false,
      reason: "V2 Personal - proactive deferred to L3",
      suggested_action: cogState?.active_intent ?? "converse",
      priority: 0.5,
      priority_label: "50%",
      goal_id: goalId,
    },
    last_updated_ago: _ago(),
  };
}

export function toCards(state: V2StateSnapshot): MindOverview["cards"] {
  return {
    goal: {
      title: state.goal.current,
      progress: state.goal.progress,
      progress_label: _pct(state.goal.progress),
      alignment: 0.75,
      alignment_label: "75%",
      priority: 0.5,
      priority_label: "50%",
    } as MindOverviewCard,
    identity: {
      summary: "CNexus 2.0 - Personal Agent",
      stability: 0.7,
      stability_label: "70%",
      consistency: 0.8,
      consistency_label: "80%",
      updated_ago: _ago(),
    } as MindOverviewCard,
    belief: {
      content: state.goal.current,
      confidence: 0.65,
      confidence_label: "65%",
      evidence_count: state.meta.total_interactions,
      conflict_count: 0,
    } as MindOverviewCard,
    focus: {
      title: state.attention.focus,
      attention_label: _pct(state.attention.level),
      duration_label: "realtime",
      related_goals: 1,
    } as MindOverviewCard,
  };
}

export function toFeeds(
  reflectResult: V2ReflectResult,
  storeResult: V2StoreResult,
): MindOverview["feeds"] {
  const episodic: MindOverviewFeedRow[] = [];
  const reflections: MindOverviewFeedRow[] = [];
  const changes: string[] = [];

  if (reflectResult.narrative_written) {
    episodic.push({ text: `Belief delta: ${reflectResult.belief_delta.toFixed(3)}`, ago: _ago() });
  }
  if (reflectResult.reflective_written) {
    reflections.push({ text: `Belief after reflection: ${reflectResult.belief_after.toFixed(3)}`, ago: _ago() });
  }
  if (storeResult.blocks_written.emotion > 0) changes.push("emotion_updated");
  if (storeResult.decay_activated) changes.push("decay_activated");
  if (reflectResult.anomaly_signal_sent) changes.push("anomaly_signal");
  if (reflectResult.state_oscillation_detected) changes.push("oscillation_detected");

  if (episodic.length === 0) episodic.push({ text: "No recent episodic records" });
  if (reflections.length === 0) reflections.push({ text: "No recent reflections" });
  if (changes.length === 0) changes.push("stable");

  return { episodic, reflections, changes };
}

export function toMemoryItems(state: V2StateSnapshot): MindOverviewMemoryItem[] {
  return [
    {
      id: `e:${state.meta.total_interactions}`,
      title: `Emotion: ${_emotionLabel(state.emotion.val, state.emotion.arousal)}`,
      tag: "emotion",
      desc: `val=${state.emotion.val.toFixed(3)} a=${state.emotion.arousal.toFixed(3)} d=${state.emotion.dominance.toFixed(3)}`,
      meta: `interaction #${state.meta.total_interactions}`,
    },
    {
      id: `g:${state.meta.total_interactions}`,
      title: state.goal.current.slice(0, 80),
      tag: "goal",
      desc: `Progress: ${_pct(state.goal.progress)}`,
      meta: `Focus: ${state.attention.focus}`,
    },
  ];
}

export function toMindOverview(
  runResponse: V2RunResponse,
  cogState: V2CogState | null,
): MindOverview {
  const { state, reflect_result, store_result, degradation_level, in_refuge } = runResponse;
  const iteration = state.meta.total_interactions;

  return {
    schema_version: "2.0.0-personal",
    generated_at: new Date().toISOString(),
    personality: toPersonality(state),
    intent: toIntent(cogState, state, iteration),
    cards: toCards(state),
    feeds: toFeeds(reflect_result, store_result),
    system: {
      health_score: degradation_level === "L0" ? 0.9 : degradation_level === "L1" ? 0.7 : 0.4,
      health_label: in_refuge ? "REFUGE" : degradation_level === "L0" ? "stable" : `degraded-${degradation_level}`,
      memory_capacity_pct: Math.min(99, store_result.total_blocks * 2),
      governance_label: "personal",
      governance_conflicts: 0,
      reflective_active: reflect_result.reflective_written ? 1 : 0,
      last_governance_at: null,
      last_update_ago: _ago(),
      api_online: true,
    },
    chat_context: {
      goal: state.goal.current.slice(0, 80),
      belief: state.goal.current.slice(0, 80),
      identity: "CNexus 2.0 - Personal Agent",
    },
    memory_items: toMemoryItems(state),
  };
}

export function converseToMindOverview(
  converseResponse: V2ConverseResponse,
): MindOverview {
  const { cog_state, iteration } = converseResponse;
  const state: V2StateSnapshot = {
    emotion: { val: 0.0, arousal: 0.5, dominance: 0.5 },
    relationship: { tone: 0.0, trust: 0.5, familiarity: 0.3 },
    goal: { current: cog_state.active_intent, progress: Math.min(1, iteration * 0.01) },
    attention: { focus: cog_state.active_intent, level: 0.5 },
    meta: { session_count: 0, total_interactions: iteration },
  };
  const runResponse: V2RunResponse = {
    response: { text: converseResponse.reply, inference_type: "llm", confidence: 1.0, latency_ms: 0, metadata: {} },
    state,
    store_result: { blocks_written: { emotion: 0, episodic: 0, intent: 0, archival: 0 }, total_blocks: converseResponse.memory_count, failed_writes: [], decay_activated: false, eviction_triggered: false, timestamp: 0.0 },
    reflect_result: { narrative_written: false, reflective_written: false, belief_delta: 0.0, belief_after: 0.0, state_oscillation_detected: false, anomaly_signal_sent: false, iteration, timestamp: 0.0 },
    drift_results: [],
    degradation_level: "L0",
    in_refuge: false,
  };
  return toMindOverview(runResponse, cog_state);
}

function normalizeMemoryTag(tag: string | undefined): MindOverviewMemoryItem["tag"] {
  const raw = (tag || "term").toLowerCase();
  if (raw === "episodic" || raw === "episode") return "episode";
  if (raw === "goal" || raw === "belief" || raw === "identity" || raw === "insight") return raw;
  if (raw === "emotion") return "insight";
  return "term";
}

export function statusToMindOverview(
  statusResponse: V2StatusResponse,
): MindOverview {
  const goalCurrent =
    statusResponse.goal?.current ??
    statusResponse.cog_state?.active_intent ??
    "explore";
  const goalProgress = statusResponse.goal?.progress ?? 0;
  const state: V2StateSnapshot = {
    emotion: normalizeEmotion(statusResponse.emotion),
    relationship: { tone: 0.0, trust: 0.5, familiarity: 0.3 },
    goal: { current: goalCurrent, progress: goalProgress },
    attention: {
      focus: statusResponse.cog_state?.active_intent ?? "general",
      level: 0.5,
    },
    meta: {
      session_count: statusResponse.session_count ?? 0,
      total_interactions:
        statusResponse.total_interactions ?? statusResponse.current_iteration ?? 0,
    },
  };
  const runResponse: V2RunResponse = {
    response: { text: "", inference_type: "idle", confidence: 1.0, latency_ms: 0, metadata: {} },
    state,
    store_result: {
      blocks_written: { emotion: 0, episodic: 0, intent: 0, archival: 0 },
      total_blocks: statusResponse.memory_count ?? 0,
      failed_writes: [],
      decay_activated: false,
      eviction_triggered: false,
      timestamp: 0.0,
    },
    reflect_result: {
      narrative_written: false,
      reflective_written: false,
      belief_delta: 0.0,
      belief_after: 0.0,
      state_oscillation_detected: false,
      anomaly_signal_sent: false,
      iteration: state.meta.total_interactions,
      timestamp: 0.0,
    },
    drift_results: [],
    degradation_level: statusResponse.degradation_level ?? "L0",
    in_refuge: statusResponse.in_refuge ?? false,
  };
  const overview = toMindOverview(runResponse, statusResponse.cog_state ?? null);

  if (statusResponse.generated_at) {
    overview.generated_at = statusResponse.generated_at;
  }
  if (statusResponse.cards) {
    overview.cards = { ...overview.cards, ...statusResponse.cards };
  }
  if (statusResponse.feeds) {
    overview.feeds = { ...overview.feeds, ...statusResponse.feeds };
  }
  if (statusResponse.chat_context) {
    overview.chat_context = { ...overview.chat_context, ...statusResponse.chat_context };
  }
  if (statusResponse.system) {
    overview.system = { ...overview.system, ...statusResponse.system };
  }
  if (statusResponse.memory_items && statusResponse.memory_items.length > 0) {
    overview.memory_items = statusResponse.memory_items.map((item) => ({
      ...item,
      tag: normalizeMemoryTag(item.tag),
      cluster: item.cluster,
      parent_id: item.parent_id,
      score: item.score,
      activity: item.activity ?? item.score,
      is_active: item.is_active,
      node_type: item.node_type,
      source_peer: item.source_peer,
      memory_origin: item.memory_origin,
    }));
  }
  if (statusResponse.wormhole_links && statusResponse.wormhole_links.length > 0) {
    overview.wormhole_links = statusResponse.wormhole_links.map((link) => ({
      source: link.source,
      target: link.target,
      similarity: link.similarity,
      energy: link.energy,
    }));
  }
  if (statusResponse.projection_links && statusResponse.projection_links.length > 0) {
    overview.projection_links = statusResponse.projection_links.map((link) => ({
      source: link.source,
      target: link.target,
      type: link.type,
    }));
  }

  return overview;
}
