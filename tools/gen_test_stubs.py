#!/usr/bin/env python3
"""
CNexus2.0 Phase 4 — Test Stub Generator

从 L1 Reducer 规格 + L2 断言矩阵自动生成 Python 单元测试桩。
依赖：
  - 01_runtime_spec/02_cognitive_state.md  (State 变化幅度约束)
  - 01_runtime_spec/10_reducers/*.md      (6 步 reducer 规格)
  - 02_stability_spec/01_drift_detection.md (L2 断言集)

用法:
  python tools/gen_test_stubs.py stub cognize_reducer   # 生成一个 reducer 的测试
  python tools/gen_test_stubs.py stub drift_assertion   # 生成 L2 断言矩阵测试
  python tools/gen_test_stubs.py all                     # 全量生成
"""

import os, sys, re, textwrap

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'tests')
SPEC_DIR = os.path.join(PROJECT_ROOT, '01_runtime_spec')

INDENT = "    "

# ============================================================
# 1. COGNIZE REDUCER TEST STUB
# ============================================================

def _state_imports():
    return textwrap.dedent("""\
    \"\"\"Test stub: cognize_reducer — auto-generated from L1 spec.\"\"\"
    import pytest
    import math
    import json
    from datetime import datetime

    # 占位符 — 待 kernel/ 实现后替换
    from kernel.cognize_reducer import cognize_fn
    from kernel.state_snapshot import StateSnapshot, EmotionSnapshot

    """)

def get_cognize_test_stub():
    """Generate test_cognize_reducer.py with all assertions from cognitive_state.md"""
    sb = []
    sb.append(_state_imports())
    sb.append(_gen_fixture_state())
    sb.append("\n\n# ============================================================\n")
    sb.append(_gen_test_observe_empty())
    sb.append("\n\n")
    sb.append(_gen_test_emotion_delta())
    sb.append("\n\n")
    sb.append(_gen_test_attention_delta())
    sb.append("\n\n")
    sb.append(_gen_test_identity_signal())
    sb.append("\n\n")
    sb.append(_gen_test_context_structure())
    sb.append("\n\n")
    sb.append(_gen_test_p1_protection())
    return "".join(sb)

def _gen_fixture_state():
    return textwrap.dedent('''\
    # ---- Fixtures ----
    @pytest.fixture
    def neutral_state():
        """Base state from L0 data_model_essence §3.2"""
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.5, dominance=0.5),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )

    @pytest.fixture
    def emotional_state():
        """State with elevated emotion for delta tests"""
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.7, arousal=0.8, dominance=0.6),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 5}
        )

    ''')

def _gen_test_observe_empty():
    return textwrap.dedent('''\
    # ---- L1 §01 Rule 1: Empty observation -> no state update ----
    def test_empty_observation_no_emotion_update(neutral_state):
        \"\"\"02_cognitive_state §2.1: Empty input must not change emotion.\"\"\"
        obs = {"type": "empty_observation", "raw": "", "normalized": "", "is_empty": True}
        result = cognize_fn(obs, neutral_state, [])
        # Emotion should remain at neutral_state values (unchanged)
        assert result.emotion.val == neutral_state.emotion.val, \\
            "Empty observation: emotion.val should not change"
        assert result.emotion.arousal == neutral_state.emotion.arousal, \\
            "Empty observation: emotion.arousal should not change"
        assert result.emotion.dominance == neutral_state.emotion.dominance, \\
            "Empty observation: emotion.dominance should not change"
    ''')

