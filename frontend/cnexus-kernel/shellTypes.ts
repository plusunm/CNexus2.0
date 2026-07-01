import type { FloatPanel } from "@/lib/floatingBarStorage";
import type { MindUiMode } from "@/components/mind/themes/types";

export type ShellLayout = MindUiMode;
export type ShellPanel = FloatPanel;

export function parseShellLayout(value: string | null | undefined): ShellLayout {
  if (value === "cognitive" || value === "float" || value === "overview") return value;
  return "overview";
}

export function parseShellPanel(value: string | null | undefined): ShellPanel | null {
  if (value === "chat" || value === "memory" || value === "upload" || value === "memchat") return value;
  return null;
}

export function panelDomId(panel: ShellPanel): string {
  if (panel === "chat") return "chat-panel";
  if (panel === "memory") return "memory-panel";
  return "import";
}

/** Overview 子页 — learn 为默认可观测主视图（认知教学） */
export type OverviewView =
  | "debugger"
  | "workbench"
  | "flow"
  | "token"
  | "learn"
  | "summary"
  | "llm"
  | "network"
  | "network-connect"
  | "network-ops"
  | "network-assets";

export function parseOverviewView(value: string | null | undefined): OverviewView {
  if (value === "debugger") return "debugger";
  if (value === "workbench") return "workbench";
  if (value === "flow") return "flow";
  if (value === "token") return "token";
  if (value === "summary") return "summary";
  if (value === "llm" || value === "models" || value === "settings") return "llm";
  if (value === "network-connect" || value === "network_connect") return "network-connect";
  if (value === "network-ops" || value === "network_ops") return "network-ops";
  if (value === "network-assets" || value === "network_assets") return "network-assets";
  if (value === "network" || value === "mission-control" || value === "mission_control") return "network";
  if (value === "learn" || value === "query") return "learn";
  return "learn";
}

export function isNetworkView(view: OverviewView): boolean {
  return view === "network" || view === "network-connect" || view === "network-ops" || view === "network-assets";
}
