"use client";

import { useState } from "react";
import { isRuntimeReady } from "@/lib/api";
import { floatTy } from "@/lib/floatTypography";
import { useMindTheme } from "../MindUiProvider";
import {
  applyLlmProviderDefaults,
  DEEPSEEK_MODEL_OPTIONS,
  DEEPSEEK_OPENAI_BASE_URL,
  LLM_UI_PROVIDER_OPTIONS,
  llmFieldHints,
  loadDingTalkConfig,
  loadLlmQuickConfig,
  normalizeDeepseekModel,
  normalizeLlmQuickConfig,
  saveDingTalkConfig,
  saveLlmQuickConfig,
  syncLlmQuickConfigToRuntime,
  type DingTalkConfig,
  type LlmQuickConfig,
} from "@/lib/floatIntegrations";
import { applyLlmSyncToStore } from "@/lib/personalChatModel";
import { useMindStore } from "@/cnexus-kernel";
import { FloatingMiniDialog } from "./FloatingMiniDialog";
import { FloatSelect } from "./FloatSelect";
import { isTauriDesktop } from "@/lib/tauriDesktop";
import { isPersonalMode } from "@/lib/personalGuard";

type DialogKind = "dingtalk" | "llm";

type Props = {
  kind: DialogKind;
  onClose: () => void;
  isDemo: boolean;
};

function fieldClass(t: ReturnType<typeof useMindTheme>) {
  return `w-full border rounded-lg px-2.5 py-2 ${floatTy.input} outline-none focus:ring-1`;
}

function fieldStyle(t: ReturnType<typeof useMindTheme>): React.CSSProperties {
  return { borderColor: t.border, backgroundColor: t.surface, color: t.text };
}

