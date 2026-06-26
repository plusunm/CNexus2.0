import type { MindOverviewMemoryItem } from "@/lib/runtimeTypes";

export const MEMORY_LEVEL_LABEL: Record<string, string> = {
  scratch: "L0",
  temporary: "L1",
  long_term: "L2",
  project: "L3",
  core: "L2+",
  foundation: "L4",
};

export function resolveMemoryLevel(item: MindOverviewMemoryItem): string | undefined {
  return item.memory_level || (item.meta === "foundation" || item.meta === "core" ? item.meta : undefined);
}

export function canPromoteMemoryItem(item: MindOverviewMemoryItem): boolean {
  const level = resolveMemoryLevel(item);
  if (level === "foundation") return false;
  const id = item.id || "";
  if (!id || id.startsWith("kw-") || id.startsWith("goal-")) return false;
  return true;
}

export function canPromoteToFoundation(item: MindOverviewMemoryItem): boolean {
  return canPromoteMemoryItem(item) && resolveMemoryLevel(item) !== "foundation";
}
