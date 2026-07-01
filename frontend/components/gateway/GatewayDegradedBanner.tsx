"use client";

import { useCallback } from "react";
import { AlertTriangle, BookOpen, Loader2, RotateCcw, X } from "lucide-react";
import { useMindStore } from "@/cnexus-kernel";
import { useGatewayStatusStore } from "@/lib/gateway/GatewayStatusStore";
import { useGatewayBanner } from "@/lib/gateway/useGatewayBanner";
import { bi, gatewayL } from "@/lib/spine/labels";
import { isTauriDesktop, restartRuntimeGateway } from "@/lib/tauriDesktop";
import { openPersonalHelpGuide } from "@/components/help/PersonalHelpModal";
import { useOptionalFloatRuntimeMonitorContext } from "@/components/mind/floating/FloatRuntimeMonitorContext";

type Props = {
  /** compact = float bar strip; root = desktop shell overlay */
  variant?: "compact" | "root";
};

const SEVERITY_STYLES = {
  info: {
    bg: "rgba(59, 130, 246, 0.12)",
    border: "rgba(59, 130, 246, 0.45)",
    text: "#93c5fd",
    icon: "#60a5fa",
  },
  warning: {
    bg: "rgba(245, 158, 11, 0.14)",
    border: "rgba(245, 158, 11, 0.5)",
    text: "#fcd34d",
    icon: "#fbbf24",
  },
  critical: {
    bg: "rgba(239, 68, 68, 0.14)",
    border: "rgba(239, 68, 68, 0.5)",
    text: "#fca5a5",
    icon: "#f87171",
  },
} as const;

export function GatewayDegradedBanner({ variant = "root" }: Props) {
  const banner = useGatewayBanner();
  const busy = useGatewayStatusStore((s) => s.busy);
  const dismiss = useGatewayStatusStore((s) => s.dismiss);
  const setBusy = useGatewayStatusStore((s) => s.setBusy);
  const setFeatureNote = useGatewayStatusStore((s) => s.setFeatureNote);
  const monitor = useOptionalFloatRuntimeMonitorContext();

  const recheck = useCallback(async () => {
    setBusy(true);
    try {
      if (monitor) {
        await monitor.runProbe();
      } else {
        await useMindStore.getState().syncSystemCapability();
      }
    } finally {
      setBusy(false);
    }
  }, [monitor, setBusy]);

  const restart = useCallback(async () => {
    if (!isTauriDesktop()) return;
    setBusy(true);
    try {
      await restartRuntimeGateway();
      await new Promise((resolve) => window.setTimeout(resolve, 2500));
      await recheck();
    } finally {
      setBusy(false);
    }
  }, [recheck, setBusy]);

  if (!banner.visible) return null;

  const palette = SEVERITY_STYLES[banner.severity];
  const compact = variant === "compact";

  return (
    <div
      className={
        compact
          ? "shrink-0 border-b px-2.5 py-2"
          : "sticky top-0 z-30 px-3 py-2.5"
      }
      style={{
        backgroundColor: palette.bg,
        borderColor: palette.border,
        borderBottomWidth: compact ? 1 : 0,
        borderBottomStyle: "solid",
        boxShadow: compact ? undefined : "0 8px 24px rgba(0,0,0,0.35)",
      }}
      role="status"
      aria-live="polite"
      data-cnexus-gateway-banner={banner.severity}
    >
      <div className={`flex items-start gap-2 ${compact ? "text-[11px]" : "text-xs"}`}>
        <AlertTriangle
          className={`shrink-0 mt-0.5 ${compact ? "w-3.5 h-3.5" : "w-4 h-4"}`}
          style={{ color: palette.icon }}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <p className="font-medium leading-snug" style={{ color: palette.text }}>
            {banner.title}
          </p>
          <p className="mt-0.5 leading-relaxed opacity-90" style={{ color: palette.text }}>
            {banner.message}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {banner.canRestart && (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium disabled:opacity-60"
                style={{ backgroundColor: "rgba(255,255,255,0.12)", color: palette.text }}
                disabled={busy}
                onClick={() => void restart()}
              >
                {busy ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RotateCcw className="w-3 h-3" />
                )}
                {bi(gatewayL.restartGateway)}
              </button>
            )}
            {banner.canRecheck && (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium disabled:opacity-60"
                style={{ backgroundColor: "rgba(255,255,255,0.08)", color: palette.text }}
                disabled={busy}
                onClick={() => void recheck()}
              >
                {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                {bi(gatewayL.recheckGateway)}
              </button>
            )}
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium"
              style={{ backgroundColor: "rgba(255,255,255,0.08)", color: palette.text }}
              onClick={() => openPersonalHelpGuide()}
            >
              <BookOpen className="w-3 h-3" />
              {bi(gatewayL.openHelpGuide)}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 opacity-80 hover:opacity-100"
              style={{ color: palette.text }}
              onClick={() => {
                dismiss();
                if (banner.severity === "info") setFeatureNote(null);
              }}
            >
              {bi(gatewayL.dismissBannerAck)}
            </button>
          </div>
        </div>
        <button
          type="button"
          className="shrink-0 p-0.5 rounded opacity-70 hover:opacity-100"
          style={{ color: palette.text }}
          aria-label={bi(gatewayL.dismissBannerAck)}
          onClick={() => {
            dismiss();
            if (banner.severity === "info") setFeatureNote(null);
          }}
        >
          <X className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
        </button>
      </div>
    </div>
  );
}
