"use client";

import { useCallback, useEffect, useState } from "react";
import { cnexusProductApi } from "@/lib/api";

function peerIdsFromRegistry(peers: Record<string, Record<string, unknown>>): Set<string> {
  const out = new Set<string>();
  for (const [pubkey, row] of Object.entries(peers)) {
    const status = String(row.status ?? "").trim();
    if (status === "trusted" || status === "online") out.add(pubkey);
  }
  return out;
}

/** Trusted peer pubkeys for group-memory scope filtering. */
export function useTrustedPeerIds(refreshMs = 30_000): Set<string> {
  const [trusted, setTrusted] = useState<Set<string>>(() => new Set());

  const refresh = useCallback(async () => {
    try {
      const peers = await cnexusProductApi.fetchNetworkPeers();
      setTrusted(peerIdsFromRegistry(peers));
    } catch {
      setTrusted(new Set());
    }
  }, []);

  useEffect(() => {
    void refresh();
    if (refreshMs <= 0) return;
    const id = window.setInterval(() => void refresh(), refreshMs);
    return () => window.clearInterval(id);
  }, [refresh, refreshMs]);

  return trusted;
}
