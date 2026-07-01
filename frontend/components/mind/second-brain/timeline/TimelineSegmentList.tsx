"use client";

import type { TimelineSegment } from "@/lib/relationshipAnalysis";
import { DYNAMICS_STATE_LABELS } from "@/lib/relationshipAnalysis";
import { useMindTheme } from "../../MindUiProvider";
import { SbCard } from "../SbUIKit";

type Props = {
  segments: TimelineSegment[];
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

export function TimelineSegmentList({ segments }: Props) {
  const t = useMindTheme();

  if (segments.length === 0) {
    return (
      <p className="text-xs" style={{ color: t.textMuted }}>
        暂无时间段数据
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {segments.map((seg, i) => (
        <SbCard key={`${seg.start}-${seg.end}`} accent="teal" padding="sm" className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-medium" style={{ color: t.text }}>
              段 {i + 1} · {fmtTime(seg.start)} — {fmtTime(seg.end)}
            </span>
            <span
              className="text-[10px] px-2 py-0.5 rounded-full border"
              style={{ borderColor: "#5eead455", color: "#5eead4", backgroundColor: "#5eead414" }}
            >
              {DYNAMICS_STATE_LABELS[seg.stateSnapshot]}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[10px]" style={{ color: t.textMuted }}>
            <span>消息 {seg.metrics.messageCount}</span>
            <span>主动性 {(seg.metrics.initiativeRatio * 100).toFixed(0)}%</span>
            <span>沉默比 {(seg.metrics.silenceRatio * 100).toFixed(0)}%</span>
            <span>平均延迟 {Math.round(seg.metrics.replyLatencyAvg / 60)} 分</span>
            <span>未回应 {seg.metrics.ignoreCount}</span>
            <span>语气趋冷 {seg.metrics.emotionColdCount}</span>
          </div>
        </SbCard>
      ))}
    </div>
  );
}
