"use client";

import { useState } from "react";
import {
  loadDingTalkConfig,
  saveDingTalkConfig,
  sendDingTalkTest,
  type DingTalkConfig,
} from "@/lib/floatIntegrations";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  className?: string;
};

export function DingTalkSettingsPanel({ className }: Props) {
  const t = useMindTheme();
  const [config, setConfig] = useState<DingTalkConfig>(() => loadDingTalkConfig());
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const inputClass = "w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1";
  const inputStyle = { borderColor: t.border, backgroundColor: t.chatBg, color: t.text };

  const save = () => {
    saveDingTalkConfig(config);
    setStatus("配置已保存");
  };

  const test = async () => {
    setBusy(true);
    setStatus(null);
    try {
      saveDingTalkConfig(config);
      await sendDingTalkTest(config, "CNexus 第二大脑 · 通知测试");
      setStatus("测试消息已发送");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "发送失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={className}>
      <label className="flex items-center gap-2 text-sm mb-4" style={{ color: t.text }}>
        <input
          type="checkbox"
          checked={config.enabled}
          onChange={(e) => setConfig((c) => ({ ...c, enabled: e.target.checked }))}
        />
        启用钉钉机器人通知
      </label>

      <div className="space-y-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium" style={{ color: t.textMuted }}>
            Webhook 地址
          </span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="https://oapi.dingtalk.com/robot/send?access_token=..."
            value={config.webhook}
            onChange={(e) => setConfig((c) => ({ ...c, webhook: e.target.value }))}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium" style={{ color: t.textMuted }}>
            加签 Secret（可选）
          </span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="SEC..."
            value={config.secret}
            onChange={(e) => setConfig((c) => ({ ...c, secret: e.target.value }))}
          />
        </label>

        <div className="space-y-2 pt-1">
          <label className="flex items-center gap-2 text-xs" style={{ color: t.text }}>
            <input
              type="checkbox"
              checked={config.notifyOnCapture}
              onChange={(e) => setConfig((c) => ({ ...c, notifyOnCapture: e.target.checked }))}
            />
            记忆导入完成时通知
          </label>
          <label className="flex items-center gap-2 text-xs" style={{ color: t.text }}>
            <input
              type="checkbox"
              checked={config.notifyOnConflict}
              onChange={(e) => setConfig((c) => ({ ...c, notifyOnConflict: e.target.checked }))}
            />
            需要确认时通知
          </label>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            className="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
            style={{ backgroundColor: t.green }}
            onClick={save}
          >
            保存配置
          </button>
          <button
            type="button"
            disabled={busy || !config.webhook.trim()}
            className="px-4 py-2 rounded-lg text-sm font-medium border disabled:opacity-50"
            style={{ borderColor: t.border, color: t.textMuted }}
            onClick={() => void test()}
          >
            {busy ? "发送中…" : "发送测试"}
          </button>
        </div>

        {status && (
          <p className="text-xs" style={{ color: t.textMuted }}>
            {status}
          </p>
        )}
      </div>
    </div>
  );
}
