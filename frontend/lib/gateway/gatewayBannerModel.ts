import type { GatewayBootFaultCode, GatewayBannerModel, GatewayTier } from "./gatewayStatusTypes";
import { isPersonalMode } from "@/lib/personalGuard";
import { isTauriDesktop } from "@/lib/tauriDesktop";
import { bi, gatewayL } from "@/lib/spine/labels";

const HIDDEN_BANNER: GatewayBannerModel = {
  visible: false,
  severity: "info",
  title: "",
  message: "",
  canRestart: false,
  canRecheck: false,
};

function bootFaultTitle(code: GatewayBootFaultCode | null): string {
  switch (code) {
    case "bundle_missing":
      return bi(gatewayL.bootBundleMissingTitle);
    case "init_failed":
      return bi(gatewayL.bootInitFailedTitle);
    case "spawn_failed":
      return bi(gatewayL.bootSpawnFailedTitle);
    case "boot_timeout":
      return bi(gatewayL.bootTimeoutTitle);
    case "probe_failed":
      return bi(gatewayL.gatewayOfflineTitle);
    default:
      return bi(gatewayL.gatewayDegradedTitle);
  }
}

export function buildGatewayBannerModel(input: {
  gatewayTier: GatewayTier;
  bootFaultCode: GatewayBootFaultCode | null;
  bootFaultDetail: string | null;
  featureNote: string | null;
  dismissedUntil: number;
}): GatewayBannerModel {
  const { gatewayTier, bootFaultCode, bootFaultDetail, featureNote, dismissedUntil } = input;

  if (!isPersonalMode()) return HIDDEN_BANNER;
  if (Date.now() < dismissedUntil) return HIDDEN_BANNER;

  if (gatewayTier === "healthy" && featureNote) {
    return {
      visible: true,
      severity: "info",
      title: bi(gatewayL.analysisDegradedTitle),
      message: featureNote,
      canRestart: false,
      canRecheck: true,
    };
  }

  if (gatewayTier === "healthy" || gatewayTier === "unknown") {
    return HIDDEN_BANNER;
  }

  if (gatewayTier === "warming") {
    return {
      visible: true,
      severity: "info",
      title: bi(gatewayL.gatewayWarmingTitle),
      message: bootFaultDetail ?? bi(gatewayL.gatewayWarmingBody),
      canRestart: isTauriDesktop(),
      canRecheck: true,
    };
  }

  if (gatewayTier === "offline") {
    return {
      visible: true,
      severity: "critical",
      title: bi(gatewayL.gatewayOfflineTitle),
      message: isTauriDesktop()
        ? bi(gatewayL.gatewayOfflineBodyTauri)
        : bi(gatewayL.gatewayOfflineBodyBrowser),
      canRestart: isTauriDesktop(),
      canRecheck: true,
    };
  }

  return {
    visible: true,
    severity: "warning",
    title: bootFaultTitle(bootFaultCode),
    message: bootFaultDetail ?? bi(gatewayL.gatewayDegradedBody),
    canRestart: isTauriDesktop(),
    canRecheck: true,
  };
}
