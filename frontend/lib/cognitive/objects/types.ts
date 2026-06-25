/** Cognitive Object Layer — semantic objects decoupled from Runtime IDs. */

import type { CopyKey } from "../projection/copyLexicon";

export type CognitiveDomain =
  | "memory"
  | "conflict"
  | "pruning"
  | "emergence"
  | "negotiation"
  | "reflection";

export type CognitiveObjectRef = {
  domain: CognitiveDomain;
  id: string;
  labDeepLink?: string;
};

export type ProvenanceSource = {
  kind: "conversation" | "document" | "long_term_memory" | "sync";
  count: number;
  labelKey: CopyKey;
};

export type ProvenanceExplain = {
  headline: string;
  sources: ProvenanceSource[];
  labDeepLink: string;
};

export type CognitiveObject = {
  ref: CognitiveObjectRef;
  titleKey: CopyKey;
  consumerSummary: string;
  provenance?: ProvenanceExplain;
  _runtime?: unknown;
};

export type ProjectedObject = {
  title: string;
  summary: string;
};
