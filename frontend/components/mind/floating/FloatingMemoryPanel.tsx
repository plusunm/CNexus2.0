"use client";

import { useRef } from "react";
import { useFloatFactorGraphFrame } from "@/hooks/useFloatFactorGraphFrame";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { useSyncMemoryScope } from "@/hooks/useSyncMemoryScope";
import { useMindTheme } from "../MindUiProvider";
import { ScopedMemoryFlowGraph3D } from "../shared/ScopedMemoryFlowGraph3D";
import { FloatTokenStrip, useFloatTokenTraces } from "./FloatTokenStrip";

/** 悬浮窗记忆页 — 力导向记忆流图（与大窗同源）+ 记忆范围 + Token 消耗 */
export function FloatingMemoryPanel() {
  const t = useMindTheme();
  const stage = useFloatingBarStore((s) => s.stage);
  const sessionEpoch = useFloatingBarStore((s) => s.sessionEpoch);
  const panelRef = useRef<HTMLDivElement>(null);
  const frame = useFloatFactorGraphFrame(stage, panelRef);
  const [scope, setScope] = useSyncMemoryScope();
  const token = useFloatTokenTraces();

  const scopeChrome = 92;
  const graphFrame = {
    width: frame.graphWidth,
    height: Math.max(120, frame.graphHeight - scopeChrome),
  };

  return (
    <div
      ref={panelRef}
      className="cnexus-float-panel min-h-0 min-w-0 overflow-hidden h-full"
      style={{
        backgroundColor: t.surface,
        borderColor: t.border,
        display: "grid",
        gridTemplateRows: `${frame.graphSlotHeight + scopeChrome}px minmax(${frame.tokenAreaHeight}px, 1fr)`,
      }}
      data-cnexus-float-memory
    >
      <ScopedMemoryFlowGraph3D
        variant="float"
        scope={scope}
        onScopeChange={setScope}
        layoutKey={`${stage}-${sessionEpoch}-${scope}`}
        frame={graphFrame}
      />

      <div className="min-h-0 flex flex-col overflow-hidden" style={{ minHeight: frame.tokenAreaHeight }}>
        <FloatTokenStrip
          traces={token.traces}
          loading={token.loading}
          error={token.error}
          traceMaxHeight={frame.tokenTraceHeight}
          isLive={token.isLive}
          emptyHint={token.emptyHint}
          onRefresh={() => void token.refresh()}
        />
      </div>
    </div>
  );
}
