export type ConflictChatSeed = {
  blockId?: string;
  local?: string;
  remote?: string;
  synthesis?: string;
  status?: string;
  peerLabel?: string;
};

const STORAGE_KEY = "cnexus-conflict-chat-seed";

export function saveConflictChatSeed(seed: ConflictChatSeed): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(seed));
  } catch {
    /* ignore */
  }
}

export function consumeConflictChatSeed(): ConflictChatSeed | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(STORAGE_KEY);
    return JSON.parse(raw) as ConflictChatSeed;
  } catch {
    return null;
  }
}

export function buildConflictChatPrompt(seed: ConflictChatSeed): string {
  const lines = [
    "请基于以下协商冲突记忆对，以涌现模式帮我进一步反思与整合：",
    seed.peerLabel ? `对端：${seed.peerLabel}` : "",
    seed.blockId ? `block：${seed.blockId}` : "",
    `本地：${seed.local || "—"}`,
    `远端：${seed.remote || "—"}`,
    seed.synthesis ? `已有消解（${seed.status || "unknown"}）：${seed.synthesis}` : "",
    "请指出仍存在的认知张力，并给出可写入长期记忆的整合建议。",
  ].filter(Boolean);
  return lines.join("\n");
}

export function conflictChatWorkbenchHref(): string {
  return "/shell?layout=overview&view=workbench";
}
