"use client";

import { useEffect, useMemo } from "react";
import { GitBranch } from "lucide-react";
import { useMindOverview, useMindStore } from "@/cnexus-kernel";
import { useCognitiveCopy } from "@/lib/cognitive";
import { buildScopedFactorGraph } from "@/lib/memoryScopeGraph";
import { FACTOR_MEMORY_GRAPH_SETTINGS, FLOAT_COMPACT_GRAPH_SETTINGS } from "@/lib/graphViewModel";
import { MEMORY_SCOPE_OPTIONS, type MemoryScope } from "@/lib/memoryScope";
import { useSyncMemoryScope } from "@/hooks/useSyncMemoryScope";
import { useTrustedPeerIds } from "@/hooks/useTrustedPeerIds";
import { bi, biSection, floatL, homeL } from "@/lib/spine/labels";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import { ChatMemoryScopeSelect } from "../ChatMemoryScopeSelect";
import { GraphViewCanvas } from "../home/GraphViewCanvas";
import { SbEmptyState, SbSection } from "../second-brain/SbUIKit";

const PAGE_GRAPH_SHELL_HEIGHT = "min(72vh, 760px)";

type Props = {
  scope?: MemoryScope;
  onScopeChange?: (scope: MemoryScope) => void;
  variant?: "page" | "float";
  layoutKey?: string;
  frame?: { width: number; height: number };
  graphMinHeight?: number;
  className?: string;
  /** Float: omit scope hint line to save vertical space */
  hideScopeHint?: boolean;
};

/** Scoped memory flow graph — classic force-directed GraphView (same as before). */
export function ScopedMemoryFlowGraph3D({
  scope: scopeProp,
  onScopeChange,
  variant = "page",
  layoutKey,
  frame,
  className = "",
  hideScopeHint = false,
}: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const { overview } = useMindOverview();
  const pullMindOverview = useMindStore((s) => s.pullMindOverview);
  const [syncedScope, setSyncedScope] = useSyncMemoryScope();
  const trustedPeerIds = useTrustedPeerIds(variant === "float" ? 45_000 : 30_000);

  const scope = scopeProp ?? syncedScope;
  const setScope = onScopeChange ?? setSyncedScope;

  useEffect(() => {
    const intervalMs = variant === "float" ? 8_000 : 6_000;
    const id = window.setInterval(() => void pullMindOverview(), intervalMs);
    return () => window.clearInterval(id);
  }, [pullMindOverview, variant]);

  const factorGraph = useMemo(
    () => buildScopedFactorGraph(overview, scope, trustedPeerIds),
    [overview, scope, trustedPeerIds],
  );

  const scopeLabel = MEMORY_SCOPE_OPTIONS.find((option) => option.id === scope)?.label ?? scope;
  const statsLabel = `${scopeLabel} · ${factorGraph.nodes.length}`;
  const graphLayoutKey =
    layoutKey ?? `${scope}-${overview.generated_at}-${factorGraph.nodes.length}`;

  const graphBody = (
    <div className="flex flex-col min-h-0 min-w-0 flex-1 gap-3 w-full" data-cnexus-scoped-memory-flow>
      <ChatMemoryScopeSelect
        value={scope}
        onChange={setScope}
        compact={variant === "float"}
        hideActiveHint={variant === "float" && hideScopeHint}
      />
      <div className={variant === "float" ? "min-h-0 flex-1 min-w-0 overflow-hidden" : "w-full min-w-0"}>
        {factorGraph.nodes.length === 0 ? (
          <div
            className="flex items-center justify-center w-full px-4 py-8 rounded-xl border"
            style={{
              borderColor: t.border,
              color: t.textMuted,
              backgroundColor: "#0B0F1A",
              minHeight: variant === "page" ? PAGE_GRAPH_SHELL_HEIGHT : 180,
            }}
          >
            <SbEmptyState>{copy("shareMemoryFlowGraphEmpty")}</SbEmptyState>
          </div>
        ) : (
          <GraphViewCanvas
            graph={factorGraph}
            compact={variant === "float"}
            className="w-full min-w-0"
            layoutKey={graphLayoutKey}
            frame={variant === "float" ? frame : undefined}
            shellHeight={variant === "page" ? PAGE_GRAPH_SHELL_HEIGHT : undefined}
            settingsPreset={
              variant === "float" ? FLOAT_COMPACT_GRAPH_SETTINGS : FACTOR_MEMORY_GRAPH_SETTINGS
            }
          />
        )}
      </div>
      {variant === "page" ? (
        <p className="text-[10px] leading-snug px-0.5" style={{ color: t.textLight }}>
          {copy("shareMemoryFlowGraphHint")}
        </p>
      ) : null}
    </div>
  );

  if (variant === "float") {
    return (
      <div className={`flex flex-col min-h-0 min-w-0 h-full overflow-hidden ${className}`} data-no-drag>
        <div
          className="shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 border-b"
          style={{ borderColor: t.border }}
          data-cnexus-float-factor-header
        >
          <GitBranch className="w-3.5 h-3.5" style={{ color: t.purple }} />
          <span className={floatTy.label} style={{ color: t.text }}>
            {bi(floatL.factorGraph)}
          </span>
          <span className={`${floatTy.mono} ml-auto`} style={{ color: t.textMuted }}>
            {factorGraph.nodes.length}
          </span>
        </div>

        <div
          className="flex flex-col min-h-0 flex-1 min-w-0 overflow-hidden px-2 pt-2 pb-1"
          data-cnexus-float-factor-graph
        >
          {graphBody}
        </div>
      </div>
    );
  }

  return (
    <SbSection
      className={`w-full min-w-0 ${className}`}
      title={biSection(homeL.neuralFlow)}
      subtitle={statsLabel}
      icon={GitBranch}
    >
      {graphBody}
    </SbSection>
  );
}
