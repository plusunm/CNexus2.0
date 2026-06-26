"""P5 repair module — diff, plan, execute."""

from .diff_engine import diff_all_manifests, diff_by_root, diff_manifest
from .execution_gate import evaluate_execution_gate
from .execution_policy_store import ExecutionPolicyStore
from .executor import execute_repair_plans
from .planner import build_repair_plans, plans_from_diff_rows
from .source_probe import enrich_suggested_sources, enrich_source_probe
from .source_suggestions import suggest_repair_sources

__all__ = [
    "build_repair_plans",
    "diff_all_manifests",
    "diff_by_root",
    "diff_manifest",
    "enrich_source_probe",
    "enrich_suggested_sources",
    "evaluate_execution_gate",
    "execute_repair_plans",
    "ExecutionPolicyStore",
    "plans_from_diff_rows",
    "suggest_repair_sources",
]