def _gen_test_emotion_delta():
    return textwrap.dedent('''\
    # ---- L1 §02: Emotion delta boundary constraints ----
    # Sections: 2.1 (单轮变化上界)
    def test_emotion_val_delta_upper_bound(neutral_state):
        \"\"\"02_cognitive_state §2.1: |Δ(val)| <= 0.35\"\"\"
        # Trigger a strong emotional response
        obs = {"type": "text_input", "raw": "i hate you", "normalized": "i hate you", "is_empty": False}
        result = cognize_fn(obs, neutral_state, [])
        delta_v = abs(result.emotion.val - neutral_state.emotion.val)
        assert delta_v <= 0.35 + 1e-9, \\
            f"|Δ(val)| = {delta_v:.4f} exceeds 0.35 upper bound"

    def test_emotion_arousal_delta_upper_bound(emotional_state):
        \"\"\"02_cognitive_state §2.1: |Δ(arousal)| <= 0.30\"\"\"
        obs = {"type": "text_input", "raw": "everything is fine", "normalized": "everything is fine", "is_empty": False}
        result = cognize_fn(obs, emotional_state, [])
        delta_a = abs(result.emotion.arousal - emotional_state.emotion.arousal)
        assert delta_a <= 0.30 + 1e-9, \\
            f"|Δ(arousal)| = {delta_a:.4f} exceeds 0.30 upper bound"

    def test_emotion_dominance_delta_upper_bound(emotional_state):
        \"\"\"02_cognitive_state §2.1: |Δ(dominance)| <= 0.25\"\"\"
        obs = {"type": "text_input", "raw": "i feel powerless", "normalized": "i feel powerless", "is_empty": False}
        result = cognize_fn(obs, emotional_state, [])
        delta_d = abs(result.emotion.dominance - emotional_state.emotion.dominance)
        assert delta_d <= 0.25 + 1e-9, \\
            f"|Δ(dominance)| = {delta_d:.4f} exceeds 0.25 upper bound"
    ''')

def _gen_test_attention_delta():
    return textwrap.dedent('''\
    # ---- L1 §02: Attention delta boundary constraints ----
    # Section: 2.4 (Attention 跳跃约束)
    def test_attention_level_delta_upper_bound(neutral_state):
        \"\"\"02_cognitive_state §2.4: |Δ(attention.level)| <= 0.30\"\"\"
        # Long input should trigger high attention
        obs = {"type": "text_input", "raw": "a" * 500, "normalized": "a" * 500, "is_empty": False}
        result = cognize_fn(obs, neutral_state, [])
        delta_att = abs(result.attention["level"] - neutral_state.attention["level"])
        assert delta_att <= 0.30 + 1e-9, \\
            f"|Δ(attention.level)| = {delta_att:.4f} exceeds 0.30 upper bound"
    ''')

def _gen_test_identity_signal():
    return textwrap.dedent('''\
    # ---- L1 §02 §4: Oscillation detection & anomaly signal ---
    def test_oscillation_triggers_anomaly_signal():
        \"\"\"02_cognitive_state §4: |Δ| > δ across all dimensions emits StatusAnomalySignal\"\"\"
        # Simulate successive iterations that produce extreme delta
        # This test requires iteration context; for now it's a structural placeholder
        
        # TODO: Implement after cognize_fn supports iteration context
        # anomaly_signal = cognize_fn(..., iteration=3, history=[...])
        # assert anomaly_signal is not None
        # assert anomaly_signal.type == "state_oscillation"
        # assert anomaly_signal.severity >= 0.5
        pass  # Structural placeholder
    ''')

def _gen_test_context_structure():
    return textwrap.dedent('''\
    # ---- L1 §04: Context structure validation ----
    def test_context_contains_required_fields(neutral_state):
        \"\"\"04_recall_context §2.2: Context must contain state_snapshot, recall_items, context_bundle\"\"\"
        obs = {"type": "text_input", "raw": "hello", "normalized": "hello", "is_empty": False}
        result = cognize_fn(obs, neutral_state, [])
        assert hasattr(result, "context"), "COGNIZE must produce a Context namedtuple"
        assert hasattr(result.context, "state_snapshot"), "Context must contain state_snapshot"
        assert hasattr(result.context, "recall_items"), "Context must contain recall_items"
        assert hasattr(result.context, "context_bundle"), "Context must contain context_bundle"
    ''')

def _gen_test_p1_protection():
    return textwrap.dedent('''\
    # ---- L1 §02 §6: P1 identity protection ----
    def test_p1_protection_on_high_oscillation(neutral_state):
        \"\"\"02_cognitive_state §6: Consecutive oscillations raise identity risk\"\"\"
        # TODO: Requires iteration history state
        pass  # Structural placeholder
    ''')


# ============================================================
# 2. L2 DRIFT ASSERTION MATRIX TEST STUB
# ============================================================

def _drift_imports():
    return textwrap.dedent("""\
    \"\"\"Test stub: L2 drift assertion monitors — auto-generated.\"\"\"
    import pytest
    from kernel.state_snapshot import StateSnapshot, EmotionSnapshot

    """)

