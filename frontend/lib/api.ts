import type { DashboardStatus } from "./dashboardTypes";
import type { CognitiveOutput } from "./cognitiveTypes";
import type { MindOverview, RuntimeState } from "./runtimeTypes";

export type GtbsRawEvent = {
  event_type: string;
  transaction_id: string;
  timestamp?: string;
  ts?: string;
  payload?: Record<string, unknown>;
};
import { getApiBase, getWsBase, getApiToken } from "./cnexusConfig";
import { humanizeNetworkConnectError } from "./networkConnectErrors";
import { isPersonalMode, isWebSocketEnabled, shouldSuppressRuntimeConnectError } from "./personalGuard";
import { statusToMindOverview, converseToMindOverview } from "../src/adapters/cnexus_v2.adapter";
import { buildExpertIngestFields, type IngestExpertFields } from "./uploadCorpusOptions";
import type { RelationshipAnalysis, RelationshipAnalysisCard } from "./relationshipAnalysis/types/relationship";
import { assertRelationshipAnalysis } from "./relationshipAnalysis/assertCanonical";
import { coerceRelationshipCard } from "./relationshipAnalysis/cardStorage";

type DocumentIngestOpts = {
  layer?: string;
  importance?: number;
  cognize?: boolean;
  goal?: string;
} & IngestExpertFields;

function appendExpertFormFields(form: FormData, opts: DocumentIngestOpts): void {
  const expert = buildExpertIngestFields(opts);
  if (!expert) return;
  form.append("subject_id", expert.subject_id);
  form.append("semantic_dimension", expert.semantic_dimension);
  form.append("distill_mode", expert.distill_mode);
}

function expertPolicyFields(opts: DocumentIngestOpts): Record<string, string> {
  return buildExpertIngestFields(opts) ?? {};
}

export type { RuntimeState, MindOverview } from "./runtimeTypes";
export type { CognitiveOutput } from "./cognitiveTypes";
export type {
  CognitiveInsightBlock,
  CognitiveActionBlock,
  CognitiveTextBlock,
} from "./cognitiveTypes";

/** Default true — wired full cognitive loop unless env disables it. */
export function getDefaultFullCognitiveLoop(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_FULL_COGNITIVE_LOOP;
  if (raw === "0" || raw === "false") return false;
  return true;
}

/** Health probes — ready endpoint is fast (Boot v2); short timeout avoids false offline. */
export const RUNTIME_PROBE_TIMEOUT_MS = 8_000;
/** Capability SSOT — allow cold-start without false offline. */
export const RUNTIME_CAPABILITY_TIMEOUT_MS = 15_000;
/** Intent job polling — allow slow server under bulk ingest load. */
export const GATEWAY_INTENT_POLL_TIMEOUT_MS = 20_000;
/** Gateway health — IO-free, short timeout for boot probe. */
export const GATEWAY_HEALTH_TIMEOUT_MS = 4_000;
export function fastPathV3Enabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_FAST_PATH_V3;
  if (raw === "0" || raw === "false") return false;
  return true;
}

/** Fast-path v2 — progressive SSE ready stream. */
export const FAST_STREAM_TIMEOUT_MS = 8_000;
/** Fast-path v1 snapshot timeout. */
export const FAST_READY_TIMEOUT_MS = 2_500;

export function fastPathV2Enabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_CNEXUS_FAST_PATH_V2;
  if (raw === "0" || raw === "false") return false;
  return true;
}
export const RUNTIME_DEFAULT_TIMEOUT_MS = 8_000;
export const MODEL_UPSERT_TIMEOUT_MS = 20_000;
export const MODEL_TEST_TIMEOUT_MS = 45_000;

function modelUpsertTimeoutMs(): number {
  return isPersonalMode() ? MODEL_UPSERT_TIMEOUT_MS : RUNTIME_DEFAULT_TIMEOUT_MS;
}

function modelTestTimeoutMs(): number {
  return isPersonalMode() ? MODEL_TEST_TIMEOUT_MS : 15_000;
}

export type ModelProfile = {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model: string;
  api_key_set: boolean;
  is_default: boolean;
  enabled: boolean;
};

export type RuntimeLogEntry = {
  id: string;
  timestamp: string;
  level: "info" | "debug" | "warn" | "error" | string;
  category: string;
  message: string;
  meta?: Record<string, unknown>;
};

function formatRequestError(data: unknown, status: number, statusText: string): string {
  const row = data as { detail?: unknown; message?: string };
  if (typeof row.detail === "string") return row.detail;
  if (row.detail && typeof row.detail === "object") {
    const payload = row.detail as Record<string, unknown>;
    if (status === 503 || payload.status === "warming") {
      return "Runtime 正在启动，记忆写入暂不可用，请稍候几秒后重试";
    }
    if (typeof payload.message === "string") return payload.message;
  }
  if (status === 503) return "Runtime 未就绪，请稍后再试";
  if (status === 401) return "API 鉴权失败";
  return statusText || "请求失败";
}

function requestTimeoutMessage(): string {
  if (isPersonalMode()) {
    return "本地网关响应超时 — 可能正在推理中，请稍候重试";
  }
  return "请求超时 — 请确认 Runtime 已启动";
}

function requestNetworkErrorMessage(): string {
  if (shouldSuppressRuntimeConnectError()) {
    return "本地网关未启动 — 请运行 start_cnexus.bat";
  }
  return "无法连接 Runtime — 请确认应用已启动且 API 在运行";
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = RUNTIME_DEFAULT_TIMEOUT_MS): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      headers,
      ...init,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = formatRequestError(data, res.status, res.statusText);
      if (res.status === 401) {
        throw new Error(`401 Unauthorized — ${detail || "API Key 无效或已过期"}`);
      }
      throw new Error(detail || res.statusText);
    }
    return data as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(requestTimeoutMessage());
    }
    if (err instanceof TypeError) {
      throw new Error(requestNetworkErrorMessage());
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

export type IngestDocumentResult = {
  memory_id: string;
  status: string;
  filename: string;
  format: string;
  char_count: number;
  preview: string;
  truncated: boolean;
  keywords: string[];
  cognition?: Record<string, unknown>;
};

export type IngestDocumentBatchResult = {
  ok: boolean;
  batch_id: string;
  status: string;
  count: number;
  indexed: Array<{
    file_id: string;
    memory_id: string;
    filename: string;
    status: string;
    preview: string;
    keywords: string[];
    char_count: number;
  }>;
  errors: Array<{ filename: string; error: string }>;
};

function uploadTimeoutMs(files: File[]): number {
  const bytes = files.reduce((sum, file) => sum + file.size, 0);
  const bySize = Math.ceil(bytes / 4096);
  const byCount = files.length * 2_000;
  return Math.min(600_000, Math.max(90_000, 30_000 + bySize + byCount));
}

function documentUploadTimeoutMessage(): string {
  return "文件上传超时 — 文件较多或较大，请分批上传或稍后重试";
}

function documentIndexTimeoutMessage(): string {
  return "后台索引超时 — 文件已接收，请刷新页面查看记忆是否已写入";
}

const BATCH_MAX_FILES = 50;
const BATCH_MAX_BYTES = 14 * 1024 * 1024;

async function requestMultipart<T>(
  path: string,
  form: FormData,
  timeoutMs = RUNTIME_DEFAULT_TIMEOUT_MS,
  timeoutMessage?: string,
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      method: "POST",
      headers,
      body: form,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = formatRequestError(data, res.status, res.statusText);
      throw new Error(detail || res.statusText);
    }
    return data as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(timeoutMessage ?? requestTimeoutMessage());
    }
    if (err instanceof TypeError) {
      throw new Error(requestNetworkErrorMessage());
    }
    throw err;
  } finally {
    window.clearTimeout(timer);
  }
}

type GatewayIntentResponse = {
  status: string;
  trace_id?: string;
  result?: unknown;
  reason?: string;
  queue_depth?: number;
  queue_size?: number;
  error?: string;
  done?: number;
  total?: number;
  files_indexed_count?: number;
  latest_finished?: string | null;
  details?: GatewayIntentFileDetail[];
  ok?: boolean;
};

export type GatewayIntentFileDetail = {
  file_id?: string;
  filename?: string;
  status: string;
  error?: string;
};

export type IngestJobProgress = {
  traceId: string;
  status: string;
  done: number;
  total: number;
  filesIndexedCount: number;
  latestFinished?: string | null;
  details: GatewayIntentFileDetail[];
  error?: string;
  ok?: boolean;
};

function mapIntentJob(traceId: string, job: GatewayIntentResponse): IngestJobProgress {
  return {
    traceId,
    status: job.status ?? "queued",
    done: typeof job.done === "number" ? job.done : 0,
    total: typeof job.total === "number" ? job.total : 0,
    filesIndexedCount:
      typeof job.files_indexed_count === "number"
        ? job.files_indexed_count
        : typeof job.done === "number"
          ? job.done
          : 0,
    latestFinished: job.latest_finished ?? null,
    details: Array.isArray(job.details) ? job.details : [],
    error: job.error,
    ok: job.ok,
  };
}

export async function fetchGatewayIntentJob(traceId: string): Promise<IngestJobProgress> {
  const job = await request<GatewayIntentResponse>(
    `/v1/gateway/intent/${encodeURIComponent(traceId)}`,
    undefined,
    GATEWAY_INTENT_POLL_TIMEOUT_MS,
  );
  return mapIntentJob(traceId, job);
}

function isTerminalIngestJob(job: IngestJobProgress): boolean {
  return job.status === "completed" || job.status === "error" || job.status === "failed";
}

