/** Raw shapes from existing CNexus backend — adapter input only. */

export type ConverseBlockingRaw = {
  ok?: boolean;
  reply?: string;
  emotion?: {
    valence?: number;
    val?: number;
    arousal?: number;
    dominance?: number;
  };
  intent?: string;
  iteration?: number;
  activation_injected?: number;
  activation_context?: string;
  activation_hits?: Array<{ id?: string; title?: string; score?: number }>;
  trace?: Array<{ step?: string; raw?: string; normalized?: string }>;
  cog_state?: {
    active_intent?: string;
    recall_strength?: number;
    total_observations?: number;
  };
  relationship?: {
    tone?: number;
    trust?: number;
    familiarity?: number;
    closeness?: number;
  };
  error?: string;
};

export type StatusRaw = {
  relationship?: {
    tone?: number;
    trust?: number;
    familiarity?: number;
    closeness?: number;
  };
  emotion?: {
    val?: number;
    valence?: number;
    arousal?: number;
    dominance?: number;
  };
  memory_items?: Array<{ id?: string; title?: string; desc?: string; tag?: string }>;
};
