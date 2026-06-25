import type { EffectiveConnectionMode } from "@/cnexus-kernel/connectionMode";
import { useMindStore } from "@/cnexus-kernel/MindStore";

import { cnexusProductApi, probePersonalBackendOnline } from "@/lib/api";
import { isPersonalMode } from "@/lib/personalGuard";

export type MemoryWriteGate = {
  isDemo: boolean;
  isWarming: boolean;
  isFallback: boolean;
  canWriteMemory: boolean;
  /** Operational ready — chat/API up but upload may still wait for full_ready. */
  isLive?: boolean;
};

export type MemoryWriteReadyResult = {
  ok: boolean;
  hint: string | null;
};

/** Accepted extensions for document ingest (PDF / Word / text). */
export const DOCUMENT_ACCEPT =
  ".pdf,.doc,.docx,.txt,.md,.markdown,.json,.jsonl,.csv,.log,.xml,.py,.ts,.tsx,.js,.jsx,.rs,.go,.java,.sql,.yaml,.yml";

const FULL_READY_POLL_MS = 1_500;
const FULL_READY_POLL_MAX_MS = 90_000;

export function buildDocumentUploadGate(effectiveMode: EffectiveConnectionMode): MemoryWriteGate {
  const state = useMindStore.getState();
  const isDemo = effectiveMode === "demo";
  const isFallback = effectiveMode === "fallback";
  const isLive = effectiveMode === "runtime" && state.runtimeOperationalReady;
  const isReachable = effectiveMode === "runtime" && state.runtimeReachable;
  const isWarming = isReachable && !isLive;
  const canWriteMemory = isDemo || isReachable;
  return { isDemo, isWarming, isFallback, canWriteMemory, isLive };
}

export function buildMemoryWriteGate(effectiveMode: EffectiveConnectionMode): MemoryWriteGate {
  const state = useMindStore.getState();
  const isDemo = effectiveMode === "demo";
  const isFallback = effectiveMode === "fallback";
  const isLive = effectiveMode === "runtime" && state.runtimeOperationalReady;
  const isReachable = effectiveMode === "runtime" && state.runtimeReachable;
  const isWarming = isReachable && !isLive;
  const canWriteMemory = isDemo || isLive;
  return { isDemo, isWarming, isFallback, canWriteMemory, isLive };
}

export function memoryWriteStatusHint(gate: MemoryWriteGate): string | null {
  if (gate.isDemo) return null;
  if (gate.canWriteMemory) return null;
  if (gate.isFallback) return "当前为离线模式，请连接 Runtime 或切换演示模式";
  if (gate.isWarming) return "Runtime 正在启动，请稍候再导入";
  if (gate.isLive) return "认知索引构建中，上传将在完全就绪后开放";
  return "Runtime 未连接，请先启动应用并等待「运行时已连接」";
}

export function documentUploadStatusHint(gate: MemoryWriteGate): string | null {
  if (gate.isDemo) return null;
  if (gate.canWriteMemory) return null;
  if (gate.isFallback) return "当前为离线模式，请连接 Runtime 或切换演示模式";
  if (gate.isWarming) return "正在唤醒核心，请稍候…";
  return "Gateway 未就绪，请先启动应用";
}

