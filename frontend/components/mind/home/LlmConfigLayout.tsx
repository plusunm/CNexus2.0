"use client";

import { Settings2 } from "lucide-react";
import { biSection, navL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";
import { OllamaControlButton } from "../OllamaControlButton";
import { OllamaConnectionBadge } from "../OllamaConnectionBadge";
import { HomeModelSettingsPanel } from "./HomeModelSettingsPanel";

export function LlmConfigLayout() {
  const t = useMindTheme();

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div
        className="rounded-2xl border p-5"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div className="flex items-start gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ backgroundColor: t.purpleSoft, color: t.purple }}
          >
            <Settings2 className="w-5 h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-semibold" style={{ color: t.text }}>
              {biSection(navL.llmConfigPageTitle)}
            </h1>
            <p className="text-sm mt-1" style={{ color: t.textMuted }}>
              {biSection(navL.llmConfigPageHint)}
            </p>
          </div>
        </div>
      </div>

      <section
        className="rounded-2xl border overflow-hidden"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <div
          className="px-5 py-4 border-b flex flex-wrap items-center justify-between gap-3"
          style={{ borderColor: t.border }}
        >
          <div>
            <p className="text-sm font-medium" style={{ color: t.text }}>
              Ollama 本地服务
            </p>
            <p className="text-xs mt-0.5" style={{ color: t.textMuted }}>
              检测、启动本机 Ollama，供本地大模型与向量推理使用
            </p>
          </div>
          <div className="flex items-center gap-2">
            <OllamaConnectionBadge inline />
            <OllamaControlButton />
          </div>
        </div>
        <HomeModelSettingsPanel />
      </section>
    </div>
  );
}