export function FloatingIntegrationDialogs({ kind, onClose, isDemo }: Props) {
  const t = useMindTheme();
  const [dingtalk, setDingtalk] = useState<DingTalkConfig>(() => loadDingTalkConfig());
  const [llm, setLlm] = useState<LlmQuickConfig>(() => loadLlmQuickConfig());
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const llmHints = llmFieldHints(llm.provider);

  const saveDingtalk = () => {
    saveDingTalkConfig(dingtalk);
    setStatus("钉钉配置已保存");
  };

  const saveLlm = async () => {
    const normalized = normalizeLlmQuickConfig(llm);
    const isOllama =
      normalized.provider === "ollama" ||
      normalized.baseUrl.includes("localhost:11434") ||
      normalized.baseUrl.includes("127.0.0.1:11434");
    if (!normalized.apiKey.trim() && !isOllama) {
      setStatus("请填写 API Key，或选择 Ollama 本地");
      return;
    }
    setLlm(normalized);
    saveLlmQuickConfig(normalized);
    setBusy(true);
    setStatus(null);
    try {
      const online = await isRuntimeReady({ skipWs: true });
      if (online) {
        const result = await syncLlmQuickConfigToRuntime();
        await applyLlmSyncToStore(result);
        if (result.ok && result.modelId) {
          if (result.modelId === "ollama-local") {
            setStatus(result.testOk ? "已切换为 Ollama 本地" : "已同步 Ollama — 请确认本机 Ollama 已启动");
          }
        }
        if (!result.ok) {
          setStatus(result.error || (isPersonalMode() ? "已保存本地，同步网关失败" : "已保存本地，同步 Runtime 失败"));
          return;
        }
      } else {
        setStatus(
          isPersonalMode()
            ? "已保存本地 — 网关离线，请先运行 start_cnexus.bat"
            : "已保存本地 — Runtime 离线，下次连接后自动生效",
        );
      }
      onClose();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  };

  if (kind === "dingtalk") {
    return (
      <FloatingMiniDialog
        title="钉钉通知配置"
        subtitle="机器人 Webhook · 本地保存"
        onClose={onClose}
        placement={isTauriDesktop() ? "panel" : "portal"}
      >
        <div className={`space-y-3 ${floatTy.body}`}>
          <label className="flex items-center gap-2" style={{ color: t.text }}>
            <input
              type="checkbox"
              checked={dingtalk.enabled}
              onChange={(e) => setDingtalk((c) => ({ ...c, enabled: e.target.checked }))}
            />
            启用钉钉通知
          </label>
          <label className="flex flex-col gap-1">
            <span style={{ color: t.textMuted }}>Webhook 地址</span>
            <input
              className={fieldClass(t)}
              style={fieldStyle(t)}
              placeholder="https://oapi.dingtalk.com/robot/send?access_token=..."
              value={dingtalk.webhook}
              onChange={(e) => setDingtalk((c) => ({ ...c, webhook: e.target.value }))}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span style={{ color: t.textMuted }}>加签 Secret（可选）</span>
            <input
              className={fieldClass(t)}
              style={fieldStyle(t)}
              placeholder="SEC..."
              value={dingtalk.secret}
              onChange={(e) => setDingtalk((c) => ({ ...c, secret: e.target.value }))}
            />
          </label>
          <div className="space-y-1.5" style={{ color: t.textMuted }}>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={dingtalk.notifyOnCapture}
                onChange={(e) => setDingtalk((c) => ({ ...c, notifyOnCapture: e.target.checked }))}
              />
              记忆导入时通知
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={dingtalk.notifyOnConflict}
                onChange={(e) => setDingtalk((c) => ({ ...c, notifyOnConflict: e.target.checked }))}
              />
              冲突告警时通知
            </label>
          </div>
          <button
            type="button"
            className={`w-full py-2 rounded-lg text-white ${floatTy.btn}`}
            style={{ backgroundColor: t.green }}
            onClick={saveDingtalk}
          >
            保存
          </button>
          {status && (
            <p className={floatTy.caption} style={{ color: t.textMuted }}>
              {status}
            </p>
          )}
        </div>
      </FloatingMiniDialog>
    );
  }

  return (
    <FloatingMiniDialog
      title={isPersonalMode() ? "大模型配置" : "大模型 API"}
      subtitle={isPersonalMode() ? "Ollama 本地或云端 API · 同步至网关" : "Provider · Base URL · API Key"}
      onClose={onClose}
      placement={isTauriDesktop() ? "panel" : "portal"}
      width={340}
    >
      <div className={`space-y-3 ${floatTy.body}`}>
        <label className="flex flex-col gap-1">
          <span style={{ color: t.textMuted }}>显示名称</span>
          <input
            className={fieldClass(t)}
            style={fieldStyle(t)}
            value={llm.label}
            onChange={(e) => setLlm((c) => ({ ...c, label: e.target.value }))}
          />
        </label>
        <FloatSelect
          label="Provider"
          value={llm.provider}
          menuPortal
          options={LLM_UI_PROVIDER_OPTIONS}
          onChange={(provider) => {
            setLlm(applyLlmProviderDefaults(provider));
            setStatus(null);
          }}
        />
        <label className="flex flex-col gap-1">
          <span style={{ color: t.textMuted }}>Base URL</span>
          <input
            className={fieldClass(t)}
            style={fieldStyle(t)}
            placeholder={llmHints.baseUrl}
            value={llm.baseUrl}
            onChange={(e) => setLlm((c) => ({ ...c, baseUrl: e.target.value }))}
          />
          <p className={floatTy.caption} style={{ color: t.textMuted }}>
            DeepSeek OpenAI 格式：{DEEPSEEK_OPENAI_BASE_URL}（无需加 /v1）
          </p>
        </label>
        <label className="flex flex-col gap-1">
          <span style={{ color: t.textMuted }}>Model ID</span>
          {llm.provider === "deepseek" || llm.baseUrl.includes("deepseek.com") ? (
            <FloatSelect
              value={llm.model}
              menuPortal
              options={DEEPSEEK_MODEL_OPTIONS.map((opt) => ({
                value: opt.value,
                label: opt.label,
              }))}
              onChange={(model) => setLlm((c) => ({ ...c, model }))}
            />
          ) : llm.provider === "ollama" ? (
            <input
              className={fieldClass(t)}
              style={fieldStyle(t)}
              placeholder={llmHints.model}
              value={llm.model}
              onChange={(e) => setLlm((c) => ({ ...c, model: e.target.value }))}
            />
          ) : (
            <input
              className={fieldClass(t)}
              style={fieldStyle(t)}
              placeholder={llmHints.model}
              value={llm.model}
              onChange={(e) => setLlm((c) => ({ ...c, model: e.target.value }))}
            />
          )}
        </label>
        <label className="flex flex-col gap-1">
          <span style={{ color: t.textMuted }}>API Key</span>
          <input
            type="password"
            className={fieldClass(t)}
            style={fieldStyle(t)}
            placeholder={llm.provider === "ollama" ? "本地 Ollama 无需 Key" : "sk-..."}
            value={llm.apiKey}
            disabled={llm.provider === "ollama"}
            onChange={(e) => setLlm((c) => ({ ...c, apiKey: e.target.value }))}
          />
        </label>
        <button
          type="button"
          className={`w-full py-2 rounded-lg text-white ${floatTy.btn} disabled:opacity-50`}
          style={{ backgroundColor: t.purple }}
          disabled={busy}
          onClick={() => void saveLlm()}
        >
          保存配置
        </button>
        {status && (
          <p className={floatTy.caption} style={{ color: t.textMuted }}>
            {status}
          </p>
        )}
      </div>
    </FloatingMiniDialog>
  );
}
