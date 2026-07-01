export type BootstrapPeer = {
  pubkey: string;
  host: string;
  label?: string;
};

let cached: BootstrapPeer[] | null = null;

export async function loadBootstrapPeers(): Promise<BootstrapPeer[]> {
  if (cached) return cached;
  try {
    const resp = await fetch("/cnexus-config.json", { cache: "no-store" });
    if (!resp.ok) return [];
    const data = (await resp.json()) as { bootstrapPeers?: BootstrapPeer[] };
    cached = Array.isArray(data.bootstrapPeers) ? data.bootstrapPeers : [];
  } catch {
    cached = [];
  }
  return cached;
}

export function bootstrapHostForPubkey(peers: BootstrapPeer[], pubkey: string): string {
  const needle = pubkey.trim().toLowerCase();
  const row = peers.find((p) => p.pubkey.trim().toLowerCase() === needle);
  return row?.host?.trim() || "";
}
