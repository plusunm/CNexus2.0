/**
 * Thinking tab — deep gateway analyze (converse + LLM), fast/offline fallback.
 */

import { cnexusProductApi } from "@/lib/api";
import type { RelationshipAnalysis } from "./types/relationship";
import { buildOfflineRelationshipAnalysis, isNetworkFetchError } from "./offlineAnalysis";

export type AnalyzeRelationshipResult = {
  analysis: RelationshipAnalysis;
  mode: "deep" | "fast" | "offline";
  warning?: string;
};

function isRetriableError(err: unknown): boolean {
  return isNetworkFetchError(err) || (err instanceof Error && err.name === "AbortError");
}

export async function analyzeRelationshipHybrid(
  sourceInput: string,
): Promise<AnalyzeRelationshipResult> {
  const text = sourceInput.trim();
  if (!text) throw new Error("请输入要分析的问题");

  try {
    const analysis = await cnexusProductApi.analyzeRelationship(text, {
      fast: false,
      use_llm: true,
    });
    return { analysis, mode: "deep" };
  } catch (deepErr) {
    if (!isRetriableError(deepErr)) throw deepErr;

    try {
      const analysis = await cnexusProductApi.analyzeRelationship(text, { fast: true });
      return {
        analysis,
        mode: "fast",
        warning: "深度思考超时或不可用，已降级为快速规则分析。",
      };
    } catch {
      return {
        analysis: buildOfflineRelationshipAnalysis(text),
        mode: "offline",
        warning: "网关未响应，已使用本地规则分析。",
      };
    }
  }
}
