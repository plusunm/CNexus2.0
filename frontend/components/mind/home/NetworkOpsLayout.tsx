"use client";

import { useCallback, useEffect, useState } from "react";
import { Play, Copy, Check } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { bi, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { RemSleepButton } from "../RemSleepButton";

type OpCard = {
  id: string;
  titleKey: keyof typeof navL;
  hintKey: keyof typeof navL;
  envKey?: keyof typeof navL;
  actionLabelKey: keyof typeof navL;
  run: () => Promise<string>;
};

export function NetworkOpsLayout() {
  const t = useMindTheme();
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  const runOp = useCallback(async (id: string, fn: () => Promise<string>) => {
    setBusy(id);
    setError("");
    setMessage("");
    try {
      setMessage(await fn());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  }, []);

  const ops: OpCard[] = [
    {
      id: "replay",
      titleKey: "networkOpReplayTitle",
      hintKey: "networkOpReplayHint",
      actionLabelKey: "networkOpReplayRun",
      run: async () => {
        const row = await cnexusProductApi.runLogReplay(true);
        const summary = String(row.summary || row.message || "");
        return summary || `blocks=${row.memory_blocks} trace=${row.trace_rows} mode=${row.mode}`;
      },
    },
    {
      id: "reindex",
      titleKey: "networkOpReindexTitle",
      hintKey: "networkOpReindexHint",
      actionLabelKey: "networkOpReindexRun",
      run: async () => {
        const row = await cnexusProductApi.reindexAssets();
        return `indexed=${row.indexed ?? "?"}`;
      },
    },
    {
      id: "push-queue",
      titleKey: "networkOpPushQueueTitle",
      hintKey: "networkOpPushQueueHint",
      envKey: "networkOpPushQueueEnv",
      actionLabelKey: "networkOpPushQueueRun",
      run: async () => {
        const row = await cnexusProductApi.fetchAssetPushQueue(true);
        const q = row.queue as { pending?: number; succeeded?: number } | undefined;
        return `pending=${q?.pending ?? 0}`;
      },
    },
    {
      id: "reflect",
      titleKey: "networkOpReflectTitle",
      hintKey: "networkOpReflectHint",
      actionLabelKey: "networkOpReflectRun",
      run: async () => {
        const row = await cnexusProductApi.runMetaReflection(
          "根据最近 100 条 AuditLog，总结我这一周的认知偏差是什么？我是否有过度关注某些领域的倾向？",
          true,
        );
        return String(row.reflection || "").slice(0, 200) + "…";
      },
    },
  ];

  const envSnippets = [
    { key: "networkEnvPeerPush", cmd: '$env:CNEXUS_ASSET_PEER_PUSH = "1"' },
    { key: "networkEnvEmbed", cmd: '$env:CNEXUS_EMBED_MODEL = "nomic-embed-text"' },
    { key: "networkEnvBind", cmd: '$env:CNEXUS_BIND_HOST = "0.0.0.0"' },
    { key: "networkEnvDht", cmd: '$env:CNEXUS_DHT_BOOTSTRAP = "http://bootstrap:7864"' },
    { key: "networkEnvClip", cmd: '$env:CNEXUS_CLIP_IMAGE_ONNX = "D:\\...\\clip-image.onnx"' },
  ] as const;

  const copyCmd = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied(""), 2000);
    } catch {
      setCopied("");
    }
  };

  return (
    <div className="space-y-4 w-full min-w-0 max-w-none">
      <header>
        <h1 className="text-xl font-bold" style={{ color: t.text }}>
          {bi(navL.networkOpsPageTitle)}
        </h1>
        <p className="text-sm mt-1" style={{ color: t.textMuted }}>
          {bi(navL.networkOpsPageHint)}
        </p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {ops.map((op) => (
          <div
            key={op.id}
            className="rounded-xl border p-3 space-y-2"
            style={{ borderColor: t.border, backgroundColor: t.surface }}
          >
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {bi(navL[op.titleKey])}
            </p>
            <p className="text-[11px] leading-relaxed" style={{ color: t.textMuted }}>
              {bi(navL[op.hintKey])}
            </p>
            {op.envKey && (
              <p className="text-[10px] font-mono rounded px-2 py-1" style={{ backgroundColor: t.chatBg, color: t.orange }}>
                {bi(navL[op.envKey])}
              </p>
            )}
            <button
              type="button"
              disabled={Boolean(busy)}
              onClick={() => void runOp(op.id, op.run)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
              style={{ borderColor: t.border, color: t.text }}
            >
              <Play className="w-3.5 h-3.5" />
              {busy === op.id ? "…" : bi(navL[op.actionLabelKey])}
            </button>
          </div>
        ))}

        <div
          className="rounded-xl border p-3 space-y-2"
          style={{ borderColor: t.border, backgroundColor: t.surface }}
        >
          <p className="text-xs font-medium" style={{ color: t.text }}>
            {bi(navL.missionControlRem)}
          </p>
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            {bi(navL.networkOpRemHint)}
          </p>
          <RemSleepButton />
        </div>
      </section>

      <section
        className="rounded-xl border p-3 space-y-3"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <p className="text-xs font-medium" style={{ color: t.text }}>
          {bi(navL.networkEnvSection)}
        </p>
        <p className="text-[11px]" style={{ color: t.textMuted }}>
          {bi(navL.networkEnvHint)}
        </p>
        <div className="space-y-2">
          {envSnippets.map((row) => (
            <div
              key={row.key}
              className="flex items-start gap-2 rounded-lg border px-2 py-1.5"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <div className="flex-1 min-w-0">
                <p className="text-[10px] mb-0.5" style={{ color: t.textMuted }}>
                  {bi(navL[row.key])}
                </p>
                <code className="text-[10px] break-all" style={{ color: t.blue }}>
                  {row.cmd}
                </code>
              </div>
              <button
                type="button"
                onClick={() => void copyCmd(row.cmd, row.key)}
                className="shrink-0 p-1 rounded"
                style={{ color: t.textMuted }}
                title="Copy"
              >
                {copied === row.key ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          ))}
        </div>
        <p className="text-[10px]" style={{ color: t.textLight }}>
          {bi(navL.networkEnvRestart)}
        </p>
      </section>

      {(message || error) && (
        <div
          className="rounded-lg border px-3 py-2 text-[11px] whitespace-pre-wrap"
          style={{
            borderColor: error ? t.orange : t.green,
            color: error ? t.orange : t.green,
            backgroundColor: error ? `${t.orange}10` : `${t.green}10`,
          }}
        >
          {error || message}
        </div>
      )}
    </div>
  );
}
