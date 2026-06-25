"""speak_reducer — L1 Step 4.

Signature:
    speak_fn(decision, context, state, *, degradation_level="L0") -> Response

§03 Rules:
    1. IDLE strategy -> empty text, inference_type="idle"
    2. SPEAK strategy -> passes context to inference, returns response with text
    3. No state mutation
    4. degradation_level alters inference_type:
       L0/L1 -> "llm"
       L2     -> "template"
       L3     -> "fixed" (REFUGE mode)
"""

_DEGRADATION_INFERENCE_MAP = {
    "L0": "llm",
    "L1": "llm",
    "L2": "template",
    "L3": "fixed",
}

_IDENTITY_MARKERS = (
    "你是谁",
    "你是誰",
    "你是什么",
    "介绍一下你",
    "介绍你自己",
    "who are you",
    "what are you",
)


def _compose_kernel_reply(user_text: str, *, degradation_level: str) -> str:
    """Local kernel path — never echo user input verbatim."""
    text = str(user_text or "").strip()
    if not text:
        return ""

    if degradation_level == "L3":
        return "系统处于保守模式，暂时无法生成回复。请稍后重试。"

    lower = text.lower()
    if any(marker in text or marker in lower for marker in _IDENTITY_MARKERS):
        return (
            "我是 CNexus 2.0 个人版认知助手，负责结合本机/组群/全网记忆与你对话。"
            "当前未走外部大模型通道；若需要更自然的回答，请在「模型」中启用 DeepSeek 或 Ollama。"
        )

    preview = text if len(text) <= 48 else f"{text[:48]}…"
    if degradation_level == "L2":
        return (
            f"（本地模板模式）我已收到：「{preview}」。"
            "此模式不能深度推理；请在设置中启用 DeepSeek/Ollama 以获得完整回复。"
        )

    return (
        f"（本地内核）已收到：「{preview}」。"
        "当前未调用外部大模型，因此不能把原文复读为回复。"
        "请在「模型」中配置 API Key 并选择 DeepSeek 或 Ollama，即可正常对话。"
    )


def speak_fn(decision, context, state, **kwargs):
    degradation_level = kwargs.get("degradation_level", "L0")

    strategy = decision.get("strategy", "SPEAK")

    if strategy == "IDLE":
        return dict(
            text="",
            inference_type="idle",
            confidence=1.0,
            latency_ms=0,
            metadata={},
        )

    inference_type = _DEGRADATION_INFERENCE_MAP.get(degradation_level, "llm")
    user_text = context.get("context_bundle", "")

    return dict(
        text=_compose_kernel_reply(user_text, degradation_level=degradation_level),
        inference_type=inference_type,
        confidence=decision.get("confidence", 0.5),
        latency_ms=0,
        metadata={"degradation_level": degradation_level, "kernel_template": True},
    )
