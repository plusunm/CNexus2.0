"use client";

import { useState } from "react";
import { CloudDownload, FileCode2, ImagePlus, Search, Upload } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { bi, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type AssetHit = {
  asset_id?: string;
  type?: string;
  filename?: string;
  summary?: string;
  desc?: string;
  score?: number;
  text?: string;
  source_peer?: string;
  content_kind?: string;
  local_blob?: boolean;
};

export function AssetIngestPanel() {
  const t = useMindTheme();
  const [code, setCode] = useState("");
  const [filename, setFilename] = useState("snippet.py");
  const [project, setProject] = useState(false);
  const [semantic, setSemantic] = useState(true);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<AssetHit[]>([]);
  const [lastAssetId, setLastAssetId] = useState("");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const formatUploadMessage = (row: { id?: string; peer_push?: string }) => {
    const base = `${bi(navL.missionControlAssetIndexed)} · ${row.id?.slice(0, 12)}…`;
    if (row.peer_push === "scheduled") {
      return `${base} · ${bi(navL.missionControlAssetPeerPushScheduled)}`;
    }
    return base;
  };

  const needsPull = (row: AssetHit) =>
    Boolean(row.asset_id) &&
    row.local_blob === false &&
    Boolean(row.source_peer || row.content_kind === "preview");

  const pullHit = async (row: AssetHit) => {
    if (!row.asset_id) return;
    await cnexusProductApi.pullAssetFromPeer(row.asset_id, row.source_peer);
    setHits((prev) =>
      prev.map((hit) =>
        hit.asset_id === row.asset_id ? { ...hit, local_blob: true, content_kind: "full" } : hit,
      ),
    );
    setMessage(`${bi(navL.missionControlAssetPeerPullDone)} · ${row.asset_id.slice(0, 12)}…`);
  };

  const search = async (q: string) => {
    setHits(await cnexusProductApi.searchAssets(q, undefined, semantic));
  };

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    setMessage("");
    try {
      await fn();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <section
      className="rounded-xl border p-3 space-y-3"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className="flex items-start gap-2">
        <Upload className="w-4 h-4 mt-0.5" style={{ color: t.blue }} />
        <div>
          <p className="text-xs font-medium" style={{ color: t.text }}>
            {bi(navL.missionControlAssets)}
          </p>
          <p className="text-[11px]" style={{ color: t.textMuted }}>
            {bi(navL.missionControlAssetsHint)}
          </p>
        </div>
      </div>

      <label className="flex items-center gap-2 text-[11px]" style={{ color: t.textMuted }}>
        <input type="checkbox" checked={project} onChange={(e) => setProject(e.target.checked)} />
        {bi(navL.missionControlAssetProject)}
      </label>
      <label className="flex items-center gap-2 text-[11px]" style={{ color: t.textMuted }}>
        <input type="checkbox" checked={semantic} onChange={(e) => setSemantic(e.target.checked)} />
        {bi(navL.missionControlAssetSemantic)}
      </label>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[11px]" style={{ color: t.textLight }}>
            <FileCode2 className="w-3.5 h-3.5" />
            {bi(navL.missionControlAssetCode)}
          </div>
          <input
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            className="w-full rounded-lg border px-2 py-1.5 text-xs font-mono"
            style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
            placeholder="module.py"
          />
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            rows={5}
            className="w-full rounded-lg border px-2 py-1.5 text-xs font-mono"
            style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
            placeholder="paste code here"
          />
          <button
            type="button"
            disabled={Boolean(busy) || !code.trim()}
            onClick={() =>
              void run("code", async () => {
                const row = await cnexusProductApi.uploadCodeAsset(code, filename, project);
                if (row.id) setLastAssetId(row.id);
                setMessage(formatUploadMessage(row));
                if (query.trim()) await search(query.trim());
              })
            }
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.text }}
          >
            <Upload className="w-3.5 h-3.5" />
            {busy === "code" ? "…" : bi(navL.missionControlAssetCode)}
          </button>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[11px]" style={{ color: t.textLight }}>
            <ImagePlus className="w-3.5 h-3.5" />
            {bi(navL.missionControlAssetImage)}
          </div>
          <input
            type="file"
            accept="image/*"
            disabled={Boolean(busy)}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              void run("image", async () => {
                const row = await cnexusProductApi.uploadImageAsset(file, project);
                if (row.id) setLastAssetId(row.id);
                setMessage(formatUploadMessage(row));
                if (query.trim()) await search(query.trim());
                e.target.value = "";
              });
            }}
            className="block w-full text-xs"
            style={{ color: t.textMuted }}
          />
          <input
            type="file"
            accept="image/*"
            disabled={Boolean(busy) || !semantic}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              void run("image-search", async () => {
                setHits(await cnexusProductApi.searchAssetsByImage(file));
                e.target.value = "";
              });
            }}
            className="block w-full text-xs"
            style={{ color: t.textMuted }}
          />
          <p className="text-[10px]" style={{ color: t.textMuted }}>
            {bi(navL.missionControlAssetImageSearchHint)}
          </p>

          <div className="flex items-center gap-1.5 text-[11px] pt-2" style={{ color: t.textLight }}>
            <Search className="w-3.5 h-3.5" />
            {bi(navL.missionControlAssetSearch)}
          </div>
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 rounded-lg border px-2 py-1.5 text-xs"
              style={{ borderColor: t.border, backgroundColor: t.chatBg, color: t.text }}
              placeholder="summary / filename / asset id"
            />
            <button
              type="button"
              disabled={Boolean(busy) || !query.trim()}
              onClick={() => void run("search", async () => search(query.trim()))}
              className="px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
              style={{ borderColor: t.border, color: t.text }}
            >
              {busy === "search" ? "…" : bi(navL.refresh)}
            </button>
          </div>

          <div
            className="rounded-lg border p-2 h-[132px] overflow-y-auto space-y-1.5 text-[11px]"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            {hits.length === 0 && (
              <p style={{ color: t.textMuted }}>{bi(navL.missionControlAssetEmpty)}</p>
            )}
            {hits.map((row) => (
              <div key={row.asset_id} className="rounded-md border px-2 py-1 space-y-1" style={{ borderColor: t.border }}>
                <p className="font-mono truncate" style={{ color: t.blue }}>
                  {row.filename || row.asset_id?.slice(0, 16)}
                </p>
                <p className="truncate" style={{ color: t.textMuted }}>
                  {row.summary || row.desc || row.text || row.type}
                  {row.score != null ? ` · ${(row.score * 100).toFixed(0)}%` : ""}
                </p>
                {needsPull(row) && (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px]" style={{ color: t.orange }}>
                      {bi(navL.missionControlAssetRemotePreview)}
                    </span>
                    <button
                      type="button"
                      disabled={Boolean(busy)}
                      onClick={() => void run(`pull-${row.asset_id}`, () => pullHit(row))}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] disabled:opacity-50"
                      style={{ borderColor: t.border, color: t.text }}
                    >
                      <CloudDownload className="w-3 h-3" />
                      {busy === `pull-${row.asset_id}` ? "…" : bi(navL.missionControlAssetPeerPull)}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {lastAssetId && (
        <button
          type="button"
          disabled={Boolean(busy)}
          onClick={() =>
            void run("push", async () => {
              const row = await cnexusProductApi.pushAssetToPeers(lastAssetId);
              setMessage(`${bi(navL.missionControlAssetPeerPush)} · ${row.pushed ?? 0}/${row.peer_count ?? 0}`);
            })
          }
          className="text-[11px] underline disabled:opacity-50"
          style={{ color: t.textMuted }}
        >
          {busy === "push" ? "…" : bi(navL.missionControlAssetPeerPush)}
        </button>
      )}

      {message && (
        <p className="text-[11px]" style={{ color: message.startsWith(bi(navL.missionControlAssetIndexed)) ? t.green : t.orange }}>
          {message}
        </p>
      )}
    </section>
  );
}
