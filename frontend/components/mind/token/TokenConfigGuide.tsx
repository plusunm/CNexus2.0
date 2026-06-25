"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { bi, biSection, tokenL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  variant?: "full" | "compact";
};

export function TokenConfigGuide({ variant = "full" }: Props) {
  const t = useMindTheme();
  const [open, setOpen] = useState(variant === "full");

  if (variant === "compact") {
    return (
      <section
        className="rounded-lg border p-3 space-y-2 shrink-0"
        style={{ borderColor: t.border, backgroundColor: t.chatBg }}
      >
        <p className="text-[11px] font-medium flex items-center gap-1.5" style={{ color: t.text }}>
          <BookOpen className="w-3.5 h-3.5 shrink-0" style={{ color: t.blue }} />
          {biSection(tokenL.guideTitle)}
        </p>
        <p className="text-[10px] leading-relaxed" style={{ color: t.textMuted }}>
          {bi(tokenL.guideIntro)}
        </p>
        <p
          className="text-[10px] leading-relaxed rounded px-2 py-1.5"
          style={{ backgroundColor: `${t.orange}18`, color: t.orange }}
        >
          {bi(tokenL.guideNoteEstimated)}
        </p>
        <Link
          href="/shell/?layout=overview&view=llm"
          className="inline-flex items-center gap-1 text-[10px] font-medium"
          style={{ color: t.blue }}
        >
          <ExternalLink className="w-3 h-3" />
          {bi(tokenL.guideOpenLlmConfig)}
        </Link>
      </section>
    );
  }

  const steps = [
    { title: biSection(tokenL.guideStep1Title), body: bi(tokenL.guideStep1Body) },
    { title: biSection(tokenL.guideStep2Title), body: bi(tokenL.guideStep2Body) },
    { title: biSection(tokenL.guideStep3Title), body: bi(tokenL.guideStep3Body) },
    { title: biSection(tokenL.guideStep4Title), body: bi(tokenL.guideStep4Body) },
    { title: biSection(tokenL.guideStep5Title), body: bi(tokenL.guideStep5Body) },
  ];

  return (
    <section
      className="rounded-xl border overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium" style={{ color: t.text }}>
          <BookOpen className="w-4 h-4 shrink-0" style={{ color: t.blue }} />
          {biSection(tokenL.guideTitle)}
        </span>
        {open ? (
          <ChevronUp className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
        ) : (
          <ChevronDown className="w-4 h-4 shrink-0" style={{ color: t.textMuted }} />
        )}
      </button>

      {open ? (
        <div className="px-4 pb-4 space-y-3 border-t" style={{ borderColor: t.border }}>
          <p className="text-xs leading-relaxed pt-3" style={{ color: t.textMuted }}>
            {bi(tokenL.guideIntro)}
          </p>

          <div className="grid gap-2">
            {steps.map((step, i) => (
              <div
                key={step.title}
                className="rounded-lg border px-3 py-2.5"
                style={{ borderColor: t.border, backgroundColor: t.surface }}
              >
                <p className="text-xs font-medium" style={{ color: t.text }}>
                  {i + 1}. {step.title}
                </p>
                <p className="text-[11px] mt-1 leading-relaxed whitespace-pre-line" style={{ color: t.textMuted }}>
                  {step.body}
                </p>
              </div>
            ))}
          </div>

          <div
            className="rounded-lg px-3 py-2 text-[11px] leading-relaxed"
            style={{ backgroundColor: `${t.orange}18`, color: t.orange }}
          >
            {bi(tokenL.guideNoteEstimated)}
          </div>

          <Link
            href="/shell/?layout=overview&view=llm"
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg border transition hover:opacity-90"
            style={{ borderColor: t.blue, color: t.blue, backgroundColor: t.blueSoft }}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            {bi(tokenL.guideOpenLlmConfig)}
          </Link>
        </div>
      ) : null}
    </section>
  );
}
