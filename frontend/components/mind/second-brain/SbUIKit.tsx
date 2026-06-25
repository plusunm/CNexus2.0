"use client";

import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import { useMindTheme } from "../MindUiProvider";

type SbSectionProps = {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

export function SbSection({ title, subtitle, icon: Icon, action, children, className }: SbSectionProps) {
  const t = useMindTheme();
  return (
    <section className={clsx("space-y-3", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 shrink-0" style={{ color: "#5eead4" }} />}
            <h2 className="text-sm font-semibold tracking-tight" style={{ color: t.text }}>
              {title}
            </h2>
          </div>
          {subtitle && (
            <p className="text-xs mt-1 leading-relaxed" style={{ color: t.textMuted }}>
              {subtitle}
            </p>
          )}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

type SbCardProps = {
  children: React.ReactNode;
  className?: string;
  accent?: "teal" | "purple" | "blue" | "none";
  padding?: "sm" | "md";
};

const ACCENT_BORDER: Record<NonNullable<SbCardProps["accent"]>, string> = {
  teal: "#5eead4",
  purple: "#A78BFA",
  blue: "#3B82F6",
  none: "transparent",
};

export function SbCard({ children, className, accent = "none", padding = "md" }: SbCardProps) {
  const t = useMindTheme();
  return (
    <div
      className={clsx(
        "rounded-2xl border overflow-hidden",
        padding === "sm" ? "p-3" : "p-4",
        className,
      )}
      style={{
        borderColor: accent !== "none" ? `${ACCENT_BORDER[accent]}44` : t.border,
        backgroundColor: t.surface,
        boxShadow: accent !== "none" ? `0 1px 0 ${ACCENT_BORDER[accent]}22 inset` : undefined,
      }}
    >
      {children}
    </div>
  );
}

type SbStatProps = {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "teal" | "purple" | "orange";
};

export function SbStat({ label, value, hint, tone = "default" }: SbStatProps) {
  const t = useMindTheme();
  const valueColor =
    tone === "teal" ? "#5eead4" : tone === "purple" ? t.purple : tone === "orange" ? t.orange : t.text;
  return (
    <SbCard padding="sm" className="flex flex-col gap-1 min-w-0">
      <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: t.textLight }}>
        {label}
      </span>
      <span className="text-lg font-semibold tabular-nums truncate" style={{ color: valueColor }}>
        {value}
      </span>
      {hint && (
        <span className="text-[10px] leading-snug line-clamp-2" style={{ color: t.textMuted }}>
          {hint}
        </span>
      )}
    </SbCard>
  );
}

type SbSettingRowProps = {
  label?: string;
  hint?: string;
  children: React.ReactNode;
};

export function SbSettingRow({ label, hint, children }: SbSettingRowProps) {
  const t = useMindTheme();
  return (
    <div className="space-y-2">
      {(label || hint) && (
        <div>
          {label && (
            <p className="text-xs font-medium" style={{ color: t.text }}>
              {label}
            </p>
          )}
          {hint && (
            <p className="text-[11px] mt-0.5 leading-relaxed" style={{ color: t.textMuted }}>
              {hint}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

type SbChipProps = {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
};

export function SbChip({ active, onClick, children }: SbChipProps) {
  const t = useMindTheme();
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-3 py-1.5 rounded-full text-xs font-medium transition border"
      style={{
        borderColor: active ? "#5eead488" : t.border,
        backgroundColor: active ? "rgba(94,234,212,0.12)" : "transparent",
        color: active ? "#5eead4" : t.textMuted,
      }}
    >
      {children}
    </button>
  );
}

type SbSegmentOption<T extends string> = {
  id: T;
  label: string;
  hint?: string;
};

type SbSegmentProps<T extends string> = {
  value: T;
  options: SbSegmentOption<T>[];
  onChange: (value: T) => void;
  disabled?: boolean;
  tone?: "teal" | "blue" | "purple";
};

export function SbSegment<T extends string>({
  value,
  options,
  onChange,
  disabled,
  tone = "teal",
}: SbSegmentProps<T>) {
  const t = useMindTheme();
  const activeColor = tone === "teal" ? "#5eead4" : tone === "blue" ? t.blue : t.purple;
  const activeBg =
    tone === "teal" ? "rgba(94,234,212,0.14)" : tone === "blue" ? t.blueSoft : t.purpleSoft;

  return (
    <div className="space-y-1.5">
      <div
        className="flex flex-wrap gap-1 p-1 rounded-xl border"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
        role="radiogroup"
      >
        {options.map((option) => {
          const active = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              title={option.hint}
              onClick={() => onChange(option.id)}
              className="flex-1 min-w-[4.5rem] px-2.5 py-2 rounded-lg text-xs font-medium transition disabled:opacity-50"
              style={{
                color: active ? activeColor : t.textMuted,
                backgroundColor: active ? activeBg : "transparent",
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function SbPageIntro({ title, subtitle }: { title: string; subtitle?: string }) {
  const t = useMindTheme();
  return (
    <div className="mb-1">
      <h1 className="text-lg font-semibold tracking-tight" style={{ color: t.text }}>
        {title}
      </h1>
      {subtitle && (
        <p className="text-xs mt-1 leading-relaxed" style={{ color: t.textMuted }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function SbEmptyState({ children }: { children: React.ReactNode }) {
  const t = useMindTheme();
  return (
    <div
      className="rounded-xl border border-dashed px-4 py-6 text-center text-sm leading-relaxed"
      style={{ borderColor: t.border, color: t.textMuted, backgroundColor: t.chatBg }}
    >
      {children}
    </div>
  );
}