/** Non-blocking poll — returns a stop function. */
export function pollDocumentIngestProgress(
  traceIds: string[],
  onUpdate: (jobs: IngestJobProgress[]) => void,
  options: {
    intervalMs?: number;
    timeoutMs?: number;
    onComplete?: (jobs: IngestJobProgress[]) => void;
    onError?: (error: Error) => void;
  } = {},
): () => void {
  if (!traceIds.length) {
    options.onComplete?.([]);
    return () => undefined;
  }

  const intervalMs = options.intervalMs ?? 2_000;
  const timeoutMs = options.timeoutMs ?? 300_000;
  const started = Date.now();
  let stopped = false;

  const tick = async () => {
    while (!stopped && Date.now() - started < timeoutMs) {
      try {
        const jobs = await Promise.all(traceIds.map((traceId) => fetchGatewayIntentJob(traceId)));
        if (stopped) return;
        onUpdate(jobs);
        if (jobs.length > 0 && jobs.every(isTerminalIngestJob)) {
          if (jobs.some((job) => job.status === "error" || job.status === "failed")) {
            const errJob = jobs.find((job) => job.error);
            options.onError?.(new Error(errJob?.error || "后台索引失败"));
          } else {
            options.onComplete?.(jobs);
          }
          return;
        }
      } catch (err) {
        if (stopped) return;
        options.onError?.(err instanceof Error ? err : new Error(String(err)));
        return;
      }
      await gatewaySleep(intervalMs);
    }
    if (!stopped) {
      options.onError?.(new Error(documentIndexTimeoutMessage()));
    }
  };

  void tick();
  return () => {
    stopped = true;
  };
}

function gatewaySleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function waitGatewayIntentWs(
  traceId: string,
  timeoutMs: number,
): Promise<GatewayIntentResponse | null> {
  if (!isWebSocketEnabled() || typeof WebSocket === "undefined") {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value: GatewayIntentResponse | null) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      resolve(value);
    };
    const ws = new WebSocket(`${getWsBase()}/v1/gateway/ws`);
    const timer = window.setTimeout(() => finish(null), timeoutMs);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as GatewayIntentResponse & {
          type?: string;
          trace_id?: string;
        };
        if (msg.type === "intent_result" && msg.trace_id === traceId) {
          finish(msg);
        }
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onerror = () => finish(null);
  });
}

async function waitGatewayIntentCompletion<T>(
  traceId: string,
  started: number,
  timeoutMs: number,
  timeoutMessage = documentIndexTimeoutMessage(),
): Promise<T> {
  let pollDelayMs = 200;

  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      fn();
    };

    void waitGatewayIntentWs(traceId, timeoutMs).then((msg) => {
      if (!msg) return;
      if (msg.status === "completed" && msg.result !== undefined) {
        finish(() => resolve(msg.result as T));
        return;
      }
      if (msg.status === "error" || msg.status === "failed") {
        finish(() => reject(new Error(msg.error || "Gateway intent failed")));
      }
    });

    void (async () => {
      while (!settled && Date.now() - started < timeoutMs) {
        await gatewaySleep(pollDelayMs);
        pollDelayMs = Math.min(1000, Math.round(pollDelayMs * 1.5));
        try {
          const poll = await request<GatewayIntentResponse>(
            `/v1/gateway/intent/${encodeURIComponent(traceId)}`,
            undefined,
            GATEWAY_INTENT_POLL_TIMEOUT_MS,
          );
          if (poll.status === "completed" && poll.result !== undefined) {
            finish(() => resolve(poll.result as T));
            return;
          }
          if (poll.status === "error" || poll.status === "failed") {
            finish(() => reject(new Error(poll.error || "Gateway intent failed")));
            return;
          }
        } catch {
          /* transient poll failure — keep waiting until overall timeout */
        }
      }
      if (!settled) {
        finish(() => reject(new Error(timeoutMessage)));
      }
    })();
  });
}

/** Gateway v2 — sole execution entry; WS push + adaptive poll when queued. */
export async function gatewayIntentExecute<T>(
  type: string,
  payload: Record<string, unknown>,
  timeoutMs = RUNTIME_DEFAULT_TIMEOUT_MS,
  clientTraceId?: string,
): Promise<T> {
  const started = Date.now();
  let res = await request<GatewayIntentResponse>(
    "/v1/gateway/intent",
    {
      method: "POST",
      body: JSON.stringify({
        type,
        payload,
        source: "frontend",
        ...(clientTraceId ? { trace_id: clientTraceId } : {}),
      }),
    },
    timeoutMs,
  );

  if (res.status === "completed" && res.result !== undefined) {
    return res.result as T;
  }
  if (res.status === "error") {
    throw new Error(res.error || res.reason || "Gateway intent failed");
  }
  if (res.status === "rejected") {
    throw new Error(res.reason || "Gateway rejected intent");
  }

  const traceId = res.trace_id;
  if (!traceId) {
    throw new Error(res.reason || "Gateway intent missing trace_id");
  }

  return waitGatewayIntentCompletion<T>(traceId, started, timeoutMs);
}

export async function expertCapture(opts: {
  subjectId: string;
  content: string;
  semanticDimension?: string;
}): Promise<{ ok?: boolean; memory_id?: string; subject_id?: string }> {
  const expert = buildExpertIngestFields({
    corpus: "expert",
    subjectId: opts.subjectId,
    semanticDimension: (opts.semanticDimension as IngestExpertFields["semanticDimension"]) ?? "style",
  });
  if (!expert) {
    throw new Error("专家语料导入缺少 subject_id");
  }
  return request("/api/expert/capture", {
    method: "POST",
    body: JSON.stringify({
      subject_id: expert.subject_id,
      content: opts.content,
      semantic_dimension: expert.semantic_dimension,
    }),
  });
}

async function ingestDocumentViaPersonalCapture(
  file: File,
  opts: DocumentIngestOpts,
): Promise<IngestDocumentResult> {
  const raw = await file.text().catch(() => "");
  const content = raw.trim();
  if (!content) {
    throw new Error("无法读取文档内容，请确认文件为文本格式或 Gateway 可用");
  }
  const expert = buildExpertIngestFields(opts);
  if (expert) {
    const captured = await expertCapture({
      subjectId: expert.subject_id,
      content: content.slice(0, 20_000),
      semanticDimension: expert.semantic_dimension,
    });
    const ext = file.name.includes(".") ? file.name.split(".").pop() ?? "txt" : "txt";
    return {
      memory_id: captured.memory_id ?? "expert-capture",
      status: "stored",
      filename: file.name,
      format: ext,
      char_count: content.length,
      preview: content.slice(0, 400),
      truncated: content.length > 400,
      keywords: [],
    };
  }
  const captured = await request<{ memory_id: string }>(
    "/v1/memory/capture",
    {
      method: "POST",
      body: JSON.stringify({
        content: content.slice(0, 20_000),
        layer: opts.layer ?? "episodic",
        label: file.name,
        importance: opts.importance ?? 0.7,
        goal: opts.goal,
      }),
    },
    60_000,
  );
  const ext = file.name.includes(".") ? file.name.split(".").pop() ?? "txt" : "txt";
  return {
    memory_id: captured.memory_id,
    status: "stored",
    filename: file.name,
    format: ext,
    char_count: content.length,
    preview: content.slice(0, 400),
    truncated: content.length > 400,
    keywords: [],
  };
}

async function ingestDocumentViaOneShot(
  file: File,
  opts: DocumentIngestOpts = {},
): Promise<IngestDocumentResult> {
  const form = new FormData();
  form.append("file", file, file.name);
  form.append("layer", opts.layer ?? "episodic");
  form.append("importance", String(opts.importance ?? 0.7));
  if (opts.goal?.trim()) form.append("label", opts.goal.trim());
  appendExpertFormFields(form, opts);

  const data = await requestMultipart<{
    ok?: boolean;
    memory_id: string;
    status: string;
    filename: string;
    preview?: string;
    keywords?: string[];
    char_count?: number;
  }>("/api/ingest/document", form, 90_000);

  const ext = file.name.includes(".") ? file.name.split(".").pop() ?? "txt" : "txt";
  const preview = data.preview ?? data.filename ?? file.name;
  return {
    memory_id: data.memory_id,
    status: data.status,
    filename: data.filename ?? file.name,
    format: ext,
    char_count: data.char_count ?? preview.length,
    preview,
    truncated: false,
    keywords: data.keywords ?? [],
  };
}

async function ingestDocumentViaGatewayTwoStep(
  file: File,
  opts: DocumentIngestOpts = {},
): Promise<IngestDocumentResult> {
  const form = new FormData();
    form.append("file", file, file.name);
    form.append("layer", opts.layer ?? "episodic");
    form.append("importance", String(opts.importance ?? 0.7));
    form.append("cognize", "false");
    form.append("process", "false");
    if (opts.goal?.trim()) form.append("goal", opts.goal.trim());
    appendExpertFormFields(form, opts);

    const upload = await requestMultipart<{
      file_id: string;
      filename: string;
      file_type: string;
      trace_id: string;
    }>("/v1/gateway/file/upload", form, 120_000);

    const processed = await gatewayIntentExecute<{
      file_id: string;
      status: string;
      filename: string;
      chunk_count: number;
      memory_ids: string[];
      summary?: string;
      keywords: string[];
      preview?: string;
    }>(
      "file_process",
      {
        file_id: upload.file_id,
        policy: {
          layer: opts.layer ?? "episodic",
          importance: opts.importance ?? 0.7,
          cognize: false,
          goal: opts.goal,
          chunk: true,
          summarize: true,
          index: true,
          ...expertPolicyFields(opts),
        },
      },
      180_000,
      upload.trace_id,
    );

    const preview =
      processed.preview ||
      processed.summary?.slice(0, 400) ||
      upload.filename;

    return {
      memory_id: processed.memory_ids?.[0] ?? processed.file_id,
      status: processed.status,
      filename: processed.filename ?? upload.filename,
      format: upload.file_type,
      char_count: preview.length,
      preview,
      truncated: false,
      keywords: processed.keywords ?? [],
    };
}

