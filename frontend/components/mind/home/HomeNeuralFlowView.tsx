"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Zap } from "lucide-react";
import type { CognitiveOutput, ExecLogEvent, ExecTraceManifest } from "@/lib/cognitiveTypes";
import { useMindOverview, useMindStore } from "@/cnexus-kernel";
import { buildFactorGraph } from "@/lib/factorGraphModel";
import { FACTOR_MEMORY_GRAPH_SETTINGS } from "@/lib/graphViewModel";
import { bi, biFmt, biSection, homeL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { GraphViewCanvas } from "./GraphViewCanvas";
import { ClearMemoryButton } from "../ClearMemoryButton";

type Props = {
  data: CognitiveOutput;
  logs: ExecLogEvent[];
  traces: ExecTraceManifest[];
  loading: boolean;
  refreshing?: boolean;
  onRefresh: () => void;
};

/** 记忆流图 — 因子网络图（memory_items 记忆锚点） */
export function HomeNeuralFlowView({ loading, refreshing, onRefresh }: Props) {
  const t = useMindTheme();
  const { overview } = useMindOverview();
  const pullMindOverview = useMindStore((s) => s.pullMindOverview);

  const factorGraph = useMemo(() => buildFactorGraph(overview), [overview]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void pullMindOverview();
    }, 6_000);
    return () => window.clearInterval(id);
  }, [pullMindOverview]);

  const handleRefresh = () => {
    void pullMindOverview();
    onRefresh();
  };

  const statsLabel = biFmt(homeL.graphNodeCount, {
    n: factorGraph.nodes.length,
    e: factorGraph.edges.length,
  });

  return (
    <div className="space-y-4 w-full min-w-0 max-w-none">
      <header className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <Zap className="w-5 h-5" style={{ color: t.purple }} />
            <h1 className="text-xl font-bold" style={{ color: t.text }}>
              {biSection(homeL.neuralFlow)}
            </h1>
            <span
              className="text-[10px] px-2 py-0.5 rounded-full border"
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              {statsLabel}
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: t.textMuted }}>
            {bi(homeL.neuralFlowSub)}
          </p>
          <p className="text-[11px] mt-1 leading-relaxed max-w-2xl" style={{ color: t.textLight }}>
            {bi(homeL.neuralFlowVitals)}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            href="/shell/?layout=overview&view=workbench"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            {bi(homeL.workbenchLink)}
          </Link>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] border disabled:opacity-50"
            style={{ borderColor: t.blue, color: t.blue, backgroundColor: t.blueSoft }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading || refreshing ? "animate-spin" : ""}`} />
            {bi(homeL.sync)}
          </button>
          <ClearMemoryButton />
        </div>
      </header>

      <section className="min-w-0 min-h-[560px]">
        <GraphViewCanvas
          graph={factorGraph}
          className="min-h-[560px]"
          settingsPreset={FACTOR_MEMORY_GRAPH_SETTINGS}
          layoutKey={`${overview.generated_at}-${factorGraph.nodes.length}`}
        />
      </section>
    </div>
  );
}
