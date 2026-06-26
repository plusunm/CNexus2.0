"use client";

import { useState } from "react";
import { CloudDownload, Search, Share2 } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { SbCard, SbEmptyState, SbSection, SbSegment } from "./SbUIKit";

import type { CopyKey } from "@/lib/cognitive/projection/copyLexicon";
import type { MemoryScope } from "@/lib/memoryScope";
import { useSyncMemoryScope } from "@/hooks/useSyncMemoryScope";

type MemoryHit = {
  kind?: string;
  block_id?: string;
  asset_id?: string;
  type?: string;
  filename?: string;
  summary?: string;
  desc?: string;
  score?: number;
  text?: string;
  source_peer?: string;
  peer_host?: string;
  content_kind?: string;
  local_blob?: boolean;
  memory_origin?: "local" | "trusted" | "network";
};

type Props = {
  asPage?: boolean;
  scope?: MemoryScope;
  onScopeChange?: (scope: MemoryScope) => void;
  /** Hide segment when parent provides unified scope control (e.g. share-memory graph). */
  hideScopeSelector?: boolean;
};

function originLabel(origin: MemoryHit["memory_origin"], copy: (key: CopyKey) => string) {
  if (origin === "trusted") return copy("shareOriginTrusted");
  if (origin === "network") return copy("shareOriginNetwork");
  return copy("shareOriginLocal");
}

