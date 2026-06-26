"use client";

import { useEffect, useState } from "react";
import { brainApi } from "@/lib/api";
import { useMindTheme } from "./MindUiProvider";

type ActiveProject = {
  project_id?: string;
  name?: string;
  locked?: boolean;
  lifecycle_id?: string;
};

export function ActiveProjectBadge() {
  const t = useMindTheme();
  const [active, setActive] = useState<ActiveProject | null>(null);

  useEffect(() => {
    void brainApi.projectActive().then((data) => setActive((data.active_project as ActiveProject) || null)).catch(() => setActive(null));
  }, []);

  if (!active?.project_id) return null;

  const locked = Boolean(active.locked);

  return (
    <span
      className="text-[10px] px-2 py-0.5 rounded-full border cursor-pointer"
      style={{
        borderColor: locked ? "#38bdf8" : t.border,
        color: locked ? "#38bdf8" : t.textMuted,
        backgroundColor: locked ? "rgba(56,189,248,0.08)" : "transparent",
      }}
      title={locked ? "L3 project lock active" : "Active project (unlocked)"}
      onClick={() => {
        void brainApi
          .setProjectActive({ project_id: active.project_id || "default", lock: !locked })
          .then((data) => setActive((data.active_project as ActiveProject) || null))
          .catch(() => undefined);
      }}
    >
      {active.name || active.project_id}
      {locked ? " · locked" : ""}
      {active.lifecycle_id ? ` · ${active.lifecycle_id}` : ""}
    </span>
  );
}
