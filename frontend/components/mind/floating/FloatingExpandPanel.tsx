"use client";

import { ChatPanel } from "../ChatPanel";
import { FloatingMemoryPanel } from "./FloatingMemoryPanel";
import { FloatingMemChatPanel } from "./FloatingMemChatPanel";
import { FloatingUploadPanel } from "./FloatingUploadPanel";
import { useFloatingBarStore } from "@/lib/floatingBarStore";
import { FloatingCognitiveHints } from "./FloatingCognitiveHints";
import { ExperienceTierSwitch } from "@/lib/cognitive";
import { isFloatPersonalEdition } from "@/lib/floatPersonal";
import { FloatExperienceTierBar } from "./FloatExperienceTierBar";
import { FloatingRelationshipShortcuts } from "./FloatingRelationshipShortcuts";
import { useMindTheme } from "../MindUiProvider";
import type { FloatPanel } from "@/lib/floatingBarStorage";

type Props = {
  panel: FloatPanel;
};

export function FloatingExpandPanel({ panel }: Props) {
  const t = useMindTheme();
  const sessionEpoch = useFloatingBarStore((s) => s.sessionEpoch);
  const personal = isFloatPersonalEdition();
  const showCognitiveHints = !(personal && (panel === "chat" || panel === "memchat" || panel === "memory"));

  return (
    <div className="cnexus-float-expand-body flex-1" data-no-drag>
      <div
        className="px-3 pt-2 pb-1 border-b shrink-0"
        style={{ borderColor: t.border }}
      >
        {personal ? <FloatExperienceTierBar /> : <ExperienceTierSwitch compact />}
        <FloatingRelationshipShortcuts />
      </div>
      {showCognitiveHints && <FloatingCognitiveHints />}
      <div
        key={`${sessionEpoch}-${panel}`}
        className="px-3 pb-3 pt-0 min-h-0 flex flex-col min-w-0 overflow-hidden flex-1"
      >
        <div className="min-h-0 min-w-0 flex flex-col overflow-hidden flex-1">
          {panel === "chat" && <ChatPanel variant="float" autoFocusInput />}
          {panel === "memory" && <FloatingMemoryPanel />}
          {panel === "memchat" &&
            (isFloatPersonalEdition() ? (
              <ChatPanel variant="float" autoFocusInput />
            ) : (
              <FloatingMemChatPanel />
            ))}
          {panel === "upload" && <FloatingUploadPanel />}
        </div>
      </div>
    </div>
  );
}
