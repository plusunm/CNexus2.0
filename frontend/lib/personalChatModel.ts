import type { ModelProfile } from "@/lib/api";
import { useMindStore } from "@/cnexus-kernel/MindStore";
import { buildRuntimeModelPayload, syncLlmQuickConfigToRuntime, type LlmSyncResult } from "@/lib/floatIntegrations";

function isExternalChatModel(model: ModelProfile | undefined): boolean {
  if (!model || !model.enabled) return false;
  if (model.provider === "cnexus") return false;
  if (model.provider === "ollama") return true;
  return Boolean(model.api_key_set);
}

/** Pick the best external LLM for personal /api/converse when user has not forced cnexus-local. */
export function resolvePersonalChatModelId(
  selectedModelId: string,
  models: ModelProfile[],
): string | undefined {
  const selected = models.find((m) => m.id === selectedModelId && m.enabled);
  if (selected && isExternalChatModel(selected)) {
    return selected.id;
  }

  const ollama = models.find((m) => m.id === "ollama-local" && m.enabled);
  if (ollama) return ollama.id;

  const keyed =
    models.find((m) => m.is_default && m.enabled && m.api_key_set && m.provider !== "cnexus") ??
    models.find((m) => m.enabled && m.api_key_set && m.provider !== "cnexus");
  if (keyed) return keyed.id;

  const local = buildRuntimeModelPayload();
  if (local?.presetId) {
    const preset = models.find((m) => m.id === local.presetId);
    if (preset && isExternalChatModel(preset)) return preset.id;
  }
  return undefined;
}

/** Apply gateway sync result to MindStore (default model selection). */
export async function applyLlmSyncToStore(result: LlmSyncResult): Promise<void> {
  if (!result.ok) return;
  await useMindStore.getState().refreshModels();
  if (result.modelId) {
    useMindStore.getState().setSelectedModel(result.modelId);
  }
}

/**
 * Before personal chat: push local LLM config to gateway if registry has no usable external model.
 */
export async function ensurePersonalChatModelForSend(
  selectedModelId: string,
  models: ModelProfile[],
): Promise<string | undefined> {
  const resolved = resolvePersonalChatModelId(selectedModelId || "cnexus-local", models);
  if (resolved && models.some((m) => m.id === resolved && isExternalChatModel(m))) {
    return resolved;
  }

  const local = buildRuntimeModelPayload();
  if (!local) return resolved;

  try {
    const result = await syncLlmQuickConfigToRuntime();
    await applyLlmSyncToStore(result);
    if (result.ok && result.modelId) {
      return resolvePersonalChatModelId(result.modelId, useMindStore.getState().models) ?? result.modelId;
    }
  } catch {
    /* gateway may still be warming */
  }
  return resolvePersonalChatModelId(selectedModelId || "cnexus-local", useMindStore.getState().models);
}
