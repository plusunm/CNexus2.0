/** CNexus 2.0 personal float — labels and helpers (no enterprise Runtime/WS). */

import { isPersonalMode } from "./personalGuard";
import { getPersonalGatewayBase, isTauriWebviewHost } from "./cnexusConfig";

export const CNEXUS2_GATEWAY_PORT = "7864";

export function isFloatPersonalEdition(): boolean {
  return isPersonalMode();
}

export function gatewayEndpointLabel(): string {
  return `127.0.0.1:${CNEXUS2_GATEWAY_PORT} · HTTP`;
}

export function personalMainUiUrl(): string {
  if (isTauriWebviewHost()) {
    return `${getPersonalGatewayBase()}/`;
  }
  if (typeof window !== "undefined" && window.location.origin.startsWith("http")) {
    const port = window.location.port;
    if (port === "3000" || port === "1420") {
      return `${getPersonalGatewayBase()}/`;
    }
    return `${window.location.origin}/`;
  }
  return `${getPersonalGatewayBase()}/`;
}

/** Full observability / cognitive lab dashboard route (Tauri + static export). */
export function personalLabUiUrl(): string {
  return "/shell?layout=overview&view=debugger";
}
