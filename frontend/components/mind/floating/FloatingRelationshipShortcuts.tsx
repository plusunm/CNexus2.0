"use client";

import { Brain, GitBranch, ExternalLink } from "lucide-react";
import { useMindTheme } from "../MindUiProvider";
import { buildSecondBrainDashboardRoute, resolveSecondBrainOpenUrl } from "@/lib/cognitive/experience/deepLink";
import { isTauriDesktop, openTauriDashboard } from "@/lib/tauriDesktop";

function openSecondBrainTab(
  tab: "timeline" | "thinking" | "memory",
  from: "float-timeline" | "float-thinking" | "float-memory",
) {
  if (isTauriDesktop()) {
    void openTauriDashboard(buildSecondBrainDashboardRoute({ tab, from }));
    return;
  }
  window.open(resolveSecondBrainOpenUrl({ tab, from }), "_blank", "noopener,noreferrer");
}

/** Float expand — shortcuts into Second Brain relationship / decision tabs. */
export function FloatingRelationshipShortcuts() {
  const t = useMindTheme();

  const items = [
    {
      id: "timeline",
      label: "关系时间轴",
      hint: "导入聊天 · 因果 · 预测",
      icon: GitBranch,
      color: "#5eead4",
      onClick: () => openSecondBrainTab("timeline", "float-timeline"),
    },
    {
      id: "thinking",
      label: "决策分析",
      hint: "结构化决策思考",
      icon: Brain,
      color: "#A78BFA",
      onClick: () => openSecondBrainTab("thinking", "float-thinking"),
    },
  ] as const;

  return (
    <div className="space-y-1.5 pt-2 border-t mt-2" style={{ borderColor: t.border }}>
      <p className="text-[10px] font-medium px-0.5" style={{ color: t.textMuted }}>
        关系决策（大屏）
      </p>
      <div className="flex gap-1.5">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className="flex-1 flex flex-col items-start gap-0.5 rounded-lg border px-2 py-1.5 text-left transition hover:opacity-90"
              style={{
                borderColor: `${item.color}44`,
                backgroundColor: `${item.color}0d`,
              }}
              title={item.hint}
              onClick={item.onClick}
            >
              <span className="flex items-center gap-1 text-[11px] font-medium w-full" style={{ color: item.color }}>
                <Icon className="w-3 h-3 shrink-0" />
                <span className="truncate flex-1">{item.label}</span>
                <ExternalLink className="w-2.5 h-2.5 shrink-0 opacity-60" />
              </span>
              <span className="text-[9px] leading-tight truncate w-full" style={{ color: t.textMuted }}>
                {item.hint}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
