"use client";

import type { ReactNode } from "react";

type Block =
  | { type: "h1" | "h2" | "h3"; text: string }
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "pre"; text: string }
  | { type: "hr" };

function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let para: string[] = [];
  let list: string[] = [];
  let code: string[] = [];
  let inCode = false;

  const flushPara = () => {
    const text = para.join(" ").trim();
    if (text) blocks.push({ type: "p", text });
    para = [];
  };

  const flushList = () => {
    if (list.length) blocks.push({ type: "ul", items: [...list] });
    list = [];
  };

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.startsWith("```")) {
      if (inCode) {
        blocks.push({ type: "pre", text: code.join("\n") });
        code = [];
        inCode = false;
      } else {
        flushPara();
        flushList();
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      code.push(raw);
      continue;
    }

    if (!line.trim()) {
      flushPara();
      flushList();
      continue;
    }

    if (line === "---") {
      flushPara();
      flushList();
      blocks.push({ type: "hr" });
      continue;
    }

    if (line.startsWith("### ")) {
      flushPara();
      flushList();
      blocks.push({ type: "h3", text: line.slice(4).trim() });
      continue;
    }
    if (line.startsWith("## ")) {
      flushPara();
      flushList();
      blocks.push({ type: "h2", text: line.slice(3).trim() });
      continue;
    }
    if (line.startsWith("# ")) {
      flushPara();
      flushList();
      blocks.push({ type: "h1", text: line.slice(2).trim() });
      continue;
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      flushPara();
      list.push(line.slice(2).trim());
      continue;
    }

    if (/^\|.+\|$/.test(line)) {
      continue;
    }

    flushList();
    para.push(line.trim());
  }

  flushPara();
  flushList();
  if (inCode && code.length) blocks.push({ type: "pre", text: code.join("\n") });
  return blocks;
}

function renderInline(text: string): ReactNode {
  const parts = text.split(/(`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={i} className="px-1 py-0.5 rounded bg-white/10 font-mono text-[0.92em]">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function SimpleMarkdown({ source }: { source: string }) {
  const blocks = parseMarkdown(source);

  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {blocks.map((block, index) => {
        switch (block.type) {
          case "h1":
            return (
              <h1 key={index} className="text-base font-semibold text-zinc-100">
                {renderInline(block.text)}
              </h1>
            );
          case "h2":
            return (
              <h2 key={index} className="text-sm font-semibold text-zinc-200 pt-1">
                {renderInline(block.text)}
              </h2>
            );
          case "h3":
            return (
              <h3 key={index} className="text-sm font-medium text-zinc-300">
                {renderInline(block.text)}
              </h3>
            );
          case "p":
            return (
              <p key={index} className="text-zinc-400">
                {renderInline(block.text)}
              </p>
            );
          case "ul":
            return (
              <ul key={index} className="list-disc pl-5 space-y-1 text-zinc-400">
                {block.items.map((item, itemIndex) => (
                  <li key={itemIndex}>{renderInline(item)}</li>
                ))}
              </ul>
            );
          case "pre":
            return (
              <pre
                key={index}
                className="overflow-x-auto rounded-md bg-black/35 border border-white/10 p-2 text-xs text-zinc-300 font-mono whitespace-pre-wrap"
              >
                {block.text}
              </pre>
            );
          case "hr":
            return <hr key={index} className="border-white/10" />;
          default:
            return null;
        }
      })}
    </div>
  );
}
