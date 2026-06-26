import type { MindOverview } from "@/lib/runtimeTypes";
import { buildFactorGraph, type FactorGraph } from "@/lib/factorGraphModel";
import type { MemoryScope } from "@/lib/memoryScope";

/** Match federated asset search semantics (local + trusted peers for trusted scope). */
export function originMatchesMemoryScope(
  sourcePeer: string | undefined | null,
  scope: MemoryScope,
  trustedPeerIds: ReadonlySet<string>,
): boolean {
  const peer = String(sourcePeer ?? "").trim();
  if (scope === "network") return true;
  if (scope === "trusted") return !peer || trustedPeerIds.has(peer);
  return !peer;
}

export function filterOverviewByMemoryScope(
  overview: MindOverview,
  scope: MemoryScope,
  trustedPeerIds: ReadonlySet<string>,
): MindOverview {
  const memory_items = overview.memory_items.filter((item) =>
    originMatchesMemoryScope(item.source_peer, scope, trustedPeerIds),
  );
  const nodeIds = new Set(memory_items.map((item) => item.id));
  const wormhole_links = (overview.wormhole_links ?? []).filter(
    (link) => nodeIds.has(link.source) && nodeIds.has(link.target),
  );
  const projection_links = (overview.projection_links ?? []).filter(
    (link) => nodeIds.has(link.source) && nodeIds.has(link.target),
  );
  return { ...overview, memory_items, wormhole_links, projection_links };
}

export function buildScopedFactorGraph(
  overview: MindOverview,
  scope: MemoryScope,
  trustedPeerIds: ReadonlySet<string>,
): FactorGraph {
  return buildFactorGraph(filterOverviewByMemoryScope(overview, scope, trustedPeerIds));
}
