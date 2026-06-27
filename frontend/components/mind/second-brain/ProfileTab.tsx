"use client";

import { Wifi, Globe } from "lucide-react";
import { useMindOverview } from "@/cnexus-kernel";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { LanguageProjectionSwitch } from "../LanguageProjectionSwitch";
import { InstallStatsOptInPanel } from "../InstallStatsOptInPanel";
import { UpdateCheckPanel } from "../UpdateCheckPanel";
import { OllamaConnectionBadge } from "../OllamaConnectionBadge";
import { SbSection, SbCard } from "./SbUIKit";
import { isPersonalMode } from "@/lib/personalGuard";

export function ProfileTab() {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const { overview, isLive, isDemo } = useMindOverview();
  const online = isLive && !isDemo;

  return (
    <div className="flex flex-col gap-6 pb-8 cnexus-float-scroll">
      <SbSection title={copy("connectionSection")} icon={Wifi}>
        <SbCard padding="sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium" style={{ color: t.text }}>
                {online ? copy("connected") : copy("offline")}
              </p>
              <p className="text-xs mt-1" style={{ color: t.textMuted }}>
                {copy("healthLabel")}：{overview.system.health_label}
              </p>
              <p className="text-xs mt-1" style={{ color: t.textLight }}>
                {copy("memoryCount", { count: overview.memory_items.length })}
              </p>
            </div>
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: online ? t.green : t.orange }}
            />
          </div>
          {!isPersonalMode() && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: t.border }}>
              <OllamaConnectionBadge inline />
            </div>
          )}
        </SbCard>
      </SbSection>

      <InstallStatsOptInPanel />

      <UpdateCheckPanel />

      <SbSection title={copy("appearanceSection")} icon={Globe}>
        <SbCard padding="sm">
          <LanguageProjectionSwitch />
        </SbCard>
      </SbSection>
    </div>
  );
}
