"use client";

import { Cpu } from "lucide-react";
import { useCognitiveCopy } from "@/lib/cognitive";
import { HomeModelSettingsPanel } from "../home/HomeModelSettingsPanel";
import { SbSection, SbCard } from "./SbUIKit";

export function ModelTab() {
  const { t: copy } = useCognitiveCopy();

  return (
    <div className="flex flex-col gap-6 pb-8 cnexus-float-scroll">
      <SbSection
        title={copy("modelSection")}
        subtitle="配置 Ollama 本地或云端大模型 API，保存后自动同步至网关。"
        icon={Cpu}
      >
        <SbCard accent="blue">
          <HomeModelSettingsPanel />
        </SbCard>
      </SbSection>
    </div>
  );
}
