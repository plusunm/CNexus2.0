import type { ExperiencePersona } from "./types";

const STORAGE_KEY = "cnexus-experience-persona";

export function loadExperiencePersona(): ExperiencePersona | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === "second-brain" || raw === "cognitive-lab") return raw;
  return null;
}

export function saveExperiencePersona(persona: ExperiencePersona): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, persona);
}

export function defaultExperiencePersona(): ExperiencePersona {
  return "second-brain";
}
