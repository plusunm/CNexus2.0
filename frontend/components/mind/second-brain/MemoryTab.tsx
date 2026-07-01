"use client";

import { useMemo, useState } from "react";
import { Sparkles, BookOpen, Lightbulb } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { useCognitiveSynthesis } from "@/hooks/useCognitiveSynthesis";
import { useMindTheme } from "../MindUiProvider";
import { useCognitiveCopy, EmergenceObject } from "@/lib/cognitive";
import { WhyExplainSheet } from "./WhyExplainSheet";
import { SbSection, SbCard, SbStat, SbChip, SbEmptyState } from "./SbUIKit";
import { PromoteToL4Button } from "../PromoteToL4Button";
import { RelationshipMemoryArchive } from "./RelationshipMemoryArchive";
import { MEMORY_LEVEL_LABEL, resolveMemoryLevel } from "@/lib/memoryPromote";
import type { CognitiveDiscoveryBlock, CognitiveInsightBlock } from "@/lib/cognitiveTypes";
import type { CognitiveObject } from "@/lib/cognitive";

type MemoryFilter = "all" | "important" | "episode" | "identity";

function isDiscovery(row: CognitiveInsightBlock | CognitiveDiscoveryBlock): row is CognitiveDiscoveryBlock {
  return typeof (row as CognitiveDiscoveryBlock).id === "string" && Boolean((row as CognitiveDiscoveryBlock).id);
}

const FILTER_TAGS: Record<Exclude<MemoryFilter, "all">, string[]> = {
  important: ["goal", "belief"],
  episode: ["episode"],
  identity: ["identity"],
};

type Props = {
  onOpenLab: (href: string) => void;
};

export function MemoryTab({ onOpenLab }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const { overview, isDemo } = useMindOverview();
  const { data } = useCognitiveSynthesis(0);
  const [explainObject, setExplainObject] = useState<CognitiveObject | null>(null);
  const [filter, setFilter] = useState<MemoryFilter>("all");

  const discoveries = useMemo(() => {
    const rows: (CognitiveInsightBlock | CognitiveDiscoveryBlock)[] = [
      ...(data.discoveries || []),
      ...(data.insights || []),
    ];
    return rows.slice(0, 6).map((row, index) => {
      if (isDiscovery(row)) return EmergenceObject.fromDiscovery(row);
      return EmergenceObject.fromInsight(row, index);
    });
  }, [data.discoveries, data.insights]);

  const filteredMemories = useMemo(() => {
    const items = overview.memory_items;
    if (filter === "all") return items;
    const tags = FILTER_TAGS[filter];
    return items.filter((item) => tags.includes(item.tag));
  }, [overview.memory_items, filter]);

  const displayMemories = filteredMemories.slice(0, 16);
  const healthLabel = overview.system.health_label || copy("systemStatus");

  return (
    <div className="flex flex-col gap-6 pb-6 cnexus-float-scroll">
      <SbSection title={copy("memoryOverview")} icon={BookOpen}>
        <div className="grid grid-cols-3 gap-2">
          <SbStat label={copy("memoryBlock")} value={overview.memory_items.length} tone="teal" />
          <SbStat label={copy("recentDiscoveries")} value={discoveries.length} tone="purple" />
          <SbStat label={copy("healthLabel")} value={healthLabel} tone="default" />
        </div>
      </SbSection>

      <SbSection
        title={copy("recentDiscoveries")}
        subtitle="系统从你的对话和文档中提炼出的新观察。"
        icon={Lightbulb}
      >
        {discoveries.length === 0 ? (
          <SbEmptyState>继续对话或上传文档，最近发现会出现在这里。</SbEmptyState>
        ) : (
          <ul className="space-y-2">
            {discoveries.map((obj) => (
              <li key={obj.ref.id}>
                <SbCard padding="sm" accent="purple" className="flex items-start gap-3">
                  <Sparkles className="w-4 h-4 shrink-0 mt-0.5" style={{ color: t.purple }} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-relaxed" style={{ color: t.text }}>
                      {obj.consumerSummary}
                    </p>
                    {obj.provenance && (
                      <button
                        type="button"
                        className="mt-2 text-xs font-medium"
                        style={{ color: t.blue }}
                        onClick={() => setExplainObject(obj)}
                      >
                        {copy("whyExplain")}
                      </button>
                    )}
                  </div>
                </SbCard>
              </li>
            ))}
          </ul>
        )}
      </SbSection>

      <SbSection title={copy("memoryBlock")} subtitle="按类别浏览已保存的记忆。">
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["all", "memoryFilterAll"],
              ["important", "memoryFilterImportant"],
              ["episode", "memoryFilterExperiences"],
              ["identity", "memoryFilterAboutMe"],
            ] as const
          ).map(([id, key]) => (
            <SbChip key={id} active={filter === id} onClick={() => setFilter(id)}>
              {copy(key)}
            </SbChip>
          ))}
        </div>
        {displayMemories.length === 0 ? (
          <SbEmptyState>
            {filter === "all"
              ? "还没有记忆。去「对话」聊聊，或在「上传记忆」导入文档。"
              : "这个分类下暂无记忆。"}
          </SbEmptyState>
        ) : (
          <ul className="space-y-2 mt-1">
            {displayMemories.map((item) => {
              const memoryLevel = resolveMemoryLevel(item);
              const levelLabel = memoryLevel ? MEMORY_LEVEL_LABEL[memoryLevel] || memoryLevel : null;
              return (
              <li key={item.id || item.title}>
                <SbCard padding="sm">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium leading-snug" style={{ color: t.text }}>
                          {item.title}
                        </p>
                        {levelLabel && (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                            style={{
                              color: memoryLevel === "foundation" ? "#a78bfa" : t.textMuted,
                              backgroundColor:
                                memoryLevel === "foundation" ? "rgba(167,139,250,0.12)" : `${t.border}44`,
                            }}
                          >
                            {levelLabel}
                          </span>
                        )}
                      </div>
                      {item.desc && (
                        <p className="text-xs mt-1.5 line-clamp-2 leading-relaxed" style={{ color: t.textMuted }}>
                          {item.desc}
                        </p>
                      )}
                    </div>
                    {!isDemo && <PromoteToL4Button item={item} />}
                  </div>
                </SbCard>
              </li>
            );
            })}
          </ul>
        )}
      </SbSection>

      <RelationshipMemoryArchive />

      <WhyExplainSheet
        object={explainObject ?? { ref: { domain: "emergence", id: "" }, titleKey: "emergentInsight", consumerSummary: "" }}
        open={Boolean(explainObject)}
        onClose={() => setExplainObject(null)}
        onOpenLab={onOpenLab}
      />
    </div>
  );
}
