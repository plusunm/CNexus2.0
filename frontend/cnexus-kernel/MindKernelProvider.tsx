"use client";

import { useEffect } from "react";
import { MindConnectionProvider } from "./MindConnectionProvider";
import { MindRuntimeBridge } from "./MindRuntimeBridge";
import { MindUiProvider } from "@/components/mind/MindUiProvider";
import { ExperienceProvider } from "@/lib/cognitive";
import {
  bootstrapRuntimeReachabilityFromDisk,
  ensureRuntimeReachabilityBus,
  setBootSessionId,
} from "./runtimeReachabilityStore";
import { isTauriDesktop, listenBootSession } from "@/lib/tauriDesktop";

if (typeof window !== "undefined") {
  ensureRuntimeReachabilityBus();
  bootstrapRuntimeReachabilityFromDisk();
}

function BootSessionListener() {
  useEffect(() => {
    if (!isTauriDesktop()) return;
    let unlisten: (() => void) | undefined;
    void listenBootSession((id) => {
      setBootSessionId(id);
      bootstrapRuntimeReachabilityFromDisk();
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, []);
  return null;
}

/** Product Kernel provider stack — all shells mount this once. */
export function MindKernelProvider({ children }: { children: React.ReactNode }) {
  return (
    <MindConnectionProvider>
      <BootSessionListener />
      <MindRuntimeBridge>
        <MindUiProvider>
          <ExperienceProvider>{children}</ExperienceProvider>
        </MindUiProvider>
      </MindRuntimeBridge>
    </MindConnectionProvider>
  );
}
