import type { CognitiveInsightBlock, CognitiveDiscoveryBlock } from "@/lib/cognitiveTypes";
import { buildEmergenceLabLink } from "../experience/deepLink";
import type { CognitiveObject, ProvenanceExplain, ProvenanceSource } from "./types";

function estimateProvenance(insight: CognitiveInsightBlock | CognitiveDiscoveryBlock): ProvenanceSource[] {
  const sources: ProvenanceSource[] = [];
  const evidence = "evidence" in insight && insight.evidence?.length ? insight.evidence.length : 0;
  if (evidence > 0) {
    sources.push({ kind: "conversation", count: Math.max(1, Math.min(evidence, 12)), labelKey: "sourceConversation" });
  }
  if (insight.source?.includes("doc") || insight.source?.includes("asset")) {
    sources.push({ kind: "document", count: 1, labelKey: "sourceDocument" });
  }
  sources.push({ kind: "long_term_memory", count: Math.max(1, Math.round((insight.confidence || 0.5) * 8)), labelKey: "sourceLongTermMemory" });
  return sources;
}

export const MemoryObject = {
  fromOverviewItem(item: { title: string; desc?: string; meta?: string }, index: number): CognitiveObject {
    const id = `mem-${index}-${item.title.slice(0, 24)}`;
    return {
      ref: { domain: "memory", id },
      titleKey: "memoryBlock",
      consumerSummary: item.desc || item.title,
    };
  },
};

export const ConflictObject = {
  fromAuditPair(pair: { block_id?: string; resolution?: { status?: string } }, auditId?: string): CognitiveObject {
    const id = pair.block_id || auditId || "unknown";
    const status = pair.resolution?.status || "pending";
    return {
      ref: {
        domain: "conflict",
        id,
        labDeepLink: buildEmergenceLabLink(id),
      },
      titleKey: status === "resolved" ? "conflictResolved" : "conflictPending",
      consumerSummary: status === "resolved" ? "已确认" : "需要确认",
      _runtime: pair,
    };
  },
};

export const PruningObject = {
  fromReport(report?: { archived_blocks?: number; summaries_created?: number }): CognitiveObject {
    const archived = report?.archived_blocks ?? 0;
    const summaries = report?.summaries_created ?? 0;
    return {
      ref: { domain: "pruning", id: "latest-pruning" },
      titleKey: "pruning",
      consumerSummary: summaries > 0 ? `整理了 ${summaries} 条摘要` : archived > 0 ? `归档了 ${archived} 条记忆` : "暂无整理记录",
      _runtime: report,
    };
  },
};

export const EmergenceObject = {
  fromInsight(insight: CognitiveInsightBlock, index = 0): CognitiveObject {
    const id = `insight-${index}-${insight.title.slice(0, 16)}`;
    const sources = estimateProvenance(insight);
    const provenance: ProvenanceExplain = {
      headline: insight.title,
      sources,
      labDeepLink: buildEmergenceLabLink(id),
    };
    return {
      ref: { domain: "emergence", id, labDeepLink: provenance.labDeepLink },
      titleKey: "emergentInsight",
      consumerSummary: insight.description || insight.title,
      provenance,
      _runtime: insight,
    };
  },

  fromDiscovery(discovery: CognitiveDiscoveryBlock): CognitiveObject {
    const sources = estimateProvenance(discovery);
    const provenance: ProvenanceExplain = {
      headline: discovery.title,
      sources,
      labDeepLink: buildEmergenceLabLink(discovery.id),
    };
    return {
      ref: { domain: "emergence", id: discovery.id, labDeepLink: provenance.labDeepLink },
      titleKey: "emergentInsight",
      consumerSummary: discovery.description || discovery.title,
      provenance,
      _runtime: discovery,
    };
  },
};
