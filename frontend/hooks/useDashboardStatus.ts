"use client";

import { useCallback, useEffect, useState } from "react";
import { cnexusProductApi } from "@/lib/api";
import type { DashboardStatus } from "@/lib/dashboardTypes";

const POLL_MS = 5_000;

export function useDashboardStatus(enabled = true) {
  const [data, setData] = useState<DashboardStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const row = await cnexusProductApi.fetchDashboardStatus();
      setData(row);
      setError(row.ok === false ? row.error || "dashboard_unavailable" : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [enabled, refresh]);

  return { data, loading, error, refresh };
};
