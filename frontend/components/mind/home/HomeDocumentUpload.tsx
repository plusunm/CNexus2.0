"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Circle, FileStack, Loader2, UploadCloud } from "lucide-react";
import { useMindOverview, useMindStore } from "@/cnexus-kernel";
import { useMindConnection } from "@/cnexus-kernel/MindConnectionProvider";
import { useMindTheme } from "../MindUiProvider";
import { isPersonalMode } from "@/lib/personalGuard";
import {
  DOCUMENT_ACCEPT,
  formatIngestKeywords,
  ingestDocumentFiles,
  pollDocumentIngestProgress,
  readLocalTextFile,
  type IngestJobProgress,
} from "@/lib/documentIngest";
import {
  UploadCorpusOptions,
  useUploadCorpusState,
} from "@/components/mind/UploadCorpusOptions";
import {
  buildDocumentUploadGate,
  documentUploadStatusHint,
  ensureDocumentUploadReady,
  formatImportError,
} from "@/lib/memoryWriteReady";
import { useShellNavigation } from "@/lib/shellNavigation";

type ProcessingRow = {
  filename: string;
  status: "queued" | "processing" | "indexed" | "error";
};

type Props = {
  onImported?: (count: number, keywords?: string[]) => void;
  compact?: boolean;
  /** 导入成功后是否跳转到记忆流图（工作台内应关闭） */
  navigateAfterImport?: boolean;
};

function mergeProcessingRows(
  base: ProcessingRow[],
  jobs: IngestJobProgress[],
): ProcessingRow[] {
  const byName = new Map(base.map((row) => [row.filename, { ...row }]));
  for (const job of jobs) {
    for (const detail of job.details) {
      const name = detail.filename?.trim();
      if (!name) continue;
      const prev = byName.get(name) ?? { filename: name, status: "queued" as const };
      if (detail.status === "indexed") prev.status = "indexed";
      else if (detail.status === "error") prev.status = "error";
      else if (job.status === "processing") prev.status = "processing";
      byName.set(name, prev);
    }
    if (job.latestFinished) {
      const row = byName.get(job.latestFinished);
      if (row && row.status !== "error") row.status = "indexed";
    }
  }
  return base.map((row) => byName.get(row.filename) ?? row);
}

