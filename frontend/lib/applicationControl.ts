/** Application control surface types — P5.3 connect → hook → gate → execute */

export type ApplicationPhase =
  | "idle"
  | "connected"
  | "diagnosed"
  | "gate_preview"
  | "repair_pending"
  | "repair_complete"
  | "published";

export type ExecutionGateKind = "allow" | "deny" | "require_confirm";

export type RepairPlanRow = {
  chunk_hash?: string;
  priority?: number;
  sources?: string[];
  strategy?: string;
  root_hash?: string;
  graph_id?: string;
  commit_id?: string;
};

export type SuggestedSourceRow = {
  rank?: number;
  host?: string;
  reason?: string;
  explain?: string;
  probe?: {
    state_checked?: boolean;
    remote_has?: boolean;
    chunk_states?: Array<{ hash?: string; remote_has?: boolean; state_checked?: boolean }>;
  };
};

export type ExecutionGateRow = {
  gate?: ExecutionGateKind;
  ok?: boolean;
  allowed_count?: number;
  denied_count?: number;
  confirm_required_count?: number;
  decisions?: Array<{ gate?: ExecutionGateKind; chunk_hash?: string; detail?: string }>;
  policy?: Record<string, unknown>;
};

export type ApplicationConnectSnapshot = {
  phase: ApplicationPhase;
  peerId: string;
  peerHost: string;
  missingCount: number;
  planCount: number;
  repairPlans: RepairPlanRow[];
  suggestedSources: SuggestedSourceRow[];
  executionGate: ExecutionGateRow;
  missing: string[];
  invalid: string[];
};

export function parseConnectApplication(row: Record<string, unknown>): ApplicationConnectSnapshot | null {
  const app = (row.application || {}) as Record<string, unknown>;
  const control = (app.control || {}) as Record<string, unknown>;
  const hook = (app.repair_hook || row.repair_hook || {}) as Record<string, unknown>;
  if (app.skipped && !hook.ok) return null;

  const executionGate = (app.execution_gate || hook.execution_gate || {}) as ExecutionGateRow;
  const phase = String(app.phase || control.phase || "connected") as ApplicationPhase;
  const missing = Array.isArray(hook.missing) ? (hook.missing as string[]) : [];
  const invalid = Array.isArray(hook.invalid) ? (hook.invalid as string[]) : [];

  return {
    phase,
    peerId: String(row.peer_id || control.peer_id || ""),
    peerHost: String(row.url || control.peer_host || ""),
    missingCount: Number(hook.missing_count ?? control.missing_count ?? missing.length + invalid.length),
    planCount: Number(hook.plan_count ?? control.plan_count ?? 0),
    repairPlans: Array.isArray(hook.repair_plans) ? (hook.repair_plans as RepairPlanRow[]) : [],
    suggestedSources: Array.isArray(hook.suggested_sources)
      ? (hook.suggested_sources as SuggestedSourceRow[])
      : [],
    executionGate,
    missing,
    invalid,
  };
}

export function gateLabel(gate?: ExecutionGateKind): { en: string; zh: string } {
  switch (gate) {
    case "allow":
      return { en: "Allowed", zh: "允许执行" };
    case "deny":
      return { en: "Denied", zh: "拒绝执行" };
    case "require_confirm":
      return { en: "Confirm required", zh: "需要确认" };
    default:
      return { en: "Unknown", zh: "未知" };
  }
}

export function phaseLabel(phase: ApplicationPhase): { en: string; zh: string } {
  switch (phase) {
    case "gate_preview":
      return { en: "Awaiting confirmation", zh: "等待人工确认" };
    case "diagnosed":
      return { en: "Integrity gap detected", zh: "检测到完整性缺口" };
    case "repair_pending":
      return { en: "Repair pending confirm", zh: "修复待确认" };
    case "repair_complete":
      return { en: "Repair complete", zh: "修复完成" };
    case "connected":
      return { en: "Connected — integrity OK", zh: "已连接 — 完整性正常" };
    default:
      return { en: phase, zh: phase };
  }
}

export function shortHash(hash: string): string {
  if (hash.length <= 16) return hash;
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`;
}
