/** Personal static edition — hard isolation from enterprise WS / cluster features. */

import { getEdition } from "@/cnexus-kernel/edition";

export function isPersonalMode(): boolean {
  const mode = process.env.NEXT_PUBLIC_APP_MODE;
  if (mode === "personal") return true;
  if (mode === "enterprise") return false;
  return getEdition() === "personal";
}

export function isWebSocketEnabled(): boolean {
  if (isPersonalMode()) return false;
  const raw = process.env.NEXT_PUBLIC_ENABLE_WS;
  return raw !== "false" && raw !== "0";
}

/** Suppress enterprise "无法连接 Runtime" UX in personal static builds. */
export function shouldSuppressRuntimeConnectError(): boolean {
  return isPersonalMode();
}
