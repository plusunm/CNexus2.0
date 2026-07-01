"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { parseOverviewView } from "@/cnexus-kernel/shellTypes";
import { parseSecondBrainTabFromSearch } from "./deepLink";
import type { CognitiveDialect } from "../projection/copyLexicon";
import {
  defaultExperiencePersona,
  loadExperiencePersona,
  saveExperiencePersona,
} from "./storage";
import {
  LAB_ONLY_VIEWS,
  PERSONA_DEFAULT_DIALECT,
  normalizeSecondBrainTab,
  type ExperiencePersona,
  type SecondBrainTab,
} from "./types";

type ExperienceContextValue = {
  persona: ExperiencePersona;
  dialect: CognitiveDialect;
  setPersona: (persona: ExperiencePersona) => void;
  isSecondBrain: boolean;
  isCognitiveLab: boolean;
  secondBrainTab: SecondBrainTab;
  setSecondBrainTab: (tab: SecondBrainTab) => void;
};

const ExperienceContext = createContext<ExperienceContextValue | null>(null);

function resolvePersonaFromLocation(): ExperiencePersona | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const experienceParam = params.get("experience");
  if (experienceParam === "second-brain" || experienceParam === "cognitive-lab") {
    return experienceParam;
  }
  const parsed = parseOverviewView(params.get("view"));
  if (LAB_ONLY_VIEWS.has(parsed)) return "cognitive-lab";
  return null;
}

export function ExperienceProvider({ children }: { children: ReactNode }) {
  const [persona, setPersonaState] = useState<ExperiencePersona>(defaultExperiencePersona());
  const [secondBrainTab, setSecondBrainTabState] = useState<SecondBrainTab>("chat");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const urlPersona = resolvePersonaFromLocation();
    const stored = loadExperiencePersona();
    setPersonaState(urlPersona ?? stored ?? defaultExperiencePersona());

    const urlTab = parseSecondBrainTabFromSearch(window.location.search);
    if (urlTab) setSecondBrainTabState(urlTab);

    setHydrated(true);

    const onPop = () => {
      const next = resolvePersonaFromLocation();
      if (next) setPersonaState(next);
      const tab = parseSecondBrainTabFromSearch(window.location.search);
      if (tab) setSecondBrainTabState(tab);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const setPersona = useCallback((next: ExperiencePersona) => {
    setPersonaState(next);
    saveExperiencePersona(next);
    window.dispatchEvent(new CustomEvent("cnexus:experience-change", { detail: next }));
  }, []);

  const setSecondBrainTab = useCallback((tab: SecondBrainTab) => {
    const normalized = normalizeSecondBrainTab(tab);
    setSecondBrainTabState(normalized);
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (normalized === "chat") url.searchParams.delete("tab");
    else url.searchParams.set("tab", normalized);
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }, []);

  const dialect = PERSONA_DEFAULT_DIALECT[persona];

  const value = useMemo(
    (): ExperienceContextValue => ({
      persona,
      dialect,
      setPersona,
      isSecondBrain: persona === "second-brain",
      isCognitiveLab: persona === "cognitive-lab",
      secondBrainTab,
      setSecondBrainTab,
    }),
    [persona, dialect, setPersona, secondBrainTab, setSecondBrainTab],
  );

  if (!hydrated) {
    return <ExperienceContext.Provider value={value}>{children}</ExperienceContext.Provider>;
  }

  return <ExperienceContext.Provider value={value}>{children}</ExperienceContext.Provider>;
}

export function useExperience(): ExperienceContextValue {
  const ctx = useContext(ExperienceContext);
  if (!ctx) throw new Error("useExperience must be used within ExperienceProvider");
  return ctx;
}

export function useExperienceOptional(): ExperienceContextValue | null {
  return useContext(ExperienceContext);
}