async function ingestDocumentViaGateway(
  file: File,
  opts: DocumentIngestOpts = {},
): Promise<IngestDocumentResult> {
  try {
    return await ingestDocumentViaOneShot(file, opts);
  } catch (primaryErr) {
    try {
      return await ingestDocumentViaGatewayTwoStep(file, opts);
    } catch (gatewayErr) {
      if (!isPersonalMode()) throw gatewayErr;
      try {
        return await ingestDocumentViaPersonalCapture(file, opts);
      } catch (fallbackErr) {
        const primary =
          primaryErr instanceof Error ? primaryErr.message : "文档导入失败";
        const gateway =
          gatewayErr instanceof Error ? gatewayErr.message : "Gateway 导入失败";
        const secondary =
          fallbackErr instanceof Error ? fallbackErr.message : "本地写入失败";
        throw new Error(`${primary}；${gateway}；${secondary}`);
      }
    }
  }
}

function chunkFilesForBatch(files: File[]): File[][] {
  const chunks: File[][] = [];
  let current: File[] = [];
  let size = 0;
  for (const file of files) {
    const nextSize = size + file.size;
    if (current.length > 0 && (current.length >= BATCH_MAX_FILES || nextSize > BATCH_MAX_BYTES)) {
      chunks.push(current);
      current = [];
      size = 0;
    }
    current.push(file);
    size += file.size;
  }
  if (current.length) chunks.push(current);
  return chunks;
}

function batchItemToResult(item: IngestDocumentBatchResult["indexed"][number]): IngestDocumentResult {
  const ext = item.filename.includes(".") ? item.filename.split(".").pop() ?? "txt" : "txt";
  return {
    memory_id: item.memory_id,
    status: item.status,
    filename: item.filename,
    format: ext,
    char_count: item.char_count,
    preview: item.preview,
    truncated: false,
    keywords: item.keywords ?? [],
  };
}

async function ingestDocumentBatch(
  files: File[],
  opts: DocumentIngestOpts = {},
): Promise<IngestDocumentResult[]> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file, file.name);
  }
  form.append("layer", opts.layer ?? "episodic");
  form.append("importance", String(opts.importance ?? 0.7));
  appendExpertFormFields(form, opts);
  const timeoutMs = Math.min(300_000, 30_000 + files.length * 2_000);
  const data = await requestMultipart<IngestDocumentBatchResult>(
    "/api/ingest/documents",
    form,
    timeoutMs,
  );
  if (!data.ok || !data.indexed?.length) {
    const detail = data.errors?.[0]?.error ?? "批量导入失败";
    throw new Error(detail);
  }
  return data.indexed.map(batchItemToResult);
}

async function stageDocumentBatch(
  files: File[],
): Promise<{ ok: boolean; trace_id: string; file_ids: string[]; count: number; status: string }> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file, file.name);
  }
  const timeoutMs = uploadTimeoutMs(files);
  return requestMultipart(
    "/api/ingest/documents/stage",
    form,
    timeoutMs,
    documentUploadTimeoutMessage(),
  );
}

async function submitFileProcessBatch(
  traceId: string,
  fileIds: string[],
  opts: DocumentIngestOpts,
): Promise<GatewayIntentResponse> {
  return request<GatewayIntentResponse>(
    "/v1/gateway/intent",
    {
      method: "POST",
      body: JSON.stringify({
        type: "file_process_batch",
        trace_id: traceId,
        payload: {
          file_ids: fileIds,
          policy: {
            layer: opts.layer ?? "episodic",
            importance: opts.importance ?? 0.7,
            ...expertPolicyFields(opts),
          },
        },
      }),
    },
    15_000,
  );
}

export type IngestDocumentsSubmit = {
  items: IngestDocumentResult[];
  traceIds: string[];
};

export type DiscoveredClientRow = {
  pubkey: string;
  pubkey_short?: string;
  host?: string;
  status?: string;
  trusted?: boolean;
  sources?: string[];
  last_seen?: number;
};

export type InstallStatsStatus = {
  ok?: boolean;
  configured?: boolean;
  stats_url_set?: boolean;
  opt_in?: boolean;
  opt_in_ui?: boolean;
  opt_in_env?: string;
  install_id?: string | null;
  install_id_short?: string | null;
  first_ping_sent?: boolean;
  first_ping_sent_at?: number | null;
  last_ping_error?: string | null;
  version?: string;
  edition?: string;
  error?: string;
};

export type UpdateCheckStatus = {
  ok?: boolean;
  enabled?: boolean;
  update_available?: boolean;
  current_version?: string;
  latest_version?: string;
  tag_name?: string;
  release_name?: string;
  release_url?: string;
  release_notes?: string;
  published_at?: string | null;
  source?: string;
  repo?: string;
  checked_at?: number;
  cached?: boolean;
  stale?: boolean;
  error?: string | null;
  skipped?: string;
};

export type ShareStatsStatus = {
  ok?: boolean;
  sharing_enabled?: boolean;
  always_share?: boolean;
  stats_url_set?: boolean;
  graph_id?: string | null;
  block_count?: number;
  local_memory_blocks?: number;
  share_count?: number;
  last_shared_at?: number | null;
  last_registry_ping_at?: number | null;
  last_registry_error?: string | null;
  version?: string;
  edition?: string;
  catalog?: {
    generation?: number;
    graph_count?: number;
    graphs?: Array<{
      graph_id?: string;
      graph_id_short?: string;
      owner?: string;
      owner_short?: string;
      topic?: string;
      head_generation?: number;
      updated_at?: number;
    }>;
  };
  visible?: {
    graph_count?: number;
    sharing_client_count?: number;
  };
  mesh?: {
    client_count?: number;
    online_count?: number;
    trusted_count?: number;
    discovered_count?: number;
  };
  error?: string;
};

export async function waitForDocumentIngest(traceIds: string[]): Promise<void> {
  const started = Date.now();
  const timeoutMs = 300_000;
  for (const traceId of traceIds) {
    await waitGatewayIntentCompletion(traceId, started, timeoutMs);
  }
}

async function ingestDocumentsAsync(
  files: File[],
  opts: DocumentIngestOpts = {},
): Promise<IngestDocumentsSubmit> {
  const items: IngestDocumentResult[] = [];
  const traceIds: string[] = [];

  const chunks = chunkFilesForBatch(files);
  for (const chunk of chunks) {
    const staged = await stageDocumentBatch(chunk);
    if (!staged.ok || !staged.file_ids?.length) {
      throw new Error("文件接收失败");
    }
    const queued = await submitFileProcessBatch(staged.trace_id, staged.file_ids, opts);
    traceIds.push(queued.trace_id || staged.trace_id);
    chunk.forEach((file, index) => {
      items.push({
        memory_id: staged.file_ids[index] ?? staged.trace_id,
        status: queued.status === "queued" ? "queued" : "indexed",
        filename: file.name,
        format: file.name.includes(".") ? file.name.split(".").pop() ?? "txt" : "txt",
        char_count: file.size,
        preview: file.name,
        truncated: false,
        keywords: [],
      });
    });
  }
  return { items, traceIds };
}

export async function ingestDocumentFiles(
  files: File[],
  opts: DocumentIngestOpts = {},
  options: { wait?: boolean } = {},
): Promise<IngestDocumentsSubmit> {
  if (files.length === 0) return { items: [], traceIds: [] };

  if (isPersonalMode()) {
    const submit = await ingestDocumentsAsync(files, opts);
    if (options.wait && submit.traceIds.length) {
      await waitForDocumentIngest(submit.traceIds);
      return {
        items: submit.items.map((item) => ({ ...item, status: "indexed" })),
        traceIds: submit.traceIds,
      };
    }
    return submit;
  }

  const merged: IngestDocumentResult[] = [];
  if (files.length === 1) {
    merged.push(await ingestDocumentViaGateway(files[0]!, opts));
  } else {
    const chunks = chunkFilesForBatch(files);
    for (const chunk of chunks) {
      merged.push(...(await ingestDocumentBatch(chunk, opts)));
    }
  }
  return { items: merged, traceIds: [] };
}

export type GatewayStateEvent = {
  type: "gateway_state";
  runtime: string;
  queue_size?: number;
  queue_depth?: number;
  operational_ready?: boolean;
  full_ready?: boolean;
};

/** Gateway control-plane state stream (replaces polling for boot/queue visibility). */
export function connectGatewayStateStream(
  onUpdate: (event: GatewayStateEvent) => void,
): () => void {
  if (!isWebSocketEnabled() || typeof WebSocket === "undefined") {
    return () => undefined;
  }
  const ws = new WebSocket(`${getWsBase()}/v1/gateway/ws`);
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data) as GatewayStateEvent;
      if (msg.type === "gateway_state") {
        onUpdate(msg);
      }
    } catch {
      /* ignore malformed frames */
    }
  };
  return () => {
    try {
      ws.close();
    } catch {
      /* ignore */
    }
  };
}

