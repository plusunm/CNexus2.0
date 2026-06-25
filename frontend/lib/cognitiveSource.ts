import type { EffectiveConnectionMode } from "@/cnexus-kernel";
import { isPersonalMode } from "@/lib/personalGuard";
import {
  resolveRuntimeConnectionDisplay,
  type RuntimeConnectionDisplay,
} from "@/lib/runtimeConnection";

export type CognitiveSourceMeta = {
  mode: EffectiveConnectionMode;
  label: string;
  description: string;
  badgeColor: "purple" | "blue" | "orange" | "red";
  isLive: boolean;
  isExample: boolean;
};

export function getCognitiveSourceMeta(
  mode: EffectiveConnectionMode,
  connection?: Pick<RuntimeConnectionDisplay, "badgeLabel" | "badgeColor" | "phase" | "canUseRuntimeApi">,
): CognitiveSourceMeta {
  if (isPersonalMode()) {
    const live = connection?.phase === "live";
    const warming = connection?.phase === "warming";
    if (mode === "demo") {
      return {
        mode,
        label: "演示",
        description: "演示模式在个人版中不可用",
        badgeColor: "orange",
        isLive: false,
        isExample: true,
      };
    }
    return {
      mode: mode === "fallback" ? "fallback" : "runtime",
      label: live ? "本地网关" : warming ? "网关就绪中" : "CNexus 2.0",
      description: live
        ? "个人版认知内核 · 记忆与对话经本地网关"
        : warming
          ? "本地网关已启动，正在同步状态…"
          : "未连接本地网关 — 请运行 start_cnexus.bat",
      badgeColor: live ? "blue" : "orange",
      isLive: live,
      isExample: false,
    };
  }

  switch (mode) {
    case "demo":
      return {
        mode,
        label: "演示示例",
        description: "以下为 UI 示例数据，用于预览布局与交互，不代表真实运行结论",
        badgeColor: "purple",
        isLive: false,
        isExample: true,
      };
    case "runtime":
      return {
        mode,
        label: connection?.badgeLabel ?? "Runtime 实时",
        description:
          connection?.phase === "warming"
            ? connection?.canUseRuntimeApi
              ? "核心部分就绪 — 上传已可用，对话部分开放"
              : "正在唤醒核心…对话就绪后开放；文档上传经 Gateway 可用"
            : connection?.phase === "live"
              ? "来自本地 Runtime 的运行历史压缩，随使用更新"
              : "正在连接本地 Runtime（127.0.0.1:8000）",
        badgeColor: connection?.badgeColor ?? "blue",
        isLive: connection?.phase === "live",
        isExample: false,
      };
    case "fallback":
      return {
        mode,
        label: "未连接 Runtime",
        description: "Runtime API 不可达 — 请在本机启动 Runtime（127.0.0.1:8000）",
        badgeColor: "orange",
        isLive: false,
        isExample: false,
      };
  }
}

export function getCognitiveSourceMetaForRuntime(input: {
  effectiveMode: EffectiveConnectionMode;
  isLive: boolean;
  isWarming: boolean;
  isDemo: boolean;
  monitorPhase?: import("@/hooks/useFloatRuntimeMonitor").RuntimeConnectionPhase | null;
}): CognitiveSourceMeta {
  const display = resolveRuntimeConnectionDisplay(input);
  return getCognitiveSourceMeta(input.effectiveMode, display);
}

export function formatGeneratedAt(iso?: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso.slice(0, 16);
  }
}
