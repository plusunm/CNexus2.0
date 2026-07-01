"use client";

import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { BookMarked, ChevronLeft, Trash2 } from "lucide-react";
import { cnexusProductApi } from "@/lib/api";
import { listRelationshipCards } from "@/lib/relationshipAnalysis/cardStorage";
import type { RelationshipAnalysisCard } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../MindUiProvider";
import { SbSection, SbCard, SbEmptyState } from "./SbUIKit";
import { DecisionModelCardView } from "./thinking/DecisionModelCardView";
import { RelationshipPhaseMap } from "./thinking/RelationshipPhaseMap";

export function CardsTab() {
  const t = useMindTheme();
  const [cards, setCards] = useState<RelationshipAnalysisCard[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoadError(null);
    try {
      const rows = await cnexusProductApi.listRelationshipCardsApi();
      setCards(rows);
    } catch {
      setCards(listRelationshipCards());
      setLoadError("后端卡片库不可用，已显示本地缓存。");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selected = cards.find((row) => row.meta.id === selectedId) ?? null;

  const removeCard = async (id: string) => {
    try {
      await cnexusProductApi.deleteRelationshipCardApi(id);
    } catch {
      /* local-only card or offline */
    }
    setCards((prev) => prev.filter((row) => row.meta.id !== id));
    if (selectedId === id) setSelectedId(null);
    void refresh();
  };

  if (selected) {
    return (
      <div className="flex flex-col gap-4 pb-8 cnexus-float-scroll">
        <button
          type="button"
          className="flex items-center gap-1.5 text-xs w-fit"
          style={{ color: t.textMuted }}
          onClick={() => setSelectedId(null)}
        >
          <ChevronLeft className="w-4 h-4" />
          返回模型库
        </button>

        <SbSection
          title="认知资产"
          subtitle={`来源：${selected.meta.sourceInput}`}
          icon={BookMarked}
        >
          <DecisionModelCardView card={selected.card} analysis={selected} />
        </SbSection>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 pb-8 cnexus-float-scroll">
      <SbSection
        title="决策模型库"
        subtitle="从分析中沉淀的可复用决策模型，不是聊天记录。"
        icon={BookMarked}
      >
        {loadError && (
          <p className="text-xs mb-2" style={{ color: t.textMuted }}>
            {loadError}
          </p>
        )}
        {cards.length === 0 ? (
          <SbEmptyState>还没有认知模型。在「思考」页完成一次分析后会自动压缩为模型卡片。</SbEmptyState>
        ) : (
          <ul className="space-y-2">
            {cards.map((card) => (
              <li key={card.meta.id}>
                <SbCard
                  className={clsx("cursor-pointer transition hover:opacity-95")}
                  accent="purple"
                  padding="sm"
                >
                  <button
                    type="button"
                    className="w-full text-left"
                    onClick={() => setSelectedId(card.meta.id)}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium" style={{ color: t.text }}>
                        {card.card.title}
                      </p>
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full border"
                        style={{ borderColor: "#A78BFA55", color: "#A78BFA" }}
                      >
                        {card.card.problemType}
                      </span>
                    </div>
                    <RelationshipPhaseMap activeId={card.card.libraryModelId} className="mt-2" />
                    <p className="text-xs mt-1.5 line-clamp-2 leading-relaxed" style={{ color: t.textMuted }}>
                      {card.card.modelSummary}
                    </p>
                    {card.card.reusabilityTags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {card.card.reusabilityTags.slice(0, 4).map((tag) => (
                          <span
                            key={tag}
                            className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                            style={{ color: t.textLight, backgroundColor: t.chatBg }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="text-[10px] mt-2 truncate" style={{ color: t.textLight }}>
                      来源：{card.meta.sourceInput}
                    </p>
                    <p className="text-[10px] mt-0.5" style={{ color: t.textLight }}>
                      {new Date(card.meta.createdAt).toLocaleString()}
                    </p>
                  </button>
                  <div className="flex justify-end mt-2 pt-2 border-t" style={{ borderColor: t.border }}>
                    <button
                      type="button"
                      className="text-[11px] flex items-center gap-1 opacity-70 hover:opacity-100"
                      style={{ color: t.textMuted }}
                      onClick={() => void removeCard(card.meta.id)}
                    >
                      <Trash2 className="w-3 h-3" />
                      删除
                    </button>
                  </div>
                </SbCard>
              </li>
            ))}
          </ul>
        )}
      </SbSection>
    </div>
  );
}