/** CNexus Product API — UI 只依赖 RUNTIME_CONTRACT.md 中的 Stable 面，不 import Python */
export const cnexusProductApi = {
  health: () => request<{ status: string; service?: string; version?: string }>("/v1/health"),
  /** Runtime Gateway v1 — always alive; use before heavy capability probe. */
  gatewayHealth: async (): Promise<Record<string, unknown>> => {
    if (isPersonalMode()) {
      try {
        const resp = await fetch(`${getApiBase()}/api/status`);
        if (resp.ok) {
          return {
            gateway: "alive",
            operational_ready: true,
            full_ready: true,
            boot_phase: "boot_4_ready",
            cognitive_status: "ready",
            progress: 100,
            reachable: true,
            booted: true,
            version: "2.0.0-personal",
          };
        }
      } catch {
        /* fall through */
      }
    }
    return request<Record<string, unknown>>("/v1/gateway/health", undefined, GATEWAY_HEALTH_TIMEOUT_MS);
  },
  gatewayState: () =>
    request<Record<string, unknown>>("/v1/gateway/state", undefined, GATEWAY_HEALTH_TIMEOUT_MS),
  gatewayWsUrl: () => `${getWsBase()}/v1/gateway/ws`,
  gatewayIntent: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/v1/gateway/intent", {
      method: "POST",
      body: JSON.stringify(body),
    }, RUNTIME_DEFAULT_TIMEOUT_MS),
  systemReady: () =>
    request<{
      status: string;
      boot_id: string;
      boot_phase?: string;
      token_valid: boolean;
      license_valid?: boolean;
      ws: string;
      http?: string;
      memory?: string;
      uptime_ms: number;
      version: string;
      boot?: Record<string, unknown>;
      render_mode?: string;
      ui?: string;
      checks?: Record<string, unknown>;
    }>("/v1/system/ready", undefined, RUNTIME_PROBE_TIMEOUT_MS),
  systemReadyFast: () =>
    request<{
      status: string;
      ui?: string;
      render_mode?: string;
      boot_id: string;
      boot_phase?: string;
      ws: string;
      http?: string;
      checks?: Record<string, unknown>;
    }>("/v1/system/ready?mode=fast", undefined, FAST_READY_TIMEOUT_MS),
  systemReadyFull: () =>
    request<{
      status: string;
      boot_id: string;
      boot_phase?: string;
      ws: string;
      boot?: Record<string, unknown>;
      ready_gate_ok?: boolean;
      layer?: string;
      ready?: boolean;
      reason?: string | null;
      progress?: number;
      operational_ready?: boolean;
      full_ready?: boolean;
      cognitive_status?: string;
      capabilities?: Record<string, boolean>;
      ready_for_chat?: boolean;
      ready_for_upload?: boolean;
    }>("/v1/system/ready?mode=full", undefined, RUNTIME_PROBE_TIMEOUT_MS),
  systemCapability: () =>
    request<Record<string, unknown>>("/v1/system/capability"),
  reportConflictLog: (body: Record<string, unknown>) =>
    request<{ ok: boolean }>("/v1/system/conflict_log", {
      method: "POST",
      body: JSON.stringify(body),
    }, 5_000),
  conflictLogTail: (tail = 200) =>
    request<{ path: string; entries: Record<string, unknown>[] }>(
      `/v1/system/conflict_log?tail=${tail}`,
      undefined,
      RUNTIME_PROBE_TIMEOUT_MS,
    ),
  systemCompute: (intent: string, payload: Record<string, unknown> = {}) =>
    request<{
      type?: string;
      status?: string;
      data?: unknown;
      l3?: number;
      cluster?: string;
      intent?: string;
      path?: string;
    }>(
      "/v1/system/compute",
      { method: "POST", body: JSON.stringify({ intent, payload }) },
      RUNTIME_PROBE_TIMEOUT_MS,
    ),
  chatFast: (input: string, options?: { timeout_s?: number; model_id?: string }) =>
    gatewayIntentExecute<{
      response: string;
      status: string;
      path: string;
      mode?: string;
    }>(
      "chat_fast",
      {
        input,
        timeout_s: options?.timeout_s,
        model_id: options?.model_id,
      },
      Math.max(FAST_READY_TIMEOUT_MS, (options?.timeout_s ?? 3) * 1000 + 500),
    ),
  chatFastStreamUrl: () => `${getApiBase()}/v1/gateway/intent/stream`,
  sibtProject: (input: string, options?: { source_lang?: string; intent?: string }) =>
    request<{
      status: string;
      semantic_invariant_id: string;
      semantic_layer: Record<string, unknown>;
      zh: { text: string; faithfulness: number };
      en: { text: string; faithfulness: number };
      reversibility_score: number;
      loss_report: Record<string, unknown>;
      mode: string;
    }>(
      "/v1/sibt/project",
      {
        method: "POST",
        body: JSON.stringify({ input, ...options }),
      },
      RUNTIME_PROBE_TIMEOUT_MS,
    ),
  systemReadyStreamUrl: () => `${getApiBase()}/v1/system/ready/stream`,
  mindOverview: () => request<MindOverview>("/v1/mind/overview"),
  v2Overview: async (): Promise<MindOverview> => {
    const timeoutMs = isPersonalMode() ? 20_000 : RUNTIME_DEFAULT_TIMEOUT_MS;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const resp = await fetch(getApiBase() + "/api/status", { signal: controller.signal });
      if (!resp.ok) throw new Error(`status ${resp.status}`);
      const raw: Record<string, unknown> = await resp.json();
      return statusToMindOverview(raw as never);
    } catch {
      if (isPersonalMode()) {
        throw new Error(requestNetworkErrorMessage());
      }
      return request<MindOverview>("/v1/mind/overview");
    } finally {
      window.clearTimeout(timer);
    }
  },
  cseLive: (window = 200) =>
    request<CognitiveOutput>(`/v1/cse/live?window=${window}`, undefined, 15_000),
  cseSynthesize: (window = 200) =>
    request<CognitiveOutput>(
      "/v1/cse/synthesize",
      { method: "POST", body: JSON.stringify({ window, mode: "full" }) },
      30_000,
    ),
  runtimeLogs: (limit = 100) =>
    request<{ logs: RuntimeLogEntry[]; count: number }>(`/logs?limit=${limit}`),
  gtbsEvents: (limit = 300) =>
    request<{ events: GtbsRawEvent[]; count: number }>(`/v1/gtbs/events?limit=${limit}`),
  executionStatus: () =>
    request<{
      active_chat_provider: string | null;
      active_embed_provider: string | null;
      providers: Record<
        string,
        {
          state: string;
          capabilities: string[];
          reachable: boolean;
          issues: string[];
          details: Record<string, unknown>;
        }
      >;
      suggested_actions: string[];
      embedding: Record<string, unknown>;
      ollama: Record<string, unknown>;
    }>("/v1/execution/status", undefined, 12_000),
  executionBootstrap: (models?: string[]) =>
    request<{ ok: boolean; detail: string; results: Record<string, unknown>[] }>(
      "/v1/execution/bootstrap",
      {
        method: "POST",
        body: JSON.stringify({ models }),
      },
      120_000,
    ),
  capture: (
    content: string,
    layer = "episodic",
    role = "user",
    importance = 0.6,
    cognize = true,
  ) =>
    request<{ memory_id: string; cognition?: Record<string, unknown> }>("/v1/memory/capture", {
      method: "POST",
      body: JSON.stringify({ role, content, layer, importance, cognize }),
    }),
  ingestDocument: (
    file: File,
    opts: {
      layer?: string;
      importance?: number;
      cognize?: boolean;
      goal?: string;
    } = {},
  ) => ingestDocumentViaGateway(file, opts),
  gatewayFileSummary: (fileId: string) =>
    request<{
      file_id: string;
      status: string;
      filename: string;
      summary: string;
      keywords: string[];
      chunk_count: number;
      highlights: string[];
    }>(`/v1/gateway/file/${encodeURIComponent(fileId)}/summary`),
  recall: (query: string) =>
    request<{ context: string }>(`/v1/memory/recall?query=${encodeURIComponent(query)}`),
  v2Converse: async (text: string): Promise<MindOverview> => {
    try {
      const resp = await fetch(getApiBase() + "/api/converse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const raw: Record<string, unknown> = await resp.json();
      return converseToMindOverview(raw as never);
    } catch {
      return request<MindOverview>("/v1/mind/overview");
    }
  },
  /** Thinking page — POST /api/analyze returns canonical RelationshipAnalysis. */
  analyzeRelationship: async (
    text: string,
    options?: { fast?: boolean; use_llm?: boolean; save_card?: boolean },
  ): Promise<RelationshipAnalysis> => {
    const fast = options?.fast ?? false;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), fast ? 15_000 : 120_000);
    try {
      const resp = await fetch(`${getApiBase()}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          text,
          fast,
          use_llm: fast ? false : (options?.use_llm ?? true),
          save_card: options?.save_card ?? true,
        }),
      });
      const data = (await resp.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        analysis?: RelationshipAnalysis;
      };
      if (!resp.ok || data.ok === false || !data.analysis) {
        throw new Error(String(data.error || `分析失败 (${resp.status})`));
      }
      assertRelationshipAnalysis(data.analysis);
      return data.analysis;
    } finally {
      window.clearTimeout(timer);
    }
  },
  /** Timeline pipeline — POST /api/analyze/timeline (Event → State → Canonical). */
  analyzeRelationshipTimeline: async (payload: {
    conversation: Array<{ timestamp: string | number; speaker: string; text: string }>;
    entities?: [string, string];
    sourceInput?: string;
    save_card?: boolean;
    use_llm?: boolean;
  }) => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 90_000);
    try {
      const resp = await fetch(`${getApiBase()}/api/analyze/timeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          save_card: false,
          use_llm: true,
          ...payload,
        }),
      });
      const data = (await resp.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        analysis?: RelationshipAnalysis;
        eventStream?: unknown;
        timeline?: unknown;
        relationshipState?: string;
      };
      if (!resp.ok || data.ok === false || !data.analysis) {
        throw new Error(String(data.error || `时间轴分析失败 (${resp.status})`));
      }
      assertRelationshipAnalysis(data.analysis);
      return data;
    } finally {
      window.clearTimeout(timer);
    }
  },
  listRelationshipCardsApi: async (): Promise<RelationshipAnalysisCard[]> => {
    const resp = await fetch(`${getApiBase()}/api/analyze/cards`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      cards?: RelationshipAnalysisCard[];
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || `加载卡片失败 (${resp.status})`));
    }
    const cards = data.cards ?? [];
    const coerced: RelationshipAnalysisCard[] = [];
    for (const row of cards) {
      const parsed = coerceRelationshipCard(row);
      if (parsed) coerced.push(parsed);
    }
    return coerced;
  },
  deleteRelationshipCardApi: async (id: string): Promise<void> => {
    const resp = await fetch(`${getApiBase()}/api/analyze/cards/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    const data = (await resp.json().catch(() => ({}))) as { ok?: boolean; error?: string };
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || `删除失败 (${resp.status})`));
    }
  },
  v2ClearMemory: async (keepModels = true) => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 30_000);
    try {
      const resp = await fetch(`${getApiBase()}/api/memory/clear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keep_models: keepModels }),
        signal: controller.signal,
      });
      const data = (await resp.json().catch(() => ({}))) as {
        ok?: boolean;
        cleared?: boolean;
        keep_models?: boolean;
        error?: string;
        detail?: string;
        message?: string;
      };
      if (!resp.ok || data.ok === false) {
        throw new Error(
          data.error || data.detail || data.message || formatRequestError(data, resp.status, resp.statusText),
        );
      }
      return {
        ok: Boolean(data.ok ?? data.cleared),
        cleared: Boolean(data.cleared),
        keep_models: data.keep_models ?? keepModels,
      };
    } finally {
      window.clearTimeout(timer);
    }
  },
  promoteMemory: async (blockId: string, memoryLevel: "project" | "core" | "foundation", confirm = true) => {
    const resp = await fetch(`${getApiBase()}/v1/memory/promote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ block_id: blockId, memory_level: memoryLevel, confirm }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      message?: string;
      memory_level?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.message || data.error || resp.statusText || "Promote failed");
    }
    return data;
  },
  upgradeFoundation: async (blockId: string, content: string) => {
    const resp = await fetch(`${getApiBase()}/v1/memory/foundation/upgrade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ block_id: blockId, content }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      block_id?: string;
      memory_version?: number;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Foundation upgrade failed");
    }
    return data;
  },
  foundationVersions: async (constitutionKey?: string) => {
    const qs = constitutionKey ? `?constitution_key=${encodeURIComponent(constitutionKey)}` : "";
    const resp = await fetch(`${getApiBase()}/v1/memory/foundation/versions${qs}`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      versions?: Array<Record<string, unknown>>;
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Failed to load foundation versions");
    }
    return data;
  },
  foundationVersionTree: async (constitutionKey?: string) => {
    const qs = constitutionKey ? `?constitution_key=${encodeURIComponent(constitutionKey)}` : "";
    const resp = await fetch(`${getApiBase()}/v1/memory/foundation/tree${qs}`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      trees?: Array<Record<string, unknown>>;
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Failed to load foundation tree");
    }
    return data;
  },
  runtimeBootStatus: async () => {
    const resp = await fetch(`${getApiBase()}/v1/runtime/boot`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      boot_phase?: string;
      signature_verified?: boolean;
      ed25519_signed?: boolean;
      constitution_docs?: number;
      policy_docs?: number;
      error?: string;
    };
    if (!resp.ok) {
      throw new Error(data.error || resp.statusText || "Runtime boot status failed");
    }
    return data;
  },
  projectActive: async () => {
    const resp = await fetch(`${getApiBase()}/v1/project/active`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      active_project?: Record<string, unknown>;
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Failed to load active project");
    }
    return data;
  },
  setProjectActive: async (body: {
    project_id: string;
    lock?: boolean;
    lifecycle_id?: string;
    name?: string;
  }) => {
    const resp = await fetch(`${getApiBase()}/v1/project/active`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      active_project?: Record<string, unknown>;
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Failed to set active project");
    }
    return data;
  },
  listProjects: async () => {
    const resp = await fetch(`${getApiBase()}/v1/project/list`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      projects?: Array<Record<string, unknown>>;
      active_project?: Record<string, unknown>;
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Failed to list projects");
    }
    return data;
  },
  clearConversationScratch: async () => {
    const resp = await fetch(`${getApiBase()}/v1/conversation/scratch/clear`, { method: "POST" });
    const data = (await resp.json().catch(() => ({}))) as { ok?: boolean; error?: string };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Failed to clear scratch");
    }
    return data;
  },
  fetchDashboardStatus: async (): Promise<DashboardStatus> => {
    const resp = await fetch(`${getApiBase()}/api/dashboard/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as DashboardStatus;
    if (!resp.ok) {
      return { ok: false, error: data.error || resp.statusText };
    }
    return data;
  },
  triggerRemSleep: async (force = true) => {
    const resp = await fetch(`${getApiBase()}/v1/memory/rem-sleep`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      skipped?: string;
      error?: string;
      pruned_nodes?: number;
      pruned_blocks?: number;
      pruned_traces?: number;
      facts_created?: number;
      status?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "REM sleep failed");
    }
    return data;
  },
  uploadCodeAsset: async (content: string, filename: string, project = false) => {
    const resp = await fetch(`${getApiBase()}/api/upload/code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, filename, project }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      id?: string;
      summary?: string;
      deduped?: boolean;
      status?: string;
      peer_push?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Code asset upload failed");
    }
    return data;
  },
  uploadImageAsset: async (file: File, project = false) => {
    const form = new FormData();
    form.append("image", file);
    if (project) form.append("project", "true");
    const resp = await fetch(`${getApiBase()}/api/upload/image`, {
      method: "POST",
      body: form,
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      id?: string;
      desc?: string;
      deduped?: boolean;
      status?: string;
      peer_push?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Image asset upload failed");
    }
    return data;
  },
  searchAssets: async (
    query: string,
    kind?: "code" | "image",
    semantic = false,
    scope: "local" | "trusted" | "network" = "local",
  ) => {
    const params = new URLSearchParams({ q: query, scope });
    if (kind) params.set("kind", kind);
    const path = semantic ? "/api/asset/search/semantic" : "/api/asset/search";
    const resp = await fetch(`${getApiBase()}${path}?${params.toString()}`, {
      cache: "no-store",
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      hits?: Array<{
        kind?: string;
        block_id?: string;
        asset_id?: string;
        type?: string;
        filename?: string;
        summary?: string;
        desc?: string;
        score?: number;
        text?: string;
        timestamp?: string | number;
        embed_mode?: string;
        source_peer?: string;
        peer_host?: string;
        content_kind?: string;
        local_blob?: boolean;
        memory_origin?: "local" | "trusted" | "network";
      }>;
      scope?: string;
      federated?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Asset search failed");
    }
    return data.hits || [];
  },
  searchAssetsByImage: async (file: File, kind: "image" = "image", limit = 10) => {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    const image_base64 = btoa(binary);
    const resp = await fetch(`${getApiBase()}/api/asset/search/semantic`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_base64, kind, limit }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      hits?: Array<{
        asset_id?: string;
        type?: string;
        filename?: string;
        score?: number;
        embed_mode?: string;
        source_peer?: string;
        content_kind?: string;
        local_blob?: boolean;
      }>;
      cross_modal?: boolean;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Image semantic search failed");
    }
    return data.hits || [];
  },
  fetchAssetPushQueue: async (process = false) => {
    const params = process ? "?process=1" : "";
    const resp = await fetch(`${getApiBase()}/api/asset/push/queue${params}`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      queue?: { pending?: number; dead?: number; enabled?: boolean };
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Push queue fetch failed");
    }
    return data;
  },
  pushAssetToPeers: async (assetId: string) => {
    const resp = await fetch(`${getApiBase()}/api/asset/push`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_id: assetId }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      pushed?: number;
      peer_count?: number;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Asset push failed");
    }
    return data;
  },
  pullAssetFromPeer: async (assetId: string, sourcePeer?: string, peerHost?: string) => {
    const resp = await fetch(`${getApiBase()}/api/asset/pull`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset_id: assetId,
        ...(sourcePeer ? { source_peer: sourcePeer } : {}),
        ...(peerHost ? { peer_host: peerHost } : {}),
      }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      local?: boolean;
      pulled?: boolean;
      status?: string;
      source_peer?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Asset pull failed");
    }
    return data;
  },
  fetchNegotiationConflicts: async () => {
    const resp = await fetch(`${getApiBase()}/api/conflict/negotiation`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      negotiation_conflicts?: {
        enabled?: boolean;
        llm_auto_resolve?: boolean;
        count?: number;
        context_preview?: string;
        items?: Array<{
          id?: string;
          at?: number;
          peer_pubkey?: string;
          negotiation_error?: string;
          negotiation_message?: string;
          global_entropy?: string;
          conflict_count?: number;
          resolved_count?: number;
          llm_used?: boolean;
          pairs?: Array<{
            block_id?: string;
            local?: { content?: string; label?: string };
            remote?: { content?: string; label?: string; source_peer?: string };
            resolution?: {
              status?: string;
              merged_content?: string;
              fork?: { local?: string; remote?: string; label?: string };
              rationale?: string;
              source?: string;
              temperature?: number;
              global_entropy?: string;
              error?: string;
            };
          }>;
        }>;
      };
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Negotiation audit fetch failed");
    }
    return data.negotiation_conflicts || { enabled: false, count: 0, items: [] };
  },
  updateConflictSettings: async (settings: {
    llmAutoResolve?: boolean;
    autoResolveEnabled?: boolean;
  }) => {
    const body: Record<string, boolean> = {};
    if (settings.llmAutoResolve != null) body.llm_auto_resolve = settings.llmAutoResolve;
    if (settings.autoResolveEnabled != null) body.auto_resolve_enabled = settings.autoResolveEnabled;
    const resp = await fetch(`${getApiBase()}/api/conflict/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      llm_auto_resolve?: boolean;
      auto_resolve_enabled?: boolean;
      runtime_override?: boolean;
      auto_resolve_runtime?: boolean;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Conflict settings update failed");
    }
    return data;
  },
  resolveConflictPair: async (payload: {
    block_id?: string;
    local: { content?: string; label?: string };
    remote: { content?: string; label?: string; source_peer?: string };
    apply?: boolean;
    use_llm?: boolean;
    mode?: "precision" | "emergent";
  }) => {
    const resp = await fetch(`${getApiBase()}/api/conflict/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        block_id: payload.block_id,
        local: payload.local,
        remote: payload.remote,
        apply: payload.apply ?? true,
        use_llm: payload.use_llm ?? true,
        mode: payload.mode ?? "emergent",
      }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Conflict resolve failed"));
    }
    return data;
  },
  fetchEntropyStatus: async () => {
    const resp = await fetch(`${getApiBase()}/api/entropy/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      entropy?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Entropy status unavailable");
    }
    return data.entropy || { enabled: false };
  },
  forcePeerSync: async (payload: { pubkey?: string; host?: string; genesis?: boolean }) => {
    const resp = await fetch(`${getApiBase()}/api/peer/force-sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pubkey: payload.pubkey,
        host: payload.host,
        genesis: payload.genesis ?? false,
      }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Peer sync failed"));
    }
    return data;
  },
  updateConsensusReputation: async (pubkey: string, action: "blacklist" | "restore" | "ban") => {
    const resp = await fetch(`${getApiBase()}/api/consensus/reputation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pubkey, action }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Reputation update failed"));
    }
    return data;
  },
  fetchPruningStatus: async () => {
    const resp = await fetch(`${getApiBase()}/api/pruning/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      pruning?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Pruning status unavailable");
    }
    return data.pruning || { enabled: false };
  },
  runCognitivePruning: async (dryRun = false) => {
    const resp = await fetch(`${getApiBase()}/api/pruning/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dry_run: dryRun }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      report?: Record<string, unknown>;
      status?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Pruning run failed");
    }
    return data;
  },
  reindexAssets: async () => {
    const resp = await fetch(`${getApiBase()}/api/asset/reindex`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as { ok?: boolean; error?: string; indexed?: number };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Asset reindex failed");
    }
    return data;
  },
  runMetaReflection: async (question: string, useLlm = true) => {
    const resp = await fetch(`${getApiBase()}/api/reflect/meta`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, use_llm: useLlm, limit: 100, window_days: 7 }),
    });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      error?: string;
      reflection?: string;
      source?: string;
      biases?: Array<{ domain?: string; share?: number }>;
      analysis?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || resp.statusText || "Meta reflection failed");
    }
    return data;
  },
  runLogReplay: async (force = true) => {
    const resp = await fetch(`${getApiBase()}/api/replay/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Log replay failed"));
    }
    return data;
  },
  fetchAwakeningStatus: async () => {
    const resp = await fetch(`${getApiBase()}/api/awakening/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as { ok?: boolean; awakening?: Record<string, unknown> };
    if (!resp.ok || data.ok === false) {
      throw new Error("Awakening status unavailable");
    }
    return data.awakening || {};
  },
  fetchConnectivityStatus: async () => {
    const resp = await fetch(`${getApiBase()}/api/connectivity/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      network?: Record<string, unknown>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error("Connectivity status unavailable");
    }
    return data.network || {};
  },
  fetchDhtStatus: async () => {
    const resp = await fetch(`${getApiBase()}/api/dht/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as { ok?: boolean; dht?: Record<string, unknown> };
    if (!resp.ok || data.ok === false) {
      throw new Error("DHT status unavailable");
    }
    return data.dht || {};
  },
  connectToPeer: async (peerId: string) => {
    const resp = await fetch(`${getApiBase()}/api/connectivity/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ peer_id: peerId }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(
        humanizeNetworkConnectError(String(data.error || resp.statusText || "Connect failed"), {
          hint: String(data.hint || ""),
        }),
      );
    }
    return data;
  },
  applicationRepair: async (body: {
    action: "hook" | "gate" | "execute";
    confirm?: boolean;
    peer_id?: string;
    peer_host?: string;
    host?: string;
    plans?: unknown[];
    suggested_sources?: unknown[];
  }) => {
    const resp = await fetch(`${getApiBase()}/api/application/repair`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok && resp.status !== 409) {
      throw new Error(String(data.error || resp.statusText || "Application repair failed"));
    }
    return { data, status: resp.status };
  },
  fetchApplicationStatus: async () => {
    const resp = await fetch(`${getApiBase()}/api/application/status`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || "Application status unavailable"));
    }
    return data;
  },
  publishLocalMemory: async (topic = "memory/local") => {
    const resp = await fetch(`${getApiBase()}/api/application/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ memory: true, topic }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Publish local memory failed"));
    }
    return data;
  },
  fetchNetworkPeers: async () => {
    const resp = await fetch(`${getApiBase()}/api/peers`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      peers?: Record<string, Record<string, unknown>>;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error("Peers status unavailable");
    }
    return data.peers || {};
  },
  fetchInstallStats: async () => {
    const resp = await fetch(`${getApiBase()}/api/stats/install`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as InstallStatsStatus;
    if (!resp.ok || data.ok === false) {
      throw new Error("Install stats status unavailable");
    }
    return data;
  },
  fetchUpdateCheck: async (refresh = false) => {
    const qs = refresh ? "?refresh=1" : "";
    const resp = await fetch(`${getApiBase()}/api/update/check${qs}`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as UpdateCheckStatus;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || "Update check unavailable"));
    }
    return data;
  },
  fetchShareStats: async () => {
    const resp = await fetch(`${getApiBase()}/api/share/stats`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as ShareStatsStatus;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || "Share stats unavailable"));
    }
    return data;
  },
  setInstallStatsOptIn: async (enabled: boolean) => {
    const resp = await fetch(`${getApiBase()}/api/stats/opt-in`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const data = (await resp.json().catch(() => ({}))) as InstallStatsStatus & { error?: string };
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || "Failed to update install stats preference"));
    }
    return data;
  },
  fetchDiscoveredClients: async (refresh = false) => {
    const qs = refresh ? "?refresh=1" : "";
    const resp = await fetch(`${getApiBase()}/api/peers/discovered${qs}`, { cache: "no-store" });
    const data = (await resp.json().catch(() => ({}))) as {
      ok?: boolean;
      clients?: DiscoveredClientRow[];
      count?: number;
      trusted_count?: number;
      online_count?: number;
      discovered_count?: number;
      refreshed?: boolean;
      lan_scan_ok?: boolean;
      lan_found?: number;
      error?: string;
    };
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || "Discovered clients unavailable"));
    }
    return data;
  },
  banPeer: async (peerId: string, reason = "ui_ban") => {
    const resp = await fetch(`${getApiBase()}/api/network/firewall/ban`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ peer_id: peerId, reason }),
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Ban failed"));
    }
    return data;
  },
  fetchAsset: async (assetId: string, includeContent = false) => {
    const params = includeContent ? "?content=1" : "";
    const resp = await fetch(`${getApiBase()}/api/asset/${assetId}${params}`, {
      cache: "no-store",
    });
    const data = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok || data.ok === false) {
      throw new Error(String(data.error || resp.statusText || "Asset fetch failed"));
    }
    return data;
  },
  chat: (
    message: string,
    modelId?: string,
    useMemory = true,
    fullCognitiveLoop = false,
    allowProactive = true,
  ) =>
    gatewayIntentExecute<{
      reply: string;
      model_name: string;
      coherence_score?: number;
      meta_reflection?: Record<string, unknown>;
      emotion_state?: Record<string, unknown>;
      active_intent?: string;
      value_alignment?: Record<string, unknown>;
      proactive?: Record<string, unknown>;
      latency_ms?: number;
      cognitive_loop?: boolean;
      human_authorized?: boolean;
    }>(
      "chat",
      {
        message,
        model_id: modelId,
        use_memory: useMemory,
        full_cognitive_loop: fullCognitiveLoop,
        allow_proactive: allowProactive,
      },
      120_000,
    ),
  chatPrepare: (
    message: string,
    modelId?: string,
    useMemory = true,
    fullCognitiveLoop = getDefaultFullCognitiveLoop(),
  ) =>
    gatewayIntentExecute<{
      prepare_id: string;
      user_message: string;
      memory_context: string;
      governance_injection: string;
      system_prompt: string;
      outbound_preview: string;
      has_injection: boolean;
      chat_governance_notes: Record<string, unknown>[];
      expires_in_seconds: number;
    }>(
      "chat_prepare",
      {
        message,
        model_id: modelId,
        use_memory: useMemory,
        full_cognitive_loop: fullCognitiveLoop,
      },
      60_000,
    ),
  chatConfirm: (
    prepareId: string,
    modelId?: string,
    options?: {
      authorized?: boolean;
      sendMode?: "with_injection" | "user_only";
      fullCognitiveLoop?: boolean;
    },
  ) =>
    gatewayIntentExecute<{
      reply: string;
      model_name: string;
      coherence_score?: number;
      meta_reflection?: Record<string, unknown>;
      emotion_state?: Record<string, unknown>;
      active_intent?: string;
      value_alignment?: Record<string, unknown>;
      proactive?: Record<string, unknown>;
      latency_ms?: number;
      human_authorized?: boolean;
      memory_capture?: {
        chat_governance_notes?: Array<Record<string, unknown>>;
        intercepted?: boolean;
        cognition_deferred?: boolean;
      };
    }>(
      "chat_confirm",
      {
        prepare_id: prepareId,
        authorized: options?.authorized ?? true,
        send_mode: options?.sendMode ?? "with_injection",
        model_id: modelId,
        full_cognitive_loop: options?.fullCognitiveLoop ?? getDefaultFullCognitiveLoop(),
      },
      120_000,
    ),
  chatCancel: (prepareId: string) =>
    gatewayIntentExecute<{ ok: boolean; cancelled: boolean }>(
      "chat_cancel",
      { prepare_id: prepareId, authorized: false },
      RUNTIME_DEFAULT_TIMEOUT_MS,
    ),
  interact: (
    message: string,
    options?: {
      userId?: string;
      sessionId?: string;
      useMemory?: boolean;
      temperature?: number;
    },
  ) =>
    request<{
      response: string;
      coherence_score?: number;
      governance_pass: boolean;
      reflection?: string;
      meta?: Record<string, unknown>;
    }>("/v1/interact", {
      method: "POST",
      body: JSON.stringify({
        user_id: options?.userId ?? "cnexus-ui",
        message,
        session_id: options?.sessionId,
        options: {
          use_memory: options?.useMemory ?? true,
          temperature: options?.temperature ?? 0.7,
        },
      }),
    }, 120_000),
  memoryStats: () =>
    request<{ total: number; by_layer: Record<string, number>; avg_importance: number }>(
      "/v1/memory/stats",
    ),
  models: () => request<{ models: ModelProfile[] }>("/models"),
  logs: (limit = 100) =>
    request<{ logs: RuntimeLogEntry[]; count: number }>(`/logs?limit=${limit}`),
  connectStateStream: (onUpdate: (state: RuntimeState) => void) => {
    if (!isWebSocketEnabled()) {
      return { close: () => undefined, onclose: null } as unknown as WebSocket;
    }
    const ws = new WebSocket(`${getWsBase()}/ws/state`);
    ws.onmessage = (e) => onUpdate(JSON.parse(e.data) as RuntimeState);
    ws.onerror = () => ws.close();
    return ws;
  },
  connectLogStream: (onEntry: (entry: RuntimeLogEntry) => void) => {
    if (!isWebSocketEnabled()) {
      return { close: () => undefined, onclose: null } as unknown as WebSocket;
    }
    const ws = new WebSocket(`${getWsBase()}/logs/ws`);
    ws.onmessage = (e) => onEntry(JSON.parse(e.data));
    ws.onerror = () => ws.close();
    return ws;
  },
};

export type StreamReadyEvent = {
  phase: "shell" | "local" | "cluster" | "final";
  status?: string;
  render_mode?: string;
  boot_phase?: string;
  ws?: string;
  l3?: boolean;
  memory?: string;
  cluster?: string;
  ready?: boolean;
  gate?: Record<string, unknown>;
};

/** Subscribe to Fast-Path v2 SSE progressive ready stream. */
export function subscribeSystemReadyStream(
  onEvent: (event: StreamReadyEvent) => void,
): () => void {
  if (!isWebSocketEnabled() && isPersonalMode()) {
    return () => {};
  }
  if (typeof window === "undefined" || typeof EventSource === "undefined") {
    return () => {};
  }

  const token = getApiToken();
  const url = new URL(cnexusProductApi.systemReadyStreamUrl());
  if (token) url.searchParams.set("token", token);

  const es = new EventSource(url.toString());
  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data) as StreamReadyEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  es.onerror = () => es.close();

  return () => es.close();
}

export type ChatFastStreamEvent = {
  token?: string;
  done?: boolean;
  status?: string;
  path?: string;
  error?: string;
};

/** Subscribe to LLM Fast Lane v2 SSE token stream (POST + fetch reader). */
export function subscribeChatFastStream(
  input: string,
  onEvent: (event: ChatFastStreamEvent) => void,
  options?: { timeout_s?: number; model_id?: string },
): () => void {
  const controller = new AbortController();
  const timeoutMs = Math.max(
    FAST_READY_TIMEOUT_MS,
    (options?.timeout_s ?? 30) * 1000 + 1000,
  );
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getApiToken();
  if (token) headers["X-CNexus-Token"] = token;

  void (async () => {
    try {
      const res = await fetch(cnexusProductApi.chatFastStreamUrl(), {
        method: "POST",
        headers,
        body: JSON.stringify({
          type: "chat_fast_stream",
          payload: {
            input,
            timeout_s: options?.timeout_s,
            model_id: options?.model_id,
          },
          source: "frontend",
        }),
        signal: controller.signal,
      });
      if (res.status === 202) {
        onEvent({ status: "queued", error: "[System: Queueing...]" });
        return;
      }
      if (!res.ok || !res.body) return;

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let pending = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        pending += decoder.decode(value, { stream: true });
        const frames = pending.split("\n\n");
        pending = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame
            .split("\n")
            .find((l) => l.startsWith("data:"));
          if (!line) continue;
          try {
            onEvent(JSON.parse(line.slice(5).trim()) as ChatFastStreamEvent);
          } catch {
            /* ignore malformed frames */
          }
        }
      }
    } catch {
      /* aborted or network error */
    } finally {
      clearTimeout(timer);
    }
  })();

  return () => {
    clearTimeout(timer);
    controller.abort();
  };
}

/** Poll authoritative Runtime READY (REST). Warming = API alive, not yet fully ready. */
export type RuntimeProbeDetail = {
  phase: "ready" | "warming" | "offline";
  bootPhase?: string | null;
  ready?: boolean;
  reason?: string | null;
  progress?: number | null;
};

export type SystemReadyPayload = {
  status?: string;
  boot_phase?: string;
  ws?: string;
  http?: string;
  ready?: boolean;
  reason?: string | null;
  progress?: number;
  runtime_pointer?: boolean;
  operational_ready?: boolean;
  full_ready?: boolean;
  ready_for_chat?: boolean;
  ready_for_upload?: boolean;
  capabilities?: Record<string, boolean>;
};

function classifyReadyPayload(
  payload: SystemReadyPayload,
  options?: { skipWs?: boolean },
): RuntimeProbeDetail {
  const bootPhase = payload.boot_phase ?? null;
  const bootMeta = {
    bootPhase,
    ready: payload.ready ?? payload.full_ready,
    reason: payload.reason ?? null,
    progress: payload.progress ?? null,
  };
  if (payload.operational_ready || payload.ready_for_chat || payload.status === "operational") {
    return {
      phase: "ready",
      ...bootMeta,
      ready: Boolean(payload.operational_ready ?? payload.ready_for_chat),
    };
  }
  if (payload.status === "ready_fast" || payload.status === "streaming") {
    return { phase: "warming", ...bootMeta };
  }
  if (payload.status === "ready" && payload.ws === "alive") {
    if (options?.skipWs) return { phase: "ready", ...bootMeta, ready: true, progress: 100, reason: null };
    return { phase: "ready", ...bootMeta, ready: true, progress: 100, reason: null };
  }
  if (payload.status === "ready" && payload.runtime_pointer === false) {
    return { phase: "warming", ...bootMeta };
  }
  if (payload.status === "warming") {
    return { phase: "warming", ...bootMeta };
  }
  if (bootPhase && bootPhase !== "boot_0_api" && bootPhase !== "boot_4_ready") {
    return { phase: "warming", ...bootMeta };
  }
  if (payload.http === "listening" && payload.ws === "starting") {
    return { phase: "warming", ...bootMeta };
  }
  return { phase: "offline", ...bootMeta };
}

export async function probeRuntimeReadyDetail(options?: {
  wsTimeoutMs?: number;
  skipWs?: boolean;
  fast?: boolean;
}): Promise<RuntimeProbeDetail> {
  try {
    if (options?.fast) {
      const payload = await cnexusProductApi.systemReadyFast();
      return classifyReadyPayload(payload, options);
    }
    const payload = await cnexusProductApi.systemCapability();
    const classified = classifyReadyPayload(payload, options);
    if (classified.phase === "ready" && payload.ws === "alive" && !options?.skipWs) {
      const wsOk = await probeWsStateHandshake(options?.wsTimeoutMs ?? 5000);
      return wsOk ? classified : { phase: "warming", bootPhase: classified.bootPhase };
    }
    return classified;
  } catch {
    try {
      const health = await cnexusProductApi.health();
      if (health.status === "ok") return { phase: "warming", bootPhase: null };
    } catch {
      /* API down */
    }
    return { phase: "offline", bootPhase: null };
  }
}

export async function probeRuntimeReady(options?: {
  wsTimeoutMs?: number;
  skipWs?: boolean;
  fast?: boolean;
}): Promise<"ready" | "warming" | "offline"> {
  const detail = await probeRuntimeReadyDetail(options);
  return detail.phase;
}

/** Personal edition: lightweight probe via bundled /api/status. */
export async function probePersonalBackendOnline(timeoutMs = 8_000): Promise<boolean> {
  if (!isPersonalMode()) return false;
  try {
    const resp = await fetch(`${getApiBase()}/api/status`, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/** True when runtime is operational (chat/basic API). Set requireFull for upload gate. */
export async function isRuntimeReady(options?: {
  wsTimeoutMs?: number;
  skipWs?: boolean;
  requireFull?: boolean;
}): Promise<boolean> {
  if (isPersonalMode()) {
    if (await probePersonalBackendOnline(5_000)) return true;
  }
  try {
    const payload = await cnexusProductApi.systemCapability();
    const operational = Boolean(payload.operational_ready ?? payload.ready_for_chat);
    const full = Boolean(payload.full_ready ?? payload.ready);
    if (options?.requireFull) {
      if (!full) return false;
    } else if (!operational) {
      return false;
    }
    if (options?.skipWs || !isWebSocketEnabled()) return true;
    return probeWsStateHandshake(options?.wsTimeoutMs ?? 5000);
  } catch {
    if (isPersonalMode() && (await probePersonalBackendOnline(3_000))) return true;
    try {
      const health = await cnexusProductApi.health();
      if (health.status === "ok" && (options?.skipWs || !isWebSocketEnabled())) return true;
    } catch {
      /* API down */
    }
    return false;
  }
}

export function probeWsStateHandshake(timeoutMs = 2000): Promise<boolean> {
  if (!isWebSocketEnabled()) {
    return Promise.resolve(false);
  }
  return new Promise((resolve) => {
    if (typeof WebSocket === "undefined") {
      resolve(false);
      return;
    }
    let settled = false;
    const finish = (ok: boolean) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      resolve(ok);
    };
    const ws = new WebSocket(`${getWsBase()}/ws/state`);
    const timer = setTimeout(() => finish(false), timeoutMs);
    ws.onmessage = () => finish(true);
    ws.onerror = () => finish(false);
  });
}

export const brainApi = {
  ...cnexusProductApi,
  state: () => request<RuntimeState>("/governance/state"),
  governance: () => request<Record<string, unknown>>("/governance/cycle", { method: "POST" }),
  clearLogs: () => request<{ ok: boolean }>("/logs", { method: "DELETE" }),
  createModel: (body: Record<string, unknown>, timeoutMs = modelUpsertTimeoutMs()) =>
    request<{ model: ModelProfile }>("/models", { method: "POST", body: JSON.stringify(body) }, timeoutMs),
  updateModel: (id: string, body: Record<string, unknown>, timeoutMs = modelUpsertTimeoutMs()) =>
    request<{ model: ModelProfile }>(`/models/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }, timeoutMs),
  deleteModel: (id: string) => request<{ ok: boolean }>(`/models/${id}`, { method: "DELETE" }),
  testModel: (id: string, options?: { timeoutMs?: number; quick?: boolean }) => {
    const quick = options?.quick ? "?quick=1" : "";
    return request<{ success: boolean; detail: string }>(
      `/models/${id}/test${quick}`,
      { method: "POST" },
      options?.timeoutMs ?? modelTestTimeoutMs(),
    );
  },
  mindOverview: () => cnexusProductApi.mindOverview(),
  embeddingStatus: () =>
    request<{
      configured_mode: string;
      active_mode: "ollama" | "hash";
      ollama_reachable: boolean;
      model: string;
      host: string;
      used_on: string[];
      not_used_on: string[];
    }>("/v1/memory/embedding-status"),
  ollamaStatus: () =>
    request<{
      installed: boolean;
      binary_found: boolean;
      running: boolean;
      host: string;
      download_url: string;
      binary_path?: string | null;
    }>("/v1/ollama/status", undefined, 4_000),
  ollamaStart: () =>
    request<{
      ok: boolean;
      detail: string;
      running: boolean;
      download_url?: string | null;
    }>("/v1/ollama/start", { method: "POST" }, 30_000),
  ollamaStop: () =>
    request<{
      ok: boolean;
      detail: string;
      running: boolean;
    }>("/v1/ollama/stop", { method: "POST" }, 15_000),
};

