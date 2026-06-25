"use client";

import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "../MindUiProvider";
import { HomeDocumentUpload } from "../home/HomeDocumentUpload";
import { SbCard, SbSection } from "./SbUIKit";
import { Upload } from "lucide-react";

export function UploadTab() {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();

  return (
    <div className="flex flex-col gap-6 pb-8 cnexus-float-scroll">
      <SbSection
        title={copy("addContent")}
        subtitle="上传文档、笔记或资料，CNexus 会读入并写入长期记忆。"
        icon={Upload}
      >
        <SbCard accent="teal">
          <HomeDocumentUpload navigateAfterImport={false} />
        </SbCard>
      </SbSection>

      <SbCard padding="sm">
        <ul className="text-xs space-y-2 leading-relaxed" style={{ color: t.textMuted }}>
          <li>· 支持 PDF、Markdown、TXT 等常见格式</li>
          <li>· 导入后可在「记忆」页查看</li>
          <li>· 可在「外部通知」配置导入完成提醒</li>
        </ul>
      </SbCard>
    </div>
  );
}
