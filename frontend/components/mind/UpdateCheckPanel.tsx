"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Sparkles } from "lucide-react";
import { cnexusProductApi, type UpdateCheckStatus } from "@/lib/api";
import { useMindTheme } from "./MindUiProvider";
import { SbCard, SbSection } from "./second-brain/SbUIKit";

export function UpdateCheckPanel() {
  const t = useMindTheme();
  const [status, setStatus] = useState<UpdateCheckStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async (force = false) => {
    setBusy(true);
    setError("");
    try {
      setStatus(await cnexusProductApi.fetchUpdateCheck(force));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void refresh(false);
  }, [refresh]);

  const disabled = status?.enabled === false;

  return (
    <SbSection title="版本更新" icon={Sparkles}>
      <SbCard padding="sm">
        <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
          启动时会向 GitHub Releases 查询是否有新版本（默认每 6 小时缓存一次）。仅对比版本号，不上传任何本地数据。
        </p>

        <div
          className="mt-3 flex items-center justify-between gap-3 px-2 py-2 rounded-lg border"
          style={{ borderColor: t.border, backgroundColor: t.chatBg }}
        >
          <div className="min-w-0">
            <p className="text-xs font-medium" style={{ color: t.text }}>
              当前 {status?.current_version || "—"}
              {status?.latest_version ? ` · 最新 ${status.latest_version}` : ""}
            </p>
            <p className="text-[10px] mt-0.5" style={{ color: t.textMuted }}>
              {disabled
                ? "已由 CNEXUS_UPDATE_CHECK=0 关闭"
                : status?.update_available
                  ? "有新版本可下载"
                  : status?.error
                    ? `查询失败：${status.error}`
                    : "已是最新版本"}
            </p>
          </div>
          <button
            type="button"
            disabled={busy || disabled}
            onClick={() => void refresh(true)}
            className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
          >
            <RefreshCw className={`w-3 h-3 ${busy ? "animate-spin" : ""}`} />
            检查更新
          </button>
        </div>

        {status?.update_available && status.release_url ? (
          <a
            href={status.release_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex mt-2 text-[11px] font-medium underline-offset-2 hover:underline"
            style={{ color: "#14b8a6" }}
          >
            打开 GitHub 发布页
          </a>
        ) : null}

        {error ? (
          <p className="text-[10px] mt-2" style={{ color: t.orange }}>
            {error}
          </p>
        ) : null}
      </SbCard>
    </SbSection>
  );
}
