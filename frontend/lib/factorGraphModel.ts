import type { MindOverview } from "@/lib/runtimeTypes";
import type { LexemeTag } from "@/lib/memoryLexicon";

export type FactorEdgeKind = "chain" | "cluster" | "parent" | "semantic" | "wormhole" | "defines" | "inherits" | "vision_flow";

export type FactorNode = {
  id: string;
  text: string;
  tag: LexemeTag;
  weight: number;
  index: number;
  cluster: string;
  parentId?: string;
  activity?: number;
  isActive?: boolean;
};

export type FactorEdge = {
  id: string;
  from: string;
  to: string;
  kind: FactorEdgeKind;
  strength: number;
};

export type FactorGraph = {
  nodes: FactorNode[];
  edges: FactorEdge[];
  brainRadius: number;
  density: number;
};

function tagWeight(tag: string): number {
  if (tag === "code_class") return 1.25;
  if (tag === "code_function") return 1.1;
  if (tag === "vision_component") return 1.05;
  if (tag === "goal") return 1.35;
  if (tag === "belief") return 1.15;
  if (tag === "identity") return 1.1;
  if (tag === "insight") return 1.05;
  if (tag === "episode") return 1.1;
  return 0.85;
}

function normalizeTag(tag: string): LexemeTag {
  if (
    tag === "goal" ||
    tag === "belief" ||
    tag === "episode" ||
    tag === "identity" ||
    tag === "insight" ||
    tag === "code_class" ||
    tag === "code_function" ||
    tag === "vision_component"
  ) {
    return tag;
  }
  return "term";
}

function inferParentId(id: string, meta: string): string | undefined {
  if (id.startsWith("kw-")) {
    const body = id.slice(3);
    const cut = body.lastIndexOf("-");
    if (cut > 0) return body.slice(0, cut);
  }
  const stem = id.match(/^(.+)-(kw|rk|rkw)-/);
  if (stem) return stem[1];
  if (meta.startsWith("v2-trace") || meta.startsWith("mem-")) return meta;
  return undefined;
}

function addEdge(edges: FactorEdge[], seen: Set<string>, from: string, to: string, kind: FactorEdgeKind, strength: number) {
  if (from === to) return;
  const id = `${kind}:${from}->${to}`;
  if (seen.has(id)) return;
  seen.add(id);
  edges.push({ id, from, to, kind, strength });
}

/**
 * 仅从 /api/status 的 memory_items（记忆锚点）构建因子网络。
 * 对话与上传产生的关键词、概念片段为节点；同簇锚点之间织成拓扑连线。
 */
export function buildFactorGraph(overview: MindOverview): FactorGraph {
  const seenIds = new Set<string>();
  const nodes: FactorNode[] = [];

  for (const item of overview.memory_items) {
    const title = item.title?.trim();
    if (!title || title === "—" || seenIds.has(item.id)) continue;
    seenIds.add(item.id);
    const cluster = (item as { cluster?: string }).cluster?.trim() || item.meta?.trim() || item.id;
    const parentId =
      (item as { parent_id?: string }).parent_id?.trim() ||
      inferParentId(item.id, item.meta) ||
      undefined;
    const nodeType = (item as { node_type?: string }).node_type;
    const tagKey = nodeType || item.tag;
    const activity = item.activity ?? item.score ?? 0;
    const baseWeight = tagWeight(tagKey);
    const activationBoost = activity > 0 ? 0.85 + activity * 0.9 : 1;
    nodes.push({
      id: item.id,
      text: title,
      tag: normalizeTag(tagKey),
      weight: baseWeight * activationBoost,
      index: nodes.length,
      cluster,
      parentId,
      activity,
      isActive: item.is_active ?? activity > 0.4,
    });
  }

  const edges: FactorEdge[] = [];
  const edgeSeen = new Set<string>();
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const byCluster = new Map<string, FactorNode[]>();

  for (const node of nodes) {
    const list = byCluster.get(node.cluster) ?? [];
    list.push(node);
    byCluster.set(node.cluster, list);
  }

  // 父锚点 → 概念/关键词子节点（结晶裂变）
  for (const node of nodes) {
    if (!node.parentId) continue;
    const parent = byId.get(node.parentId);
    if (parent) {
      addEdge(edges, edgeSeen, parent.id, node.id, "parent", 0.92);
    }
  }

  // 同簇内：锚点 episode/goal 辐射连接概念词
  for (const [, clusterNodes] of byCluster) {
    if (clusterNodes.length < 2) continue;
    const hub =
      clusterNodes.find((n) => n.tag === "episode" || n.tag === "goal") ?? clusterNodes[0];
    for (const n of clusterNodes) {
      if (n.id === hub.id) continue;
      addEdge(edges, edgeSeen, hub.id, n.id, "cluster", n.tag === "term" ? 0.72 : 0.58);
    }
    for (let i = 0; i < clusterNodes.length - 1; i += 1) {
      addEdge(edges, edgeSeen, clusterNodes[i].id, clusterNodes[i + 1].id, "chain", 0.42);
    }
  }

  // 跨簇弱语义：共享 desc 片段的术语互连
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i];
      const b = nodes[j];
      if (a.cluster === b.cluster) continue;
      if (a.tag !== "term" && b.tag !== "term") continue;
      if (a.text.length >= 2 && b.text.includes(a.text)) {
        addEdge(edges, edgeSeen, a.id, b.id, "semantic", 0.28);
      } else if (b.text.length >= 2 && a.text.includes(b.text)) {
        addEdge(edges, edgeSeen, b.id, a.id, "semantic", 0.28);
      }
    }
  }

  // 虫洞暗物质通道：语义余弦桥接（无物理边）
  const nodeIds = new Set(nodes.map((n) => n.id));
  for (const wh of overview.wormhole_links ?? []) {
    const from = wh.source?.trim();
    const to = wh.target?.trim();
    if (!from || !to || from === to) continue;
    if (!nodeIds.has(from) || !nodeIds.has(to)) continue;
    const sim = typeof wh.similarity === "number" ? wh.similarity : 0.75;
    addEdge(edges, edgeSeen, from, to, "wormhole", sim);
  }

  // 代码/视觉结构投影边
  for (const pl of overview.projection_links ?? []) {
    const from = pl.source?.trim();
    const to = pl.target?.trim();
    if (!from || !to || from === to) continue;
    if (!nodeIds.has(from) || !nodeIds.has(to)) continue;
    const kind = pl.type === "inherits" ? "inherits" : pl.type === "defines" ? "defines" : pl.type === "vision_flow" ? "vision_flow" : "parent";
    const strength = kind === "inherits" ? 0.88 : kind === "defines" ? 0.95 : 0.78;
    addEdge(edges, edgeSeen, from, to, kind, strength);
  }

  const n = nodes.length;
  const brainRadius = n <= 1 ? 56 : 72 + Math.sqrt(n) * 24;
  const density = Math.min(1, n / 24);

  return { nodes, edges, brainRadius, density };
}

export const FACTOR_TAG_LABEL: Record<LexemeTag, string> = {
  goal: "目标因子",
  belief: "信念因子",
  episode: "经历因子",
  identity: "身份因子",
  insight: "洞察因子",
  term: "术语因子",
  code_class: "代码类",
  code_function: "代码函数",
  vision_component: "架构组件",
};
