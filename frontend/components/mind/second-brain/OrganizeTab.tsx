"use client";

import { Moon, Trash2 } from "lucide-react";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { RemSleepButton } from "../RemSleepButton";
import { ClearMemoryButton } from "../ClearMemoryButton";
import { SbSection, SbCard } from "./SbUIKit";

export function OrganizeTab() {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();

  return (
    <div className="flex flex-col gap-6 pb-8 cnexus-float-scroll">
      <SbSection
        title={copy("organizeSection")}
        subtitle={copy("organizeSectionHint")}
        icon={Moon}
      >
        <SbCard accent="purple" className="space-y-4">
          <p className="text-sm leading-relaxed" style={{ color: t.textMuted }}>
            定期整理可以归档不常用的记忆，并生成更易读的摘要。你的对话记录不会被删除。
          </p>
          <RemSleepButton />
        </SbCard>
      </SbSection>

      <SbSection
        title={copy("dataManagement")}
        subtitle="清空全部记忆与对话记录，模型配置会保留。"
        icon={Trash2}
      >
        <SbCard>
          <p className="text-xs mb-3 leading-relaxed" style={{ color: t.textMuted }}>
            此操作不可撤销。若只想整理而非全部删除，请使用上方的「整理记忆」。
          </p>
          <ClearMemoryButton />
        </SbCard>
      </SbSection>
    </div>
  );
}
