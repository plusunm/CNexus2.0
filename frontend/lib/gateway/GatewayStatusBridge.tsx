"use client";

import { useEffect } from "react";
import { useMindStore } from "@/cnexus-kernel";
import { useGatewayStatusStore } from "./GatewayStatusStore";

/** Subscribes MindStore runtime gates into GatewayStatusStore — no UI. */
export function GatewayStatusBridge() {
  const syncFromRuntime = useGatewayStatusStore((s) => s.syncFromRuntime);

  useEffect(() => {
    const sync = () => {
      const state = useMindStore.getState();
      syncFromRuntime({
        operationalReady: state.runtimeOperationalReady,
        reachable: state.runtimeReachable,
        bootReason: state.runtimeBootReason,
      });
    };

    sync();
    return useMindStore.subscribe(sync);
  }, [syncFromRuntime]);

  useEffect(() => {
    const id = window.setInterval(() => {
      void useMindStore.getState().syncSystemCapability();
    }, 4000);
    return () => window.clearInterval(id);
  }, []);

  return null;
}
