"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { EventStream } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  eventStream: EventStream;
};

const TYPE_LABELS: Record<string, string> = {
  message: "消息",
  reply_delay: "回复延迟",
  initiative: "主动发起",
  silence: "沉默窗口",
  ignore: "未回应",
  emotion_shift: "语气变化",
  intensity: "强度变化",
};

function fmtTime(ts: number): string {
  try {
    return new Date(ts).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(ts);
  }
}

export function EventStreamViewer({ eventStream }: Props) {
  const t = useMindTheme();
  const [open, setOpen] = useState(false);
  const events = eventStream.events;

  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: t.border, backgroundColor: t.chatBg }}>
      <button
        type="button"
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div>
          <span className="text-xs font-medium" style={{ color: t.text }}>
            事件流
          </span>
          <p className="text-[10px] mt-0.5" style={{ color: t.textMuted }}>
            {events.length} 个行为事件 · {eventStream.entities.join(" ↔ ")}
          </p>
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
        ) : (
          <ChevronDown className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
        )}
      </button>

      {open && (
        <div
          className="px-3 pb-3 pt-1 border-t max-h-[280px] overflow-y-auto cnexus-float-scroll space-y-1.5"
          style={{ borderColor: t.border }}
        >
          {events.map((ev, i) => (
            <div
              key={`${ev.type}-${ev.timestamp}-${i}`}
              className="text-[11px] px-2 py-1.5 rounded-lg border flex flex-wrap gap-x-2 gap-y-0.5"
              style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.surface }}
            >
              <span className="font-mono text-[10px]" style={{ color: "#5eead4" }}>
                {TYPE_LABELS[ev.type] ?? ev.type}
              </span>
              <span>{fmtTime(ev.timestamp)}</span>
              {"actor" in ev && ev.actor && <span>@{ev.actor}</span>}
              {"text" in ev && ev.text && (
                <span className="w-full truncate" style={{ color: t.text }}>
                  {ev.text}
                </span>
              )}
              {"value" in ev && typeof ev.value === "number" && (
                <span>{Math.round(ev.value / 60)} 分</span>
              )}
              {"duration" in ev && typeof ev.duration === "number" && (
                <span>{Math.round(ev.duration / 3600)} 小时</span>
              )}
              {"direction" in ev && ev.direction && <span>{ev.direction}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
