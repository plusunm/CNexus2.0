"use client";

import clsx from "clsx";
import { useMindTheme } from "../../MindUiProvider";
import {
  DECISION_EXAMPLE_DOMAINS,
  THINKING_DOMAIN_COLORS,
  type DecisionExampleDomain,
} from "./thinkingDomains";

type Props = {
  value: DecisionExampleDomain;
  onChange: (domain: DecisionExampleDomain) => void;
  disabled?: boolean;
  className?: string;
};

export function ThinkingDomainNav({ value, onChange, disabled, className }: Props) {
  const t = useMindTheme();

  return (
    <nav
      className={clsx(
        "flex gap-1 p-1 rounded-xl border overflow-x-auto cnexus-float-scroll shrink-0",
        className,
      )}
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      aria-label="思考方向"
    >
      {DECISION_EXAMPLE_DOMAINS.map((domain) => {
        const active = domain === value;
        const color = THINKING_DOMAIN_COLORS[domain];
        return (
          <button
            key={domain}
            type="button"
            disabled={disabled}
            onClick={() => onChange(domain)}
            className="shrink-0 px-3 py-2 rounded-lg text-xs font-medium transition disabled:opacity-50 border border-transparent"
            style={{
              color: active ? color : t.textMuted,
              backgroundColor: active ? `${color}18` : "transparent",
              borderColor: active ? `${color}55` : "transparent",
            }}
            aria-current={active ? "page" : undefined}
          >
            {domain}
          </button>
        );
      })}
    </nav>
  );
}
