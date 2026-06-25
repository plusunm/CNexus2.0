"use client";

import { useState } from "react";
import { Cpu, KeyRound, Sparkles } from "lucide-react";
import {
  CONNECTION_LABELS,
  getEdition,
  getEditionProfile,
  saveStoredLicense,
  type ConnectionPreference,
} from "@/cnexus-kernel";
import { activateEnterpriseEdition } from "@/lib/cnexusConfig";
import { isTauriDesktop, saveEnterpriseLicense } from "@/lib/tauriDesktop";
import { CnexusAvatarIcon } from "./CnexusAvatarIcon";
import { overviewTheme } from "./themes/overviewTheme";
import { useMindConnection } from "./MindConnectionProvider";

export function ConnectionModeGate({ compact = false }: { compact?: boolean }) {
  const { hydrated, selectPreference } = useMindConnection();
  const t = overviewTheme;
  const profile = getEditionProfile(getEdition());
  const [showLicense, setShowLicense] = useState(false);
  const [licenseInput, setLicenseInput] = useState("");

  if (!hydrated) {
    return (
      <div
        className={compact ? "h-full flex items-center justify-center" : "min-h-screen flex items-center justify-center"}
        style={{ backgroundColor: t.bg }}
      >
        <p style={{ color: t.textMuted }}>加载 CNexus…</p>
      </div>
    );
  }

  const cards: {
    mode: ConnectionPreference;
    icon: typeof Sparkles;
    accent: string;
  }[] = [];

  if (profile.allowDemo && !compact) {
    cards.push({ mode: "demo", icon: Sparkles, accent: t.purple });
  }
  if (profile.allowRuntimeConnect) {
    cards.push({ mode: "runtime", icon: Cpu, accent: t.blue });
  }

  const activateEnterprise = async () => {
    const key = licenseInput.trim();
    if (!key) return;
    saveStoredLicense(key);
    activateEnterpriseEdition();
    if (isTauriDesktop()) {
      await saveEnterpriseLicense(key);
    }
    selectPreference("runtime");
    window.location.reload();
  };

  return (
    <div
      className={
        compact
          ? "h-full min-h-0 overflow-y-auto flex flex-col items-center justify-center p-4"
          : "min-h-screen flex flex-col items-center justify-center p-6"
      }
      style={{ backgroundColor: t.bg, fontFamily: t.fontSans }}
    >
      <div className={`max-w-lg w-full text-center ${compact ? "mb-6" : "mb-10"}`}>
        <CnexusAvatarIcon size={compact ? 44 : 56} rounded="2xl" className="mx-auto mb-4" />
        <h1 className={`font-bold mb-2 ${compact ? "text-lg" : "text-2xl"}`} style={{ color: t.text }}>
          CNexus
        </h1>
        <p className="text-sm" style={{ color: t.textMuted }}>
          {compact
            ? "连接本机 Runtime 以使用 Live 数据与 Ollama"
            : "个人版 · 纯净离线版"}
        </p>
      </div>

      {cards.length > 0 && (
        <div
          className={`grid gap-4 max-w-2xl w-full ${
            cards.length > 1 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1 max-w-md"
          }`}
        >
          {cards.map(({ mode, icon: Icon, accent }) => {
            const meta = CONNECTION_LABELS[mode];
            return (
              <button
                key={mode}
                type="button"
                onClick={() => selectPreference(mode)}
                className="text-left p-6 rounded-2xl border transition hover:shadow-lg"
                style={{
                  backgroundColor: t.surface,
                  borderColor: t.border,
                  borderTopWidth: 4,
                  borderTopColor: accent,
                }}
              >
                <Icon className="w-8 h-8 mb-3" style={{ color: accent }} />
                <p className="font-semibold mb-1" style={{ color: t.text }}>
                  {mode === "demo" ? "Demo 模式" : compact ? "连接 Runtime" : "连接本地 Runtime"}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
                  {meta.subtitle}
                </p>
              </button>
            );
          })}
        </div>
      )}

      {profile.id === "personal" && (
        <div className="mt-8 max-w-md w-full">
        </div>
      )}

      <p className="text-[11px] mt-8 max-w-md text-center" style={{ color: t.textLight }}>
        {compact
          ? "CNexus 个人版 · 纯净离线"
          : "CNexus 个人版 · 纯净离线 · 无需 Runtime 或 License"}
      </p>
    </div>
  );
}
