"use client";

import type { CognitivePipelineResult } from "@/lib/relationshipAnalysis";
import { SbSection } from "../SbUIKit";
import { GitBranch } from "lucide-react";
import { PhaseIndicator } from "./PhaseIndicator";
import { TimelineSegmentList } from "./TimelineSegmentList";
import { EventStreamViewer } from "./EventStreamViewer";
import { StateSnapshotCard } from "./StateSnapshotCard";
import { CausalPanel } from "./CausalPanel";
import { PredictionPanel } from "./PredictionPanel";
import { DecisionPanel } from "./DecisionPanel";

type Props = {
  result: CognitivePipelineResult;
  actions?: React.ReactNode;
};

export function TimelinePage({ result, actions }: Props) {
  const { timeline, eventStream, analysis, causal, prediction, counterfactual } = result;

  return (
    <div className="flex flex-col gap-5">
      <SbSection title="关系时间轴" subtitle={analysis.meta.sourceInput} icon={GitBranch} action={actions}>
        <PhaseIndicator current={timeline.currentState} />
      </SbSection>

      <SbSection title="时间段" subtitle={`共 ${timeline.segments.length} 个阶段窗口`}>
        <TimelineSegmentList segments={timeline.segments} />
      </SbSection>

      <SbSection title="状态与决策">
        <StateSnapshotCard timeline={timeline} analysis={analysis} />
      </SbSection>

      <CausalPanel causal={causal} />

      <PredictionPanel prediction={prediction} />

      <DecisionPanel counterfactual={counterfactual} />

      <EventStreamViewer eventStream={eventStream} />
    </div>
  );
}
