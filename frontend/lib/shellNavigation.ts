"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import type { OverviewView } from "@/cnexus-kernel/shellTypes";

/** Static export uses trailingSlash — full navigation avoids stale query params with client router. */
export function shellOverviewHref(view?: OverviewView): string {
  const base = "/shell/?layout=overview";
  if (!view || view === "learn") return base;
  return `${base}&view=${view}`;
}

export function useShellNavigation() {
  const router = useRouter();

  const navigateOverviewView = useCallback(
    (view: OverviewView) => {
      const href = shellOverviewHref(view);
      if (typeof window !== "undefined") {
        const current = `${window.location.pathname}${window.location.search}`;
        if (current !== href) {
          window.location.assign(href);
          return;
        }
      }
      router.push(href);
    },
    [router],
  );

  const navigateFlowAfterImport = useCallback(() => {
    navigateOverviewView("flow");
  }, [navigateOverviewView]);

  return {
    navigateOverviewView,
    navigateFlowAfterImport,
    /** @deprecated use navigateFlowAfterImport */
    navigateDebuggerAfterImport: navigateFlowAfterImport,
  };
}
