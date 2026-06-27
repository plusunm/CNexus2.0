"""
CNexus Application Facade — unified semantic entry (P5.3 control surface).

Single entry for publish / find / sync / connect / repair without exposing
protocol-layer wiring to callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from protocol.constants import EXECUTION_GATE_REQUIRE_CONFIRM
    from protocol.ids import graph_id_for_owner_topic
    from protocol.models import CatalogEntry, Commit, Graph, Manifest
except ImportError:
    from cnexus_protocol.constants import EXECUTION_GATE_REQUIRE_CONFIRM
    from cnexus_protocol.ids import graph_id_for_owner_topic
    from cnexus_protocol.models import CatalogEntry, Commit, Graph, Manifest

from .memory_publish import build_memory_publish_objects, encode_memory_blocks
from .state import (
    PHASE_CONNECTED,
    PHASE_DIAGNOSED,
    PHASE_GATE_PREVIEW,
    PHASE_IDLE,
    PHASE_PUBLISHED,
    PHASE_REPAIR_COMPLETE,
    PHASE_REPAIR_PENDING,
    ApplicationControlState,
)

JsonResponse = Tuple[Dict[str, Any], int]
MemoryBlocksFn = Callable[[], List[Dict[str, Any]]]
IdentityFn = Callable[[], str]
PeerRegistryFn = Callable[[], Any]


@dataclass
class ApplicationFacade:
    """
    Runtime Application Layer — binds memory, cognitive, catalog, storage, repair.

    Transport (handshake, DHT) stays outside; connect reports are absorbed here.
    """

    cognitive: Any
    catalog: Any = None
    storage: Any = None
    repair_service: Any = None
    control: ApplicationControlState = field(default_factory=ApplicationControlState)
    memory_blocks: Optional[MemoryBlocksFn] = None
    identity_pubkey: IdentityFn = lambda: ""
    get_peer_registry: Optional[PeerRegistryFn] = None
    constitution_hash: str = ""

    def _owner(self) -> str:
        return str(self.identity_pubkey() or "").strip().lower()

    def _constitution(self) -> str:
        return str(self.constitution_hash or ("00" * 32))

    def status(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "ok": True,
            "layer": "application",
            "control": self.control.to_dict(),
            "memory_block_count": len(self.memory_blocks()) if self.memory_blocks else 0,
        }
        if self.cognitive is not None:
            payload["cognitive"] = self.cognitive.status()
        if self.catalog is not None:
            payload["catalog"] = self.catalog.store.status()
        if self.storage is not None:
            payload["storage"] = self.storage.status()
        if self.repair_service is not None:
            policy, _ = self.repair_service.get_execution_policy()
            payload["repair_policy"] = policy.get("policy")
        return payload

    def publish(
        self,
        graph: Graph,
        commit: Commit,
        *,
        manifest: Optional[Manifest] = None,
        chunk_hashes: Optional[Sequence[str]] = None,
        chunk_payloads: Optional[Sequence[Any]] = None,
        size: int = 0,
    ) -> Dict[str, Any]:
        if self.cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}
        result = self.cognitive.publish(
            graph,
            commit,
            manifest=manifest,
            chunk_hashes=chunk_hashes,
            chunk_payloads=chunk_payloads,
            size=int(size),
        )
        if result.get("ok"):
            self.control.transition(PHASE_PUBLISHED, last_publish=dict(result))
        return result

    def publish_memory(
        self,
        *,
        block_ids: Optional[Sequence[str]] = None,
        graph_id: str = "",
        topic: str = "memory/local",
        parent_commit: str = "",
    ) -> Dict[str, Any]:
        """Publish selected memory blocks as verified chunks → manifest → commit → catalog."""
        if self.cognitive is None:
            return {"ok": False, "error": "cognitive_unavailable"}
        if self.memory_blocks is None:
            return {"ok": False, "error": "memory_unavailable"}
        owner = self._owner()
        if not owner:
            return {"ok": False, "error": "identity_unavailable"}

        all_blocks = self.memory_blocks()
        if block_ids:
            wanted = {str(b).lower() for b in block_ids}
            blocks = [
                b for b in all_blocks
                if str(b.get("block_id") or b.get("id") or "").lower() in wanted
            ]
        else:
            blocks = list(all_blocks)
        if not blocks:
            return {"ok": False, "error": "no_memory_blocks"}

        gid = str(graph_id or "").strip().lower() or graph_id_for_owner_topic(owner, topic)
        parent_ids: Tuple[str, ...] = ()
        if parent_commit:
            parent_ids = (str(parent_commit),)
        elif self.cognitive.store.get_head_commit_id(gid):
            parent_ids = (self.cognitive.store.get_head_commit_id(gid),)

        payloads, hashes = encode_memory_blocks(blocks)
        graph, commit, manifest = build_memory_publish_objects(
            graph_id=gid,
            owner=owner,
            topic=topic,
            chunk_hashes=hashes,
            parent_ids=parent_ids,
            constitution_hash=self._constitution(),
            message=f"memory blocks: {len(blocks)}",
        )
        return self.publish(
            graph,
            commit,
            manifest=manifest,
            chunk_payloads=payloads,
            size=sum(len(p["bytes"]) for p in payloads),
        ) | {"block_count": len(blocks)}

    def find(
        self,
        *,
        graph_id: str = "",
        topic: str = "",
        owner: str = "",
        limit: int = 64,
    ) -> Dict[str, Any]:
        if self.catalog is None:
            return {"ok": False, "error": "catalog_unavailable", "entries": []}
        rows = self.catalog.store.list_entries(limit=int(limit))
        gid = str(graph_id or "").strip().lower()
        topic_l = str(topic or "").strip().lower()
        owner_l = str(owner or "").strip().lower()
        filtered: List[CatalogEntry] = []
        for entry in rows:
            if gid and entry.graph_id.lower() != gid:
                continue
            if topic_l and topic_l not in (entry.topic or "").lower():
                continue
            if owner_l and entry.owner.lower() != owner_l:
                continue
            filtered.append(entry)
        return {
            "ok": True,
            "count": len(filtered),
            "entries": [row.to_dict() for row in filtered],
        }

    def sync(self, peer_host: str, *, peer_id: str = "") -> Dict[str, Any]:
        """Catalog exchange + cognitive commit pull (no handshake — use connect for full flow)."""
        if not peer_host:
            return {"ok": False, "error": "missing_peer_host"}
        report: Dict[str, Any] = {"ok": False, "peer_host": peer_host}
        if self.catalog is None:
            report["error"] = "catalog_unavailable"
            return report
        catalog_report = self.catalog.exchange_with_peer(peer_host, peer_id=peer_id)
        report["catalog"] = catalog_report
        if not catalog_report.get("ok"):
            report["error"] = str(catalog_report.get("error") or "catalog_exchange_failed")
            return report
        if self.cognitive is None:
            report["ok"] = True
            report["cognitive"] = {"ok": False, "skipped": True}
            return report
        cognitive_report = self.cognitive.sync_from_catalog_peer(peer_host, catalog_report)
        report["cognitive"] = cognitive_report
        report["ok"] = bool(cognitive_report.get("ok"))
        if report["ok"]:
            self.control.transition(PHASE_CONNECTED, peer_id=peer_id, peer_host=peer_host)
        return report

    def absorb_connect(self, connect_report: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest connectivity_connect output into unified application control state."""
        self.control.absorb_connect(connect_report or {})
        hook = dict(self.control.last_hook)
        gate = dict(self.control.last_gate)
        return {
            "ok": bool(connect_report.get("ok")),
            "phase": self.control.phase,
            "control": self.control.to_dict(),
            "repair_hook": hook,
            "execution_gate": gate or hook.get("execution_gate"),
            "next_steps": hook.get("next_steps") or {
                "preview_gate": "POST /api/application/repair {\"action\":\"gate\"}",
                "execute": "POST /api/application/repair {\"action\":\"execute\",\"confirm\":true}",
            },
        }

    def diagnose(self, *, scope: str = "all") -> Dict[str, Any]:
        """Local integrity diagnosis — diff + plans, no peer required."""
        if self.repair_service is None:
            return {"ok": False, "error": "repair_unavailable"}
        diff_payload, diff_status = self.repair_service.detect_missing(scope=scope)
        plans_payload, _ = self.repair_service.generate_plan(scope=scope)
        self.control.transition(PHASE_DIAGNOSED)
        return {
            "ok": diff_status == 200,
            "scope": scope,
            "diff": diff_payload,
            "repair_plans": plans_payload.get("plans") or [],
            "plan_count": int(plans_payload.get("count") or 0),
            "control": self.control.to_dict(),
        }

    def repair(
        self,
        action: str,
        *,
        peer_host: str = "",
        peer_id: str = "",
        plans: Optional[Sequence[Dict[str, Any]]] = None,
        suggested_sources: Optional[Sequence[Dict[str, Any]]] = None,
        confirm: bool = False,
        probe_sources: bool = True,
        include_gate: bool = True,
        user_confirmed: bool = False,
    ) -> JsonResponse:
        """
        Unified repair control surface: hook | gate | execute.

        Uses last connect context when peer_host omitted.
        """
        if self.repair_service is None:
            return {"ok": False, "error": "repair_unavailable"}, 503

        act = str(action or "hook").strip().lower()
        host = str(peer_host or self.control.peer_host or "").strip()
        pid = str(peer_id or self.control.peer_id or "").strip()
        reg = self.get_peer_registry() if self.get_peer_registry else None

        if act == "hook":
            if not host:
                return {"ok": False, "error": "missing_peer_host"}, 400
            hook = self.repair_service.build_connect_hook(
                peer_host=host,
                peer_id=pid,
                peer_registry=reg,
                probe_sources=probe_sources,
                include_gate=include_gate,
            )
            self.control.transition(
                PHASE_GATE_PREVIEW if hook.get("execution_gate") else PHASE_DIAGNOSED,
                peer_id=pid,
                peer_host=host,
                last_hook=hook,
                last_gate=dict(hook.get("execution_gate") or {}),
            )
            return {
                "ok": True,
                "action": "hook",
                "phase": self.control.phase,
                "control": self.control.to_dict(),
                **hook,
            }, 200

        plan_rows = list(plans or self.control.last_hook.get("repair_plans") or [])
        source_rows = list(
            suggested_sources or self.control.last_hook.get("suggested_sources") or []
        )

        if act == "gate":
            confirmed = bool(user_confirmed or confirm)
            gate, status = self.repair_service.evaluate_gate(
                plans=plan_rows,
                suggested_sources=source_rows,
                user_confirmed=confirmed,
            )
            self.control.transition(
                PHASE_REPAIR_PENDING if gate.get("gate") == EXECUTION_GATE_REQUIRE_CONFIRM else PHASE_GATE_PREVIEW,
                last_gate=gate,
            )
            return {
                "ok": True,
                "action": "gate",
                "phase": self.control.phase,
                "control": self.control.to_dict(),
                **gate,
            }, status

        if act == "execute":
            if not confirm and not user_confirmed:
                gate, _ = self.repair_service.evaluate_gate(
                    plans=plan_rows,
                    suggested_sources=source_rows,
                    user_confirmed=False,
                )
                self.control.transition(PHASE_REPAIR_PENDING, last_gate=gate)
                return {
                    "ok": False,
                    "error": "confirm_required",
                    "gate": gate.get("gate"),
                    "control": self.control.to_dict(),
                }, 409
            result, status = self.repair_service.execute(
                plans=plan_rows,
                suggested_sources=source_rows,
                user_confirmed=True,
                verifier_peer_id=pid,
            )
            if status == 200 and int(result.get("repaired") or 0) > 0:
                self.control.transition(PHASE_REPAIR_COMPLETE)
            return {
                "ok": status < 400,
                "action": "execute",
                "phase": self.control.phase,
                "control": self.control.to_dict(),
                **result,
            }, status

        return {"ok": False, "error": f"unknown_repair_action:{act}"}, 400
