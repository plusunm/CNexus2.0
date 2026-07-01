import {
  DECISION_EXAMPLE_DOMAINS,
  type DecisionExampleDomain,
} from "@/lib/relationshipAnalysis";

export { DECISION_EXAMPLE_DOMAINS, type DecisionExampleDomain };

export const THINKING_DOMAIN_COLORS: Record<DecisionExampleDomain, string> = {
  恋爱: "#f472b6",
  求职: "#60a5fa",
  职场: "#a78bfa",
  人际: "#5eead4",
  家庭: "#fbbf24",
  生活: "#94a3b8",
};

export type ThinkingDomainMeta = {
  title: string;
  subtitle: string;
  placeholder: string;
};

export const THINKING_DOMAIN_META: Record<DecisionExampleDomain, ThinkingDomainMeta> = {
  恋爱: {
    title: "恋爱关系",
    subtitle: "暧昧、冷淡、推进或边界——单次输入，固定结构输出。",
    placeholder: "例如：他最近不理我、暧昧要不要推进、是否该明确关系……",
  },
  求职: {
    title: "求职机会",
    subtitle: "offer 评估、跳槽时机、求职策略——结构化拆解，不是聊天。",
    placeholder: "例如：收到新 offer 要不要跳、裸辞还是先骑驴找马……",
  },
  职场: {
    title: "职场决策",
    subtitle: "上下级、同事协作、权益争取——把局面拆成可执行选项。",
    placeholder: "例如：领导甩锅、要不要提加薪、同事抢功劳……",
  },
  人际: {
    title: "人际边界",
    subtitle: "朋友、熟人之间的请求与边界——看清信号再行动。",
    placeholder: "例如：朋友反复借钱、要不要拒绝、如何不伤和气……",
  },
  家庭: {
    title: "家庭压力",
    subtitle: "父母期待、家庭选择与沟通——在压力下做清晰决策。",
    placeholder: "例如：催婚但不想将就、是否搬回父母身边……",
  },
  生活: {
    title: "人生选择",
    subtitle: "城市、生活方式、长期方向——把模糊焦虑变成结构。",
    placeholder: "例如：留在大城市还是回老家、要不要读博/转行……",
  },
};
