/** Personal edition help doc + log folder helpers. */

import { isTauriDesktop } from "@/lib/tauriDesktop";

export const PERSONAL_HELP_DOC_URL = "/help/cnexus-personal-troubleshooting.md";

export const PERSONAL_DATA_DIR_HINT =
  typeof window !== "undefined" && window.navigator?.platform?.toLowerCase().includes("win")
    ? "%LOCALAPPDATA%\\CNexus\\data"
    : "~/.cnexus/data";

export async function fetchPersonalHelpMarkdown(): Promise<string> {
  const res = await fetch(PERSONAL_HELP_DOC_URL, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`无法加载帮助文档 (${res.status})`);
  }
  return res.text();
}

export async function openPersonalDataDir(): Promise<void> {
  if (isTauriDesktop()) {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("open_personal_data_dir");
    return;
  }
  window.alert(`日志目录：${PERSONAL_DATA_DIR_HINT}`);
}
