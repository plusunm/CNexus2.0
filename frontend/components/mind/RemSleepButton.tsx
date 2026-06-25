"use client";

import { useState } from "react";
import { Moon } from "lucide-react";
import clsx from "clsx";
import { cnexusProductApi } from "@/lib/api";
import { useMindStore } from "@/cnexus-kernel";
import { isPersonalMode } from "@/lib/personalGuard";
import { useCognitiveCopy } from "@/lib/cognitive";
import { useMindTheme } from "./MindUiProvider";

type Props = {
  compact?: boolean;
  className?: string;
  onComplete?: () => void;
  disabled?: boolean;
};

export function RemSleepButton({ compact, className, onComplete, disabled: disabledProp }: Props) {
  const t = useMindTheme();
  const { t: copy } = useCognitiveCopy();
  const pullMindOverview = useMindStore((s) => s.pullMindOverview);
  const [busy, setBusy] = useState(false);

  if (!isPersonalMode()) return null;

  const disabled = disabledProp || busy;

  const handleClick = async () => {
    if (disabled) return;
    if (!window.confirm(copy("remSleepConfirm"))) return;
    setBusy(true);
    try {
      const result = await cnexusProductApi.triggerRemSleep(true);
      if (result.skipped) {
        window.alert(`${copy("remSleepSkipped")}: ${result.skipped}`);
      } else {
        window.alert(copy("remSleepDone"));
      }
      await pullMindOverview();
      onComplete?.();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : copy("remSleepFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => void handleClick()}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium disabled:opacity-50 transition",
        compact ? "px-3 py-1.5 text-xs border" : "px-3 py-2 text-sm border",
        className,
      )}
      style={{
        borderColor: t.border,
        color: disabled ? t.textMuted : t.purple,
        backgroundColor: disabled ? "transparent" : `${t.purpleSoft}`,
      }}
    >
      <Moon className="w-3.5 h-3.5" />
      {busy ? copy("remSleepBusy") : copy("remSleepTrigger")}
    </button>
  );
}
