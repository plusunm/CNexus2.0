/** Gateway health / degradation signals for Personal GA UX. */

export type GatewayTier = "unknown" | "healthy" | "warming" | "offline" | "degraded";

export type GatewayBootFaultCode =
  | "boot_timeout"
  | "bundle_missing"
  | "init_failed"
  | "spawn_failed"
  | "probe_failed"
  | "unknown";

export type GatewayBannerSeverity = "info" | "warning" | "critical";

export type GatewayBannerModel = {
  visible: boolean;
  severity: GatewayBannerSeverity;
  title: string;
  message: string;
  canRestart: boolean;
  canRecheck: boolean;
};