// ==================== WS Interact 重连管理器 ====================

export interface InteractMessage {
  type: string;
  content?: string;
  [key: string]: unknown;
}

export interface InteractWSError {
  type: "error";
  error: string;
  message?: string;
  retry?: boolean;
  retry_after?: number;
  [key: string]: unknown;
}

export type InteractWSResponse = InteractWSError | Record<string, unknown>;

class WSInteractManager {
  private ws: WebSocket | null = null;
  private retries = 0;
  private maxRetries = 6;
  private messageQueue: Array<{
    msg: InteractMessage;
    resolve: (res: InteractWSResponse) => void;
    reject: (err: unknown) => void;
  }> = [];
  private isConnecting = false;
  private pendingPing: ReturnType<typeof setInterval> | null = null;
  private onMessageCallback: ((data: InteractWSResponse) => void) | null = null;
  private onStatusChange: ((status: "connected" | "disconnected" | "reconnecting") => void) | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connect(
    onMessage: (data: InteractWSResponse) => void,
    onStatus?: (status: "connected" | "disconnected" | "reconnecting") => void,
  ): void {
    this.onMessageCallback = onMessage;
    this.onStatusChange = onStatus ?? null;
    this._connect();
  }

  private _connect(): void {
    if (!isWebSocketEnabled()) {
      this.onStatusChange?.("disconnected");
      return;
    }
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) return;
    this.isConnecting = true;
    this.onStatusChange?.("reconnecting");

