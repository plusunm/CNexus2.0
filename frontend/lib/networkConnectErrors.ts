import { bi, navL } from "./spine/labels";

const CONNECT_ERROR_LABELS: Record<string, keyof typeof navL> = {
  no_viable_path: "networkErrorNoViablePath",
  missing_peer_id: "networkErrorMissingPeerId",
  connectivity_unavailable: "networkErrorConnectivityUnavailable",
  dht_unavailable: "networkErrorDhtUnavailable",
  firewall_blocked: "networkErrorFirewallBlocked",
  handshake_failed: "networkErrorHandshakeFailed",
};

const CONNECT_ERROR_HINTS: Record<string, keyof typeof navL> = {
  peer_offline: "networkErrorPeerOffline",
  host_unreachable: "networkErrorHostUnreachable",
};

/** Map backend connectivity error codes to bilingual user hints. */
export function humanizeNetworkConnectError(raw: string, extras?: { hint?: string }): string {
  const code = String(raw || "").trim().toLowerCase();
  const hintKey = extras?.hint ? CONNECT_ERROR_HINTS[String(extras.hint).trim()] : undefined;
  if (hintKey && navL[hintKey]) {
    return bi(navL[hintKey]);
  }
  const key = CONNECT_ERROR_LABELS[code];
  if (key && navL[key]) {
    return bi(navL[key]);
  }
  return raw;
}
