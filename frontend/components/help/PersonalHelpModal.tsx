"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, FolderOpen, Loader2 } from "lucide-react";
import { FloatingMiniDialog } from "@/components/mind/floating/FloatingMiniDialog";
import { SimpleMarkdown } from "@/components/help/SimpleMarkdown";
import { fetchPersonalHelpMarkdown, openPersonalDataDir } from "@/lib/personalHelp";
import { usePersonalHelpUiStore } from "@/lib/personalHelpUiStore";
import { bi, gatewayL } from "@/lib/spine/labels";
import { floatTy } from "@/lib/floatTypography";

type Props = {
  /** Wider layout for main shell pages */
  wide?: boolean;
};

export function PersonalHelpModal({ wide = false }: Props) {
  const open = usePersonalHelpUiStore((s) => s.open);
  const closeHelp = usePersonalHelpUiStore((s) => s.closeHelp);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const text = await fetchPersonalHelpMarkdown();
      setMarkdown(text);
    } catch (err) {
      setMarkdown(null);
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void load();
  }, [open, load]);

  if (!open) return null;

  return (
    <FloatingMiniDialog
      title={bi(gatewayL.openHelpGuide)}
      onClose={closeHelp}
      width={wide ? 560 : 420}
      placement={wide ? "portal" : "panel"}
    >
      <div className={`space-y-3 ${floatTy.body}`}>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 ${floatTy.btn} text-zinc-200 bg-white/8 border border-white/15`}
            onClick={() => void load()}
            disabled={loading}
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BookOpen className="w-3.5 h-3.5" />}
            刷新
          </button>
          <button
            type="button"
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 ${floatTy.btn} text-zinc-200 bg-white/8 border border-white/15`}
            onClick={() => void openPersonalDataDir()}
          >
            <FolderOpen className="w-3.5 h-3.5" />
            {bi(gatewayL.openLogsFolder)}
          </button>
        </div>

        <div className="max-h-[min(70vh,520px)] overflow-y-auto pr-1">
          {loading && !markdown ? (
            <div className="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
              正在加载帮助文档…
            </div>
          ) : error ? (
            <p className="text-sm text-amber-300/90 rounded-md border border-amber-400/30 bg-amber-400/10 px-3 py-2">
              {error}
            </p>
          ) : markdown ? (
            <SimpleMarkdown source={markdown} />
          ) : null}
        </div>
      </div>
    </FloatingMiniDialog>
  );
}

export function openPersonalHelpGuide(): void {
  usePersonalHelpUiStore.getState().openHelp();
}