function uploadBlockedHint(gate: MemoryWriteGate, kind: "document" | "memory"): string {
  return kind === "document"
    ? (documentUploadStatusHint(gate) ?? "Gateway 未就绪，无法导入文档")
    : (memoryWriteStatusHint(gate) ?? "Runtime 未连接，无法导入");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function verifyGatewayUploadPath(): Promise<{ ok: boolean; hint: string | null }> {
  if (isPersonalMode()) {
    return { ok: true, hint: null };
  }
  try {
    const gw = await cnexusProductApi.gatewayHealth();
    if (gw.gateway === "alive") {
      return { ok: true, hint: null };
    }
    return { ok: false, hint: "Gateway 未就绪，无法导入文档" };
  } catch (err) {
    const message =
      err instanceof Error && err.message.trim()
        ? err.message
        : "Gateway 不可用，请稍后再试";
    return { ok: false, hint: message };
  }
}

async function verifyRuntimeWritePath(): Promise<{ ok: boolean; hint: string | null }> {
  try {
    await cnexusProductApi.memoryStats();
    return { ok: true, hint: null };
  } catch (err) {
    void useMindStore.getState().syncSystemCapability();
    const message =
      err instanceof Error && err.message.trim()
        ? err.message
        : "记忆写入路径不可用，请稍后再试";
    return { ok: false, hint: message };
  }
}

/** Probe Gateway + offline ingest path before document upload. */
export async function ensureDocumentUploadReady(
  gate?: MemoryWriteGate,
  options?: { pollForGateway?: boolean },
): Promise<MemoryWriteReadyResult> {
  if (isPersonalMode()) {
    if (await probePersonalBackendOnline()) {
      return { ok: true, hint: null };
    }
    return { ok: false, hint: "本地服务未启动，请运行 start_cnexus.bat 后重试" };
  }

  const pollForGateway = options?.pollForGateway !== false;
  const store = useMindStore.getState();
  let current = gate ?? buildDocumentUploadGate(store.effectiveMode);

  if (current.isDemo) return { ok: true, hint: null };
  if (current.isFallback) return { ok: false, hint: uploadBlockedHint(current, "document") };

  const deadline = Date.now() + FULL_READY_POLL_MAX_MS;

  while (Date.now() < deadline) {
    await store.syncSystemCapability();
    current = buildDocumentUploadGate(store.effectiveMode);

    if (current.isFallback) return { ok: false, hint: uploadBlockedHint(current, "document") };

    if (current.canWriteMemory) {
      const probe = await verifyGatewayUploadPath();
      if (probe.ok) return { ok: true, hint: null };
      return { ok: false, hint: probe.hint ?? uploadBlockedHint(current, "document") };
    }

    if (!current.isWarming && !current.isLive) {
      return { ok: false, hint: uploadBlockedHint(current, "document") };
    }

    if (!pollForGateway) {
      return { ok: false, hint: uploadBlockedHint(current, "document") };
    }

    await sleep(FULL_READY_POLL_MS);
  }

  return { ok: false, hint: uploadBlockedHint(current, "document") };
}

/** Probe full ready + write path before text/memory capture. Polls capability when chat is live but upload waits. */
export async function ensureMemoryWriteReady(
  gate?: MemoryWriteGate,
  options?: { pollForFull?: boolean },
): Promise<MemoryWriteReadyResult> {
  const pollForFull = options?.pollForFull !== false;
  const store = useMindStore.getState();
  let current = gate ?? buildMemoryWriteGate(store.effectiveMode);

  if (current.isDemo) return { ok: true, hint: null };
  if (current.isFallback) return { ok: false, hint: uploadBlockedHint(current, "memory") };

  const deadline = Date.now() + FULL_READY_POLL_MAX_MS;

  while (Date.now() < deadline) {
    await store.syncSystemCapability();
    current = buildMemoryWriteGate(store.effectiveMode);

    if (current.isFallback) return { ok: false, hint: uploadBlockedHint(current, "memory") };

    if (current.canWriteMemory) {
      const probe = await verifyRuntimeWritePath();
      if (probe.ok) return { ok: true, hint: null };
      return { ok: false, hint: probe.hint ?? uploadBlockedHint(current, "memory") };
    }

    if (!current.isLive && !current.isWarming) {
      return { ok: false, hint: uploadBlockedHint(current, "memory") };
    }

    if (!pollForFull) {
      return { ok: false, hint: uploadBlockedHint(current, "memory") };
    }

    await sleep(FULL_READY_POLL_MS);
  }

  return { ok: false, hint: uploadBlockedHint(current, "memory") };
}

export function formatImportError(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message.trim()) return err.message;
  return fallback;
}
