"use client";

import { useEffect, useState } from "react";
import { brainApi } from "@/lib/api";
import { useMindTheme } from "./MindUiProvider";

export function RuntimeBootBadge() {
  const t = useMindTheme();
  const [status, setStatus] = useState<{
    boot_phase?: string;
    signature_verified?: boolean;
    ed25519_signed?: boolean;
    constitution_docs?: number;
    policy_docs?: number;
  } | null>(null);

  useEffect(() => {
    void brainApi.runtimeBootStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status?.boot_phase) return null;

  const ok = status.boot_phase === "conversation_ready" && status.signature_verified !== false;

  return (
    <span
      className="text-[10px] px-2 py-0.5 rounded-full border"
      style={{
        borderColor: ok ? "#34d399" : t.orange,
        color: ok ? "#34d399" : t.orange,
        backgroundColor: ok ? "rgba(52,211,153,0.08)" : "rgba(251,146,60,0.08)",
      }}
      title="Runtime BOOT · Constitution + Policy"
    >
      BOOT {status.boot_phase}
      {status.signature_verified ? " · signed" : ""}
      {status.ed25519_signed ? " · Ed25519" : ""}
      {typeof status.constitution_docs === "number"
        ? ` · C${status.constitution_docs}/P${status.policy_docs ?? 0}`
        : ""}
    </span>
  );
}
