"""L0 mind overview snapshot — aligned with frontend statusToMindOverview."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from ..state import EngineStateManager
from .activation import ActivationService
from .api_auth_status import ApiAuthStatusService
from .assets_status import AssetsStatusService
from .audit_chain_status import AuditChainStatusService
from .consensus_status import ConsensusStatusService
from .identity_status import IdentityStatusService
from .peers_status import PeersStatusService
from .resilience_status import ResilienceStatusService
from .status_subsystems import StatusSubsystemsService


class StatusSnapshotService:
    """Build /api/status L0 payload from engine state + gateway status services."""

    def __init__(
        self,
        state: EngineStateManager,
        subsystems: StatusSubsystemsService,
        peers: PeersStatusService,
        resilience: ResilienceStatusService,
        identity: IdentityStatusService,
        audit: AuditChainStatusService,
        api_auth: ApiAuthStatusService,
        consensus: ConsensusStatusService,
        assets: AssetsStatusService,
        activation: ActivationService,
    ):
        self._state = state
        self._subsystems = subsystems
        self._peers = peers
        self._resilience = resilience
        self._identity = identity
        self._audit = audit
        self._api_auth = api_auth
        self._consensus = consensus
        self._assets = assets
        self._activation = activation

    def build(self) -> Dict[str, Any]:
        memory_items = self._activation.overview_items()

        def _snapshot(engine: Dict[str, Any]) -> Dict[str, Any]:
            st = engine["state"]
            ms = engine["memory_store"]
            iteration = engine["current_iteration"]
            goal = st.goal or {}
            meta = st.meta or {}
            relationship = st.relationship or {}
            episodic_feed = [
                {"text": item.get("title", ""), "ago": "recent"}
                for item in memory_items
                if item.get("tag") == "episode"
            ][:8] or [{"text": "等待对话或上传以生成记忆节点", "ago": "now"}]

            return {
                "schema_version": "2.0",
                "active": True,
                "engine_initialized": True,
                "memory_count": len(ms.blocks),
                "execution_count": iteration,
                "current_iteration": iteration,
                "status": "online",
                "emotion": {
                    "valence": st.emotion.val,
                    "arousal": st.emotion.arousal,
                    "dominance": st.emotion.dominance,
                },
                "goal": {
                    "current": goal.get("current", "explore"),
                    "progress": goal.get("progress", 0.0),
                },
                "relationship": {"closeness": relationship.get("closeness", 0.5)},
                "cog_state": {
                    "active_intent": meta.get("active_intent", "idle"),
                    "accumulated_weight": meta.get("weight", 0),
                    "total_observations": iteration,
                },
                "attention": {"focus": "general", "level": 0.5},
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                "cards": {
                    "goal": {
                        "title": goal.get("current", "探索"),
                        "progress": goal.get("progress", 0.0),
                        "progress_label": f"{round(goal.get('progress', 0.0) * 100)}%",
                        "alignment": 0.75,
                        "alignment_label": "75%",
                        "priority": 0.5,
                        "priority_label": "中",
                    },
                    "identity": {
                        "summary": "CNexus 2.0 Personal",
                        "stability": 0.7,
                        "stability_label": "70%",
                        "consistency": 0.8,
                        "consistency_label": "80%",
                        "updated_ago": "now",
                    },
                    "belief": {
                        "content": goal.get("current", "探索"),
                        "confidence": 0.65,
                        "confidence_label": "65%",
                        "evidence_count": iteration,
                        "conflict_count": 0,
                    },
                    "focus": {
                        "title": meta.get("active_intent", "idle"),
                        "attention_label": "50%",
                        "duration_label": "realtime",
                        "related_goals": 1,
                    },
                },
                "feeds": {
                    "episodic": episodic_feed,
                    "reflections": [{"text": f"已完成 {iteration} 次认知循环", "ago": "now"}],
                    "changes": [f"memory_blocks={len(ms.blocks)}", "stable"],
                },
                "system": {
                    "health_score": 0.85,
                    "health_label": "stable",
                    "memory_capacity_pct": min(99, len(ms.blocks) * 2),
                    "governance_label": "personal",
                    "governance_conflicts": 0,
                    "reflective_active": 0,
                    "last_update_ago": "now",
                    "api_online": True,
                },
                "chat_context": {
                    "goal": goal.get("current", "探索"),
                    "belief": "探索",
                    "identity": "CNexus 2.0 Personal",
                },
                "memory_items": memory_items,
                "consolidation": self._subsystems.consolidation_status(),
                "wormhole_links": _wormhole_links_snapshot(engine),
                "projection_links": _projection_links_snapshot(engine),
                "persistence": self._subsystems.persistence_status(),
                "node_identity": self._identity.build(),
                "audit_chain": self._audit.build(),
                "api_auth": self._api_auth.build(),
                "peers": self._peers.build(),
                "consensus": self._consensus.build(),
                "assets": self._assets.build(),
                "resilience": self._resilience.build(),
                "replay": self._subsystems.replay_status(),
                "reflection": self._subsystems.reflection_status(),
            }

        return self._state.mutate(_snapshot)


def _projection_links_snapshot(engine: Dict[str, Any]) -> List[Dict[str, Any]]:
    store = engine.setdefault("projection", {"nodes": {}, "links": []})
    return [
        {
            "source": link.get("source"),
            "target": link.get("target"),
            "type": link.get("type"),
        }
        for link in store.get("links", [])
    ]


def _wormhole_links_snapshot(engine: Dict[str, Any]) -> List[Dict[str, Any]]:
    links = engine.setdefault("activation", {}).setdefault("wormhole_links", [])
    return [
        {
            "source": link.get("source"),
            "target": link.get("target"),
            "similarity": link.get("similarity"),
            "energy": link.get("energy"),
        }
        for link in links
    ]
