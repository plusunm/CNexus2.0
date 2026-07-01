"use client";

import { BookOpen, ExternalLink, FolderOpen } from "lucide-react";
import { CNEXUS_ABOUT } from "@/lib/cnexusAbout";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import { FloatingMiniDialog } from "./FloatingMiniDialog";
import { openPersonalHelpGuide } from "@/components/help/PersonalHelpModal";
import { openPersonalDataDir } from "@/lib/personalHelp";
import { bi, gatewayL } from "@/lib/spine/labels";
import { isPersonalMode } from "@/lib/personalGuard";

type Props = {
  onClose: () => void;
};

export function FloatingAboutDialog({ onClose }: Props) {
  const t = useMindTheme();
  const personal = isPersonalMode();

  return (
    <FloatingMiniDialog title={`关于 ${CNEXUS_ABOUT.productName}`} onClose={onClose} width={300}>
      <div className={`space-y-4 ${floatTy.body}`}>
        <div className="flex items-baseline justify-between gap-3">
          <span style={{ color: t.textMuted }}>产品</span>
          <span style={{ color: t.text }}>{CNEXUS_ABOUT.productName}</span>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <span style={{ color: t.textMuted }}>版本</span>
          <span className={floatTy.mono} style={{ color: t.text }}>
            {CNEXUS_ABOUT.version}
          </span>
        </div>

        {personal && (
          <div className="space-y-2">
            <span className="block" style={{ color: t.textMuted }}>
              帮助与诊断
            </span>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                className={`flex items-center gap-2 p-2 rounded-lg transition hover:brightness-110 text-left w-full ${floatTy.btn}`}
                style={{
                  backgroundColor: "rgba(255,255,255,0.04)",
                  border: `1px solid ${t.border}`,
                  color: t.blue,
                }}
                onClick={() => {
                  openPersonalHelpGuide();
                  onClose();
                }}
              >
                <BookOpen className="w-3.5 h-3.5 shrink-0" />
                {bi(gatewayL.openHelpGuide)}
              </button>
              <button
                type="button"
                className={`flex items-center gap-2 p-2 rounded-lg transition hover:brightness-110 text-left w-full ${floatTy.btn}`}
                style={{
                  backgroundColor: "rgba(255,255,255,0.04)",
                  border: `1px solid ${t.border}`,
                  color: t.text,
                }}
                onClick={() => void openPersonalDataDir()}
              >
                <FolderOpen className="w-3.5 h-3.5 shrink-0" />
                {bi(gatewayL.openLogsFolder)}
              </button>
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <span className="block" style={{ color: t.textMuted }}>
            联系方式
          </span>
          <a
            href={CNEXUS_ABOUT.contactUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 p-2 rounded-lg transition hover:brightness-110 break-all"
            style={{
              backgroundColor: "rgba(255,255,255,0.04)",
              border: `1px solid ${t.border}`,
              color: t.blue,
            }}
          >
            <ExternalLink className="w-3.5 h-3.5 shrink-0" />
            {CNEXUS_ABOUT.contactUrl}
          </a>
        </div>
      </div>
    </FloatingMiniDialog>
  );
}
