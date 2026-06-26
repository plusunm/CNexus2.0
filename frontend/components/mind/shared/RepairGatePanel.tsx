"use client";

import { useState } from "react";
import { ShieldCheck, Wrench, AlertTriangle, CheckCircle2 } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import {
  type ApplicationConnectSnapshot,
  type ApplicationPhase,
  type ExecutionGateRow,
  gateLabel,
  phaseLabel,
  shortHash,
} from "@/lib/applicationControl";
import { bi, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type RepairGatePanelProps = {
  snapshot: ApplicationConnectSnapshot;
  onComplete?: () => void;
};

function mergeGate(base: ExecutionGateRow, next: ExecutionGateRow): ExecutionGateRow {
  return { ...base, ...next };
}

export function RepairGatePanel({ snapshot, onComplete }: RepairGatePanelProps) {
  const t = useMindTheme();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [gate, setGate] = useState(snapshot.executionGate);
  const [phase, setPhase] = useState(snapshot.phase);

  const gateKind = gate.gate;
  const gateColors = {
    allow: t.green,
    deny: t.orange,
    require_confirm: t.blue,
  };
  const accent = gateKind ? gateColors[gateKind] || t.textMuted : t.textMuted;

  const runPreviewGate = async () => {
    setBusy("gate");
    setError("");
    setMessage("");
    try {
      const { data } = await cnexusProductApi.applicationRepair({
        action: "gate",
        peer_id: snapshot.peerId,
        peer_host: snapshot.peerHost,
        plans: snapshot.repairPlans,
        suggested_sources: snapshot.suggestedSources,
        confirm: false,
      });
      setGate(mergeGate(gate, data as ExecutionGateRow));
      setPhase(String(data.phase || "gate_preview") as ApplicationPhase);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const runExecute = async () => {
    if (!window.confirm(bi(navL.repairControlConfirmPrompt))) return;
    setBusy("execute");
    setError("");
    setMessage("");
    try {
      const { data, status } = await cnexusProductApi.applicationRepair({
        action: "execute",
        confirm: true,
        peer_id: snapshot.peerId,
        peer_host: snapshot.peerHost,
        plans: snapshot.repairPlans,
        suggested_sources: snapshot.suggestedSources,
      });
      if (status === 409) {
        setError(bi(navL.repairControlConfirmRequired));
        return;
      }
      const row = data as Record<string, unknown>;
      const gateRow = (row.gate || row) as ExecutionGateRow;
      if (gateRow.gate) setGate(mergeGate(gate, gateRow));
      setPhase(String(row.phase || "repair_complete") as ApplicationPhase);
      const repaired = Number(row.repaired ?? 0);
      if (repaired > 0) {
        setMessage(`${bi(navL.repairControlExecuteOk)} (${repaired})`);
        onComplete?.();
      } else if (gateRow.gate === "deny" || row.ok === false) {
        setError(bi(navL.repairControlExecuteDenied));
      } else {
        setMessage(bi(navL.repairControlIntegrityOk));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const showRepairActions = snapshot.missingCount > 0 && snapshot.planCount > 0;
  const canExecute = showRepairActions && gateKind !== "deny";

  return (
    <section
      className="rounded-xl border p-3 space-y-3"
      style={{ borderColor: `${accent}55`, backgroundColor: `${accent}08` }}
    >
      <div className="flex items-start gap-2">
        {snapshot.missingCount > 0 ? (
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: accent }} />
        ) : (
          <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" style={{ color: t.green }} />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium" style={{ color: t.text }}>
            {bi(navL.repairControlTitle)}
          </p>
          <p className="text-[11px] mt-0.5" style={{ color: t.textMuted }}>
            {snapshot.missingCount > 0 ? bi(navL.repairControlHint) : bi(navL.repairControlIntegrityOk)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
        <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: t.border, backgroundColor: t.surface }}>
          <p style={{ color: t.textLight }}>{bi(navL.repairControlPhase)}</p>
          <p className="font-medium" style={{ color: t.text }}>
            {bi(phaseLabel(phase))}
          </p>
        </div>
        <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: t.border, backgroundColor: t.surface }}>
          <p style={{ color: t.textLight }}>{bi(navL.repairControlMissing)}</p>
          <p className="font-medium" style={{ color: t.text }}>
            {snapshot.missingCount}
          </p>
        </div>
        <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: t.border, backgroundColor: t.surface }}>
          <p style={{ color: t.textLight }}>{bi(navL.repairControlPlans)}</p>
          <p className="font-medium" style={{ color: t.text }}>
            {snapshot.planCount}
          </p>
        </div>
        <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: t.border, backgroundColor: t.surface }}>
          <p style={{ color: t.textLight }}>{bi(navL.repairControlGate)}</p>
          <p className="font-medium" style={{ color: accent }}>
            {gateKind ? bi(gateLabel(gateKind)) : "—"}
          </p>
        </div>
      </div>

      {snapshot.missingCount > 0 && (
        <div className="rounded-lg border px-2 py-1.5 max-h-20 overflow-y-auto" style={{ borderColor: t.border }}>
          <p className="text-[10px] mb-1" style={{ color: t.textLight }}>
            {bi(navL.repairControlMissing)}
          </p>
          <p className="text-[10px] font-mono truncate" style={{ color: t.textMuted }}>
            {[...snapshot.missing, ...snapshot.invalid].map(shortHash).join(", ") || "—"}
          </p>
        </div>
      )}

      {snapshot.suggestedSources.length > 0 && (
        <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: t.border }}>
          <p className="text-[10px] mb-1 flex items-center gap-1" style={{ color: t.textLight }}>
            <ShieldCheck className="w-3 h-3" />
            {bi(navL.repairControlSources)}
          </p>
          <ul className="space-y-1">
            {snapshot.suggestedSources.slice(0, 3).map((src, idx) => (
              <li key={`${src.host}-${idx}`} className="text-[10px]" style={{ color: t.textMuted }}>
                <span className="font-mono">{src.host || "—"}</span>
                {" · "}
                {src.reason || "source"}
                {src.probe?.state_checked ? (src.probe.remote_has ? " · probe ✓" : " · probe ✗") : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(gate.decisions) && gate.decisions.length > 0 && (
        <div className="rounded-lg border px-2 py-1.5 max-h-24 overflow-y-auto" style={{ borderColor: t.border }}>
          {gate.decisions.slice(0, 4).map((row) => (
            <p key={row.chunk_hash} className="text-[10px] font-mono truncate" style={{ color: t.textMuted }}>
              {shortHash(String(row.chunk_hash || ""))} · {row.gate}
              {row.detail ? ` · ${row.detail}` : ""}
            </p>
          ))}
        </div>
      )}

      {showRepairActions && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={Boolean(busy)}
            onClick={() => void runPreviewGate()}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            <Wrench className="w-3.5 h-3.5" />
            {busy === "gate" ? "…" : bi(navL.repairControlPreviewGate)}
          </button>
          <button
            type="button"
            disabled={Boolean(busy) || !canExecute}
            onClick={() => void runExecute()}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs border disabled:opacity-50"
            style={{
              borderColor: gateKind === "allow" ? t.green : t.blue,
              color: gateKind === "allow" ? t.green : t.blue,
            }}
          >
            {busy === "execute" ? "…" : bi(navL.repairControlConfirm)}
          </button>
        </div>
      )}

      {(message || error) && (
        <p className="text-[11px]" style={{ color: error ? t.orange : t.green }}>
          {error || message}
        </p>
      )}
    </section>
  );
}