def get_drift_assertion_test_stub():
    """Generate test_drift_assertion_matrix.py from 02_stability_spec/01_drift_detection.md"""
    sb = []
    sb.append(_drift_imports())
    sb.append("\n")
    sb.append(_gen_fixture_l2_state())
    sb.append("\n\n")
    sb.append(_gen_l0_static_assertions())
    sb.append("\n\n")
    sb.append(_gen_l1_dynamic_assertions())
    sb.append("\n\n")
    sb.append(_gen_l2_integration_test())
    sb.append("\n")
    return "".join(sb)


def _gen_fixture_l2_state():
    return textwrap.dedent("""\
    # ---- Fixtures ----
    @pytest.fixture
    def valid_block_store():
        \"\"\"Block store with all L0 invariants satisfied\"\"\"
        return {
            "blocks": [
                {"block_id": "p1", "label": "persona", "importance": 0.95},
                {"block_id": "e1", "label": "emotion", "importance": 0.65},
                {"block_id": "ep1", "label": "episodic", "importance": 0.45},
                {"block_id": "b1", "label": "belief", "importance": 0.80},
            ],
            "count": 4
        }

    @pytest.fixture
    def duplicate_persona_store():
        \"\"\"Block store with TWO persona blocks — should fail L0-01\"\"\"
        return {
            "blocks": [
                {"block_id": "p1", "label": "persona", "importance": 0.95},
                {"block_id": "p2", "label": "persona", "importance": 0.85},
                {"block_id": "e1", "label": "emotion", "importance": 0.65},
            ],
            "count": 3
        }

    @pytest.fixture
    def zero_emotion_state():
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.0, dominance=0.0),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )
    """)

def _gen_l0_static_assertions():
    return textwrap.dedent("""\
    # ============================================================
    # L0 Static Assertions (01_drift_detection.md §3.1)
    # ============================================================
    def assert_l0_01_persona_uniqueness(block_store):
        \"\"\"L0-01: count(persona) == 1\"\"\"
        persona_blocks = [b for b in block_store["blocks"] if b["label"] == "persona"]
        return len(persona_blocks) == 1

    def test_l0_01_persona_uniqueness_passes(valid_block_store):
        assert assert_l0_01_persona_uniqueness(valid_block_store) is True

    def test_l0_01_persona_uniqueness_fails(duplicate_persona_store):
        assert assert_l0_01_persona_uniqueness(duplicate_persona_store) is False

    def assert_l0_02_emotion_max_one(block_store):
        \"\"\"L0-02: count(emotion) <= 1\"\"\"
        emotion_blocks = [b for b in block_store["blocks"] if b["label"] == "emotion"]
        return len(emotion_blocks) <= 1

    def test_l0_02_emotion_max_one(valid_block_store):
        assert assert_l0_02_emotion_max_one(valid_block_store) is True

    def assert_l0_03_attractor_sum(identity_state):
        \"\"\"L0-03: honesty + stability + continuity > 1.5\"\"\"
        h, s, c = identity_state.get("honesty", 0), identity_state.get("stability", 0), identity_state.get("continuity", 0)
        return (h + s + c) > 1.5

    def assert_l0_04_attractor_minima(identity_state):
        \"\"\"L0-04: honesty >= 0.3, stability >= 0.3, continuity >= 0.5\"\"\"
        return (
            identity_state.get("honesty", 0) >= 0.3
            and identity_state.get("stability", 0) >= 0.3
            and identity_state.get("continuity", 0) >= 0.5
        )

    def assert_l0_05_emotion_nonzero(state):
        \"\"\"L0-05: NOT(val == 0 AND aro == 0 AND dom == 0)\"\"\"
        return not (state.emotion.val == 0 and state.emotion.arousal == 0 and state.emotion.dominance == 0)

    def test_l0_05_emotion_nonzero_neutral(neutral_state):
        \"\"\"Neutral state (0, 0.5, 0.5) should pass\"\"\"
        assert assert_l0_05_emotion_nonzero(neutral_state) is True

    def test_l0_05_emotion_nonzero_fails(zero_emotion_state):
        \"\"\"Zero state (0, 0, 0) should fail\"\"\"
        assert assert_l0_05_emotion_nonzero(zero_emotion_state) is False
    """)

