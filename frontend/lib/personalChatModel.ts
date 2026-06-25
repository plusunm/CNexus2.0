import type { ModelProfile } from "@/lib/api";

/** Pick the best external LLM for personal /api/converse when user has not forced cnexus-local. */
export function resolvePersonalChatModelId(
  selectedModelId: string,
  models: ModelProfile[],
): string | undefined {
  const selected = models.find((m) => m.id === selectedModelId && m.enabled);
  if (selected && selected.provider !== "cnexus") {
    if (selected.provider === "ollama" || selected.api_key_set) {
      return selected.id;
    }
  }

  const ollama = models.find((m) => m.id === "ollama-local" && m.enabled);
  if (ollama) return ollama.id;

  const keyed =
    models.find((m) => m.is_default && m.enabled && m.api_key_set && m.provider !== "cnexus") ??
    models.find((m) => m.enabled && m.api_key_set && m.provider !== "cnexus");
  return keyed?.id;
}
