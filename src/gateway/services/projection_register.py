"""Write AST/vision nodes into projection store + memory blocks."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from ..state import EngineStateManager


@dataclass(frozen=True)
class ProjectionRegisterHooks:
    schedule_projection_wormhole: Callable[[List[str]], None]
    append_runtime_log: Callable[..., None]
    schedule_persist: Callable[[], None]


class ProjectionRegisterService:
    def __init__(
        self,
        state: EngineStateManager,
        hooks: ProjectionRegisterHooks,
        *,
        activation_max_score: float = 1.0,
    ):
        self._state = state
        self._hooks = hooks
        self._activation_max_score = activation_max_score

    def register(
        self,
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        cluster: str,
        source_kind: str = "code",
    ) -> List[str]:
        def _write(engine: Dict[str, Any]) -> List[str]:
            proj = engine.setdefault("projection", {"nodes": {}, "links": []})
            proj.setdefault("nodes", {})
            proj.setdefault("links", [])
            now = time.time()
            scores = engine.setdefault("activation", {}).setdefault("scores", {})
            registered_ids: List[str] = []
            parent_by_target: Dict[str, str] = {}
            for link in links:
                if link.get("type") == "defines":
                    parent_by_target[str(link["target"])] = str(link["source"])

            for node in nodes:
                nid = str(node.get("id") or "").strip()
                if not nid:
                    continue
                ntype = node.get("type") or "term"
                title = str(node.get("label") or node.get("title") or nid)[:120]
                parent_id = parent_by_target.get(nid, "")
                record = {
                    "id": nid,
                    "title": title,
                    "tag": ntype,
                    "node_type": ntype,
                    "desc": f"{source_kind}:{node.get('file', cluster)}"[:160],
                    "meta": source_kind,
                    "cluster": cluster or nid,
                    "parent_id": parent_id,
                    "file": node.get("file", ""),
                }
                proj["nodes"][nid] = record
                registered_ids.append(nid)
                scores[nid] = self._activation_max_score
                engine["memory_store"].add(
                    {
                        "label": ntype,
                        "block_id": nid,
                        "data": {
                            **node,
                            **record,
                            "content": title,
                            "cluster": cluster,
                        },
                        "importance": 0.95,
                        "timestamp": now,
                    }
                )

            seen_links = {(l.get("source"), l.get("target"), l.get("type")) for l in proj["links"]}
            for link in links:
                key = (link.get("source"), link.get("target"), link.get("type"))
                if key in seen_links:
                    continue
                seen_links.add(key)
                proj["links"].append(
                    {
                        "source": link.get("source"),
                        "target": link.get("target"),
                        "type": link.get("type", "rel"),
                        "cluster": cluster,
                    }
                )
            return registered_ids

        registered_ids = self._state.mutate(_write)
        self._state.touch_consolidation_activity()
        self._hooks.schedule_projection_wormhole(registered_ids)
        self._hooks.append_runtime_log(
            f"{'代码' if source_kind == 'code' else '视觉'}投影 · nodes={len(registered_ids)} links={len(links)}",
            category="capture",
        )
        self._hooks.schedule_persist()
        return registered_ids