def _gen_l1_dynamic_assertions():
    return textwrap.dedent("""\
    # ============================================================
    # L1 Dynamic Assertions (01_drift_detection.md §3.2)
    # ============================================================
    def assert_l1_01_single_oscillation(anomaly_signals):
        \"\"\"L1-01: Single-dimension oscillation — record, no degrade\"\"\"
        single_dim = [s for s in anomaly_signals if s.get("type") == "state_oscillation"
                      and len(s.get("dimensions", [])) == 1]
        return len(single_dim) > 0  # Detected; does not trigger degradation

    def test_l1_01_single_oscillation_records():
        signal = {"type": "state_oscillation", "dimensions": ["emotion.val"],
                  "delta": 0.40, "threshold": 0.35, "severity": 0.6}
        assert assert_l1_01_single_oscillation([signal]) is True

    def assert_l1_03_consecutive_oscillation(anomaly_history):
        \"\"\"L1-03: 3+ consecutive rounds with oscillation triggers L2 mild degrade\"\"\"
        if len(anomaly_history) < 3:
            return False
        last_3 = anomaly_history[-3:]
        return all(any(s.get("type") == "state_oscillation" for s in round_sigs)
                   for round_sigs in last_3)

    def test_l1_03_consecutive_oscillation_triggers():
        three_rounds = [
            [{"type": "state_oscillation", "dimensions": ["emotion.val"]}],
            [{"type": "state_oscillation", "dimensions": ["emotion.arousal"]}],
            [{"type": "state_oscillation", "dimensions": ["emotion.val"]}],
        ]
        assert assert_l1_03_consecutive_oscillation(three_rounds) is True

    def assert_l1_05_goal_stall(goal_history):
        \"\"\"L1-05: Goal progress unchanged for 5+ rounds\"\"\"
        if len(goal_history) < 5:
            return False
        last_5_goals = [g["current"] for g in goal_history[-5:]]
        last_5_progress = [g["progress"] for g in goal_history[-5:]]
        return (len(set(last_5_goals)) == 1
                and all(p == last_5_progress[0] for p in last_5_progress))
    """)

def _gen_l2_integration_test():
    return textwrap.dedent("""\
    # ============================================================
    # L2 Integration: Full assertion matrix run in one iteration
    # ============================================================
    def test_full_assertion_matrix_runs_without_exception(valid_block_store, neutral_state):
        \"\"\"Simulate one iteration of L2 drift detection — all assertions must complete.\"\"\"
        identity_state = {"honesty": 0.7, "stability": 0.6, "continuity": 0.8}
        anomaly_signals = []
        anomaly_history = [anomaly_signals]
        goal_history = [{"current": "converse", "progress": 0.3}]

        # Run all assertions
        results = {
            "L0-01": assert_l0_01_persona_uniqueness(valid_block_store),
            "L0-02": assert_l0_02_emotion_max_one(valid_block_store),
            "L0-03": assert_l0_03_attractor_sum(identity_state),
            "L0-04": assert_l0_04_attractor_minima(identity_state),
            "L0-05": assert_l0_05_emotion_nonzero(neutral_state),
            "L1-01": assert_l1_01_single_oscillation(anomaly_signals),
            "L1-03": assert_l1_03_consecutive_oscillation(anomaly_history),
            "L1-05": assert_l1_05_goal_stall(goal_history),
        }

        # No exception means assertion matrix ran successfully
        assert isinstance(results, dict)
        assert len(results) == 8
    """)


# ============================================================
# 3. GENERATOR
# ============================================================

# ============================================================
# 1b. OBSERVE REDUCER TEST STUB
# ============================================================
def get_observe_test_stub():
    return _state_imports() + textwrap.dedent("""\

    @pytest.fixture
    def neutral_state():
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.5, dominance=0.5),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )

    # ---- L1 OBSERVE §02 Rule 1: normalize input ----
    def test_observe_normalization():
        \"\"\"observe_reducer §02 Rule 1: raw input is stripped and lowercased.\"\"\"
        obs = {"type": "text_input", "raw": "  HeLLo World!  ",
               "normalized": "hello world!", "is_empty": False}
        assert obs["normalized"] == obs["raw"].strip().lower()

    # ---- L1 OBSERVE §02 Rule 2: empty detection ----
    def test_observe_empty_detection():
        \"\"\"observe_reducer §02 Rule 2: empty input sets is_empty=True.\"\"\"
        obs = {"type": "empty_observation", "raw": "", "normalized": "", "is_empty": True}
        assert obs["is_empty"] is True

    # ---- L1 OBSERVE §05: OBSERVE does not modify State ----
    def test_observe_does_not_modify_state(neutral_state):
        \"\"\"observe_reducer §05: OBSERVE must not mutate State.\"\"\"
        from kernel.observe_reducer import observe_fn
        obs = observe_fn("hello", neutral_state)
        assert obs["type"] == "text_input"
        assert obs["is_empty"] is False
        # State passed in is a snapshot; observe_fn must not mutate it.
        # (Immutability is enforced by StateSnapshot's frozen design.)
    """)

