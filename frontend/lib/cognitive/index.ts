export type { CognitiveDomain, CognitiveObject, CognitiveObjectRef, ProvenanceExplain, ProvenanceSource, ProjectedObject } from "./objects/types";
export { MemoryObject, ConflictObject, PruningObject, EmergenceObject } from "./objects/index";

export type { CognitiveDialect, CopyKey, CognitiveCopyEntry } from "./projection/copyLexicon";
export { cognitiveCopy, getCopyEntry } from "./projection/copyLexicon";
export { projectCopy, projectCopyFmt, projectObject, projectProvenanceSource } from "./projection/projectCopy";
export { useCognitiveCopy, useConflictCopy, useEmergenceCopy } from "./projection/hooks";

export type { ExperiencePersona, SecondBrainTab } from "./experience/types";
export { PERSONA_DEFAULT_DIALECT, PERSONA_LABELS, LAB_ONLY_VIEWS } from "./experience/types";
export { ExperienceProvider, useExperience, useExperienceOptional } from "./experience/ExperienceProvider";
export { ExperienceTierSwitch } from "./experience/ExperienceTierSwitch";
export { buildLabShellHref, buildEmergenceLabLink, buildConflictLabLink } from "./experience/deepLink";
export type { LabDeepLink, SecondBrainDeepLink } from "./experience/deepLink";
export {
  buildSecondBrainShellHref,
  buildSecondBrainDashboardRoute,
  resolveSecondBrainOpenUrl,
  parseSecondBrainTabFromSearch,
} from "./experience/deepLink";
