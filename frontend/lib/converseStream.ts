import { getApiBase } from "./cnexusConfig";
import type { ConverseMode } from "./converseMode";
import type { MemoryScope } from "./memoryScope";
import type { ThinkingMode } from "./thinkingMode";

export type ConverseStreamDone = {
  ok?: boolean;
  reply?: string;
  latency_ms?: {
    prepare?: number;
    llm?: number;
    post?: number;
    total?: number;
    ttft?: number;
  };
  activation_injected?: number;
  llm_source?: string;
  model_name?: string | null;
  converse_mode?: string;
  thinking_mode?: string;
  memory_scope?: string;
  global_entropy?: string;
  temperature?: number;
};

export type ConverseStreamHandlers = {
  onMeta?: (data: Record<string, unknown>) => void;
  onToken: (text: string) => void;
  onDone?: (data: ConverseStreamDone) => void;
  onError?: (message: string) => void;
};

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (!dataLines.length) return null;
  return { event, data: dataLines.join("\n") };
}

export async function converseStreamPersonal(
  text: string,
  handlers: ConverseStreamHandlers,
  modelId?: string,
  converseMode: ConverseMode = "fast",
  thinkingMode: ThinkingMode = "precision",
  memoryScope: MemoryScope = "local",
): Promise<ConverseStreamDone | null> {
  const body: Record<string, unknown> = {
    text,
    stream: true,
    converse_mode: converseMode,
    thinking_mode: thinkingMode,
    memory_scope: memoryScope,
  };
  if (modelId && modelId !== "cnexus-local") {
    body.model_id = modelId;
  }

  const resp = await fetch(`${getApiBase()}/api/converse/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    let message = `对话失败 (${resp.status})`;
    try {
      const err = (await resp.json()) as { error?: string };
      if (err.error) message = err.error;
    } catch {
      /* ignore */
    }
    handlers.onError?.(message);
    throw new Error(message);
  }

  const reader = resp.body?.getReader();
  if (!reader) {
    const message = "浏览器不支持流式响应";
    handlers.onError?.(message);
    throw new Error(message);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let donePayload: ConverseStreamDone | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const parsed = parseSseBlock(part.trim());
      if (!parsed) continue;
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(parsed.data) as Record<string, unknown>;
      } catch {
        continue;
      }
      if (parsed.event === "meta") {
        handlers.onMeta?.(payload);
      } else if (parsed.event === "token") {
        const chunk = String(payload.text ?? "");
        if (chunk) handlers.onToken(chunk);
      } else if (parsed.event === "error") {
        const message = String(payload.error ?? "流式对话失败");
        handlers.onError?.(message);
        throw new Error(message);
      } else if (parsed.event === "done") {
        donePayload = payload as ConverseStreamDone;
        handlers.onDone?.(donePayload);
      }
    }
  }

  return donePayload;
}