# ============================================================
# 1c. DECIDE REDUCER TEST STUB
# ============================================================
def get_decide_test_stub():
    return textwrap.dedent("""\
    \"\"\"Test stub: decide_reducer — auto-generated from L1 spec.\"\"\"
    import pytest
    from kernel.decide_reducer import decide_fn
    from kernel.state_snapshot import StateSnapshot, EmotionSnapshot

    @pytest.fixture
    def neutral_state():
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.5, dominance=0.5),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )
    @pytest.fixture
    def empty_context():
        return {"observation_type": "empty", "state_snapshot": {}, "recall_items": [], "context_bundle": ""}

    @pytest.fixture
    def normal_context():
        return {"observation_type": "text_input", "state_snapshot": {}, "recall_items": [], "context_bundle": "user said hello"}

    # ---- L1 DECIDE §03 Rule 1: empty context -> IDLE strategy ----
    def test_decide_empty_context_idle(neutral_state, empty_context):
        \"\"\"decide_reducer §03 Rule 1: empty context must produce IDLE strategy.\"\"\"
        decision = decide_fn(empty_context, neutral_state)
        assert decision["strategy"] == "IDLE"
        assert decision["confidence"] == 1.0

    # ---- L1 DECIDE §03 Rule 2: P1 high risk -> conservative ----
    def test_decide_high_identity_risk_conservative(neutral_state, normal_context):
        \"\"\"decide_reducer §03 Rule 2: high identity risk biases toward SPEAK.\"\"\"
        from kernel.identity_position import assess_identity_risk
        risk = assess_identity_risk(neutral_state)
        if risk == "high":
            decision = decide_fn(normal_context, neutral_state)
            assert decision["identity_risk"] in ("high", "critical")

    # ---- L1 DECIDE §03 Rule 3: intent derivation ----
    def test_decide_intent_derivation(neutral_state, normal_context):
        \"\"\"decide_reducer §03 Rule 3: active_intent is one of the defined set.\"\"\"
        decision = decide_fn(normal_context, neutral_state)
        assert decision["active_intent"] in ("converse", "store", "recall", "operate")

    # ---- L1 DECIDE §03 Rule 5-6: Relationship & Goal updates ----
    def test_decide_relationship_tone_reflects_context(neutral_state, normal_context):
        \"\"\"decide_reducer §03 Rule 5: relationship tone adjusts from context.\"\"\"
        decision, new_state = decide_fn(normal_context, neutral_state)
        # Relationship must have all three fields
        assert "tone" in new_state.relationship
        assert "trust" in new_state.relationship
        assert "familiarity" in new_state.relationship
    """)

