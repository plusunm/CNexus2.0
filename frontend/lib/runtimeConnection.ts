import type { EffectiveConnectionMode } from "@/cnexus-kernel";
import type { RuntimeConnectionPhase } from "@/hooks/useFloatRuntimeMonitor";
import { isPersonalMode } from "@/lib/personalGuard";

/** UI 对外呈现的连接状态 — 不压缩能力层 */

export type RuntimeUIState = {
  /** 整体连接面 — 反映 gateway 是否可达 */
  connection: "offline" | "warming" | "live";

  /** 各层独立状态 */
  gateway: "down" | "up";
  runtime: "starting" | "warming" | "operational";
  cognitive: "booting" | "ready";

  /** 独立能力门 */
  capability: {
    chat: boolean;
    upload: boolean;
    suggestion: boolean;
  };

  /** 简化消费 flags */
  flags: {
    canChat: boolean;
    canUpload: boolean;
    canUseRuntimeApi: boolean;
  };

  /** 向后兼容的显示字段 */
  connectionLabel: string;
  badgeLabel: string;
  badgeColor: "purple" | "blue" | "orange" | "red";
  phase: "demo" | "live" | "warming" | "offline" | "fallback";
};

/**
 * 从 monitor + capability snapshot 推导完整 RuntimeUIState。
 *
 * 核心原则：
 * - operational_ready = SSOT 判断 runtime 可用性（不依赖 BOOT_4）
 * - capability 层独立判断 canChat / canUpload / canUseRuntimeApi
 * - warming ≠ 全不可用
 */
export function resolveRuntimeUIState(input: {
  effectiveMode: EffectiveConnectionMode;
  isDemo: boolean;

  /** Monitor probe 结果（来自 /v1/system/capability） */
  monitorPhase?: RuntimeConnectionPhase | null;
  /** operational_ready 现场值（从 MindStore 取） */
  operationalReady?: boolean | null;
  /** 各能力门现场值（从 MindStore 取） */
  capabilities?: {
    chat?: boolean;
    upload?: boolean;
    full?: boolean;
  } | null;
}): RuntimeUIState {
  const { effectiveMode, isDemo, monitorPhase, operationalReady, capabilities } = input;

  // ————— demo / fallback 不走状态机 —————
  if (isDemo || effectiveMode === "demo") {
    return {
      connection: "live",
      gateway: "up",
      runtime: "operational",
      cognitive: "ready",
      capability: { chat: true, upload: true, suggestion: true },
      flags: { canChat: true, canUpload: true, canUseRuntimeApi: true },
      connectionLabel: isPersonalMode() ? "演示" : "演示模式",
      badgeLabel: isPersonalMode() ? "演示" : "演示示例",
      badgeColor: "purple",
      phase: "demo",
    };
  }

  if (effectiveMode === "fallback") {
    return {
      connection: "offline",
      gateway: "down",
      runtime: "starting",
      cognitive: "booting",
      capability: { chat: false, upload: false, suggestion: false },
      flags: { canChat: false, canUpload: false, canUseRuntimeApi: false },
      connectionLabel: isPersonalMode() ? "未连接" : "未连接",
      badgeLabel: isPersonalMode() ? "网关离线" : "未连接 Runtime",
      badgeColor: "orange",
      phase: "fallback",
    };
  }

  // ————— gateway 层 —————
  const gatewayUp =
    operationalReady === true || (monitorPhase != null && monitorPhase !== "offline");
  // ————— runtime 层 —————
  const isOperational = operationalReady === true;
  const runtimeState: "starting" | "warming" | "operational" = !gatewayUp
    ? "starting"
    : isOperational
      ? "operational"
      : "warming";
  // ————— cognitive 层 —————
  const cognitive = isOperational && monitorPhase === "ready" ? "ready" : "booting";
  // ————— capability 层（独立判断）—————
  const canChat = gatewayUp && (capabilities?.chat === true || isOperational);
  const canUpload = gatewayUp && (capabilities?.upload === true);
  const canSuggestion = gatewayUp && capabilities?.full === true;

  // ————— connection 汇总 —————
  const connection: "offline" | "warming" | "live" = !gatewayUp
    ? "offline"
    : runtimeState === "operational"
      ? "live"
      : "warming";

  // ————— 向后兼容的显示字段 —————
  const canUseRuntimeApi = canChat || canUpload;

  let connectionLabel: string;
  let badgeLabel: string;
  let badgeColor: "purple" | "blue" | "orange" | "red";
  let phase: "demo" | "live" | "warming" | "offline" | "fallback";

  if (connection === "live") {
    connectionLabel = isPersonalMode() ? "已连接" : "上线";
    badgeLabel = isPersonalMode() ? "本地网关" : "Runtime 实时";
    badgeColor = "blue";
    phase = "live";
  } else if (connection === "warming") {
    if (canUseRuntimeApi) {
      connectionLabel = isPersonalMode() ? "网关繁忙" : "运行中（部分能力可用）";
      badgeLabel = isPersonalMode() ? "本地网关" : "Runtime 部分可用";
      badgeColor = "blue";
    } else {
      connectionLabel = isPersonalMode() ? "正在连接" : "正在启动";
      badgeLabel = isPersonalMode() ? "连接中" : "Runtime 正在启动";
      badgeColor = "orange";
    }
    phase = "warming";
  } else {
    connectionLabel = "未连接";
    badgeLabel = isPersonalMode() ? "网关离线" : "未连接 Runtime";
    badgeColor = "orange";
    phase = "offline";
  }

  return {
    connection,
    gateway: gatewayUp ? "up" : "down",
    runtime: runtimeState,
    cognitive,
    capability: { chat: canChat, upload: canUpload, suggestion: canSuggestion },
    flags: { canChat, canUpload, canUseRuntimeApi },
    connectionLabel,
    badgeLabel,
    badgeColor,
    phase,
  };
}

/** 旧版保留 — 委托给新版，抽 monitorPhase → operationalReady/capabilities 的桥梁 */
export type RuntimeConnectionDisplay = {
  connectionLabel: string;
  badgeLabel: string;
  badgeColor: "purple" | "blue" | "orange" | "red";
  /** Same gate as memory ingest + chat */
  canUseRuntimeApi: boolean;
  phase: "demo" | "live" | "warming" | "offline" | "fallback";
};

/**
 * @deprecated use resolveRuntimeUIState instead.
 * Legacy wrapper — resolves display fields from the old calling convention.
 */
export function resolveRuntimeConnectionDisplay(input: {
  effectiveMode: EffectiveConnectionMode;
  isLive: boolean;
  isWarming: boolean;
  isDemo: boolean;
  monitorPhase?: RuntimeConnectionPhase | null;
  /** New: pass operationalReady and capabilities from MindStore to enable capability-layer fix. */
  operationalReady?: boolean | null;
  capabilities?: {
    chat?: boolean;
    upload?: boolean;
    full?: boolean;
  } | null;
}): RuntimeConnectionDisplay {
  const state = resolveRuntimeUIState({
    effectiveMode: input.effectiveMode,
    isDemo: input.isDemo,
    monitorPhase: input.monitorPhase,
    operationalReady: input.operationalReady ?? null,
    capabilities: input.capabilities ?? null,
  });
  return {
    connectionLabel: state.connectionLabel,
    badgeLabel: state.badgeLabel,
    badgeColor: state.badgeColor,
    canUseRuntimeApi: state.flags.canUseRuntimeApi,
    phase: state.phase,
  };
}
