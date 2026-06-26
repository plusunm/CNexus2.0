/** Cognitive copy lexicon — one capability, three dialects. */

import type { BilingualLabel } from "@/lib/spine/labels";

export type CognitiveDialect = "consumer" | "creator" | "research";

export type CognitiveCopyEntry = Record<CognitiveDialect, BilingualLabel>;

function copy(
  consumer: BilingualLabel,
  creator: BilingualLabel,
  research: BilingualLabel,
): CognitiveCopyEntry {
  return { consumer, creator, research };
}

export const cognitiveCopy = {
  // Persona
  personaSecondBrain: copy(
    { en: "Second Brain", zh: "第二大脑" },
    { en: "Second Brain", zh: "第二大脑" },
    { en: "Second Brain", zh: "第二大脑" },
  ),
  personaCognitiveLab: copy(
    { en: "Cognitive Lab", zh: "认知实验室" },
    { en: "Cognitive Lab", zh: "认知实验室" },
    { en: "Cognitive Lab", zh: "认知实验室" },
  ),
  personaSwitchHint: copy(
    { en: "Switch how you use CNexus", zh: "切换使用方式" },
    { en: "Switch cognitive interface", zh: "切换认知界面" },
    { en: "Switch cognitive interface", zh: "切换认知界面" },
  ),
  floatOpenBigWindowSection: copy(
    { en: "Open full window", zh: "打开大窗口" },
    { en: "Open full window", zh: "打开大窗口" },
    { en: "Open full window", zh: "打开大窗口" },
  ),
  floatSecondBrainBigWindow: copy(
    { en: "Second Brain · Full window", zh: "第二大脑 · 大窗口" },
    { en: "Second Brain · Full window", zh: "第二大脑 · 大窗口" },
    { en: "Second Brain · Full window", zh: "第二大脑 · 大窗口" },
  ),
  floatCognitiveLabBigWindow: copy(
    { en: "Cognitive Lab · Full window", zh: "认知实验室 · 大窗口" },
    { en: "Cognitive Lab · Full window", zh: "认知实验室 · 大窗口" },
    { en: "Cognitive Lab · Full window", zh: "认知实验室 · 大窗口" },
  ),
  floatBigWindowFootnote: copy(
    {
      en: "Quick chat stays in the float window; open a full window above for the complete UI.",
      zh: "悬浮窗适合快速对话；第二大脑与认知实验室的完整界面请点上方打开。",
    },
    {
      en: "Quick chat stays in the float window; open a full window above for the complete UI.",
      zh: "悬浮窗适合快速对话；第二大脑与认知实验室的完整界面请点上方打开。",
    },
    {
      en: "Quick chat stays in the float window; open a full window above for the complete UI.",
      zh: "悬浮窗适合快速对话；第二大脑与认知实验室的完整界面请点上方打开。",
    },
  ),
  switchToLab: copy(
    { en: "Enter Cognitive Lab — see the full cognitive chain", zh: "进入认知实验室 — 可查看完整认知链路" },
    { en: "Open Cognitive Lab", zh: "打开认知实验室" },
    { en: "Open Cognitive Lab", zh: "打开认知实验室" },
  ),
  switchToSecondBrain: copy(
    { en: "Back to Second Brain — focus on chat & memory", zh: "回到第二大脑 — 专注对话与记忆" },
    { en: "Back to Second Brain", zh: "回到第二大脑" },
    { en: "Back to Second Brain", zh: "回到第二大脑" },
  ),
  backToSecondBrain: copy(
    { en: "← Back to Second Brain", zh: "← 返回第二大脑" },
    { en: "← Back to Second Brain", zh: "← 返回第二大脑" },
    { en: "← Back to Second Brain", zh: "← 返回第二大脑" },
  ),

  // Memory
  memoryBlock: copy(
    { en: "Memory", zh: "记忆" },
    { en: "Memory entry", zh: "记忆条目" },
    { en: "Memory Block", zh: "Memory Block" },
  ),
  recall: copy(
    { en: "Related memories", zh: "相关记忆" },
    { en: "Recall results", zh: "召回结果" },
    { en: "Block Recall", zh: "Block Recall" },
  ),
  remember: copy(
    { en: "Remembered", zh: "已记住" },
    { en: "Stored", zh: "已写入" },
    { en: "Stored to L2", zh: "Stored to L2" },
  ),
  forget: copy(
    { en: "Archived", zh: "已归档" },
    { en: "Archived", zh: "已归档" },
    { en: "Pruned / Archived", zh: "Pruned / Archived" },
  ),
  memoryCount: copy(
    { en: "{count} memories", zh: "共 {count} 条记忆" },
    { en: "{count} memory entries", zh: "共 {count} 条记忆条目" },
    { en: "{count} blocks", zh: "共 {count} blocks" },
  ),
  clearMemory: copy(
    { en: "Clear all memories", zh: "清空记忆" },
    { en: "Clear memory store", zh: "清空记忆库" },
    { en: "Clear memory", zh: "一键清空" },
  ),
  clearMemoryConfirm: copy(
    {
      en: "Clear conversation and non-protected memories? Runtime Constitution is unaffected.",
      zh: "确定清空对话与非保护记忆？Runtime 认知宪法不受影响。",
    },
    {
      en: "Clear memory blocks, graph nodes, and chat history? Foundation / constitution memories are preserved.",
      zh: "确定清空记忆、图谱节点与对话记录？认知宪法与系统基石记忆将保留。",
    },
    {
      en: "Clear memory blocks, graph nodes, and chat history? Foundation / constitution memories are preserved.",
      zh: "确定清空记忆、图谱节点与对话记录？认知宪法与系统基石记忆将保留。",
    },
  ),
  clearMemoryBusy: copy(
    { en: "Clearing…", zh: "清空中…" },
    { en: "Clearing…", zh: "清空中…" },
    { en: "Clearing…", zh: "清空中…" },
  ),
  clearMemoryFailed: copy(
    { en: "Could not clear memories", zh: "清空失败" },
    { en: "Clear failed", zh: "清空失败" },
    { en: "Clear failed", zh: "清空失败" },
  ),

  // REM / Pruning
  remSleep: copy(
    { en: "Organize memories", zh: "记忆整理" },
    { en: "Memory consolidation", zh: "记忆整合" },
    { en: "REM Sleep", zh: "REM 深度睡眠" },
  ),
  remSleepTrigger: copy(
    { en: "Organize now", zh: "整理记忆" },
    { en: "Run consolidation", zh: "开始整合" },
    { en: "Run REM now", zh: "手动触发 REM" },
  ),
  remSleepBusy: copy(
    { en: "Organizing…", zh: "正在整理记忆…" },
    { en: "Consolidating…", zh: "整合中…" },
    { en: "REM running…", zh: "REM 执行中…" },
  ),
  remSleepConfirm: copy(
    {
      en: "Organize your memories? Less-used items may be archived and summarized.",
      zh: "确定整理记忆？不常用的内容可能被归档并生成摘要。",
    },
    {
      en: "Run a memory consolidation cycle? Low-value memories may be pruned and summarized.",
      zh: "确定进行记忆整合？低价值记忆可能被修剪并生成摘要。",
    },
    {
      en: "Force a REM consolidation cycle? Low-value memories may be pruned and summaries generated.",
      zh: "确定手动触发 REM 深度睡眠？系统将修剪低价值记忆并尝试生成语义摘要。",
    },
  ),
  remSleepSkipped: copy(
    { en: "Skipped", zh: "已跳过" },
    { en: "Skipped", zh: "已跳过" },
    { en: "REM skipped", zh: "REM 已跳过" },
  ),
  remSleepDone: copy(
    { en: "Memories organized", zh: "记忆整理完成" },
    { en: "Consolidation complete", zh: "整合完成" },
    { en: "REM completed", zh: "REM completed" },
  ),
  remSleepFailed: copy(
    { en: "Could not organize memories", zh: "记忆整理失败" },
    { en: "Consolidation failed", zh: "整合失败" },
    { en: "REM trigger failed", zh: "REM 触发失败" },
  ),
  pruning: copy(
    { en: "Memory cleanup", zh: "记忆清理" },
    { en: "Cognitive tidying", zh: "认知整理" },
    { en: "Cognitive Pruning", zh: "Cognitive Pruning" },
  ),
  pruningRun: copy(
    { en: "Clean up", zh: "清理记忆" },
    { en: "Run pruning", zh: "执行修剪" },
    { en: "Run pruning", zh: "执行修剪" },
  ),
  pruningPreview: copy(
    { en: "Preview cleanup", zh: "预览清理" },
    { en: "Dry run", zh: "试运行" },
    { en: "Dry run", zh: "Dry run" },
  ),
  activeMemory: copy(
    { en: "Active memories", zh: "常用记忆" },
    { en: "Active memories", zh: "活跃记忆" },
    { en: "Active Blocks", zh: "Active Blocks" },
  ),
  archivedMemory: copy(
    { en: "Archived", zh: "已归档" },
    { en: "Archived memories", zh: "归档记忆" },
    { en: "Archived Blocks", zh: "Archived Blocks" },
  ),
  knowledgeConclusion: copy(
    { en: "Summaries", zh: "总结" },
    { en: "Knowledge conclusions", zh: "知识结论" },
    { en: "Knowledge Synthesis", zh: "Knowledge Synthesis" },
  ),

  // Conflict
  conflictResolution: copy(
    { en: "Needs confirmation", zh: "需要确认" },
    { en: "Viewpoint divergence", zh: "观点分歧" },
    { en: "Conflict Resolution", zh: "Conflict Resolution" },
  ),
  conflictPending: copy(
    { en: "Pending confirmation", zh: "待确认" },
    { en: "Pending divergence", zh: "待处理分歧" },
    { en: "Unresolved", zh: "Unresolved" },
  ),
  conflictLocalView: copy(
    { en: "My view", zh: "我的看法" },
    { en: "Local view", zh: "本地观点" },
    { en: "Local View", zh: "Local View" },
  ),
  conflictRemoteView: copy(
    { en: "Their view", zh: "对方看法" },
    { en: "Remote view", zh: "远程观点" },
    { en: "Remote View", zh: "Remote View" },
  ),
  conflictSynthesis: copy(
    { en: "Combined result", zh: "综合结果" },
    { en: "Merged view", zh: "融合观点" },
    { en: "Synthesis", zh: "Synthesis" },
  ),
  conflictResolved: copy(
    { en: "Confirmed", zh: "已确认" },
    { en: "Resolved", zh: "已处理" },
    { en: "Conflict resolved", zh: "Conflict resolved" },
  ),

  // Emergence
  emergentInsight: copy(
    { en: "Recent discovery", zh: "最近发现" },
    { en: "Emergent insight", zh: "涌现洞察" },
    { en: "Emergent Insight", zh: "Emergent Insight" },
  ),
  recentDiscoveries: copy(
    { en: "Recent discoveries", zh: "最近发现" },
    { en: "Emergent insights", zh: "涌现洞察" },
    { en: "Emergent insights", zh: "Emergent insights" },
  ),
  whyExplain: copy(
    { en: "Why is this?", zh: "为什么会这样？" },
    { en: "View basis", zh: "查看依据" },
    { en: "View Provenance", zh: "View Provenance" },
  ),
  openInLab: copy(
    { en: "View in Cognitive Lab", zh: "在认知实验室查看" },
    { en: "Open in Cognitive Lab", zh: "在认知实验室查看" },
    { en: "Open in Cognitive Lab", zh: "Open in Cognitive Lab" },
  ),
  provenanceHeadline: copy(
    { en: "Based on:", zh: "参考了：" },
    { en: "Provenance:", zh: "依据：" },
    { en: "Provenance:", zh: "Provenance:" },
  ),
  sourceConversation: copy(
    { en: "Recent {count} conversations", zh: "最近 {count} 次对话" },
    { en: "{count} recent conversations", zh: "最近 {count} 次对话" },
    { en: "{count} chat traces", zh: "{count} chat traces" },
  ),
  sourceDocument: copy(
    { en: "{count} project documents", zh: "{count} 个项目文档" },
    { en: "{count} documents", zh: "{count} 个文档" },
    { en: "{count} ingested assets", zh: "{count} ingested assets" },
  ),
  sourceLongTermMemory: copy(
    { en: "{count} long-term memories", zh: "{count} 条长期记忆" },
    { en: "{count} long-term entries", zh: "{count} 条长期记忆" },
    { en: "{count} L2 blocks", zh: "{count} L2 blocks" },
  ),
  sourceSync: copy(
    { en: "{count} sync records", zh: "{count} 条同步记录" },
    { en: "{count} sync events", zh: "{count} 条同步记录" },
    { en: "{count} negotiation events", zh: "{count} negotiation events" },
  ),

  // Negotiation
  negotiation: copy(
    { en: "Sync record", zh: "同步记录" },
    { en: "Negotiation record", zh: "协商记录" },
    { en: "Negotiation", zh: "Negotiation" },
  ),
  consensus: copy(
    { en: "Synced", zh: "已同步" },
    { en: "Consensus reached", zh: "已共识" },
    { en: "Consensus", zh: "Consensus" },
  ),
  syncFailed: copy(
    { en: "Sync incomplete", zh: "同步未完成" },
    { en: "Negotiation failed", zh: "协商失败" },
    { en: "Negotiation failed", zh: "Negotiation failed" },
  ),

  // Six-step loop (research / creator in lab)
  observe: copy(
    { en: "Receive", zh: "接收" },
    { en: "Receive", zh: "接收" },
    { en: "Observe", zh: "Observe" },
  ),
  cognize: copy(
    { en: "Understand", zh: "理解" },
    { en: "Understand", zh: "理解" },
    { en: "Cognize", zh: "Cognize" },
  ),
  decide: copy(
    { en: "Decide", zh: "判断" },
    { en: "Decide", zh: "判断" },
    { en: "Decide", zh: "Decide" },
  ),
  speak: copy(
    { en: "Reply", zh: "回答" },
    { en: "Reply", zh: "回答" },
    { en: "Speak", zh: "Speak" },
  ),
  store: copy(
    { en: "Remember", zh: "记住" },
    { en: "Store", zh: "记住" },
    { en: "Store", zh: "Store" },
  ),
  reflect: copy(
    { en: "Organize", zh: "整理" },
    { en: "Reflect", zh: "整理" },
    { en: "Reflect", zh: "Reflect" },
  ),

  // Second brain tabs
  tabChat: copy(
    { en: "Chat", zh: "对话" },
    { en: "Chat", zh: "对话" },
    { en: "Chat", zh: "对话" },
  ),
  tabMemory: copy(
    { en: "Memories", zh: "记忆" },
    { en: "Memories", zh: "记忆" },
    { en: "Memories", zh: "记忆" },
  ),
  tabProfile: copy(
    { en: "Me", zh: "我的" },
    { en: "Profile", zh: "我的" },
    { en: "Profile", zh: "Profile" },
  ),
  tabUpload: copy(
    { en: "Upload", zh: "上传记忆" },
    { en: "Upload", zh: "上传记忆" },
    { en: "Upload", zh: "Upload" },
  ),
  tabOrganize: copy(
    { en: "Organize", zh: "数据整理" },
    { en: "Organize", zh: "数据整理" },
    { en: "Organize", zh: "Organize" },
  ),
  tabModel: copy(
    { en: "Model", zh: "模型配置" },
    { en: "Model", zh: "模型配置" },
    { en: "Model", zh: "Model" },
  ),
  tabShare: copy(
    { en: "Share", zh: "网络分享" },
    { en: "Share", zh: "网络分享" },
    { en: "Share", zh: "Share" },
  ),
  tabNetwork: copy(
    { en: "Device network", zh: "设备网络" },
    { en: "Device network", zh: "设备网络" },
    { en: "Network topology", zh: "Network topology" },
  ),
  tabConnect: copy(
    { en: "Connect", zh: "连接设备" },
    { en: "Connect devices", zh: "连接设备" },
    { en: "Peer connect", zh: "Peer connect" },
  ),
  tabShareMemory: copy(
    { en: "Shared memories", zh: "共享记忆" },
    { en: "Shared memories", zh: "共享记忆" },
    { en: "Remote assets", zh: "Remote assets" },
  ),
  tabNotify: copy(
    { en: "Notifications", zh: "外部通知" },
    { en: "External alerts", zh: "外部通知" },
    { en: "Notifications", zh: "Notifications" },
  ),
  tabChatShare: copy(
    { en: "Chat links", zh: "对话分享" },
    { en: "Chat sharing", zh: "对话分享" },
    { en: "Chat sharing", zh: "Chat sharing" },
  ),

  // Second brain — network share (P2P, consumer dialect)
  sharePageSubtitle: copy(
    { en: "Connect devices, share memories, and get notifications", zh: "连接设备、共享记忆，并接收外部通知" },
    { en: "Devices, memories, and notifications", zh: "设备互联、记忆共享与通知" },
    { en: "P2P mesh & notifications", zh: "P2P mesh & notifications" },
  ),
  shareMyNetwork: copy(
    { en: "My device network", zh: "我的设备网络" },
    { en: "Device network", zh: "设备网络" },
    { en: "Network topology", zh: "Network topology" },
  ),
  shareMyNetworkHint: copy(
    { en: "See trusted devices around you and sync status", zh: "查看已连接的设备与同步状态" },
    { en: "Trusted devices and sync health", zh: "信任设备与同步健康度" },
    { en: "Live mesh topology", zh: "Live mesh topology" },
  ),
  shareDevicesOnline: copy(
    { en: "Devices online", zh: "在线设备" },
    { en: "Online", zh: "在线" },
    { en: "Peers online", zh: "Peers online" },
  ),
  shareDevicesSynced: copy(
    { en: "In sync", zh: "已同步" },
    { en: "Aligned", zh: "已对齐" },
    { en: "Aligned", zh: "Aligned" },
  ),
  shareDiscoveryReach: copy(
    { en: "Discovery reach", zh: "发现范围" },
    { en: "Discovery nodes", zh: "可发现节点" },
    { en: "DHT nodes", zh: "DHT nodes" },
  ),
  shareMyDeviceId: copy(
    { en: "My device ID", zh: "我的设备 ID" },
    { en: "Local device ID", zh: "本机设备 ID" },
    { en: "Local pubkey", zh: "Local pubkey" },
  ),
  shareCopyDeviceId: copy(
    { en: "Copy ID", zh: "复制 ID" },
    { en: "Copy", zh: "复制" },
    { en: "Copy", zh: "Copy" },
  ),
  shareDeviceIdMissing: copy(
    {
      en: "Device ID unavailable — restart CNexus after installing PyNaCl (pip install pynacl).",
      zh: "设备 ID 未生成 — 请安装 PyNaCl（pip install pynacl）后重启 CNexus。",
    },
    {
      en: "Identity not loaded. Run: pip install pynacl, then restart start_cnexus.bat.",
      zh: "身份未加载。请运行 pip install pynacl，然后重新双击 start_cnexus.bat。",
    },
    {
      en: "Missing identity pubkey",
      zh: "缺少设备公钥",
    },
  ),
  shareCopied: copy(
    { en: "Copied", zh: "已复制" },
    { en: "Copied", zh: "已复制" },
    { en: "Copied", zh: "Copied" },
  ),
  shareConnectDevice: copy(
    { en: "Connect a device", zh: "连接其他设备" },
    { en: "Connect device", zh: "连接设备" },
    { en: "Connect peer", zh: "Connect peer" },
  ),
  shareConnectDeviceHint: copy(
    {
      en: "Paste the other device's ID — CNexus auto-discovers it on your network. No IP or port setup needed.",
      zh: "粘贴对方设备 ID 即可，系统会自动在局域网寻址并建立信任，无需填写 IP 或端口。",
    },
    {
      en: "DHT lookup + secure handshake, then memory sync",
      zh: "自动寻址并握手，随后可同步记忆",
    },
    { en: "DHT + ICE + Ed25519 handshake", zh: "DHT + ICE + Ed25519 handshake" },
  ),
  shareConnectRun: copy(
    { en: "Connect", zh: "连接设备" },
    { en: "Connect & trust", zh: "连接并信任" },
    { en: "Connect & trust", zh: "Connect & trust" },
  ),
  shareConnectOk: copy(
    { en: "Device connected", zh: "设备已连接" },
    { en: "Trusted peer connected", zh: "已建立信任连接" },
    { en: "Trusted peer connected", zh: "Trusted peer connected" },
  ),
  shareConnectErrorNoViablePath: copy(
    {
      en: "No viable path — enter the peer ID and ensure the other device is online on the same network.",
      zh: "无法连通 — 请填写对方设备 ID，并确认对方 CNexus 已在同一网络下运行。",
    },
    {
      en: "No viable path — add peer ID above",
      zh: "无法建立路径 — 请添加对方节点 ID 后重试",
    },
    {
      en: "no_viable_path — enter peer ID above",
      zh: "no_viable_path — enter peer ID above",
    },
  ),
  shareTrustedDevices: copy(
    { en: "Trusted devices", zh: "已信任设备" },
    { en: "Trusted peers", zh: "信任设备" },
    { en: "Trusted peers", zh: "Trusted peers" },
  ),
  shareTrustedDevicesEmpty: copy(
    { en: "No trusted devices yet — connect one above", zh: "暂无信任设备，请在上方输入设备 ID 连接" },
    { en: "No trusted peers — connect by ID above", zh: "暂无信任设备" },
    { en: "No trusted peers", zh: "No trusted peers" },
  ),
  shareBlockDevice: copy(
    { en: "Block a device", zh: "屏蔽设备" },
    { en: "Block device", zh: "屏蔽设备" },
    { en: "Ban peer", zh: "Ban peer" },
  ),
  shareBlockDeviceHint: copy(
    { en: "Stop unwanted devices from connecting again", zh: "阻止不受信任的设备再次连接" },
    { en: "Firewall ban for malicious peers", zh: "封禁恶意节点" },
    { en: "Firewall ban", zh: "Firewall ban" },
  ),
  shareBlockRun: copy(
    { en: "Block", zh: "屏蔽" },
    { en: "Block", zh: "屏蔽" },
    { en: "Ban", zh: "Ban" },
  ),
  shareBlockDone: copy(
    { en: "Device blocked", zh: "已屏蔽该设备" },
    { en: "Peer banned", zh: "已封禁节点" },
    { en: "Peer banned", zh: "Peer banned" },
  ),
  shareRemoteMemory: copy(
    { en: "Shared memories", zh: "共享记忆" },
    { en: "Remote memories", zh: "远程记忆" },
    { en: "Cognitive assets", zh: "Cognitive assets" },
  ),
  shareRemoteMemoryHint: copy(
    {
      en: "Search your device, trusted group, or the whole network — then download copies locally",
      zh: "可搜索本机、信任组群或全网记忆，并将文档下载到本机",
    },
    {
      en: "Local · trusted mesh · DHT-wide semantic search",
      zh: "本机 · 信任组群 · 全网三层范围",
    },
    { en: "Scoped federated asset search", zh: "Scoped federated asset search" },
  ),
  shareScopeLocal: copy(
    { en: "This device", zh: "本机记忆" },
    { en: "Local only", zh: "仅本机" },
    { en: "Local", zh: "Local" },
  ),
  shareScopeTrusted: copy(
    { en: "Trusted group", zh: "组群记忆" },
    { en: "Trusted mesh", zh: "信任组群" },
    { en: "Trusted peers", zh: "Trusted peers" },
  ),
  shareScopeNetwork: copy(
    { en: "Whole network", zh: "全网记忆" },
    { en: "Network-wide", zh: "全网" },
    { en: "Network-wide", zh: "Network-wide" },
  ),
  shareScopeLocalHint: copy(
    { en: "Memories created or owned on this device", zh: "本机创建或拥有的记忆与文档" },
    { en: "No remote source_peer", zh: "不含远端来源" },
    { en: "Local origin only", zh: "Local origin only" },
  ),
  shareScopeTrustedHint: copy(
    { en: "Your device plus all trusted peers", zh: "本机 + 已信任设备上的记忆" },
    { en: "Trusted peer mesh", zh: "信任设备互联" },
    { en: "Trusted federation", zh: "Trusted federation" },
  ),
  shareScopeNetworkHint: copy(
    { en: "Search every reachable node on the mesh", zh: "搜索网络中所有可发现的节点" },
    { en: "DHT + discovered peers", zh: "DHT 与发现节点" },
    { en: "Full mesh search", zh: "Full mesh search" },
  ),
  shareMemoryFlowGraphTitle: copy(
    { en: "Memory flow graph", zh: "记忆流图" },
    { en: "Memory flow graph", zh: "记忆流图" },
    { en: "Memory flow graph", zh: "记忆流图" },
  ),
  shareMemoryFlowGraphHint: copy(
    {
      en: "Switch scope to view local, group, or network-wide memory topology.",
      zh: "切换记忆范围，查看本机、组群或全网记忆因子网络。",
    },
    {
      en: "Switch scope to view local, group, or network-wide memory topology.",
      zh: "切换记忆范围，查看本机、组群或全网记忆因子网络。",
    },
    {
      en: "Switch scope to view local, group, or network-wide memory topology.",
      zh: "切换记忆范围，查看本机、组群或全网记忆因子网络。",
    },
  ),
  shareMemoryFlowGraphEmpty: copy(
    {
      en: "No memory nodes in this scope yet — chat, upload, or search to populate.",
      zh: "当前范围暂无记忆节点，对话、上传或搜索后会在此显示。",
    },
    {
      en: "No memory nodes in this scope yet — chat, upload, or search to populate.",
      zh: "当前范围暂无记忆节点，对话、上传或搜索后会在此显示。",
    },
    {
      en: "No memory nodes in this scope yet — chat, upload, or search to populate.",
      zh: "当前范围暂无记忆节点，对话、上传或搜索后会在此显示。",
    },
  ),
  shareOriginLocal: copy(
    { en: "Local", zh: "本机" },
    { en: "Local", zh: "本机" },
    { en: "Local", zh: "Local" },
  ),
  shareOriginTrusted: copy(
    { en: "Group", zh: "组群" },
    { en: "Trusted", zh: "组群" },
    { en: "Trusted", zh: "Trusted" },
  ),
  shareOriginNetwork: copy(
    { en: "Network", zh: "全网" },
    { en: "Network", zh: "全网" },
    { en: "Network", zh: "Network" },
  ),
  shareMemoryBlock: copy(
    { en: "Memory", zh: "记忆块" },
    { en: "Memory block", zh: "记忆块" },
    { en: "Memory block", zh: "Memory block" },
  ),
  shareSearchPlaceholder: copy(
    { en: "Search title, filename, or ID…", zh: "搜索标题、文件名或 ID…" },
    { en: "summary / filename / asset id", zh: "摘要 / 文件名 / 资产 ID" },
    { en: "Asset query", zh: "Asset query" },
  ),
  shareSearchRun: copy(
    { en: "Search", zh: "搜索" },
    { en: "Search", zh: "搜索" },
    { en: "Search", zh: "Search" },
  ),
  shareDownloadMemory: copy(
    { en: "Download", zh: "下载到本机" },
    { en: "Pull locally", zh: "拉取到本地" },
    { en: "Pull from peer", zh: "Pull from peer" },
  ),
  shareDownloadDone: copy(
    { en: "Saved on this device", zh: "已保存到本机" },
    { en: "Asset pulled locally", zh: "已拉取到本地" },
    { en: "Asset pulled locally", zh: "Asset pulled locally" },
  ),
  shareRemotePreviewOnly: copy(
    { en: "Preview only — not on this device yet", zh: "仅预览，尚未下载到本机" },
    { en: "Remote preview only", zh: "仅远程预览" },
    { en: "Remote preview only", zh: "Remote preview only" },
  ),
  shareSearchEmpty: copy(
    { en: "No matching memories found", zh: "未找到匹配的记忆" },
    { en: "No matching assets", zh: "无匹配资产" },
    { en: "No matching assets", zh: "No matching assets" },
  ),
  shareSemanticSearch: copy(
    { en: "Smart search (vectors)", zh: "智能搜索（语义）" },
    { en: "Semantic search", zh: "语义搜索" },
    { en: "Semantic search (CLIP)", zh: "Semantic search (CLIP)" },
  ),
  shareExternalNotify: copy(
    { en: "External notifications", zh: "外部通知" },
    { en: "External alerts", zh: "外部提醒" },
    { en: "External notifications", zh: "External notifications" },
  ),
  shareExternalNotifyHint: copy(
    { en: "Get alerts when memories import or need your confirmation", zh: "记忆导入完成或需要确认时，推送到外部应用" },
    { en: "DingTalk robot on capture / conflict", zh: "导入/冲突时钉钉通知" },
    { en: "DingTalk integration", zh: "DingTalk integration" },
  ),
  shareChatShare: copy(
    { en: "Chat sharing", zh: "对话分享" },
    { en: "Chat links", zh: "对话链接" },
    { en: "Chat sharing", zh: "Chat sharing" },
  ),
  shareChatShareHint: copy(
    { en: "Right-click a message in chat to create a local share link", zh: "在对话中右键消息，可生成本地分享链接" },
    { en: "Local-only chat share links", zh: "本地对话分享链接" },
    { en: "Local chat share links", zh: "Local chat share links" },
  ),
  shareChatShareBody: copy(
    {
      en: "Links are generated locally and never uploaded. Copy to a trusted colleague or another device.",
      zh: "分享链接仅在本地生成，不会上传到服务器。适合复制给信任的同事或另一台设备打开。",
    },
    {
      en: "Local-only share payloads",
      zh: "仅本地生成分享内容",
    },
    { en: "Local share payload only", zh: "Local share payload only" },
  ),
  shareOpenLabLink: copy(
    { en: "Advanced network details in Cognitive Lab", zh: "在认知实验室查看高级网络详情" },
    { en: "Open full network console", zh: "打开完整网络控制台" },
    { en: "Open Cognitive Lab network", zh: "Open Cognitive Lab network" },
  ),

  // Second brain — settings & sections
  chatPreferences: copy(
    { en: "Chat preferences", zh: "对话偏好" },
    { en: "Chat preferences", zh: "对话偏好" },
    { en: "Chat preferences", zh: "Chat preferences" },
  ),
  thinkingStyle: copy(
    { en: "Answer style", zh: "回答风格" },
    { en: "Answer style", zh: "回答风格" },
    { en: "Thinking mode", zh: "Thinking mode" },
  ),
  converseMode: copy(
    { en: "Reply mode", zh: "回复方式" },
    { en: "Reply mode", zh: "回复方式" },
    { en: "Converse mode", zh: "Converse mode" },
  ),
  converseFast: copy(
    { en: "Quick", zh: "快速回复" },
    { en: "Quick reply", zh: "快速回复" },
    { en: "Fast", zh: "Fast" },
  ),
  converseDeep: copy(
    { en: "Thoughtful", zh: "认真想想" },
    { en: "Deep reply", zh: "深度回复" },
    { en: "Deep", zh: "Deep" },
  ),
  converseRaw: copy(
    { en: "No memory", zh: "不参考记忆" },
    { en: "Raw only", zh: "仅原文" },
    { en: "Raw", zh: "Raw" },
  ),
  converseFastHint: copy(
    { en: "Fast replies with key memories", zh: "优先速度，参考重要记忆" },
    { en: "Fast with selective recall", zh: "少量记忆，优先速度" },
    { en: "Fast thinking", zh: "Fast thinking" },
  ),
  converseDeepHint: copy(
    { en: "More context for complex questions", zh: "适合复杂问题，参考更多记忆" },
    { en: "Long context + more recall", zh: "长上下文 + 更多召回" },
    { en: "Deep reasoning", zh: "Deep reasoning" },
  ),
  converseRawHint: copy(
    { en: "Chat without memory context", zh: "不注入记忆，只发送你的文字" },
    { en: "No memory injection", zh: "不注入记忆" },
    { en: "Raw input only", zh: "Raw input only" },
  ),
  chatMemoryScope: copy(
    { en: "Memory source", zh: "记忆范围" },
    { en: "Recall scope", zh: "记忆来源" },
    { en: "Memory scope", zh: "Memory scope" },
  ),
  precisionHint: copy(
    { en: "Accurate, grounded answers", zh: "准确、有据可依的回答" },
    { en: "Strict provenance", zh: "严守依据" },
    { en: "Temperature 0 · strict", zh: "Temperature 0" },
  ),
  precision: copy(
    { en: "Accurate", zh: "准确回答" },
    { en: "Precision", zh: "精确模式" },
    { en: "Precision", zh: "Precision" },
  ),
  emergentHint: copy(
    { en: "Connect ideas across memories", zh: "联想更多记忆，适合探索性话题" },
    { en: "Cross-link insights", zh: "跨记忆联想" },
    { en: "Entropy-driven", zh: "Entropy-driven" },
  ),
  emergent: copy(
    { en: "Explore", zh: "深入思考" },
    { en: "Emergent", zh: "涌现模式" },
    { en: "Emergent", zh: "Emergent" },
  ),
  memoryOverview: copy(
    { en: "Overview", zh: "记忆概览" },
    { en: "Overview", zh: "记忆概览" },
    { en: "Overview", zh: "Overview" },
  ),
  memoryFilterAll: copy(
    { en: "All", zh: "全部" },
    { en: "All", zh: "全部" },
    { en: "All", zh: "All" },
  ),
  memoryFilterImportant: copy(
    { en: "Important", zh: "重要" },
    { en: "Goals & beliefs", zh: "目标与信念" },
    { en: "Goals & beliefs", zh: "Goals & beliefs" },
  ),
  memoryFilterExperiences: copy(
    { en: "Experiences", zh: "经历" },
    { en: "Experiences", zh: "经历" },
    { en: "Episodes", zh: "Episodes" },
  ),
  memoryFilterAboutMe: copy(
    { en: "About me", zh: "关于我" },
    { en: "Identity", zh: "身份" },
    { en: "Identity", zh: "Identity" },
  ),
  addContent: copy(
    { en: "Add content", zh: "添加内容" },
    { en: "Add content", zh: "添加内容" },
    { en: "Ingest", zh: "Ingest" },
  ),
  organizeSection: copy(
    { en: "Organize", zh: "整理记忆" },
    { en: "Consolidate", zh: "记忆整合" },
    { en: "REM / Organize", zh: "REM / Organize" },
  ),
  organizeSectionHint: copy(
    { en: "Archive unused items and create summaries", zh: "归档不常用内容，并生成摘要" },
    { en: "Prune low-value and summarize", zh: "修剪低价值并摘要" },
    { en: "REM consolidation cycle", zh: "REM cycle" },
  ),
  modelSection: copy(
    { en: "Model", zh: "模型" },
    { en: "Model", zh: "模型" },
    { en: "LLM", zh: "LLM" },
  ),
  connectionSection: copy(
    { en: "Connection", zh: "连接状态" },
    { en: "Connection", zh: "连接状态" },
    { en: "Runtime", zh: "Runtime" },
  ),
  dataManagement: copy(
    { en: "Data", zh: "数据管理" },
    { en: "Data management", zh: "数据管理" },
    { en: "Data", zh: "Data" },
  ),
  appearanceSection: copy(
    { en: "Appearance", zh: "界面" },
    { en: "Appearance", zh: "界面" },
    { en: "Appearance", zh: "Appearance" },
  ),
  healthLabel: copy(
    { en: "Status", zh: "运行状态" },
    { en: "Health", zh: "健康度" },
    { en: "Health", zh: "Health" },
  ),

  // Status
  systemStatus: copy(
    { en: "Running normally", zh: "运行正常" },
    { en: "System health", zh: "系统健康" },
    { en: "Health Score", zh: "Health Score" },
  ),
  lastOrganized: copy(
    { en: "Last organized {time}", zh: "上次整理 {time}" },
    { en: "Last consolidation {time}", zh: "上次整合 {time}" },
    { en: "Last REM {time}", zh: "Last REM {time}" },
  ),
  uploadDocuments: copy(
    { en: "Upload files", zh: "上传文件" },
    { en: "Import documents", zh: "导入文档" },
    { en: "Document ingest", zh: "文档导入" },
  ),
  refresh: copy(
    { en: "Refresh", zh: "刷新" },
    { en: "Refresh", zh: "刷新" },
    { en: "Refresh", zh: "刷新" },
  ),
  connected: copy(
    { en: "Online", zh: "在线" },
    { en: "Connected", zh: "已连接" },
    { en: "Connected", zh: "Connected" },
  ),
  offline: copy(
    { en: "Offline", zh: "离线" },
    { en: "Offline", zh: "离线" },
    { en: "Offline", zh: "Offline" },
  ),
  pendingConfirmations: copy(
    { en: "{count} need confirmation", zh: "{count} 条需要确认" },
    { en: "{count} divergences", zh: "{count} 条观点分歧" },
    { en: "{count} unresolved conflicts", zh: "{count} unresolved conflicts" },
  ),
  labJumpToast: copy(
    { en: "Opened in Cognitive Lab", zh: "已从第二大脑跳转至此记录" },
    { en: "Opened in Cognitive Lab", zh: "已在认知实验室打开" },
    { en: "Opened record in Cognitive Lab", zh: "Opened record in Cognitive Lab" },
  ),
} as const satisfies Record<string, CognitiveCopyEntry>;

export type CopyKey = keyof typeof cognitiveCopy;

export function getCopyEntry(key: CopyKey): CognitiveCopyEntry {
  return cognitiveCopy[key];
}
