"use client";

import { Download, X } from "lucide-react";
import type { UpdateCheckStatus } from "@/lib/api";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  status: UpdateCheckStatus;
  compact?: boolean;
  onDismiss?: () => void;
};

export function UpdateAvailableBanner({ status, compact = false, onDismiss }: Props) {
  const t = useMindTheme();
  const current = status.current_version || "—";
  const latest = status.latest_version || "—";
  const url = status.release_url || "https://github.com/plusunm/CNexus2.0/releases/latest";

  return (
    <div
      className={compact ? "shrink-0 px-2 pt-2" : "shrink-0 px-4 lg:px-6 pt-3"}
      role="status"
      aria-live="polite"
    >
      <div
        className="flex items-start gap-3 rounded-xl border px-3 py-2.5"
        style={{
          borderColor: "rgba(20,184,166,0.35)",
          backgroundColor: "rgba(20,184,166,0.08)",
        }}
      >
        <Download className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#14b8a6" }} />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium" style={{ color: t.text }}>
            发现新版本 {latest}
          </p>
          <p className="text-[10px] mt-0.5 leading-relaxed" style={{ color: t.textMuted }}>
            当前 {current}
            {status.release_name ? ` · ${status.release_name}` : ""}
          </p>
          {!compact && status.release_notes ? (
            <p className="text-[10px] mt-1 line-clamp-2 whitespace-pre-wrap" style={{ color: t.textLight }}>
              {status.release_notes}
            </p>
          ) : null}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium text-white"
              style={{ backgroundColor: "#14b8a6" }}
            >
              前往 GitHub 下载
            </a>
            {onDismiss ? (
              <button
                type="button"
                onClick={onDismiss}
                className="text-[10px] underline-offset-2 hover:underline"
                style={{ color: t.textMuted }}
              >
                稍后提醒
              </button>
            ) : null}
          </div>
        </div>
        {onDismiss ? (
          <button
            type="button"
            aria-label="关闭更新提示"
            onClick={onDismiss}
            className="shrink-0 p-1 rounded-md hover:bg-white/5"
            style={{ color: t.textMuted }}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>
    </div>
  );
}
