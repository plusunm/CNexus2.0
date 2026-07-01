import { useMemo } from "react";
import { buildGatewayBannerModel } from "./gatewayBannerModel";
import { useGatewayStatusStore } from "./GatewayStatusStore";

export function useGatewayBanner() {
  const gatewayTier = useGatewayStatusStore((s) => s.gatewayTier);
  const bootFaultCode = useGatewayStatusStore((s) => s.bootFaultCode);
  const bootFaultDetail = useGatewayStatusStore((s) => s.bootFaultDetail);
  const featureNote = useGatewayStatusStore((s) => s.featureNote);
  const dismissedUntil = useGatewayStatusStore((s) => s.dismissedUntil);

  return useMemo(
    () =>
      buildGatewayBannerModel({
        gatewayTier,
        bootFaultCode,
        bootFaultDetail,
        featureNote,
        dismissedUntil,
      }),
    [gatewayTier, bootFaultCode, bootFaultDetail, featureNote, dismissedUntil],
  );
}