    this.ws = new WebSocket(`${getWsBase()}/ws/interact`);

    this.ws.onopen = () => {
      console.log("[WS Interact] Connected");
      this.retries = 0;
      this.isConnecting = false;
      this.onStatusChange?.("connected");
      this._flushQueue();
      this._startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data: InteractWSResponse = JSON.parse(event.data as string);
        this.onMessageCallback?.(data);
        if (data && "error" in data && data.error && (data as InteractWSError).retry) {
          console.warn("[WS Interact] Server asked to retry:", (data as InteractWSError).message);
        }
      } catch (e) {
        console.error("[WS Interact] Parse error", e);
      }
    };

    this.ws.onclose = () => {
      console.warn("[WS Interact] Closed");
      this.isConnecting = false;
      this._stopHeartbeat();
      this.onStatusChange?.("disconnected");

      if (this.retries < this.maxRetries) {
        this.retries++;
        const delay = Math.min(1000 * Math.pow(1.5, this.retries), 30000);
        console.log(`[WS Interact] Reconnecting in ${delay}ms (${this.retries}/${this.maxRetries})`);
        this.reconnectTimer = setTimeout(() => this._connect(), delay);
      } else {
        console.error("[WS Interact] Max retries reached");
      }
    };

    this.ws.onerror = () => {
      console.error("[WS Interact] Error");
      this.ws?.close();
    };
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat();
    this.pendingPing = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000);
  }

  private _stopHeartbeat(): void {
    if (this.pendingPing) {
      clearInterval(this.pendingPing);
      this.pendingPing = null;
    }
  }

  private _flushQueue(): void {
    while (this.messageQueue.length > 0) {
      const item = this.messageQueue.shift()!;
      this._sendNow(item.msg).then(item.resolve).catch(item.reject);
    }
  }

  private _sendNow(msg: InteractMessage): Promise<InteractWSResponse> {
    return new Promise((resolve) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(msg));
        resolve({ type: "sent" });
      } else {
        resolve({ type: "buffer" });
      }
    });
  }

  send(msg: InteractMessage): Promise<InteractWSResponse> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(msg));
        resolve({ type: "sent" });
      } else {
        this.messageQueue.push({ msg, resolve, reject });
        if (!this.isConnecting) this._connect();
      }
    });
  }

  close(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this._stopHeartbeat();
    this.ws?.close();
    this.messageQueue = [];
    this.retries = this.maxRetries;
  }

  getStatus(): "connected" | "disconnected" | "connecting" {
    if (this.ws?.readyState === WebSocket.OPEN) return "connected";
    if (this.isConnecting) return "connecting";
    return "disconnected";
  }
}

