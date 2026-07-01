/** 思考页示例 — 多领域、多方向，不限于恋爱关系。 */

export const DECISION_EXAMPLE_DOMAINS = [
  "恋爱",
  "求职",
  "职场",
  "人际",
  "家庭",
  "生活",
] as const;

export type DecisionExampleDomain = (typeof DECISION_EXAMPLE_DOMAINS)[number];

export type DecisionExamplePrompt = {
  id: string;
  domain: DecisionExampleDomain;
  /** 该领域内的决策方向 */
  direction: string;
  text: string;
};

export const DECISION_ANALYSIS_EXAMPLE_GROUPS: DecisionExamplePrompt[] = [
  { id: "romance-cold", domain: "恋爱", direction: "冷淡信号", text: "他最近不理我，是在冷处理吗" },
  { id: "romance-advance", domain: "恋爱", direction: "关系推进", text: "暧昧关系要不要推进" },
  { id: "job-offer", domain: "求职", direction: "机会评估", text: "收到新 offer，要不要辞职跳槽" },
  { id: "job-search", domain: "求职", direction: "求职策略", text: "裸辞找工作还是先骑驴找马" },
  { id: "work-boss", domain: "职场", direction: "上下级", text: "领导总甩锅给我，要不要正面沟通" },
  { id: "work-pay", domain: "职场", direction: "权益争取", text: "该不该跟老板提加薪" },
  { id: "work-peer", domain: "职场", direction: "同事协作", text: "同事抢功劳，我怎么应对" },
  { id: "social-boundary", domain: "人际", direction: "边界", text: "朋友反复借钱，要不要拒绝" },
  { id: "family-pressure", domain: "家庭", direction: "家庭压力", text: "父母催婚但我不想将就" },
  { id: "life-city", domain: "生活", direction: "人生选择", text: "留在大城市还是回老家发展" },
];

/** @deprecated use DECISION_ANALYSIS_EXAMPLE_GROUPS */
export const RELATIONSHIP_ANALYSIS_EXAMPLE_GROUPS = DECISION_ANALYSIS_EXAMPLE_GROUPS;

/** 扁平列表 — 兼容旧引用 */
export const RELATIONSHIP_ANALYSIS_EXAMPLES = DECISION_ANALYSIS_EXAMPLE_GROUPS.map(
  (row) => row.text,
) as readonly string[];

export function decisionExamplesByDomain(): Record<DecisionExampleDomain, DecisionExamplePrompt[]> {
  const grouped = Object.fromEntries(
    DECISION_EXAMPLE_DOMAINS.map((domain) => [domain, [] as DecisionExamplePrompt[]]),
  ) as Record<DecisionExampleDomain, DecisionExamplePrompt[]>;

  for (const row of DECISION_ANALYSIS_EXAMPLE_GROUPS) {
    grouped[row.domain].push(row);
  }
  return grouped;
}
