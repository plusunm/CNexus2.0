import type { FactorGraph, FactorNode } from "./factorGraphModel";

export type GraphGroupId = "goal" | "belief" | "episode" | "identity" | "insight" | "term" | "code_class" | "code_function" | "vision_component" | "halo";

export type GraphViewNode = {
  id: string;
  label: string;
  group: GraphGroupId;
  weight: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  fixed?: boolean;
  birthIndex: number;
  activity?: number;
  isActive?: boolean;
};

export type GraphViewLink = {
  id: string;
  source: string;
  target: string;
  strength: number;
  wormhole?: boolean;
  similarity?: number;
  structural?: boolean;
  structuralKind?: string;
};

export type GraphViewModel = {
  nodes: GraphViewNode[];
  links: GraphViewLink[];
};

export type GraphViewSettings = {
  centerForce: number;
  repelForce: number;
  linkForce: number;
  linkDistance: number;
  nodeSize: number;
  linkThickness: number;
  textFade: number;
  animate: boolean;
  showArrows: boolean;
  search: string;
  tagsOnly: boolean;
  orphansOnly: boolean;
};

export const DEFAULT_GRAPH_SETTINGS: GraphViewSettings = {
  centerForce: 0.08,
  repelForce: 120,
  linkForce: 0.04,
  linkDistance: 72,
  nodeSize: 1,
  linkThickness: 1,
  textFade: 0.35,
  animate: true,
  showArrows: false,
  search: "",
  tagsOnly: false,
  orphansOnly: false,
};

/** 记忆流图主视图 — 展示全部锚点含关键词节点 */
export const FACTOR_MEMORY_GRAPH_SETTINGS: GraphViewSettings = {
  ...DEFAULT_GRAPH_SETTINGS,
  centerForce: 0.05,
  repelForce: 95,
  linkForce: 0.055,
  linkDistance: 64,
  linkThickness: 1.15,
  textFade: 0.82,
  tagsOnly: false,
  showArrows: true,
  animate: true,
};

/** Float compact factor graph — tuned for ~400×280 viewport */
export const FLOAT_COMPACT_GRAPH_SETTINGS: GraphViewSettings = {
  ...DEFAULT_GRAPH_SETTINGS,
  centerForce: 0.1,
  repelForce: 85,
  linkForce: 0.05,
  linkDistance: 52,
  nodeSize: 0.92,
  linkThickness: 0.85,
  textFade: 0.58,
  tagsOnly: false,
};

const GROUP_FOR_TAG: Record<FactorNode["tag"], GraphGroupId> = {
  goal: "goal",
  belief: "belief",
  episode: "episode",
  identity: "identity",
  insight: "insight",
  term: "term",
  code_class: "code_class",
  code_function: "code_function",
  vision_component: "vision_component",
};

const TAG_LANE: Record<GraphGroupId, number> = {
  goal: -90,
  belief: -45,
  episode: 0,
  identity: 45,
  insight: 60,
  term: 30,
  code_class: -60,
  code_function: 75,
  vision_component: -30,
  halo: 0,
};

/** 按 memory_items 顺序：旧锚点靠左，新结晶节点靠右 */
function seedCrystallizedLayout(nodes: FactorNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const n = nodes.length;
  const spanX = Math.max(320, Math.min(520, 180 + n * 28));
  const left = -spanX / 2;
  const step = n > 1 ? spanX / (n - 1) : 0;

  nodes.forEach((node, i) => {
    const group = GROUP_FOR_TAG[node.tag] ?? "term";
    const lane = TAG_LANE[group] ?? 0;
    const jitter = ((i * 17) % 7) - 3;
    positions.set(node.id, {
      x: left + step * i + (i % 3) * 6,
      y: lane + jitter * 5 + (node.parentId ? 18 : 0),
    });
  });

  return positions;
}

export function buildGraphViewModel(graph: FactorGraph): GraphViewModel {
  const layout = seedCrystallizedLayout(graph.nodes);

  const nodes: GraphViewNode[] = graph.nodes.map((n, i) => {
    const pos = layout.get(n.id) ?? { x: 0, y: 0 };
    return {
      id: n.id,
      label: n.text,
      group: GROUP_FOR_TAG[n.tag] ?? "term",
      weight: n.weight,
      x: pos.x,
      y: pos.y,
      vx: 0,
      vy: 0,
      birthIndex: i,
      activity: n.activity,
      isActive: n.isActive,
    };
  });

  const links: GraphViewLink[] = graph.edges.map((e) => ({
    id: e.id,
    source: e.from,
    target: e.to,
    strength: e.strength,
    wormhole: e.kind === "wormhole",
    similarity: e.kind === "wormhole" ? e.strength : undefined,
    structural: e.kind === "defines" || e.kind === "inherits" || e.kind === "vision_flow",
    structuralKind: e.kind,
  }));

  // 仅在没有真实锚点时添加装饰光晕
  if (nodes.length < 3) {
    const haloCount = 10;
    for (let i = 0; i < haloCount; i += 1) {
      const angle = (i / haloCount) * Math.PI * 2;
      const id = `halo-${i}`;
      nodes.push({
        id,
        label: "",
        group: "halo",
        weight: 0.35,
        x: Math.cos(angle) * 200,
        y: Math.sin(angle) * 120,
        vx: 0,
        vy: 0,
        birthIndex: 1000 + i,
      });
      const anchor = graph.nodes[i % Math.max(graph.nodes.length, 1)]?.id;
      if (anchor) {
        links.push({ id: `halo-link-${i}`, source: id, target: anchor, strength: 0.05 });
      }
    }
  }

  return { nodes, links };
}

export function filterGraphModel(model: GraphViewModel, settings: GraphViewSettings): GraphViewModel {
  let nodes = model.nodes;
  const q = settings.search.trim().toLowerCase();
  if (q) {
    nodes = nodes.filter((n) => n.label.toLowerCase().includes(q) || n.group.includes(q));
  }
  if (settings.orphansOnly) {
    const linked = new Set<string>();
    for (const l of model.links) {
      linked.add(l.source);
      linked.add(l.target);
    }
    nodes = nodes.filter((n) => n.group === "halo" || !linked.has(n.id));
  }
  if (settings.tagsOnly) {
    nodes = nodes.filter((n) => n.group === "halo" || n.group !== "term");
  }
  const ids = new Set(nodes.map((n) => n.id));
  const links = model.links.filter((l) => ids.has(l.source) && ids.has(l.target));
  return { nodes, links };
}
