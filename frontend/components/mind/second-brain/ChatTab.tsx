"use client";

import { ChatPanel } from "../ChatPanel";

export function ChatTab() {
  return (
    <div className="flex flex-col flex-1 min-h-0 h-full overflow-hidden">
      <div className="flex-1 min-h-0 flex flex-col px-4 lg:px-8 py-4 lg:py-6 overflow-hidden">
        <div className="flex-1 min-h-0 flex flex-col max-w-3xl mx-auto w-full h-full overflow-hidden">
          <ChatPanel variant="second-brain" autoFocusInput />
        </div>
      </div>
    </div>
  );
}