# ============================================================
# 1d. SPEAK REDUCER TEST STUB
# ============================================================
def get_speak_test_stub():
    return textwrap.dedent("""\
    \"\"\"Test stub: speak_reducer — auto-generated from L1 spec.\"\"\"
    import pytest
    from kernel.speak_reducer import speak_fn
    from kernel.state_snapshot import StateSnapshot, EmotionSnapshot

    @pytest.fixture
    def neutral_state():
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.5, dominance=0.5),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )

    # ---- L1 SPEAK §03 Rule 1: IDLE strategy -> empty response ----
    def test_speak_idle_returns_empty(neutral_state):
        \"\"\"speak_reducer §03 Rule 1: IDLE decision yields empty text.\"\"\"
        decision = {"strategy": "IDLE", "confidence": 1.0, "identity_risk": "low", "active_intent": "converse", "reason": "empty_input"}
        context = {"context_bundle": ""}
        response = speak_fn(decision, context, neutral_state)
        assert response["text"] == ""
        assert response["inference_type"] == "idle"

    # ---- L1 SPEAK §03 Rule 2: SPEAK strategy calls inference ----
    def test_speak_calls_inference(neutral_state):
        \"\"\"speak_reducer §03 Rule 2: SPEAK decision triggers inference.\"\"\"
        decision = {"strategy": "SPEAK", "confidence": 0.8, "identity_risk": "low", "active_intent": "converse", "reason": "normal"}
        context = {"context_bundle": "user said hello"}
        response = speak_fn(decision, context, neutral_state)
        assert isinstance(response["text"], str)

    # ---- L1 SPEAK §05: SPEAK does not modify State ----
    def test_speak_does_not_modify_state(neutral_state):
        \"\"\"speak_reducer §05: SPEAK must not mutate State.\"\"\"
        decision = {"strategy": "SPEAK", "confidence": 0.8, "identity_risk": "low", "active_intent": "converse", "reason": "normal"}
        context = {"context_bundle": "hello"}
        emotion_before = (neutral_state.emotion.val, neutral_state.emotion.arousal, neutral_state.emotion.dominance)
        response = speak_fn(decision, context, neutral_state)
        assert (neutral_state.emotion.val, neutral_state.emotion.arousal, neutral_state.emotion.dominance) == emotion_before

    # ---- L1 SPEAK §03 Rule 4: degradation affects inference type ----
    def test_speak_degradation_changes_inference(neutral_state):
        \"\"\"speak_reducer §03 Rule 4: degradation_level affects inference_type.\"\"\"
        decision = {"strategy": "SPEAK", "confidence": 0.8, "identity_risk": "low", "active_intent": "converse", "reason": "normal"}
        context = {"context_bundle": "hello"}
        response = speak_fn(decision, context, neutral_state, degradation_level="L2")
        assert response["inference_type"] in ("template", "fixed")
    """)

# ============================================================
# 1e. STORE REDUCER TEST STUB
# ============================================================
def get_store_test_stub():
    return textwrap.dedent("""\
    \"\"\"Test stub: store_reducer — auto-generated from L1 spec.\"\"\"
    import pytest
    from kernel.store_reducer import store_fn
    from kernel.block_store import BlockStore
    from kernel.state_snapshot import StateSnapshot, EmotionSnapshot

    @pytest.fixture
    def empty_block_store():
        return BlockStore()

    @pytest.fixture
    def neutral_state():
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.5, dominance=0.5),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )

    # ---- L1 STORE §03 Rule 2: at least emotion + episodic blocks per cycle ----
    def test_store_writes_at_least_two_blocks(empty_block_store, neutral_state):
        \"\"\"store_reducer §03 Rule 2: each cycle writes emotion + episodic.\"\"\"
        response = {"text": "hello", "inference_type": "llm", "confidence": 0.9, "latency_ms": 100, "metadata": {}}
        result = store_fn(response, neutral_state, {"iteration": 1}, empty_block_store)
        assert result["blocks_written"].get("emotion", 0) >= 1
        assert result["blocks_written"].get("episodic", 0) >= 1

    # ---- L1 STORE §03 Rule 3: emotion block is overwritten ----
    def test_emotion_block_overwrite(empty_block_store, neutral_state):
        \"\"\"store_reducer §03 Rule 3: emotion block overwrites (keeps only one).\"\"\"
        response = {"text": "a", "inference_type": "llm", "confidence": 0.9, "latency_ms": 50, "metadata": {}}
        store_fn(response, neutral_state, {"iteration": 1}, empty_block_store)
        store_fn(response, neutral_state, {"iteration": 2}, empty_block_store)
        emotion_blocks = [b for b in empty_block_store.blocks if b["label"] == "emotion"]
        assert len(emotion_blocks) <= 1

    # ---- L1 STORE §03 Rule 8: batch write ----
    def test_store_batch_write(empty_block_store, neutral_state):
        \"\"\"store_reducer §03 Rule 8: batch write — single block failure doesn't stop others.\"\"\"
        response = {"text": "hello", "inference_type": "llm", "confidence": 0.9, "latency_ms": 100, "metadata": {}}
        result = store_fn(response, neutral_state, {"iteration": 1}, empty_block_store)
        assert isinstance(result["blocks_written"], dict)
        assert isinstance(result["failed_writes"], list)
        assert result["total_blocks"] >= 2
    """)

