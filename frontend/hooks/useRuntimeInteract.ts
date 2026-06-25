"use client";

import { useMemo } from "react";
import { useMindConnection, useMindOverview } from "@/cnexus-kernel";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { useOptionalFloatRuntimeMonitorContext } from "@/components/mind/floating/FloatRuntimeMonitorContext";
import { resolveRuntimeConnectionDisplay } from "@/lib/runtimeConnection";
import { isPersonalMode } from "@/lib/personalGuard";
import { bi, navL } from "@/lib/spine/labels";

/** Microsoft-style runtime gate — single source for disable/hint across float + main shell. */
export function useRuntimeInteract() {
  const { effectiveMode } = useMindConnection();
  const { isDemo, isLive, isWarming, isReachable, isFallback, canUploadDocuments } = useMindOverview();
  const monitor = useOptionalFloatRuntimeMonitorContext();
  const operationalReady = useMindStore((s) => s.runtimeOperationalReady);
  const capabilities = useMindStore((s) => s.runtimeCapabilities);

  const connection = useMemo(
    () =>
      resolveRuntimeConnectionDisplay({
        effectiveMode,
        isLive,
        isWarming,
        isDemo,
        monitorPhase: monitor?.phase ?? null,
        operationalReady,
        capabilities,
      }),
    [effectiveMode, isDemo, isLive, isWarming, monitor?.phase, operationalReady, capabilities],
  );

  const personalRuntime = isPersonalMode() && effectiveMode === "runtime";
  const canUpload = isDemo || canUploadDocuments || connection.canUseRuntimeApi || personalRuntime;
  const canChat = isDemo || connection.canUseRuntimeApi || (personalRuntime && (isLive || isReachable));

  const uploadStatusHint = useMemo(() => {
    if (isDemo) return null;
    if (canUpload) return null;
    if (personalRuntime) return "未连接本地网关 — 请运行 start_cnexus.bat";
    if (isFallback || effectiveMode === "fallback") return "当前为离线模式，上传需连接 Gateway";
    if (isWarming || isReachable) return "正在唤醒核心，Gateway 暂不可用";
    return bi(navL.workbenchOffline);
  }, [isDemo, canUpload, personalRuntime, isFallback, effectiveMode, isWarming, isReachable]);

  const isConnecting =
    monitor?.isChecking === true ||
    monitor?.phase === "checking" ||
    (effectiveMode === "runtime" && isWarming && !isLive);

  const statusHint = useMemo(() => {
    if (isDemo) return null;
    if (isLive) return null;
    if (personalRuntime) {
      if (isReachable) return "网关繁忙，正在处理请求…";
      return "未连接本地网关 — 请运行 start_cnexus.bat";
    }
    if (isFallback || effectiveMode === "fallback") return bi(navL.workbenchOffline);
    if (isWarming || isReachable || monitor?.isWarming || isConnecting) return bi(navL.workbenchWarming);
    return bi(navL.workbenchOffline);
  }, [
    isDemo,
    isLive,
    isFallback,
    effectiveMode,
    isWarming,
    isReachable,
    monitor?.isWarming,
    isConnecting,
    personalRuntime,
  ]);

  return {
    canChat,
    canUpload,
    canInteract: canChat,
    connection,
    statusHint,
    uploadStatusHint,
    isWarming: !isDemo && effectiveMode === "runtime" && !canChat && (isWarming || monitor?.isWarming),
    isConnecting,
    isLive,
    isDemo,
    phase: connection.phase,
  };
}
