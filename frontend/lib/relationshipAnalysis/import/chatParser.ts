/**
 * Chat Parser v2 — raw chat logs → normalized ConversationTurn[].
 * Supports: generic timestamp+speaker, WeChat-style, CSV.
 */

import type { ConversationTurn } from "../events/eventOntology";

export type ParsedConversation = {
  turns: ConversationTurn[];
  participants: [string, string];
  warnings: string[];
};

const LINE_PATTERNS: Array<{
  re: RegExp;
  map: (m: RegExpMatchArray) => ConversationTurn | null;
}> = [
  {
    re: /^[\[【]?(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?)[\]】]?\s+([AB]|[\u4e00-\u9fa5A-Za-z0-9_]+)\s*[:：]\s*(.+)$/,
    map: (m) => ({ timestamp: m[1], speaker: m[2], text: m[3].trim() }),
  },
  {
    re: /^(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?)\s+([AB]|[\u4e00-\u9fa5A-Za-z0-9_]+)\s*[:：]\s*(.+)$/,
    map: (m) => ({ timestamp: m[1], speaker: m[2], text: m[3].trim() }),
  },
  {
    re: /^([AB])\s*[:：]\s*(.+)$/,
    map: (m) => ({ timestamp: Date.now(), speaker: m[1], text: m[2].trim() }),
  },
];

const WECHAT_HEADER =
  /^(\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?)\s+([\u4e00-\u9fa5A-Za-z0-9_]+)$/;

function parseTimestamp(raw: string | number): number {
  if (typeof raw === "number") return raw > 1e12 ? raw : raw * 1000;
  const d = Date.parse(String(raw).replace(" ", "T"));
  return Number.isFinite(d) ? d : Date.now();
}

function normalizeSpeakers(
  turns: ConversationTurn[],
  entityA?: string,
  entityB?: string,
): { turns: ConversationTurn[]; participants: [string, string] } {
  const speakers: string[] = [];
  for (const t of turns) {
    const sp = t.speaker.trim();
    if (sp && !speakers.includes(sp)) speakers.push(sp);
  }

  const a = entityA ?? speakers[0] ?? "A";
  const b = entityB ?? speakers[1] ?? (a === "A" ? "B" : "A");

  const alias = new Map<string, string>();
  if (speakers.length >= 1) alias.set(speakers[0], a);
  if (speakers.length >= 2) alias.set(speakers[1], b);
  for (const sp of speakers) {
    if (!alias.has(sp)) alias.set(sp, sp === speakers[0] ? a : b);
  }

  const normalized = turns.map((t) => ({
    ...t,
    speaker: alias.get(t.speaker.trim()) ?? t.speaker,
  }));

  return { turns: normalized, participants: [a, b] };
}

function parseCsvLine(line: string): ConversationTurn | null {
  const parts = line.split(",").map((p) => p.trim().replace(/^"|"$/g, ""));
  if (parts.length < 3) return null;
  const [ts, speaker, ...rest] = parts;
  const text = rest.join(",").trim();
  if (!text || !speaker) return null;
  return { timestamp: ts, speaker, text };
}

export class ChatParser {
  parse(rawText: string, options?: { entityA?: string; entityB?: string }): ParsedConversation {
    const warnings: string[] = [];
    const lines = rawText.replace(/\r\n/g, "\n").split("\n");
    const turns: ConversationTurn[] = [];
    let pendingWechat: { timestamp: string; speaker: string } | null = null;

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;

      if (line.toLowerCase().startsWith("timestamp,") || line.includes(",speaker,")) continue;

      const csv = parseCsvLine(line);
      if (csv && (/^\d{4}|^\d{10,}/.test(String(csv.timestamp)) || /^[AB]$/.test(csv.speaker))) {
        turns.push(csv);
        pendingWechat = null;
        continue;
      }

      const wx = line.match(WECHAT_HEADER);
      if (wx) {
        pendingWechat = { timestamp: wx[1], speaker: wx[2] };
        continue;
      }

      if (pendingWechat && line) {
        turns.push({
          timestamp: pendingWechat.timestamp,
          speaker: pendingWechat.speaker,
          text: line,
        });
        pendingWechat = null;
        continue;
      }

      let matched = false;
      for (const { re, map } of LINE_PATTERNS) {
        const m = line.match(re);
        if (m) {
          const row = map(m);
          if (row?.text) {
            turns.push(row);
            matched = true;
            break;
          }
        }
      }
      if (!matched && turns.length > 0) {
        const last = turns[turns.length - 1];
        last.text = `${last.text}\n${line}`;
      } else if (!matched) {
        warnings.push(`无法解析行: ${line.slice(0, 40)}…`);
      }
    }

    const sorted = [...turns].sort(
      (a, b) => parseTimestamp(a.timestamp) - parseTimestamp(b.timestamp),
    );

    const { turns: normalized, participants } = normalizeSpeakers(
      sorted,
      options?.entityA,
      options?.entityB,
    );

    if (normalized.length === 0) {
      warnings.push("未解析到任何消息，请检查格式（例：2025-04-01 10:00 A: 在干嘛）");
    }

    return { turns: normalized, participants, warnings };
  }

  parseFileContent(text: string, filename: string, options?: { entityA?: string; entityB?: string }) {
    const result = this.parse(text, options);
    if (filename.toLowerCase().endsWith(".csv") && result.turns.length === 0) {
      return this.parseCsv(text, options);
    }
    return result;
  }

  parseCsv(raw: string, options?: { entityA?: string; entityB?: string }): ParsedConversation {
    const warnings: string[] = [];
    const turns: ConversationTurn[] = [];
    for (const line of raw.replace(/\r\n/g, "\n").split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || /^timestamp[,，]/i.test(trimmed)) continue;
      const row = parseCsvLine(trimmed);
      if (!row) continue;
      if (!/^[\dAB]/i.test(String(row.timestamp))) continue;
      turns.push(row);
    }
    const { turns: normalized, participants } = normalizeSpeakers(turns, options?.entityA, options?.entityB);
    if (!normalized.length) warnings.push("CSV 无有效行");
    return { turns: normalized, participants, warnings };
  }
}

export const chatParser = new ChatParser();

export function parseChatLog(
  rawText: string,
  options?: { entityA?: string; entityB?: string },
): ParsedConversation {
  return chatParser.parse(rawText, options);
}
