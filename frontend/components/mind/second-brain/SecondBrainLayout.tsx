"use client";

import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useExperience, useCognitiveCopy, ExperienceTierSwitch } from "@/lib/cognitive";
import { SECOND_BRAIN_TABS } from "@/lib/cognitive/experience/types";
import { useMindTheme } from "../MindUiProvider";
import { SecondBrainSidebar } from "./SecondBrainSidebar";
import { secondBrainNavMeta, secondBrainTabMaxWidth } from "./secondBrainNav";
import { ChatTab } from "./ChatTab";
import { ThinkingTab } from "./ThinkingTab";
import { TimelineTab } from "./TimelineTab";
import { CardsTab } from "./CardsTab";
import { MemoryTab } from "./MemoryTab";
import { UploadTab } from "./UploadTab";
import { OrganizeTab } from "./OrganizeTab";
import { NetworkTab } from "./NetworkTab";
import { ConnectTab } from "./ConnectTab";
import { ShareMemoryTab } from "./ShareMemoryTab";
import { NotifyTab } from "./NotifyTab";
import { ChatShareTab } from "./ChatShareTab";
import { ModelTab } from "./ModelTab";
import { ProfileTab } from "./ProfileTab";
import type { SecondBrainTab } from "@/lib/cognitive/experience/types";

function TabFrame({ tab, children }: { tab: SecondBrainTab; children: React.ReactNode }) {
  return (
    <div className="w-full min-h-0" style={{ maxWidth: secondBrainTabMaxWidth(tab) }}>
      {children}
    </div>
  );
}

export function SecondBrainLayout() {
  const t = useMindTheme();
  const router = useRouter();
  const { secondBrainTab, setSecondBrainTab, setPersona } = useExperience();
  const { t: copy } = useCognitiveCopy();

  const meta = secondBrainNavMeta(secondBrainTab);
  const ActiveIcon = meta.icon;

  const openLab = (href: string) => {
    setPersona("cognitive-lab");
    router.push(href);
  };

  return (
    <div
      className="h-dvh max-h-dvh flex w-full overflow-hidden"
      style={{
        backgroundColor: t.bg,
        color: t.text,
        fontFamily: t.fontSans,
        backgroundImage: `radial-gradient(ellipse 100% 60% at 70% 0%, rgba(94,234,212,0.06), transparent), radial-gradient(ellipse 80% 50% at 0% 100%, rgba(167,139,250,0.05), transparent)`,
      }}
      data-experience="second-brain"
    >
      <SecondBrainSidebar activeTab={secondBrainTab} onTabChange={setSecondBrainTab} />

      <div className="flex-1 flex flex-col min-w-0 min-h-0 h-full overflow-hidden">
        <header
          className="lg:hidden shrink-0 border-b px-4 py-3 space-y-3"
          style={{ borderColor: t.border, backgroundColor: t.surface }}
        >
          <div className="flex items-center gap-2">
            <ActiveIcon className="w-4 h-4" style={{ color: "#5eead4" }} />
            <div>
              <p className="text-sm font-semibold">{copy(meta.labelKey)}</p>
              <p className="text-[10px]" style={{ color: t.textMuted }}>
                {meta.sub}
              </p>
            </div>
          </div>
          <div
            className="flex gap-1 p-1 rounded-xl border overflow-x-auto cnexus-float-scroll"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            {SECOND_BRAIN_TABS.map((tab) => {
              const item = secondBrainNavMeta(tab);
              const Icon = item.icon;
              const active = secondBrainTab === tab;
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setSecondBrainTab(tab)}
                  className="flex shrink-0 items-center justify-center gap-1 px-2.5 py-2 rounded-lg text-[11px] font-medium"
                  style={{
                    color: active ? "#5eead4" : t.textMuted,
                    backgroundColor: active ? "rgba(94,234,212,0.12)" : "transparent",
                  }}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {copy(item.labelKey)}
                </button>
              );
            })}
          </div>
          <ExperienceTierSwitch compact />
        </header>

        <header
          className="hidden lg:flex shrink-0 items-center justify-between gap-4 pl-5 pr-6 py-3 border-b"
          style={{ borderColor: t.border, backgroundColor: t.surface }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <ActiveIcon className="w-5 h-5 shrink-0" style={{ color: "#5eead4" }} />
            <div className="min-w-0">
              <h1 className="text-base font-semibold tracking-tight">{copy(meta.labelKey)}</h1>
              <p className="text-xs mt-0.5 truncate" style={{ color: t.textMuted }}>
                {meta.sub}
              </p>
            </div>
          </div>
        </header>

        <main
          className={clsx(
            "flex-1 min-h-0 flex flex-col overflow-hidden",
            secondBrainTab === "chat" ? "p-0" : "overflow-y-auto py-4 lg:py-5 pl-4 lg:pl-5 pr-4 lg:pr-6",
          )}
        >
          {secondBrainTab === "chat" && <ChatTab />}
          {secondBrainTab === "thinking" && (
            <TabFrame tab="thinking">
              <ThinkingTab />
            </TabFrame>
          )}
          {secondBrainTab === "timeline" && (
            <TabFrame tab="timeline">
              <TimelineTab />
            </TabFrame>
          )}
          {secondBrainTab === "cards" && (
            <TabFrame tab="cards">
              <CardsTab />
            </TabFrame>
          )}
          {secondBrainTab === "memory" && (
            <TabFrame tab="memory">
              <MemoryTab onOpenLab={openLab} />
            </TabFrame>
          )}
          {secondBrainTab === "upload" && (
            <TabFrame tab="upload">
              <UploadTab />
            </TabFrame>
          )}
          {secondBrainTab === "organize" && (
            <TabFrame tab="organize">
              <OrganizeTab />
            </TabFrame>
          )}
          {secondBrainTab === "network" && (
            <TabFrame tab="network">
              <NetworkTab />
            </TabFrame>
          )}
          {secondBrainTab === "connect" && (
            <TabFrame tab="connect">
              <ConnectTab />
            </TabFrame>
          )}
          {secondBrainTab === "share-memory" && (
            <TabFrame tab="share-memory">
              <ShareMemoryTab />
            </TabFrame>
          )}
          {secondBrainTab === "notify" && (
            <TabFrame tab="notify">
              <NotifyTab />
            </TabFrame>
          )}
          {secondBrainTab === "chat-share" && (
            <TabFrame tab="chat-share">
              <ChatShareTab />
            </TabFrame>
          )}
          {secondBrainTab === "model" && (
            <TabFrame tab="model">
              <ModelTab />
            </TabFrame>
          )}
          {secondBrainTab === "profile" && (
            <TabFrame tab="profile">
              <ProfileTab />
            </TabFrame>
          )}
        </main>
      </div>
    </div>
  );
}

export default SecondBrainLayout;
