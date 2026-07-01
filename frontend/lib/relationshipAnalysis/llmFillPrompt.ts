/**
 * LLM fill prompt reference — execution lives on backend (relationship_llm_prompt.py).
 * Frontend must never send this to models directly; UI only consumes canonical JSON.
 */

export const RELATIONSHIP_LLM_FILL_SYSTEM_REF = `CNexus Relationship Analysis Engine — fill-only, anti-drift.
See: src/gateway/services/relationship_llm_prompt.py`;

/** LLM may emit snake_case; canonical API uses camelCase — normalized server-side. */
export const LLM_FILL_SNAKE_CASE_KEYS = {
  state: ["emotion_connection", "initiative_level", "interaction_frequency", "relationship_stage"],
  uncertainty: ["missing_info", "risk_of_misjudgment"],
  decision: ["A", "B", "C", "D", "recommended", "reason"],
} as const;
