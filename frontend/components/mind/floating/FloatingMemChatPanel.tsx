"use client";

/** FloatingMemChatPanel — 记忆对话双模面板
 *  Tab1: 记忆检索（纯查询，不调 LLM，响应快）
 *  Tab2: 对话（记忆检索 + LLM 推理，完整链路）
 *
 *  写在悬浮窗内作为独立 panel，不改动原有 ChatPanel 逻辑。
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, MessageSquare, Send, Search } from "lucide-react";
import { useMindTheme } from "../MindUiProvider";
import { floatTy } from "@/lib/floatTypography";

type Mode = "recall" | "chat";

interface Msg {
  role: "user" | "assistant" | "memory" | "system";
  text: string;
  meta?: string;
}

const MODE_OPTIONS: { id: Mode; label: string; icon: typeof Search }[] = [
  { id: "recall", label: "记忆检索", icon: Search },
  { id: "chat", label: "对话", icon: MessageSquare },
];

export function FloatingMemChatPanel() {
  const t = useMindTheme();
  const [mode, setMode] = useState<Mode>("recall");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const addMsg = useCallback((m: Msg) => {
    setMessages((prev) => [...prev, m]);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    addMsg({ role: "user", text });
    setLoading(true);

    try {
      if (mode === "recall") {
        await doRecall(text);
      } else {
        await doChat(text);
      }
    } catch (err) {
      addMsg({ role: "assistant", text: `❌ 请求失败: ${err instanceof Error ? err.message : "未知错误"}` });
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [input, loading, mode, addMsg]);

  /** Tab1: 纯记忆检索 */
  const doRecall = async (query: string) => {
    const r = await fetch(
      `/memory/recall?query=${encodeURIComponent(query)}`,
      { signal: AbortSignal.timeout(15000) },
    );
    if (!r.ok) {
      addMsg({ role: "assistant", text: `❌ API 错误: ${r.status}` });
      return;
    }
    const data = await r.json();
    const ctx: string = data.context || "";
    if (ctx.trim()) {
      addMsg({ role: "memory", text: ctx, meta: "📖 记忆检索结果" });
    } else {
      addMsg({ role: "memory", text: "📭 未找到相关记忆。", meta: "记忆检索" });
    }
  };

  /** Tab2: 完整对话（记忆 + LLM） */
  const doChat = async (msg: string) => {
    addMsg({ role: "assistant", text: "🤔 思考中..." });
    try {
      const r = await fetch("/v1/gateway/intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "chat_send",
          payload: {
            message: msg,
            use_memory: true,
            model_id: "qwen2.5:1.5b",
          },
        }),
        signal: AbortSignal.timeout(120000),
      });
      const data = await r.json();

      // Remove loading message
      setMessages((prev) => prev.slice(0, -1));

      if (data.status === "completed" && data.result) {
        const reply = data.result.reply || data.result.response || "(无回复)";
        const timeoutHint = data.result._timeout ? "\n\n⚠️ 准备阶段超时，未检索记忆。" : "";
        addMsg({ role: "assistant", text: reply + timeoutHint });
      } else if (data.reply) {
        addMsg({ role: "assistant", text: data.reply });
      } else if (data.status === "timeout") {
        addMsg({ role: "assistant", text: "⏱️ 请求超时。纯 CPU 推理较慢，可切换到记忆检索模式快速获取上下文。" });
      } else {
        addMsg({ role: "assistant", text: `⚠️ ${data.reason || "未知错误"}` });
      }
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1));
      throw err;
    }
  };

  /** Mode switch welcome messages */
  const onModeSwitch = useCallback(
    (newMode: Mode) => {
      if (newMode === mode) return;
      setMode(newMode);
      setMessages([]);
      if (newMode === "recall") {
        addMsg({ role: "system", text: "切换到记忆检索模式。输入关键词查询记忆库，不调用大模型。" });
      } else {
        addMsg({ role: "system", text: "切换到对话模式。消息会经过记忆检索 + 大模型推理（响应较慢）。" });
      }
    },
    [mode, addMsg],
  );

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden" data-no-drag>
      {/* Mode tabs */}
      <div className="flex gap-1 px-3 pt-2 pb-1 shrink-0">
        {MODE_OPTIONS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onModeSwitch(id)}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-xs transition ${
              mode === id ? "" : "opacity-60 hover:opacity-90"
            }`}
            style={{
              backgroundColor: mode === id ? `${t.blue}22` : "transparent",
              color: mode === id ? t.blue : t.textMuted,
            }}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Quick description */}
      <div
        className="px-3 py-1 text-[10px] shrink-0"
        style={{ color: t.textMuted }}
      >
        {mode === "recall"
          ? "纯记忆查询，不调用大模型，响应快"
          : "记忆检索 → LLM 推理，响应较慢但可对话"}
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overscroll-contain space-y-2 px-3 py-2"
        style={{ minHeight: 0 }}
      >
        {messages.length === 0 && (
          <p
            className="text-center py-6 text-xs"
            style={{ color: t.textMuted }}
          >
            {mode === "recall"
              ? "输入关键词检索记忆库"
              : "输入消息开始对话（带记忆检索）"}
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "ml-auto max-w-[92%]"
                : m.role === "memory"
                  ? "max-w-[96%]"
                  : "max-w-[92%]"
            }
          >
            <div
              className={`px-3 py-2 rounded-lg whitespace-pre-wrap break-words ${floatTy.body}`}
              style={
                m.role === "user"
                  ? { backgroundColor: t.blueSoft, color: t.text }
                  : m.role === "memory"
                    ? {
                        backgroundColor: "#0d3a1a",
                        color: t.text,
                        border: "1px solid #238636",
                      }
                    : m.role === "system"
                      ? {
                          backgroundColor: "rgba(255,255,255,0.04)",
                          color: t.textMuted,
                          border: "1px solid #30363d",
                          fontSize: 12,
                        }
                      : {
                          backgroundColor: t.bg,
                          color: t.text,
                          border: `1px solid ${t.border}`,
                        }
              }
            >
              {m.meta && (
                <div className="text-[11px] mb-1" style={{ color: t.textMuted }}>
                  {m.meta}
                </div>
              )}
              {m.text}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div
        className="shrink-0 px-3 pt-2 pb-3 border-t flex gap-2 items-end"
        style={{ borderColor: t.border, backgroundColor: t.surface }}
      >
        <textarea
          ref={inputRef}
          rows={1}
          className="flex-1 min-w-0 px-3 py-2 rounded-lg border outline-none resize-none leading-relaxed text-sm"
          style={{
            borderColor: t.border,
            color: t.text,
            backgroundColor: t.bg,
            maxHeight: 120,
            minHeight: 36,
          }}
          placeholder={mode === "recall" ? "搜索记忆库…" : "输入问题…"}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            const el = e.target;
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          disabled={loading}
        />
        <button
          type="button"
          className="w-9 h-9 rounded-lg flex items-center justify-center text-white shrink-0 disabled:opacity-50 transition-transform active:scale-95"
          style={{ backgroundColor: t.blue, opacity: loading ? 0.5 : 1 }}
          onClick={send}
          disabled={loading || !input.trim()}
          aria-label="发送"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : mode === "recall" ? (
            <Search className="w-4 h-4" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}
