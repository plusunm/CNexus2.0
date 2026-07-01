/** Runtime-configurable endpoints + edition (single installer). */

import {
  parseEdition,
  resolveEdition,
  saveStoredEdition,
  setEdition,
  loadStoredEdition,
  type CnexusEdition,
} from "@/cnexus-kernel/edition";

let apiBase = ""; // relative / same-origin by default (personal edition)
let wsBase = ""; // WebSocket disabled in personal edition
let apiToken = "";
let configEdition: CnexusEdition | undefined;

const DEFAULT_GATEWAY_PORT = "7864";

export function getPersonalGatewayBase(): string {
  const port = process.env.NEXT_PUBLIC_CNEXUS_GATEWAY_PORT ?? DEFAULT_GATEWAY_PORT;
  return `http://127.0.0.1:${port}`.replace(/\/$/, "");
}

export function getApiToken(): string {
  return apiToken;
}

function isLocalHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "[::1]";
}

/** Tauri 2 desktop webview — not the Python gateway origin. */
export function isTauriWebviewHost(): boolean {
  if (typeof window === "undefined") return false;
  if ((window as Window & { __TAURI__?: unknown }).__TAURI__) return true;
  const host = window.location.hostname;
  return host === "tauri.localhost" || host.endsWith(".tauri.localhost");
}

/** When UI is opened via LAN IP, keep API on the same host (not 127.0.0.1). */
export function resolveApiBaseForBrowser(configured: string): string {
  if (isTauriWebviewHost()) {
    return getPersonalGatewayBase();
  }

  const trimmed = configured.replace(/\/$/, "");
  if (!trimmed) return "";
  if (typeof window === "undefined") return trimmed;

  try {
    const cfg = new URL(trimmed);
    const pageHost = window.location.hostname;
    if (isLocalHost(cfg.hostname) && !isLocalHost(pageHost)) {
      const port = cfg.port || window.location.port || DEFAULT_GATEWAY_PORT;
      const portSuffix = port ? `:${port}` : "";
      return `${window.location.protocol}//${pageHost}${portSuffix}`.replace(/\/$/, "");
    }
    return cfg.origin.replace(/\/$/, "");
  } catch {
    return window.location.origin.replace(/\/$/, "");
  }
}

export function getApiBase(): string {
  if (isTauriWebviewHost()) {
    return getPersonalGatewayBase();
  }
  if (apiBase) return apiBase;
  if (typeof window !== "undefined") {
    return window.location.origin.replace(/\/$/, "");
  }
  return getPersonalGatewayBase();
}

export function getWsBase(): string {
  if (wsBase) return wsBase;
  return getApiBase().replace(/^http/, "ws");
}

export function setCnexusEndpoints(nextApi: string, nextWs?: string): void {
  apiBase = resolveApiBaseForBrowser(nextApi);
  wsBase = (nextWs ?? getApiBase().replace(/^http/, "ws")).replace(/\/$/, "");
}

export function activateEnterpriseEdition(): void {
  // enterprise edition not available in personal build
  setEdition("personal");
  saveStoredEdition("personal");
}

/** Load cnexus-config.json — written by installer or Docker entrypoint. */
export async function initCnexusConfig(): Promise<void> {
  if (typeof window === "undefined") return;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3000);
  try {
    const res = await fetch("/cnexus-config.json", {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) return;
    const cfg = (await res.json()) as {
      edition?: string;
      apiBase?: string;
      wsBase?: string;
      apiToken?: string;
    };
    configEdition = parseEdition(cfg.edition);
    if (cfg.apiBase !== undefined) setCnexusEndpoints(cfg.apiBase, cfg.wsBase);
    if (cfg.apiToken) apiToken = cfg.apiToken;
  } catch {
    /* defaults: same-origin gateway or Tauri → 127.0.0.1:7864 */
  } finally {
    clearTimeout(timer);
    const edition = resolveEdition(configEdition, loadStoredEdition());
    setEdition(edition);
    if (!apiBase && edition === "personal") {
      setCnexusEndpoints(isTauriWebviewHost() ? getPersonalGatewayBase() : "");
    }
  }
}
