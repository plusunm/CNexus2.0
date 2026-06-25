#!/usr/bin/env python3
"""Conversation engine thinking mode tests."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.conversation_engine import (  # noqa: E402
    build_emergent_system_content,
    build_precision_system_content,
    get_inference_params,
    normalize_thinking_mode,
)
from core.entropy import combine_entropy_seeds, temperature_from_seed  # noqa: E402


def main():
    assert normalize_thinking_mode("emergent") == "emergent"
    assert normalize_thinking_mode("strict") == "precision"

    seed = combine_entropy_seeds(0x1111, 0x2222, 0x3333)
    precision = get_inference_params("precision", seed)
    emergent = get_inference_params("emergent", seed)
    assert precision["temperature"] == 0.0
    assert precision["provenance_enforced"] is True
    assert emergent["temperature"] == temperature_from_seed(seed)
    assert emergent["use_reflection"] is True
    assert emergent["provenance_enforced"] is False

    emergent_prompt = build_emergent_system_content("如何设计 DAO?", "memory A", seed)
    assert "EMERGENT" in emergent_prompt
    assert "Reflection Log" in emergent_prompt
    assert "如何设计 DAO?" in emergent_prompt

    precision_prompt = build_precision_system_content("memory B", provenance_preamble="Prov hint")
    assert "PRECISION" in precision_prompt
    assert "memory B" in precision_prompt

    print("precision temp:", precision["temperature"])
    print("emergent temp:", emergent["temperature"])
    print("\nCONVERSATION ENGINE TEST PASSED")


if __name__ == "__main__":
    main()
