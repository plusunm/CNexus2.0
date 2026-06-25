"use client";



import { useEffect, useMemo, useState } from "react";

import { brainApi, isRuntimeReady, probePersonalBackendOnline } from "@/lib/api";

import { useMindStore } from "@/cnexus-kernel";

import { isPersonalMode } from "@/lib/personalGuard";

import {

  applyLlmProviderDefaults,

  DEEPSEEK_MODEL_OPTIONS,

  DEEPSEEK_OPENAI_BASE_URL,

  LLM_UI_PROVIDER_OPTIONS,

  llmFieldHints,

  loadLlmQuickConfig,

  normalizeDeepseekModel,

  normalizeLlmQuickConfig,

  saveLlmQuickConfig,

  syncLlmQuickConfigToRuntime,

  formatLlmTestFailure,

  type LlmQuickConfig,

} from "@/lib/floatIntegrations";

import { useMindTheme } from "../MindUiProvider";

import { FloatSelect } from "../floating/FloatSelect";



export function HomeModelSettingsPanel() {

  const t = useMindTheme();

  const models = useMindStore((s) => s.models);

  const selectedModelId = useMindStore((s) => s.selectedModelId);

  const [llm, setLlm] = useState<LlmQuickConfig>(() => loadLlmQuickConfig());

  const [status, setStatus] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);

  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null);



  const hints = useMemo(() => llmFieldHints(llm.provider), [llm.provider]);



  useEffect(() => {

    setLlm(loadLlmQuickConfig());

  }, []);



  useEffect(() => {

    let cancelled = false;

    const probe = async () => {

      try {

        const ollama = await brainApi.ollamaStatus();

        if (cancelled) return;

        setOllamaOnline(Boolean(ollama.running));

        if (ollama.running) {

          await useMindStore.getState().refreshModels();

        }

      } catch {

        if (!cancelled) setOllamaOnline(false);

      }

    };

    void probe();

    const id = window.setInterval(() => void probe(), 15_000);

    return () => {

      cancelled = true;

      window.clearInterval(id);

    };

  }, []);



  const fieldClass = "w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1";

  const fieldStyle: React.CSSProperties = {

    borderColor: t.border,

    backgroundColor: t.chatBg,

    color: t.text,

  };



  const activeModel = models.find((m) => m.id === selectedModelId);



  const onProviderChange = (provider: string) => {

    setLlm(applyLlmProviderDefaults(provider));

    setStatus(null);

  };



  const save = async () => {

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

    setStatus("配置已保存，正在同步…");

    const personal = isPersonalMode();

    try {

      const online = personal

        ? await probePersonalBackendOnline()

        : await isRuntimeReady({ skipWs: true });

      if (!online) {

        setStatus(

          personal

            ? "配置已保存 — 本地服务未连接，启动应用后将自动同步"

            : "已保存到本地 — 连接 Runtime 后将自动同步",

        );

        return;

      }

      const result = await syncLlmQuickConfigToRuntime();

      await useMindStore.getState().refreshModels();

      if (result.ok && result.testOk && result.modelId) {

        useMindStore.getState().setSelectedModel(result.modelId);

        setStatus(

          result.modelId === "ollama-local"

            ? "已保存并切换为 Ollama 本地 — 可直接聊天（无需 Key）"

            : "已保存并同步到本机网关",

        );

      } else if (result.ok) {

        setStatus(

          result.testDetail

            ? `已保存并同步 — ${result.testDetail}`

            : "已保存并同步 — 连通性将在下次对话时验证",

        );

      } else {

        setStatus(

          result.error === "missing_key"

            ? "请填写 API Key，或选择 Ollama 本地"

            : `已保存到本地 — 同步失败：${result.error ?? "未知错误"}`,

        );

      }

    } catch (err) {

      setStatus(err instanceof Error ? err.message : "保存失败");

    } finally {

      setBusy(false);

    }

  };



  const statusColor = (msg: string) => {

    if (/失败|错误|请填写|无效|Unauthorized/i.test(msg) && !/已保存/.test(msg)) {

      return t.orange;

    }

    if (/已保存|成功|同步|切换|Ollama|可直接聊天/.test(msg)) {

      return t.green;

    }

    return t.textMuted;

  };



  return (

    <div className="p-4 space-y-4">

      {activeModel && (

        <div

          className="rounded-xl px-3 py-2.5 text-xs border flex items-center justify-between gap-2"

          style={{ borderColor: t.border, backgroundColor: t.chatBg }}

        >

          <span style={{ color: t.textMuted }}>当前对话模型</span>

          <span className="font-medium truncate" style={{ color: t.green }}>

            {activeModel.name || activeModel.model}

          </span>

        </div>

      )}



      {ollamaOnline !== null && (

        <div

          className="rounded-xl px-3 py-2 text-xs border flex items-center justify-between gap-2"

          style={{

            borderColor: ollamaOnline ? t.green : t.border,

            backgroundColor: ollamaOnline ? t.greenSoft : t.chatBg,

            color: ollamaOnline ? t.green : t.textMuted,

          }}

        >

          <span>Ollama 本机检测</span>

          <span className="font-medium">{ollamaOnline ? "在线 · 已自动接入" : "未运行"}</span>

        </div>

      )}



      <p className="text-xs" style={{ color: t.textMuted }}>

        先选择 Provider，系统将自动填入推荐配置，再按需修改 API Key 后保存。

      </p>



      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        <FloatSelect

          label="Provider"

          value={llm.provider}

          options={LLM_UI_PROVIDER_OPTIONS}

          onChange={onProviderChange}

        />

        <label className="flex flex-col gap-1.5 text-xs">

          <span style={{ color: t.textMuted }}>显示名称</span>

          <input

            className={fieldClass}

            style={fieldStyle}

            value={llm.label}

            onChange={(e) => setLlm((c) => ({ ...c, label: e.target.value }))}

          />

        </label>

        <label className="flex flex-col gap-1.5 text-xs md:col-span-2">

          <span style={{ color: t.textMuted }}>Base URL</span>

          <input

            className={fieldClass}

            style={fieldStyle}

            placeholder={hints.baseUrl}

            value={llm.baseUrl}

            onChange={(e) => setLlm((c) => ({ ...c, baseUrl: e.target.value }))}

          />

          {llm.provider === "ollama" && (

            <span className="text-[10px]" style={{ color: t.textLight }}>

              填写 Ollama 服务地址即可，不要加 /api/chat

            </span>

          )}

        </label>

        <label className="flex flex-col gap-1.5 text-xs">

          <span style={{ color: t.textMuted }}>Model ID</span>

          {llm.provider === "deepseek" || llm.baseUrl.includes("deepseek.com") ? (

            <FloatSelect

              value={llm.model}

              options={DEEPSEEK_MODEL_OPTIONS.map((opt) => ({

                value: opt.value,

                label: opt.label,

              }))}

              onChange={(model) => setLlm((c) => ({ ...c, model: normalizeDeepseekModel(model) }))}

            />

          ) : (

            <input

              className={fieldClass}

              style={fieldStyle}

              placeholder={hints.model}

              value={llm.model}

              onChange={(e) => setLlm((c) => ({ ...c, model: e.target.value }))}

            />

          )}

        </label>

        <label className="flex flex-col gap-1.5 text-xs">

          <span style={{ color: t.textMuted }}>API Key</span>

          <input

            type="password"

            className={fieldClass}

            style={fieldStyle}

            placeholder={hints.apiKey}

            value={llm.apiKey}

            disabled={llm.provider === "ollama"}

            onChange={(e) => setLlm((c) => ({ ...c, apiKey: e.target.value }))}

          />

        </label>

      </div>



      <button

        type="button"

        disabled={busy}

        onClick={() => void save()}

        className="px-5 py-2.5 rounded-xl text-sm font-medium disabled:opacity-50"

        style={{ backgroundColor: t.purple, color: "#fff" }}

      >

        {busy ? "保存中…" : "保存配置"}

      </button>



      {status && (

        <p className="text-xs" style={{ color: statusColor(status) }}>

          {status}

        </p>

      )}

    </div>

  );

}

