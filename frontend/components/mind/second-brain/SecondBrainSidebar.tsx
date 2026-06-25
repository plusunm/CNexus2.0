"use client";

import clsx from "clsx";
import { Sparkles } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";
import { ExperienceTierSwitch, useCognitiveCopy } from "@/lib/cognitive";
import { LanguageProjectionSwitch } from "../LanguageProjectionSwitch";
import { useMindTheme } from "../MindUiProvider";
import { CnexusAvatarIcon } from "../CnexusAvatarIcon";
import type { SecondBrainTab } from "@/lib/cognitive/experience/types";
import { SECOND_BRAIN_NAV, SECOND_BRAIN_NAV_GROUPS } from "./secondBrainNav";

type Props = {
  activeTab: SecondBrainTab;
  onTabChange: (tab: SecondBrainTab) => void;
};

export function SecondBrainSidebar({ activeTab, onTabChange }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const { overview, isDemo, isLive, isWarming } = useMindOverview();
  const runtimeStatus = useRuntimeStatus();

  const statusColor = isDemo ? t.orange : isLive ? t.green : isWarming ? t.orange : t.red;
  const statusText = isDemo
    ? copy("offline")
    : isLive
      ? copy("connected")
      : isWarming
        ? "正在连接…"
        : copy("offline");

  return (
    <aside
      className="hidden lg:flex w-[220px] shrink-0 flex-col h-screen overflow-hidden border-r"
      style={{ borderColor: t.border, backgroundColor: t.surface }}
      data-cnexus-sb-sidebar
    >
      <div className="px-4 pt-5 pb-4 border-b" style={{ borderColor: t.border }}>
        <div className="flex items-center gap-3">
          <CnexusAvatarIcon size={40} rounded="xl" />
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate" style={{ color: t.text }}>
              CNexus
            </p>
            <p className="text-[11px] truncate" style={{ color: "#5eead4" }}>
              {copy("personaSecondBrain")}
            </p>
          </div>
        </div>
      </div>

      <div className="px-4 py-4">
        <div
          className="rounded-xl p-3 border"
          style={{ borderColor: t.border, backgroundColor: t.chatBg }}
        >
          <div className="flex items-center gap-1.5 mb-1.5">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: statusColor }} />
            <span className="text-xs font-medium" style={{ color: t.text }}>
              {statusText}
            </span>
          </div>
          <p className="text-[11px] leading-relaxed" style={{ color: t.textMuted }}>
            {copy("healthLabel")}：{isWarming ? runtimeStatus.label : overview.system.health_label}
          </p>
          <p className="text-[11px] mt-1" style={{ color: t.textLight }}>
            {copy("memoryCount", { count: overview.memory_items.length })}
          </p>
        </div>
      </div>

      <nav className="px-2 flex-1 min-h-0 overflow-y-auto cnexus-float-scroll [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        {SECOND_BRAIN_NAV_GROUPS.map(({ key, label }) => (
          <div key={key} className="space-y-0.5">
            <p className="text-[10px] uppercase tracking-wider px-2 pb-0.5 pt-1" style={{ color: t.textLight }}>
              {label}
            </p>
            {SECOND_BRAIN_NAV.filter((item) => item.group === key).map(({ id, icon: Icon, labelKey }) => {
              const active = activeTab === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onTabChange(id)}
                  className={clsx(
                    "w-full flex items-center gap-2 px-2 py-2 rounded-lg text-left transition",
                    active ? "font-medium" : "opacity-85 hover:opacity-100",
                  )}
                  style={{
                    backgroundColor: active ? t.sidebarActive : "transparent",
                    color: active ? "#5eead4" : t.textMuted,
                    border: active ? `1px solid ${t.border}` : "1px solid transparent",
                  }}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="text-xs leading-tight truncate">{copy(labelKey)}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="px-3 py-3 space-y-2 border-t shrink-0" style={{ borderColor: t.border }}>
        <div className="flex items-start gap-2 text-[11px]" style={{ color: t.textLight }}>
          <Sparkles className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color: "#5eead4" }} />
          <span>需要调试完整认知链路时，切换到认知实验室。</span>
        </div>
        <ExperienceTierSwitch />
        <LanguageProjectionSwitch compact />
      </div>
    </aside>
  );
}
