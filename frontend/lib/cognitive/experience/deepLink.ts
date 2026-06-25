import type { CognitiveDomain } from "../objects/types";
import type { ExperiencePersona } from "./types";

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
