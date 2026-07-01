import type { CognitiveDomain } from "../objects/types";
import type { ExperiencePersona, SecondBrainTab } from "./types";
import { isSecondBrainTab } from "./types";
import { isFloatPersonalEdition, personalMainUiUrl } from "@/lib/floatPersonal";
import { getPersonalGatewayBase, isTauriWebviewHost } from "@/lib/cnexusConfig";

export type LabDeepLink = {
  view: "network" | "workbench" | "debugger";
  highlight?: {
    domain: CognitiveDomain;
    id: string;
    panel?: "audit" | "pruning" | "entropy";
  };
  from?: "second-brain-explain";
};

export function buildLabShellHref(link: LabDeepLink): string {
  const params = new URLSearchParams();
  params.set("layout", "overview");
  params.set("experience", "cognitive-lab" satisfies ExperiencePersona);
  params.set("view", link.view);
  if (link.highlight?.domain) params.set("highlightDomain", link.highlight.domain);
  if (link.highlight?.id) params.set("highlightId", link.highlight.id);
  if (link.highlight?.panel) params.set("highlightPanel", link.highlight.panel);
  if (link.from) params.set("from", link.from);
  return `/shell?${params.toString()}`;
}

export function buildEmergenceLabLink(id: string): string {
  return buildLabShellHref({
    view: "network",
    highlight: { domain: "emergence", id, panel: "audit" },
    from: "second-brain-explain",
  });
}

export function buildConflictLabLink(id: string): string {
  return buildLabShellHref({
    view: "network",
    highlight: { domain: "conflict", id, panel: "audit" },
    from: "second-brain-explain",
  });
}

export type SecondBrainDeepLink = {
  tab?: SecondBrainTab;
  from?: "float" | "float-timeline" | "float-thinking" | "float-memory";
};

/** In-app route for Second Brain (shell / static export). */
export function buildSecondBrainShellHref(link?: SecondBrainDeepLink): string {
  const params = new URLSearchParams();
  params.set("layout", "overview");
  params.set("experience", "second-brain" satisfies ExperiencePersona);
  if (link?.tab && link.tab !== "chat") params.set("tab", link.tab);
  if (link?.from) params.set("from", link.from);
  return `/shell?${params.toString()}`;
}

/** Tauri dashboard route — personal uses `/`, enterprise uses `/shell`. */
export function buildSecondBrainDashboardRoute(link?: SecondBrainDeepLink): string {
  const params = new URLSearchParams();
  params.set("experience", "second-brain");
  if (link?.tab && link.tab !== "chat") params.set("tab", link.tab);
  if (link?.from) params.set("from", link.from);

  if (isFloatPersonalEdition()) {
    return `/?${params.toString()}`;
  }

  const shell = new URLSearchParams();
  shell.set("layout", "overview");
  params.forEach((v, k) => shell.set(k, v));
  return `/shell?${shell.toString()}`;
}

/** Absolute URL for opening Second Brain from float / Tauri (handles personal gateway port). */
export function resolveSecondBrainOpenUrl(link?: SecondBrainDeepLink): string {
  if (typeof window === "undefined") return buildSecondBrainShellHref(link);

  if (isFloatPersonalEdition()) {
    const base = isTauriWebviewHost() ? getPersonalGatewayBase() : personalMainUiUrl();
    const url = new URL(base);
    url.searchParams.set("experience", "second-brain");
    if (link?.tab && link.tab !== "chat") url.searchParams.set("tab", link.tab);
    if (link?.from) url.searchParams.set("from", link.from);
    return url.toString();
  }

  return `${window.location.origin}${buildSecondBrainShellHref(link)}`;
}

export function parseSecondBrainTabFromSearch(search: string): SecondBrainTab | null {
  const tab = new URLSearchParams(search).get("tab");
  return isSecondBrainTab(tab) ? tab : null;
}