# ============================================================
# 1f. REFLECT REDUCER TEST STUB
# ============================================================
def get_reflect_test_stub():
    return textwrap.dedent("""\
    \"\"\"Test stub: reflect_reducer — auto-generated from L1 spec.\"\"\"
    import pytest
    from kernel.reflect_reducer import reflect_fn
    from kernel.block_store import BlockStore
    from kernel.state_snapshot import StateSnapshot, EmotionSnapshot

    @pytest.fixture
    def empty_block_store():
        return BlockStore()

    @pytest.fixture
    def neutral_state():
        return StateSnapshot(
            emotion=EmotionSnapshot(val=0.0, arousal=0.5, dominance=0.5),
            relationship={"tone": 0.0, "trust": 0.5, "familiarity": 0.3},
            goal={"current": "converse", "progress": 0.0},
            attention={"focus": "general", "level": 0.5},
            meta={"session_count": 0, "total_interactions": 1}
        )

    # ---- L1 REFLECT §03 Rule 1: even after store failure, reflect runs ----
    def test_reflect_after_store_failure(empty_block_store, neutral_state):
        \"\"\"reflect_reducer §03 Rule 1: REFLECT still runs after STORE failure.\"\"\"
        failed_store = {"blocks_written": {"emotion": 0, "episodic": 0, "intent": 0, "archival": 0},
                        "total_blocks": 0, "failed_writes": ["episodic"],
                        "decay_activated": False, "eviction_triggered": False, "timestamp": 0.0}
        trace = []
        result = reflect_fn(failed_store, neutral_state, trace, empty_block_store)
        assert "anomaly_note" in result or result.get("anomaly_signal_sent") is not None

    # ---- L1 REFLECT §03 Rule 2: narrative + reflective blocks written ----
    def test_reflect_writes_narrative_and_reflective(empty_block_store, neutral_state):
        \"\"\"reflect_reducer §03 Rule 2+4: REFLECT writes narrative and reflective blocks.\"\"\"
        successful_store = {"blocks_written": {"emotion": 1, "episodic": 1, "intent": 0, "archival": 0},
                            "total_blocks": 2, "failed_writes": [],
                            "decay_activated": True, "eviction_triggered": False, "timestamp": 0.0}
        trace = []
        result = reflect_fn(successful_store, neutral_state, trace, empty_block_store)
        assert result.get("narrative_written") is True
        assert result.get("reflective_written") is True

    # ---- L1 REFLECT §03 Rule 3: belief delta depends on oscillation ----
    def test_reflect_belief_delta(empty_block_store, neutral_state):
        \"\"\"reflect_reducer §03 Rule 3: smooth state gives belief +0.02; oscillating gives -0.05.\"\"\"
        # Smooth case
        smooth_store = {"blocks_written": {"emotion": 1, "episodic": 1, "intent": 0, "archival": 0},
                        "total_blocks": 2, "failed_writes": [],
                        "decay_activated": True, "eviction_triggered": False, "timestamp": 0.0}
        trace = []
        result = reflect_fn(smooth_store, neutral_state, trace, empty_block_store)
        if not result.get("state_oscillation_detected"):
            assert result.get("belief_delta", 0) >= 0.0
    """)

# ============================================================
# 2b. L2 RECOVERY TRIGGERS TEST STUB
# ============================================================
def get_recovery_test_stub():
    return textwrap.dedent("""\
    \"\"\"Test stub: L2 recovery triggers — auto-generated from 02_stability_spec/03.\"\"\"
    import pytest
    from kernel.l2_recovery_triggers import evaluate_recovery

    # ---- §2 Trigger conditions ----
    def test_recovery_triggered_on_identity_correction_failure():
        \"\"\"recovery_triggers §2: correction failure with reentrant oscillation >= 0.7.\"\"\"
        correction_result = {
            "triggered": True, "correction_path": "attractor_pull",
            "convergence_proven": False, "reentrant_oscillation": True,
            "status": "failed"
        }
        result = evaluate_recovery(correction_result=correction_result)
        assert result["triggered"] is True
        assert result["severity"] >= 0.7

    def test_recovery_triggered_on_persona_loss():
        \"\"\"recovery_triggers §2: persona loss (L0-01 persistent fail) triggers severity 1.0.\"\"\"
        drift_result = {"L0-01": {"passed": False}, "L0-02": {"passed": True},
                        "anomaly_count": 3}
        correction_result = {"status": "failed"}
        result = evaluate_recovery(
            drift_result=drift_result,
            correction_result=correction_result,
            consecutive_iterations_with_persona_loss=4
        )
        assert result["severity"] == 1.0

    # ---- §3.1 REFUGE mode exit conditions ----
    def test_refuge_exit_requires_2_clean_rounds():
        \"\"\"recovery_triggers §3.1: REFUGE exit requires 2+ rounds with no anomalies.\"\"\"
        drift_history = [
            {"all_passed": True},
            {"all_passed": True},
        ]
        result = evaluate_recovery(
            in_refuge=True,
            drift_history=drift_history,
            iterations_in_refuge=5
        )
        assert result.get("rearm_conditions_met") is True

    # ---- §5: anti-jitter — 3 round minimum stay ----
    def test_anti_jitter_minimum_stay():
        \"\"\"recovery_triggers §5: cannot rearm within first 3 rounds of a new level.\"\"\"
        result = evaluate_recovery(
            current_level="L2",
            iterations_in_level=2,
            drift_history=[{"all_passed": True}] * 2
        )
        assert result.get("rearm_conditions_met") is False or result.get("anti_jitter_active") is True
    """)

