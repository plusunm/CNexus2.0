"use client";

import { useCallback, useEffect, useState } from "react";
import { cnexusProductApi, type UpdateCheckStatus } from "@/lib/api";

const DISMISS_KEY = "cnexus-update-dismissed";

export function useUpdateCheck(active: boolean) {
  const [status, setStatus] = useState<UpdateCheckStatus | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async (force = false) => {
    if (!active) return null;
    setLoading(true);
    try {
      const data = await cnexusProductApi.fetchUpdateCheck(force);
      setStatus(data);
      const latest = String(data.latest_version || "");
      if (latest && typeof window !== "undefined") {
        setDismissed(window.localStorage.getItem(DISMISS_KEY) === latest);
      }
      return data;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, [active]);

  useEffect(() => {
    if (!active) return;
    void refresh(false);
  }, [active, refresh]);

  const dismiss = useCallback(() => {
    const latest = String(status?.latest_version || "");
    if (latest && typeof window !== "undefined") {
      window.localStorage.setItem(DISMISS_KEY, latest);
    }
    setDismissed(true);
  }, [status?.latest_version]);

  const showBanner =
    Boolean(status?.enabled !== false && status?.update_available && status?.latest_version) && !dismissed;

  return {
    status,
    loading,
    showBanner,
    dismiss,
    refresh,
  };
}