/** 批量文档上传 — 写入长期记忆 */
export function HomeDocumentUpload({ onImported, compact, navigateAfterImport = false }: Props) {
  const t = useMindTheme();
  const { effectiveMode } = useMindConnection();
  const { isDemo, canUploadDocuments } = useMindOverview();
  const afterMemoryCapture = useMindStore((s) => s.afterMemoryCapture);
  const pullMindOverview = useMindStore((s) => s.pullMindOverview);
  const { navigateFlowAfterImport } = useShellNavigation();
  const inputRef = useRef<HTMLInputElement>(null);
  const stopPollRef = useRef<(() => void) | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [layer, setLayer] = useState<"episodic" | "goal">("episodic");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [processing, setProcessing] = useState<ProcessingRow[]>([]);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const uploadCorpus = useUploadCorpusState();

  useEffect(() => {
    return () => {
      stopPollRef.current?.();
    };
  }, []);

  const personalRuntime = isPersonalMode() && effectiveMode === "runtime";
  const writeGate = buildDocumentUploadGate(useMindStore.getState().effectiveMode);
  const canImport = isDemo || canUploadDocuments || personalRuntime;
  const statusHint = personalRuntime ? null : documentUploadStatusHint(writeGate);
  const progressPct =
    progress.total > 0 ? Math.min(100, Math.round((progress.done / progress.total) * 100)) : 0;

  const addFiles = (list: FileList | null) => {
    if (!list?.length) return;
    setFiles((prev) => [...prev, ...Array.from(list)]);
    setNote(null);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const startBackgroundPoll = (traceIds: string[], submitted: ProcessingRow[], total: number) => {
    stopPollRef.current?.();
    stopPollRef.current = pollDocumentIngestProgress(
      traceIds,
      (jobs) => {
        const done = jobs.reduce((sum, job) => sum + job.done, 0);
        const jobTotal = jobs.reduce((sum, job) => sum + (job.total || 0), 0) || total;
        setProgress({ done, total: jobTotal });
        setProcessing((prev) => mergeProcessingRows(prev.length ? prev : submitted, jobs));
        const latest = jobs.map((job) => job.latestFinished).filter(Boolean).pop();
        if (latest) {
          setNote(`后台索引中… ${done}/${jobTotal} · 最近完成：${latest}`);
        } else {
          setNote(`后台索引中… ${done}/${jobTotal}`);
        }
      },
      {
        onComplete: () => {
          void pullMindOverview();
          const base = `已成功导入 ${total} 个文档到${layer === "goal" ? "目标" : "经历"}记忆${
            uploadCorpus.corpus === "expert" ? `（专家语料 · ${uploadCorpus.subjectId}）` : ""
          }`;
          setNote(navigateAfterImport ? `${base} · 已跳转记忆流图` : base);
          setProcessing([]);
          if (navigateAfterImport) navigateFlowAfterImport();
          onImported?.(total);
        },
        onError: (err) => {
          setNote(formatImportError(err, "后台索引未完成"));
        },
      },
    );
  };

  const importAll = async () => {
    if (files.length === 0) {
      setNote("请先选择要上传的文档");
      return;
    }
    if (!isDemo) {
      const ready = await ensureDocumentUploadReady(writeGate);
      if (!ready.ok) {
        setNote(ready.hint ?? statusHint ?? "Runtime 未连接，无法上传");
        return;
      }
    }

    setBusy(true);
    setNote(null);
    let ok = 0;
    let lastKeywords: string[] | undefined;
    let lastError: string | null = null;

    try {
      if (isDemo) {
        for (const file of files) {
          const text = await readLocalTextFile(file);
          await afterMemoryCapture({ content: text, layer, label: file.name, refresh: false });
          ok += 1;
        }
      } else {
        const picked = [...files];
        const { items, traceIds } = await ingestDocumentFiles(picked, {
          layer,
          cognize: false,
          ...uploadCorpus.ingestExpertFields,
        });
        ok = items.length;
        if (ok > 0 && traceIds.length > 0) {
          const queuedRows: ProcessingRow[] = items.map((item) => ({
            filename: item.filename,
            status: "queued",
          }));
          setProcessing(queuedRows);
          setProgress({ done: 0, total: ok });
          setFiles([]);
          if (inputRef.current) inputRef.current.value = "";
          setNote(`已提交 ${ok} 个文件，后台索引中…`);
          setBusy(false);
          startBackgroundPoll(traceIds, queuedRows, ok);
          return;
        }
      }
    } catch (err) {
      lastError = formatImportError(err, "导入失败");
    }

    if (!isDemo && ok > 0) {
      await pullMindOverview();
    }

    setBusy(false);
    if (ok > 0) {
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      const keywordHint = formatIngestKeywords(lastKeywords);
      const base = `已成功导入 ${ok} 个文档到${layer === "goal" ? "目标" : "经历"}记忆${
        uploadCorpus.corpus === "expert" ? `（专家语料 · ${uploadCorpus.subjectId}）` : ""
      }`;
      setNote(
        navigateAfterImport
          ? keywordHint
            ? `${base} · 关键词：${keywordHint} · 已跳转记忆流图`
            : `${base} · 已跳转记忆流图`
          : keywordHint
            ? `${base} · 关键词：${keywordHint}`
            : base,
      );
      if (navigateAfterImport) navigateFlowAfterImport();
      onImported?.(ok, lastKeywords);
    } else {
      setNote(lastError ?? (isDemo ? "导入失败" : "导入失败 — 请确认 Runtime 已连接"));
    }
  };

  return (
    <section
      className={`rounded-2xl border ${compact ? "p-3 flex-1 flex flex-col min-h-0" : "p-4"}`}
      style={{ borderColor: t.border, backgroundColor: t.surface }}
    >
      <div className={`flex items-center justify-between gap-2 ${compact ? "mb-2" : "mb-3"}`}>
        <div className="flex items-center gap-2 min-w-0">
          <FileStack className="w-4 h-4 shrink-0" style={{ color: t.green }} />
          <h3 className="text-sm font-semibold truncate" style={{ color: t.text }}>
            批量上传文档
          </h3>
        </div>
        <div className="flex gap-1 p-0.5 rounded-lg text-[10px] shrink-0" style={{ backgroundColor: t.chatBg }}>
          {(
            [
              { id: "episodic" as const, label: "经历记忆" },
              { id: "goal" as const, label: "目标记忆" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => setLayer(opt.id)}
              className="px-2.5 py-1 rounded-md font-medium"
              style={{
                backgroundColor: layer === opt.id ? t.greenSoft : "transparent",
                color: layer === opt.id ? t.green : t.textMuted,
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {statusHint && (
        <p className="text-[11px] mb-2 leading-snug" style={{ color: t.orange }}>
          {statusHint}
        </p>
      )}

      <UploadCorpusOptions
        className={compact ? "mb-2" : "mb-3"}
        compact={compact}
        corpus={uploadCorpus.corpus}
        onCorpusChange={uploadCorpus.setCorpus}
        subjectId={uploadCorpus.subjectId}
        onSubjectIdChange={uploadCorpus.setSubjectId}
        semanticDimension={uploadCorpus.semanticDimension}
        onSemanticDimensionChange={uploadCorpus.setSemanticDimension}
      />

      <div className={compact ? "flex flex-col gap-2 flex-1 min-h-0" : "grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3"}>
        <label
          className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed transition-colors ${
            compact ? "p-4 flex-1 min-h-[100px]" : "p-5"
          } ${
            !canImport && !isDemo
              ? "opacity-55 cursor-not-allowed pointer-events-none"
              : "cursor-pointer"
          }`}
          style={{
            borderColor: dragging ? t.green : `${t.green}55`,
            backgroundColor: dragging ? t.greenSoft : t.chatBg,
          }}
          onDragEnter={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            addFiles(e.dataTransfer.files);
          }}
        >
          <UploadCloud className={compact ? "w-6 h-6" : "w-7 h-7"} style={{ color: t.green }} />
          <span className="text-[11px] text-center leading-snug px-2" style={{ color: t.textMuted }}>
            {compact ? "拖拽或点击选择多个文件" : "拖拽 PDF / Word / TXT / Markdown，或点击选择多个文件"}
          </span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={DOCUMENT_ACCEPT}
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
        </label>

        <div className={compact ? "flex gap-2" : "flex flex-col gap-2 min-w-[140px]"}>
          <button
            type="button"
            disabled={busy || files.length === 0 || (!canImport && !isDemo)}
            onClick={() => void importAll()}
            className={`rounded-xl text-sm font-medium disabled:opacity-40 flex items-center justify-center gap-2 ${
              compact ? "flex-1 py-2" : "py-2.5 px-4"
            }`}
            style={{ backgroundColor: t.green, color: "#fff" }}
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            开始导入 {files.length > 0 ? `(${files.length})` : ""}
          </button>
          {files.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setFiles([]);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className={`rounded-lg text-xs border ${compact ? "px-3 py-2" : "py-2"}`}
              style={{ borderColor: t.border, color: t.textMuted }}
            >
              清空
            </button>
          )}
        </div>
      </div>

      {files.length > 0 && (
        <ul className={`mt-2 overflow-auto space-y-1 ${compact ? "max-h-[72px]" : "max-h-[120px]"}`}>
          {files.map((file, i) => (
            <li
              key={`${file.name}-${i}`}
              className="flex items-center justify-between gap-2 text-xs px-3 py-1.5 rounded-lg"
              style={{ backgroundColor: t.chatBg, color: t.textMuted }}
            >
              <span className="truncate">{file.name}</span>
              <button type="button" onClick={() => removeFile(i)} style={{ color: t.red }}>
                移除
              </button>
            </li>
          ))}
        </ul>
      )}

      {processing.length > 0 && (
        <div className="mt-3 space-y-2">
          <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: t.chatBg }}>
            <div
              className="h-full transition-all duration-300"
              style={{ width: `${progressPct}%`, backgroundColor: t.green }}
            />
          </div>
          <p className="text-[10px]" style={{ color: t.textMuted }}>
            后台索引 {progress.done}/{progress.total}
          </p>
          <ul className={`overflow-auto space-y-1 ${compact ? "max-h-[96px]" : "max-h-[160px]"}`}>
            {processing.map((row) => (
              <li
                key={row.filename}
                className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg"
                style={{ backgroundColor: t.chatBg, color: t.textMuted }}
              >
                {row.status === "indexed" ? (
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" style={{ color: t.green }} />
                ) : row.status === "processing" ? (
                  <Loader2 className="w-3.5 h-3.5 shrink-0 animate-spin" style={{ color: t.blue }} />
                ) : (
                  <Circle className="w-3.5 h-3.5 shrink-0" />
                )}
                <span className="truncate flex-1">{row.filename}</span>
                <span className="shrink-0 text-[10px]">
                  {row.status === "indexed"
                    ? "已索引"
                    : row.status === "processing"
                      ? "处理中"
                      : row.status === "error"
                        ? "失败"
                        : "排队中"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {note && (
        <p className="mt-2 text-xs" style={{ color: note.includes("成功") || note.includes("已提交") ? t.green : t.orange }}>
          {note}
        </p>
      )}
    </section>
  );
}
