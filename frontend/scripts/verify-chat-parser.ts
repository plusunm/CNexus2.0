import { ChatParser, parseChatLog } from "../lib/relationshipAnalysis/import/chatParser";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

const parser = new ChatParser();

const generic = parser.parse(`2025-04-01 10:00 A: 在干嘛
2025-04-01 10:05 B: 刚下班
2025-04-01 10:10 A: 周末一起吃饭？`);
assert(generic.turns.length === 3, "generic: 3 turns");
assert(generic.turns[0].speaker === "A", "generic speaker A");
assert(generic.turns[0].text === "在干嘛", "generic text");

const wechat = parser.parse(`2025-04-01 10:00:00 张三
在干嘛
2025-04-01 10:05:00 李四
刚下班`);
assert(wechat.turns.length === 2, "wechat: 2 turns");
assert(wechat.participants[0] === "张三", "wechat participant A");
assert(wechat.turns[1].text === "刚下班", "wechat message body");

const aliased = parseChatLog(`2025-04-01 10:00 张三: hi
2025-04-01 10:01 李四: hello`, { entityA: "我", entityB: "对方" });
assert(aliased.turns[0].speaker === "我", "alias A");
assert(aliased.turns[1].speaker === "对方", "alias B");

const csv = parser.parseCsv(`timestamp,speaker,text
2025-04-01T10:00:00,A,第一条
2025-04-01T10:05:00,B,第二条`);
assert(csv.turns.length === 2, "csv: 2 turns");

const bracket = parser.parse(`[2025-04-01 10:00:00] A: bracket format`);
assert(bracket.turns.length === 1, "bracket: 1 turn");

console.log("Chat parser verification: OK");
