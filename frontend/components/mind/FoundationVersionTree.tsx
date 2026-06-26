"use client";

import type { ReactNode } from "react";
import { useMindTheme } from "./MindUiProvider";

export type FoundationVersionNode = {
  block_id: string;
  version_label?: string;
  memory_version?: number;
  active?: boolean;
  superseded?: boolean;
  title?: string;
  children?: FoundationVersionNode[];
};

type TreePayload = {
  constitution_key: string;
  active_block_id?: string | null;
  version_count?: number;
  roots?: FoundationVersionNode[];
};

function VersionNode({ node, depth = 0 }: { node: FoundationVersionNode; depth?: number }) {
  const t = useMindTheme();
  const label = node.version_label || `v${node.memory_version ?? "?"}`;
  const isActive = node.active && !node.superseded;
  return (
    <div style={{ marginLeft: depth * 14 }}>
      <div
        className="flex items-center gap-2 py-1 text-[11px]"
        style={{ color: isActive ? t.purple || "#a78bfa" : t.textMuted }}
      >
        <span className="font-mono">{label}</span>
        {isActive && (
          <span className="text-[10px] px-1 rounded" style={{ backgroundColor: `${t.purple || "#a78bfa"}22` }}>
            active
          </span>
        )}
        <span className="truncate">{node.title}</span>
      </div>
      {(node.children || []).map((child) => (
        <VersionNode key={child.block_id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export function FoundationVersionTree({ trees }: { trees: TreePayload[] }) {
  const t = useMindTheme();
  if (!trees.length) return null;

  const blocks: ReactNode[] = [];
  for (const tree of trees) {
    blocks.push(
      <div key={tree.constitution_key} className="mb-3">
        <p className="text-[10px] font-semibold mb-1" style={{ color: t.textLight }}>
          {tree.constitution_key} · {tree.version_count ?? 0} 版
        </p>
        {(tree.roots || []).map((root) => (
          <VersionNode key={root.block_id} node={root} />
        ))}
      </div>,
    );
  }

  return (
    <div
      className="mb-2 px-2 py-2 rounded-lg border text-left"
      style={{ borderColor: t.border, backgroundColor: t.bg }}
    >
      <p className="text-[10px] font-semibold mb-2" style={{ color: t.blue }}>
        Foundation 版本链
      </p>
      {blocks}
    </div>
  );
}
