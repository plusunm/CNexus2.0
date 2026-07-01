import { create } from "zustand";
import type { GatewayBootFaultCode, GatewayTier } from "./gatewayStatusTypes";

const DISMISS_MS = 30 * 60 * 1000;

type GatewayStatusState = {
  gatewayTier: GatewayTier;
  bootFaultCode: GatewayBootFaultCode | null;
  bootFaultDetail: string | null;
  featureNote: string | null;
  dismissedUntil: number;
  busy: boolean;
  reportBootFault: (code: GatewayBootFaultCode, detail?: string | null) => void;
  clearBootFault: () => void;
  setFeatureNote: (note: string | null) => void;
  syncFromRuntime: (snapshot: {
    operationalReady: boolean;
    reachable: boolean;
    bootReason?: string | null;
  }) => void;
  dismiss: (ms?: number) => void;
  setBusy: (busy: boolean) => void;
};

function tierFromRuntime(snapshot: {
  operationalReady: boolean;
  reachable: boolean;
}): GatewayTier {
  if (snapshot.operationalReady) return "healthy";
  if (snapshot.reachable) return "warming";
  return "offline";
}

export const useGatewayStatusStore = create<GatewayStatusState>((set, get) => ({
  gatewayTier: "unknown",
  bootFaultCode: null,
  bootFaultDetail: null,
  featureNote: null,
  dismissedUntil: 0,
  busy: false,

  reportBootFault: (code, detail = null) => {
    set({
      gatewayTier: "degraded",
      bootFaultCode: code,
      bootFaultDetail: detail,
      dismissedUntil: 0,
    });
  },

  clearBootFault: () => {
    set({ bootFaultCode: null, bootFaultDetail: null });
  },

  setFeatureNote: (note) => {
    const prev = get().featureNote;
    if (prev === note) return;
    set({ featureNote: note });
  },

  syncFromRuntime: (snapshot) => {
    const nextTier = tierFromRuntime(snapshot);
    const prev = get();

    if (nextTier === "healthy") {
      if (prev.gatewayTier === "healthy" && !prev.bootFaultCode && !prev.bootFaultDetail) {
        return;
      }
      set({
        gatewayTier: "healthy",
        bootFaultCode: null,
        bootFaultDetail: null,
      });
      return;
    }

    if (nextTier === "warming" && prev.gatewayTier === "degraded" && prev.bootFaultCode) {
      return;
    }

    const nextDetail = snapshot.bootReason ?? prev.bootFaultDetail;
    if (prev.gatewayTier === nextTier && prev.bootFaultDetail === nextDetail) {
      return;
    }

    set({
      gatewayTier: nextTier,
      bootFaultDetail: nextDetail,
    });
  },

  dismiss: (ms = DISMISS_MS) => {
    set({ dismissedUntil: Date.now() + ms });
  },

  setBusy: (busy) => {
    if (get().busy === busy) return;
    set({ busy });
  },
}));

/** Feature-layer hook (e.g. analyze fallback) — keeps gateway tier separate. */
export function reportGatewayFeatureNote(note: string | null): void {
  useGatewayStatusStore.getState().setFeatureNote(note);
}

export function reportGatewayBootFault(
  code: GatewayBootFaultCode,
  detail?: string | null,
): void {
  useGatewayStatusStore.getState().reportBootFault(code, detail ?? null);
}