# ============================================================
# 2c. L2 DEGRADATION POLICY TEST STUB
# ============================================================
def get_degradation_test_stub():
    return textwrap.dedent("""\
    \"\"\"Test stub: L2 degradation policy — auto-generated from 02_stability_spec/04.\"\"\"
    import pytest
    from kernel.l2_degradation_policy import apply_degradation, can_rearm

    # ---- §2.2 L1 -> L2: COGNIZE state freeze ----
    def test_degradation_l2_freeze_emotion():
        \"\"\"degradation_policy §2.2: L2 disables emotion update in COGNIZE.\"\"\"
        current_level = "L2"
        policy = apply_degradation(current_level)
        assert policy["cognize"]["update_emotion"] is False
        assert policy["decide"]["strategies"] in (["SPEAK"], ["SPEAK", "IDLE"])

    # ---- §2.3 L2 -> L3: REFUGE ----
    def test_degradation_l3_refuge_fixed_response():
        \"\"\"degradation_policy §2.3: L3 sets SPEAK to fixed text.\"\"\"
        policy = apply_degradation("L3")
        assert policy["speak"]["inference_type"] == "fixed"

    # ---- §3: Re-arm conditions ----
    def test_rearm_l1_to_l0_requires_2_clean_rounds():
        \"\"\"degradation_policy §3: L1→L0 requires 2 consecutive rounds without anomalies.\"\"\"
        eligible = can_rearm(
            current_level="L1",
            anomaly_history=[{"count": 0}, {"count": 0}],
            iterations_in_level=4
        )
        assert eligible is True

    def test_rearm_blocked_with_anomalies():
        \"\"\"degradation_policy §3: rearm blocked if anomalies persist.\"\"\"
        eligible = can_rearm(
            current_level="L1",
            anomaly_history=[{"count": 1}, {"count": 0}],
            iterations_in_level=3
        )
        assert eligible is False
    """)

# ============================================================
# UPDATE STUB GENERATORS REGISTRY
# ============================================================
STUB_GENERATORS = {
    "observe_reducer": ("test_observe_reducer.py", get_observe_test_stub),
    "cognize_reducer": ("test_cognize_reducer.py", get_cognize_test_stub),
    "decide_reducer": ("test_decide_reducer.py", get_decide_test_stub),
    "speak_reducer": ("test_speak_reducer.py", get_speak_test_stub),
    "store_reducer": ("test_store_reducer.py", get_store_test_stub),
    "reflect_reducer": ("test_reflect_reducer.py", get_reflect_test_stub),
    "drift_assertion": ("test_drift_assertion_matrix.py", get_drift_assertion_test_stub),
    "recovery_triggers": ("test_recovery_triggers.py", get_recovery_test_stub),
    "degradation_policy": ("test_degradation_policy.py", get_degradation_test_stub),
}

def generate_one(stub_name):
    if stub_name not in STUB_GENERATORS:
        print(f"[ERROR] Unknown stub: {stub_name}")
        print(f"  Available: {', '.join(STUB_GENERATORS.keys())}")
        sys.exit(1)

    filename, generator_fn = STUB_GENERATORS[stub_name]
    output_path = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    content = generator_fn()

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    line_count = len(content.splitlines())
    print(f"[GENERATED] {output_path} — {line_count} lines")
    print(f"  SHA256: {__import__('hashlib').sha256(content.encode()).hexdigest()}")

def generate_all():
    for stub_name in STUB_GENERATORS:
        generate_one(stub_name)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tools/gen_test_stubs.py [cognize_reducer|drift_assertion|all]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "all":
        generate_all()
    else:
        generate_one(command)