export function SbRemoteMemoryPanel({
  asPage,
  scope: scopeProp,
  onScopeChange,
  hideScopeSelector = false,
}: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const [syncedScope, setSyncedScope] = useSyncMemoryScope();
  const scope = scopeProp ?? syncedScope;
  const setScope = onScopeChange ?? setSyncedScope;
  const [semantic, setSemantic] = useState(true);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<MemoryHit[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const scopeHint =
    scope === "local"
      ? copy("shareScopeLocalHint")
      : scope === "trusted"
        ? copy("shareScopeTrustedHint")
        : copy("shareScopeNetworkHint");

  const needsDownload = (row: MemoryHit) =>
    row.kind !== "memory" &&
    Boolean(row.asset_id) &&
    row.local_blob === false &&
    Boolean(row.source_peer || row.peer_host || row.content_kind === "preview");

  const downloadHit = async (row: MemoryHit) => {
    if (!row.asset_id) return;
    await cnexusProductApi.pullAssetFromPeer(row.asset_id, row.source_peer, row.peer_host);
    setHits((prev) =>
      prev.map((hit) =>
        hit.asset_id === row.asset_id ? { ...hit, local_blob: true, content_kind: "full" } : hit,
      ),
    );
    setMessage(`${copy("shareDownloadDone")} · ${row.filename || row.asset_id.slice(0, 12)}…`);
  };

  const runSearch = async () => {
    if (!query.trim()) return;
    setBusy("search");
    setMessage("");
    try {
      setHits(await cnexusProductApi.searchAssets(query.trim(), undefined, semantic, scope));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
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

  const inputClass = "flex-1 border rounded-xl px-3 py-2.5 text-sm outline-none focus:ring-1";
  const inputStyle = { borderColor: t.border, backgroundColor: t.chatBg, color: t.text };

  const body = (
    <SbCard accent="purple">
      {!hideScopeSelector ? (
        <>
          <SbSegment
            value={scope}
            tone="teal"
            onChange={setScope}
            options={[
              { id: "local", label: copy("shareScopeLocal"), hint: copy("shareScopeLocalHint") },
              { id: "trusted", label: copy("shareScopeTrusted"), hint: copy("shareScopeTrustedHint") },
              { id: "network", label: copy("shareScopeNetwork"), hint: copy("shareScopeNetworkHint") },
            ]}
          />
          <p className="text-[11px] mt-2 mb-3 leading-relaxed" style={{ color: t.textMuted }}>
            {scopeHint}
          </p>
        </>
      ) : (
        <p className="text-[11px] mb-3 leading-relaxed" style={{ color: t.textMuted }}>
          {scopeHint}
        </p>
      )}

      <label className="flex items-center gap-2 text-xs mb-3" style={{ color: t.textMuted }}>
        <input type="checkbox" checked={semantic} onChange={(e) => setSemantic(e.target.checked)} />
        {copy("shareSemanticSearch")}
      </label>

      <div className="flex gap-2">
        <input
          className={inputClass}
          style={inputStyle}
          placeholder={copy("shareSearchPlaceholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void runSearch();
          }}
        />
        <button
          type="button"
          disabled={Boolean(busy) || !query.trim()}
          onClick={() => void runSearch()}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium text-white disabled:opacity-50 shrink-0"
          style={{ backgroundColor: t.purple }}
        >
          <Search className="w-4 h-4" />
          {busy === "search" ? "…" : copy("shareSearchRun")}
        </button>
      </div>

      <div className={`mt-4 space-y-2 overflow-y-auto cnexus-float-scroll ${asPage ? "max-h-[min(60vh,520px)]" : "max-h-72"}`}>
        {hits.length === 0 && !busy && <SbEmptyState>{copy("shareSearchEmpty")}</SbEmptyState>}
        {hits.map((row) => {
          const key = row.asset_id || row.block_id || row.filename;
          const origin = row.memory_origin || (row.source_peer ? "trusted" : "local");
          return (
            <div
              key={key}
              className="rounded-xl border px-3 py-2.5 space-y-1.5"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium truncate min-w-0" style={{ color: t.text }}>
                  {row.filename || row.summary || row.asset_id?.slice(0, 16) || row.block_id?.slice(0, 16)}
                </p>
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full shrink-0"
                  style={{
                    color: origin === "local" ? "#5eead4" : origin === "trusted" ? t.blue : t.orange,
                    backgroundColor:
                      origin === "local"
                        ? "rgba(94,234,212,0.12)"
                        : origin === "trusted"
                          ? t.blueSoft
                          : `${t.orange}18`,
                  }}
                >
                  {row.kind === "memory" ? copy("shareMemoryBlock") : originLabel(origin, copy)}
                </span>
              </div>
              <p className="text-xs leading-relaxed line-clamp-2" style={{ color: t.textMuted }}>
                {row.summary || row.desc || row.text || row.type}
                {row.score != null ? ` · ${(row.score * 100).toFixed(0)}%` : ""}
              </p>
              {needsDownload(row) ? (
                <div className="flex items-center justify-between gap-2 pt-1">
                  <span className="text-[10px]" style={{ color: t.orange }}>
                    {copy("shareRemotePreviewOnly")}
                  </span>
                  <button
                    type="button"
                    disabled={Boolean(busy)}
                    onClick={() => void run(`pull-${row.asset_id}`, () => downloadHit(row))}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium border disabled:opacity-50"
                    style={{ borderColor: "#5eead466", color: "#5eead4" }}
                  >
                    <CloudDownload className="w-3.5 h-3.5" />
                    {busy === `pull-${row.asset_id}` ? "…" : copy("shareDownloadMemory")}
                  </button>
                </div>
              ) : row.kind === "memory" ? (
                <span className="text-[10px]" style={{ color: t.textLight }}>
                  {copy("shareOriginLocal")} · {copy("shareDownloadDone")}
                </span>
              ) : (
                <span className="text-[10px]" style={{ color: t.green }}>
                  {copy("shareDownloadDone")}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {message && (
        <p
          className="text-xs mt-3"
          style={{ color: message.includes(copy("shareDownloadDone")) ? t.green : t.orange }}
        >
          {message}
        </p>
      )}
    </SbCard>
  );

  if (asPage) {
    return <div className="space-y-3">{body}</div>;
  }

  return (
    <SbSection
      title={copy("shareRemoteMemory")}
      subtitle={copy("shareRemoteMemoryHint")}
      icon={Share2}
    >
      {body}
    </SbSection>
  );
}
