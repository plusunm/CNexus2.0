"use client";

import type { DashboardPeerRow, DashboardTopology } from "@/lib/dashboardTypes";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  topology?: DashboardTopology;
  peers?: DashboardPeerRow[];
  localLabel?: string;
};

function edgeColor(peer?: DashboardPeerRow): string {
  if (peer?.fork_panic) return "#ef4444";
  if (peer?.aligned) return "#22c55e";
  if (peer?.status === "online") return "#f59e0b";
  return "#64748b";
}

export function MissionTopologyGraph({ topology, peers = [], localLabel = "本节点" }: Props) {
  const t = useMindTheme();
  const cx = 220;
  const cy = 180;
  const radius = 120;
  const localId = topology?.nodes?.[0]?.id || "local";

  const peerNodes = peers.length
    ? peers
    : (topology?.nodes || []).filter((n) => n.id !== localId).map((n) => ({
        pubkey: n.id,
        host: n.name,
        status: n.status,
        aligned: false,
        fork_panic: false,
      }));

  return (
    <div
      className="rounded-xl border p-3 w-full overflow-hidden"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <svg viewBox="0 0 440 360" className="w-full h-[320px]">
        {peerNodes.map((peer, index) => {
          const angle = (index / Math.max(peerNodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
          const x = cx + Math.cos(angle) * radius;
          const y = cy + Math.sin(angle) * radius;
          const color = edgeColor(peer);
          const fork = Boolean(peer.fork_panic);
          const label =
            peer.host ||
            ("pubkey_short" in peer ? peer.pubkey_short : undefined) ||
            peer.pubkey?.slice(0, 8) ||
            "peer";
          return (
            <g key={peer.pubkey || index}>
              <line
                x1={cx}
                y1={cy}
                x2={x}
                y2={y}
                stroke={color}
                strokeWidth={fork ? 3 : 2}
                strokeDasharray={fork ? "6 4" : undefined}
                opacity={0.85}
              />
              <circle cx={x} cy={y} r={22} fill={t.surface} stroke={color} strokeWidth={2} />
              <text x={x} y={y + 4} textAnchor="middle" fontSize="9" fill={t.textMuted}>
                {label.slice(0, 8)}
              </text>
            </g>
          );
        })}
        <circle cx={cx} cy={cy} r={30} fill={t.blue} opacity={0.9} />
        <circle cx={cx} cy={cy} r={34} fill="none" stroke="#5eead4" strokeWidth={2} opacity={0.5} />
        <text x={cx} y={cy + 4} textAnchor="middle" fontSize="11" fill="#fff" fontWeight="600">
          {localLabel.slice(0, 6)}
        </text>
      </svg>
    </div>
  );
}
