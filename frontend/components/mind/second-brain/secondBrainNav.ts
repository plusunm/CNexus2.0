import type { LucideIcon } from "lucide-react";
import {
  MessageCircle,
  Brain,
  GitBranch,
  BookMarked,
  BookOpen,
  Upload,
  Moon,
  Network,
  Link2,
  CloudDownload,
  Bell,
  MessageSquareShare,
  Cpu,
  User,
} from "lucide-react";
import type { CopyKey } from "@/lib/cognitive/projection/copyLexicon";
import type { SecondBrainTab } from "@/lib/cognitive/experience/types";

export type SecondBrainNavGroup = "chat" | "decision" | "memory" | "network" | "settings";

export type SecondBrainNavItem = {
  id: SecondBrainTab;
  icon: LucideIcon;
  labelKey: CopyKey;
  sub: string;
  group: SecondBrainNavGroup;
};

export const SECOND_BRAIN_NAV: SecondBrainNavItem[] = [
  { id: "chat", icon: MessageCircle, labelKey: "tabChat", sub: "和 CNexus 聊天", group: "chat" },
  { id: "chat-share", icon: MessageSquareShare, labelKey: "tabChatShare", sub: "生成本地分享链接", group: "chat" },
  { id: "thinking", icon: Brain, labelKey: "tabThinking", sub: "恋爱·求职·职场等结构化决策", group: "decision" },
  { id: "timeline", icon: GitBranch, labelKey: "tabTimeline", sub: "导入聊天 · 关系变化时间轴", group: "decision" },
  { id: "cards", icon: BookMarked, labelKey: "tabCards", sub: "决策模型库（多领域）", group: "decision" },
  { id: "memory", icon: BookOpen, labelKey: "tabMemory", sub: "浏览与筛选记忆", group: "memory" },
  { id: "share-memory", icon: CloudDownload, labelKey: "tabShareMemory", sub: "本机 · 组群 · 全网", group: "memory" },
  { id: "upload", icon: Upload, labelKey: "tabUpload", sub: "上传文档与资料", group: "memory" },
  { id: "organize", icon: Moon, labelKey: "tabOrganize", sub: "整理与清空数据", group: "memory" },
  { id: "network", icon: Network, labelKey: "tabNetwork", sub: "拓扑与我的设备 ID", group: "network" },
  { id: "connect", icon: Link2, labelKey: "tabConnect", sub: "发现与信任其他设备", group: "network" },
  { id: "notify", icon: Bell, labelKey: "tabNotify", sub: "钉钉等外部提醒", group: "network" },
  { id: "model", icon: Cpu, labelKey: "tabModel", sub: "大模型 API 配置", group: "settings" },
  { id: "profile", icon: User, labelKey: "tabProfile", sub: "连接与界面", group: "settings" },
];

export const SECOND_BRAIN_NAV_GROUPS: { key: SecondBrainNavGroup; label: string }[] = [
  { key: "chat", label: "对话" },
  { key: "decision", label: "决策分析" },
  { key: "memory", label: "记忆" },
  { key: "network", label: "分享与互联" },
  { key: "settings", label: "配置" },
];

export function secondBrainNavMeta(tab: SecondBrainTab) {
  return SECOND_BRAIN_NAV.find((item) => item.id === tab) ?? SECOND_BRAIN_NAV[0];
}

/** Wider layout for topology-heavy pages. */
export function secondBrainTabMaxWidth(tab: SecondBrainTab): string {
  if (tab === "network" || tab === "memory" || tab === "share-memory" || tab === "cards" || tab === "timeline") {
    return "min(100%, 1200px)";
  }
  return "720px";
}
