"use client";

import { useCallback, useState } from "react";
import { cnexusProductApi } from "@/lib/api";
import { buildOfflineRelationshipAnalysis, isNetworkFetchError } from "@/lib/relationshipAnalysis/offlineAnalysis";
import { reportGatewayFeatureNote } from "@/lib/gateway/GatewayStatusStore";
import type { RelationshipAnalysis } from "@/lib/relationshipAnalysis";

function isDegradableAnalyzeError(err: unknown): boolean {
  if (isNetworkFetchError(err)) return true;
  if (!(err instanceof Error)) return false;
  if (err.name === "AbortError") return true;
  const msg = err.message.toLowerCase();
  return (
    msg.includes("converse failed") ||
    msg.includes("分析失败 (5") ||
    msg.includes("分析失败 (503") ||
    msg.includes("gateway") ||
    msg.includes("timeout")
  );
}

export function useRelationshipAnalysis() {
  const [result, setResult] = useState<RelationshipAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const analyze = useCallback(async (sourceInput: string) => {
    const text = sourceInput.trim();
    if (!text) return null;

    setLoading(true);
    setError(null);
    setWarning(null);
    setResult(null);
    reportGatewayFeatureNote(null);

    try {
      const analysis = await cnexusProductApi.analyzeRelationship(text, {
        fast: false,
        use_llm: true,
      });
      setResult(analysis);
      return analysis;
    } catch (deepErr) {
      if (!isDegradableAnalyzeError(deepErr)) {
        const message = deepErr instanceof Error ? deepErr.message : "分析失败";
        setError(message);
        return null;
      }

      try {
        const fast = await cnexusProductApi.analyzeRelationship(text, { fast: true });
        setResult(fast);
        const note = "深度思考未完成，已降级为快速规则分析。";
        setWarning(note);
        reportGatewayFeatureNote(note);
        return fast;
      } catch {
        const quick = buildOfflineRelationshipAnalysis(text);
        setResult(quick);
        const note = "网关未响应，当前为本地规则分析。";
        setWarning(note);
        reportGatewayFeatureNote(note);
        return quick;
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setWarning(null);
    reportGatewayFeatureNote(null);
  }, []);

  return { result, loading, error, warning, analyze, reset };
}
