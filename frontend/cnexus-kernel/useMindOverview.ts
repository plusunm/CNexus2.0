"use client";



import { useMemo } from "react";

import { useMindConnection } from "./MindConnectionProvider";

import { extractMindSignals } from "./MindOverviewContract";

import { useMindStore } from "./MindStore";

import type { MindOverview } from "@/lib/runtimeTypes";

import type { MindSignals } from "./MindOverviewContract";

import type { EffectiveConnectionMode } from "./connectionMode";



/**

 * Connection SSOT for all UI:

 * - isReachable: Gateway HTTP 200 / gateway alive

 * - isLive: operational_ready === true only

 * - isWarming: reachable && !live

 */

export function useMindOverview() {

  const { effectiveMode, preference } = useMindConnection();

  const runtimeState = useMindStore((s) => s.runtimeState);

  const runtimeLogs = useMindStore((s) => s.runtimeLogs);

  const runtimeReachable = useMindStore((s) => s.runtimeReachable);

  const runtimeOperationalReady = useMindStore((s) => s.runtimeOperationalReady);

  const overview = useMindStore((s) => s.getOverview());



  const signals = useMemo(

    () => extractMindSignals(overview, effectiveMode),

    [overview, effectiveMode],

  );



  const inRuntimeMode = effectiveMode === "runtime";

  const isReachable = inRuntimeMode && runtimeReachable;

  const isLive = inRuntimeMode && runtimeOperationalReady;

  const isWarming = isReachable && !isLive;

  const canUploadDocuments = effectiveMode === "demo" || isReachable;

  const canWriteMemory =

    effectiveMode === "demo" || (inRuntimeMode && runtimeOperationalReady);



  return {

    overview,

    signals,

    source: effectiveMode as EffectiveConnectionMode,

    preference,

    isDemo: effectiveMode === "demo",

    isReachable,

    isLive,

    isWarming,

    canUploadDocuments,

    canWriteMemory,

    isFallback: effectiveMode === "fallback",

    runtimeState: effectiveMode === "demo" ? null : runtimeState,

    runtimeLogs: effectiveMode === "demo" ? [] : runtimeLogs,

  };

}

export type { MindOverview, MindSignals };

