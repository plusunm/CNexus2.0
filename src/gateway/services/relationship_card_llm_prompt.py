"""CNexus Card Memory Engine — ontology-constrained slot fill only."""

import json
from typing import Any, Dict, Optional

RELATIONSHIP_CARD_MODEL_SYSTEM = """你是 CNexus Relationship Memory Engine。

你的任务是：将一次结构化分析结果，按已选 Model Ontology 模板「填充槽位」——不是自由生成模型。

# 绝对禁止

- 不得重新分析问题
- 不得改变模型族（library_model_id）
- 不得改变 title / problem_type / model_summary
- 不得改变 trigger_conditions
- 不得改变 decision 分支逻辑（recommended_action_logic 由系统映射）
- 不得改变 reusability_tags
- 不得改变 risk_model 结构与条目数量
- 不得输出非 JSON

# 唯一允许填充的字段

{
  "signal_model": {
    "key_positive_signals": [],
    "key_negative_signals": []
  },
  "action_template": []
}

从 CanonicalSchema 的 signals / actions 抽象为可复用信号与行动槽位文本。
槽位数量不得超过 ontology canonical_structure 的 maxItems。

只输出 JSON，无其他字符。"""


def build_card_model_user_prompt(
    analysis_json: str,
    *,
    route: Optional[Dict[str, Any]] = None,
    library_template: Optional[Dict[str, Any]] = None,
) -> str:
    parts = [
        "以下是一次已完成的结构化分析结果 + Model Ontology 模板。",
        "你只能输出 signal_model 与 action_template 的槽位填充 JSON。",
        "",
    ]

    if route:
        parts.extend([
            f"Model Router: family_id={route.get('familyId')} confidence={route.get('confidence')} "
            f"matched_rules={route.get('matchedRules')} reason={route.get('reason')}",
            "",
        ])

    if library_template:
        parts.extend([
            "Model Ontology 模板（结构已锁定，不可修改）：",
            json.dumps(library_template, ensure_ascii=False, indent=2),
            "",
        ])

    parts.extend(["CanonicalSchema 分析结果：", analysis_json])
    return "\n".join(parts)
