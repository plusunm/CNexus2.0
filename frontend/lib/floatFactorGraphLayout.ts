import type { FloatStage } from "./floatingBarStorage";
import { floatShellHeight, floatShellWidth } from "./floatWindowSpec";

/**
 * Chrome heights (px) derived from float shell Tailwind classes.
 * Keep in sync with FloatingHeaderBar, FloatingQuickButtons, FloatExperienceTierBar,
 * FloatingExpandPanel, FloatingMemoryPanel, FloatTokenStrip, ScopedMemoryFlowGraph3D.
 */
export const FLOAT_SHELL_CHROME = {
  /** FloatingHeaderBar — px-3 py-2 border-b */
  headerBar: 44,
  /** FloatingQuickButtons — px-3 py-2 + tab py-2 */
  quickTabs: 48,
  /** FloatExperienceTierBar wrapper — pt-2 pb-1 border-b + tier buttons + footnote */
  experienceTierBar: 92,
  /** FloatingCognitiveHints — pt-2 pb-1.5 + badge + suggestion row */
  cognitiveHints: 76,
  /** FloatingExpandPanel content — pb-3 */
  expandPadBottom: 12,
  /** FloatingExpandPanel content — px-3 × 2 */
  expandPadX: 24,
} as const;

export const FLOAT_MEMORY_PANEL_CHROME = {
  /** Section header — py-1.5 + 12px label */
  sectionHeader: 32,
  /** ChatMemoryScopeSelect compact (no active-hint line) */
  scopeSelectBlock: 74,
  /** space-y-3 between scope row and canvas */
  graphBodyGap: 12,
  /** Graph wrapper — px-2 × 2 */
  graphPadX: 16,
  graphPadTop: 8,
  graphPadBottom: 4,
  /** GraphViewCanvas compact border */
  graphBorder: 2,
  /** Compact footer — factorGraphHint + node count */
  graphFooter: 16,
  /** FloatTokenStrip fixed chrome (header + stats) before trace list */
  tokenStripFixed: 82,
  tokenTraceMin: 56,
  tokenTraceMax: 120,
} as const;

const GRAPH_HEIGHT_BOUNDS: Record<FloatStage, { min: number; max: number }> = {
  expanded: { min: 96, max: 200 },
  bar: { min: 72, max: 120 },
  dock: { min: 48, max: 80 },
};

export type FloatFactorGraphFrame = {
  shellWidth: number;
  shellHeight: number;
  memoryPanelHeight: number;
  graphWidth: number;
  /** Canvas drawable height (px) */
  graphHeight: number;
  /** Canvas + inner chrome (padding, border, footer) */
  graphSlotHeight: number;
  /** Header + scope + gap + graphSlot — grid row for graph section */
  graphSectionHeight: number;
  tokenTraceHeight: number;
  tokenAreaHeight: number;
};

function canvasChrome(mem: typeof FLOAT_MEMORY_PANEL_CHROME): number {
  return mem.graphPadTop + mem.graphPadBottom + mem.graphBorder + mem.graphFooter;
}

function graphSectionFixedChrome(
  mem: typeof FLOAT_MEMORY_PANEL_CHROME,
  headerHeight: number = mem.sectionHeader,
  scopeHeight: number = mem.scopeSelectBlock,
): number {
  return headerHeight + scopeHeight + mem.graphBodyGap + canvasChrome(mem);
}

/** Memory panel lives below tier bar; cognitive hints hidden on memory tab (personal). */
function memoryPanelHeightForStage(stage: FloatStage): number {
  const shellH = floatShellHeight(stage);
  const c = FLOAT_SHELL_CHROME;
  const expandBody = shellH - c.headerBar - c.quickTabs;
  return expandBody - c.experienceTierBar - c.expandPadBottom;
}

export function computeFloatFactorGraphFrame(stage: FloatStage): FloatFactorGraphFrame {
  const shellW = floatShellWidth(stage);
  const shellH = floatShellHeight(stage);
  const shell = FLOAT_SHELL_CHROME;
  const mem = FLOAT_MEMORY_PANEL_CHROME;
  const bounds = GRAPH_HEIGHT_BOUNDS[stage];

  const memoryPanelH = memoryPanelHeightForStage(stage);
  const fixedChrome = graphSectionFixedChrome(mem);
  const tokenMinArea = mem.tokenStripFixed + mem.tokenTraceMin;
  const maxGraphHeight = Math.max(0, memoryPanelH - fixedChrome - tokenMinArea);

  let graphHeight = Math.min(bounds.max, Math.max(bounds.min, maxGraphHeight));
  let tokenTraceH = Math.max(
    mem.tokenTraceMin,
    Math.min(mem.tokenTraceMax, memoryPanelH - fixedChrome - graphHeight - mem.tokenStripFixed),
  );
  let tokenAreaHeight = mem.tokenStripFixed + tokenTraceH;

  let graphSectionHeight = fixedChrome + graphHeight;
  let total = graphSectionHeight + tokenAreaHeight;
  if (total > memoryPanelH) {
    const excess = total - memoryPanelH;
    tokenTraceH = Math.max(mem.tokenTraceMin, tokenTraceH - excess);
    tokenAreaHeight = mem.tokenStripFixed + tokenTraceH;
    graphHeight = Math.max(0, memoryPanelH - fixedChrome - tokenAreaHeight);
    graphHeight = Math.min(bounds.max, graphHeight);
    graphSectionHeight = fixedChrome + graphHeight;
  }

  const graphChrome = canvasChrome(mem);
  const graphSlotHeight = graphHeight + graphChrome;
  const graphWidth = Math.max(160, shellW - shell.expandPadX - mem.graphPadX);

  return {
    shellWidth: shellW,
    shellHeight: shellH,
    memoryPanelHeight: memoryPanelH,
    graphWidth,
    graphHeight,
    graphSlotHeight,
    graphSectionHeight,
    tokenTraceHeight: tokenTraceH,
    tokenAreaHeight,
  };
}

/** Refine frame from measured panel + header + scope select heights. */
export function refineFloatFactorGraphFrame(
  stage: FloatStage,
  panelWidth: number,
  panelHeight: number,
  headerHeight: number,
  scopeHeight: number,
  base: FloatFactorGraphFrame,
): FloatFactorGraphFrame {
  const mem = FLOAT_MEMORY_PANEL_CHROME;
  const bounds = GRAPH_HEIGHT_BOUNDS[stage];

  if (panelWidth < 1 || panelHeight < 1) return base;

  const fixedChrome = graphSectionFixedChrome(mem, headerHeight, scopeHeight);
  const graphChrome = canvasChrome(mem);
  const graphWidth = Math.max(160, panelWidth - mem.graphPadX);

  const maxGraphHeight = Math.max(0, panelHeight - base.tokenAreaHeight - fixedChrome);
  const graphHeight = Math.min(bounds.max, maxGraphHeight);
  const graphSlotHeight = graphHeight + graphChrome;
  const graphSectionHeight = fixedChrome + graphHeight;

  return {
    ...base,
    memoryPanelHeight: panelHeight,
    graphWidth,
    graphHeight,
    graphSlotHeight,
    graphSectionHeight,
  };
}