export const wsInteractManager = new WSInteractManager();

// ==================== HTTP interact 自动重试 ====================

export interface InteractPayload {
  message: string;
  userId?: string;
  sessionId?: string;
  useMemory?: boolean;
  temperature?: number;
}

export interface InteractResult {
  response: string;
  coherence_score?: number;
  governance_pass: boolean;
  reflection?: string;
  meta?: Record<string, unknown>;
  error?: string;
  retry?: boolean;
  retry_after?: number;
}

export async function interactWithRetry(
  payload: InteractPayload,
  maxRetries = 3,
): Promise<InteractResult> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await cnexusProductApi.interact(
        payload.message,
        {
          userId: payload.userId,
          sessionId: payload.sessionId,
          useMemory: payload.useMemory,
          temperature: payload.temperature,
        },
      );

      const r = result as InteractResult;
      if (r.retry) {
        const delay = (r.retry_after ?? 5) * 1000;
        console.warn(`[Interact] Server retry requested, waiting ${delay}ms`);
        await new Promise((r) => { setTimeout(r, delay); });
        continue;
      }

      return result as InteractResult;
    } catch (err: unknown) {
      lastError = err;
      const errMsg = err instanceof Error ? err.message : String(err);
      console.warn(`[Interact] Attempt ${attempt + 1}/${maxRetries + 1} failed: ${errMsg}`);

      if (attempt === maxRetries) break;

      const delay = Math.min(1000 * Math.pow(1.5, attempt), 10000);
      await new Promise((r) => { setTimeout(r, delay); });
    }
  }

  throw lastError;
}


export { getApiBase as API_BASE, getWsBase as WS_BASE };
