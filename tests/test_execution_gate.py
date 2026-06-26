"""Tests for P5.3 execution boundary layer."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol.constants import (  # noqa: E402
    EXECUTION_GATE_ALLOW,
    EXECUTION_GATE_DENY,
    EXECUTION_GATE_REQUIRE_CONFIRM,
)
from protocol.models import ExecutionPolicy, RepairPlan  # noqa: E402
from storage.repair.execution_gate import evaluate_execution_gate  # noqa: E402
from storage.repair.execution_policy_store import ExecutionPolicyStore  # noqa: E402

CHUNK = "aa" * 32


class ExecutionGateTests(unittest.TestCase):
    def _plan(self, sources=("http://127.0.0.1:7864",)):
        return RepairPlan(chunk_hash=CHUNK, priority=1.0, sources=sources)

    def _source(self, *, probe_checked=True, remote_has=True):
        return {
            "rank": 1,
            "host": "http://127.0.0.1:7864",
            "reason": "connected_peer",
            "probe": {
                "state_checked": probe_checked,
                "remote_has": remote_has,
                "chunk_states": [
                    {"hash": CHUNK, "remote_has": remote_has, "state_checked": probe_checked},
                ],
            },
        }

    def test_require_confirm_without_user(self):
        policy = ExecutionPolicy.default()
        gate = evaluate_execution_gate(
            [self._plan()],
            policy,
            suggested_sources=[self._source()],
            user_confirmed=False,
        )
        self.assertEqual(gate["gate"], EXECUTION_GATE_REQUIRE_CONFIRM)

    def test_allow_with_confirm_and_probe(self):
        policy = ExecutionPolicy.default()
        gate = evaluate_execution_gate(
            [self._plan()],
            policy,
            suggested_sources=[self._source()],
            user_confirmed=True,
        )
        self.assertEqual(gate["gate"], EXECUTION_GATE_ALLOW)
        self.assertEqual(gate["allowed_count"], 1)

    def test_deny_without_probe_evidence(self):
        policy = ExecutionPolicy.default()
        gate = evaluate_execution_gate(
            [self._plan()],
            policy,
            suggested_sources=[self._source(probe_checked=False, remote_has=False)],
            user_confirmed=True,
        )
        self.assertEqual(gate["gate"], EXECUTION_GATE_DENY)

    def test_deny_disallowed_source_reason(self):
        policy = ExecutionPolicy(
            allowed_sources=("trusted_registry_peer",),
            require_probe=False,
            require_user_confirm=False,
        )
        gate = evaluate_execution_gate(
            [self._plan()],
            policy,
            suggested_sources=[{"host": "http://127.0.0.1:7864", "reason": "connected_peer"}],
            user_confirmed=True,
        )
        self.assertEqual(gate["gate"], EXECUTION_GATE_DENY)


class ExecutionPolicyStoreTests(unittest.TestCase):
    def test_persist_policy(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            path = os.path.join(tmp.name, "policy.json")
            store = ExecutionPolicyStore(path)
            custom = ExecutionPolicy(require_user_confirm=False, max_concurrency=4)
            store.set(custom)
            restored = ExecutionPolicyStore(path)
            self.assertFalse(restored.get().require_user_confirm)
            self.assertEqual(restored.get().max_concurrency, 4)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
