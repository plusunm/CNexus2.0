"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { cnexusProductApi, type InstallStatsStatus } from "@/lib/api";
import { useMindTheme } from "./MindUiProvider";
import { SbCard, SbSection } from "./second-brain/SbUIKit";

export function InstallStatsOptInPanel() {
  const t = useMindTheme();
  const [stats, setStats] = useState<InstallStatsStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setStats(await cnexusProductApi.fetchInstallStats());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const toggle = async () => {
    if (!stats?.configured) return;
    setBusy(true);
    setError("");
    try {
      const next = !stats.opt_in;
      const updated = await cnexusProductApi.setInstallStatsOptIn(next);
      setStats(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const envForced =
    stats?.opt_in_env === "1" || stats?.opt_in_env === "true" || stats?.opt_in_env === "yes";
  const enabled = Boolean(stats?.opt_in);

  return (
    <SbSection title="匿名安装统计" icon={BarChart3}>
      <SbCard padding="sm">
        <p className="text-xs leading-relaxed" style={{ color: t.textMuted }}>
          仅首次启动上报一次：版本、版本类型（edition）、随机 install_id。不上传记忆、聊天或设备公钥。
          需服务端配置 <code className="font-mono text-[10px]">CNEXUS_STATS_URL</code>。
        </p>

        {!stats?.configured ? (
          <p className="text-[11px] mt-2" style={{ color: t.textLight }}>
            当前未配置统计服务器（本地/内测可忽略）。
          </p>
        ) : (
          <div
            className="mt-3 flex items-center justify-between gap-3 px-2 py-2 rounded-lg border"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <div className="min-w-0">
              <p className="text-xs font-medium" style={{ color: t.text }}>
                {enabled ? "已参与匿名统计" : "不参与统计"}
              </p>
              <p className="text-[10px] mt-0.5 truncate" style={{ color: t.textMuted }}>
                {stats.first_ping_sent
                  ? `已上报 · ${stats.install_id_short ?? "—"}`
                  : enabled
                    ? "下次启动或开启时将上报"
                    : "关闭时不发送任何数据"}
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={enabled}
              disabled={busy || envForced}
              onClick={() => void toggle()}
              className="w-9 h-5 rounded-full relative shrink-0 disabled:opacity-50"
              style={{ backgroundColor: enabled ? "#14b8a6" : t.border }}
            >
              <span
                className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all"
                style={{ left: enabled ? "1.125rem" : "0.125rem" }}
              />
            </button>
          </div>
        )}

        {envForced ? (
          <p className="text-[10px] mt-2" style={{ color: t.textLight }}>
            已由环境变量 CNEXUS_STATS_OPT_IN 启用。
          </p>
        ) : null}
        {stats?.last_ping_error ? (
          <p className="text-[10px] mt-2" style={{ color: t.orange }}>
            上次上报失败：{stats.last_ping_error}
          </p>
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
