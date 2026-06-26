"""MemoryGraphService — node specs, adjacency, spreading activation, wormhole resonance."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from ...state import EngineStateManager
from ..converse_speech import decision_intent, speech_text
from .provenance import ProvenancePort
from .wormhole_embed import WormholeEmbedder

ExtractKeywordsFn = Callable[[str, int], List[str]]
NormalizeMemoryTagFn = Callable[[str], str]
AppendLogFn = Callable[..., None]
SchedulePersistFn = Callable[[], None]
BackgroundUpdateFn = Callable[[], None]


def default_normalize_memory_tag(label: str) -> str:
    raw = str(label or "episode").lower()
    if raw in ("code_class", "code_function", "vision_component"):
        return raw
    if raw in ("episodic", "episode"):
        return "episode"
    if raw in ("goal", "belief", "identity", "insight", "semantic"):
        return "belief" if raw == "semantic" else raw
    if raw == "emotion":
        return "insight"
    return "term"


@dataclass(frozen=True)
class MemoryGraphConfig:
    activation_decay: float = 0.8
    activation_threshold: float = 0.4
    spread_hop1: float = 0.5
    spread_hop2: float = 0.2
    seed_pulse: float = 1.0
    max_score: float = 1.0
    wormhole_sim_threshold: float = field(
        default_factory=lambda: float(os.environ.get("CNEXUS_WORMHOLE_SIM_THRESHOLD", "0.75"))
    )
    wormhole_energy_coeff: float = field(
        default_factory=lambda: float(os.environ.get("CNEXUS_WORMHOLE_ENERGY_COEFF", "0.40"))
    )
    wormhole_max_links: int = field(
        default_factory=lambda: int(os.environ.get("CNEXUS_WORMHOLE_MAX_LINKS", "64"))
    )
    wormhole_max_compare: int = field(
        default_factory=lambda: int(os.environ.get("CNEXUS_WORMHOLE_MAX_COMPARE", "28"))
    )
    max_items: int = 128
    recent_blocks: int = 20
    recent_trace: int = 14


@dataclass(frozen=True)
class MemoryGraphHooks:
    extract_keywords: ExtractKeywordsFn
    append_runtime_log: AppendLogFn = lambda *a, **k: None
    schedule_persist: SchedulePersistFn = lambda: None
    background_cognitive_update: BackgroundUpdateFn = lambda: None
    normalize_memory_tag: NormalizeMemoryTagFn = default_normalize_memory_tag


def node_embedding_text(spec: Dict[str, Any]) -> str:
    title = str(spec.get("title") or "").strip()
    desc = str(spec.get("desc") or "").strip()
    return f"{title} {desc}".strip()[:512]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def has_physical_link(a: str, b: str, adj: Dict[str, Set[str]]) -> bool:
    return b in adj.get(a, set()) or a in adj.get(b, set())


class MemoryGraphService:
    """Memory graph read/write — node specs, spread, wormhole — no app_v2 imports."""

    def __init__(
        self,
        state: EngineStateManager,
        hooks: MemoryGraphHooks,
        *,
        provenance: Optional[ProvenancePort] = None,
        embedder: Optional[WormholeEmbedder] = None,
        config: Optional[MemoryGraphConfig] = None,
        activation_lock: Optional[threading.Lock] = None,
    ):
        self._state = state
        self._hooks = hooks
        self._provenance = provenance
        self._embedder = embedder or WormholeEmbedder()
        self._config = config or MemoryGraphConfig()
        self._lock = activation_lock or threading.Lock()

    def collect(self) -> List[Dict[str, Any]]:
        return self._state.mutate(self._collect_from_engine)

    def build_adjacency(self, specs: List[Dict[str, Any]], engine: Dict[str, Any]) -> Dict[str, Set[str]]:
        by_cluster: Dict[str, List[str]] = {}
        for spec in specs:
            cluster = str(spec.get("cluster") or spec["id"])
            by_cluster.setdefault(cluster, []).append(spec["id"])
        adj: Dict[str, Set[str]] = {spec["id"]: set() for spec in specs}
        for spec in specs:
            nid = spec["id"]
            parent = str(spec.get("parent_id") or "").strip()
            if parent and parent in adj:
                adj[nid].add(parent)
                adj[parent].add(nid)
            cluster = str(spec.get("cluster") or "")
            for peer in by_cluster.get(cluster, ()):
                if peer != nid:
                    adj[nid].add(peer)
        id_set = set(adj.keys())
        projection = engine.get("projection") or {}
        for link in projection.get("links") or []:
            src = str(link.get("source") or "")
            tgt = str(link.get("target") or "")
            if src in id_set and tgt in id_set:
                adj[src].add(tgt)
                adj[tgt].add(src)
        return adj

    def match_seed_ids(self, text: str, specs: List[Dict[str, Any]]) -> Set[str]:
        text_l = (text or "").lower()
        seeds: Set[str] = set()
        keywords = self._hooks.extract_keywords(text, 8)
        for spec in specs:
            title = spec["title"]
            title_l = title.lower()
            if len(title) >= 2 and title_l in text_l:
                seeds.add(spec["id"])
                continue
            for kw in keywords:
                kw_l = kw.lower()
                if kw_l in title_l or title_l in kw_l:
                    seeds.add(spec["id"])
                    break
        return seeds

    def sync_activation_scores(self, specs: List[Dict[str, Any]]) -> None:
        def apply(engine: Dict[str, Any]) -> None:
            scores = engine.setdefault("activation", {}).setdefault("scores", {})
            for spec in specs:
                scores.setdefault(spec["id"], 0.0)

        self._state.mutate(apply)

    def spread_activation(
        self,
        seed_ids: Set[str],
        adj: Dict[str, Set[str]],
        scores: Dict[str, float],
    ) -> None:
        cfg = self._config
        hop1: Set[str] = set()
        for sid in seed_ids:
            for nb in adj.get(sid, ()):
                if nb not in seed_ids:
                    hop1.add(nb)
        hop2: Set[str] = set()
        for h1 in hop1:
            for nb in adj.get(h1, ()):
                if nb not in seed_ids and nb not in hop1:
                    hop2.add(nb)
        for sid in seed_ids:
            scores[sid] = min(cfg.max_score, scores.get(sid, 0.0) + cfg.seed_pulse)
        for nid in hop1:
            scores[nid] = min(cfg.max_score, scores.get(nid, 0.0) + cfg.spread_hop1)
        for nid in hop2:
            scores[nid] = min(cfg.max_score, scores.get(nid, 0.0) + cfg.spread_hop2)

    def spread_wormhole_resonance(
        self,
        seed_ids: Set[str],
        specs: List[Dict[str, Any]],
        adj: Dict[str, Set[str]],
        scores: Dict[str, float],
        *,
        engine: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        cfg = self._config
        if engine is None:
            raise ValueError("engine required for wormhole link store")
        store = engine.setdefault("activation", {}).setdefault("wormhole_links", [])

        if not seed_ids or not specs:
            store[:] = []
            return []

        embed_backend = self._embedder.backend()
        if not embed_backend:
            store[:] = []
            return []

        by_id = {spec["id"]: spec for spec in specs}
        links: List[Dict[str, Any]] = []
        seen_pairs: Set[tuple] = set()
        denom = max(1e-9, 1.0 - cfg.wormhole_sim_threshold)

        for sid in seed_ids:
            if sid not in by_id:
                continue
            source_energy = float(scores.get(sid, 0.0))
            if source_energy < 0.05:
                continue
            active_vector = self._embedder.embed(node_embedding_text(by_id[sid]), embed_backend)
            if not active_vector:
                continue

            candidates: List[tuple] = []
            for tid, spec in by_id.items():
                if tid == sid or has_physical_link(sid, tid, adj):
                    continue
                pair = tuple(sorted((sid, tid)))
                if pair in seen_pairs:
                    continue
                text = node_embedding_text(spec)
                if len(text) < 2:
                    continue
                candidates.append((tid, text, float(scores.get(tid, 0.0))))

            candidates.sort(key=lambda x: -x[2])
            compared = 0
            for tid, target_text, _ in candidates:
                if compared >= cfg.wormhole_max_compare:
                    break
                pair = tuple(sorted((sid, tid)))
                if pair in seen_pairs:
                    continue
                target_vector = self._embedder.embed(target_text, embed_backend)
                if not target_vector:
                    continue
                compared += 1
                similarity = cosine_similarity(active_vector, target_vector)
                if similarity < cfg.wormhole_sim_threshold:
                    continue
                normalized_sim = (similarity - cfg.wormhole_sim_threshold) / denom
                radiated = source_energy * normalized_sim * cfg.wormhole_energy_coeff
                scores[tid] = min(cfg.max_score, scores.get(tid, 0.0) + radiated)
                seen_pairs.add(pair)
                links.append(
                    {
                        "source": sid,
                        "target": tid,
                        "similarity": round(similarity, 4),
                        "energy": round(radiated, 4),
                    }
                )

        links.sort(key=lambda x: (-x["similarity"], -x["energy"]))
        capped = links[: cfg.wormhole_max_links]
        store[:] = capped
        return capped

    def protected_node_ids(self, specs: List[Dict[str, Any]], trace: List[Dict[str, Any]]) -> Set[str]:
        protected = {"goal-current"}
        try:
            from .protection import level_priority
        except ImportError:
            level_priority = lambda _lvl: 0  # type: ignore[assignment,misc]
        for spec in specs:
            nid = spec["id"]
            if nid.startswith("sem-rem-") or spec.get("tag") in ("code_class", "code_function", "vision_component"):
                protected.add(nid)
            if level_priority(str(spec.get("memory_level") or "long_term")) >= level_priority("project"):
                protected.add(nid)
        for entry in trace[-5:]:
            trace_id = entry.get("trace_id") or f"v2-trace-{entry.get('iteration', 0)}"
            protected.add(trace_id)
            protected.add(f"{trace_id}-intent")
        return protected

    def rem_graph_snapshot(self) -> Dict[str, Any]:
        def read(engine: Dict[str, Any]) -> Dict[str, Any]:
            specs = self._collect_from_engine(engine)
            return {
                "specs": specs,
                "scores": dict(engine.setdefault("activation", {}).setdefault("scores", {})),
                "adjacency": self.build_adjacency(specs, engine),
                "protected_ids": list(self.protected_node_ids(specs, engine.get("trace", []))),
            }

        return self._state.mutate(read)

    def prune_stale_activation_scores(self) -> None:
        def apply(engine: Dict[str, Any]) -> None:
            specs = self._collect_from_engine(engine)
            live_ids = {spec["id"] for spec in specs}
            scores = engine.setdefault("activation", {}).setdefault("scores", {})
            for nid in list(scores.keys()):
                if nid not in live_ids:
                    scores.pop(nid, None)

        self._state.mutate(apply)

    def post_turn(self, user_text: str, reply: str, trace_id: str) -> None:
        cfg = self._config
        with self._lock:

            def apply(engine: Dict[str, Any]) -> Dict[str, Any]:
                scores = engine.setdefault("activation", {}).setdefault("scores", {})
                specs = self._collect_from_engine(engine)
                for spec in specs:
                    scores.setdefault(spec["id"], 0.0)
                for nid in list(scores.keys()):
                    scores[nid] = float(scores[nid]) * cfg.activation_decay
                adj = self.build_adjacency(specs, engine)
                seeds = self.match_seed_ids(user_text, specs) | self.match_seed_ids(reply, specs)
                if trace_id:
                    for spec in specs:
                        if spec.get("cluster") == trace_id or spec["id"] == trace_id or spec["id"].startswith(trace_id):
                            seeds.add(spec["id"])
                if not seeds and specs:
                    for spec in reversed(specs):
                        if spec.get("tag") == "episode":
                            seeds.add(spec["id"])
                            break
                self.spread_activation(seeds, adj, scores)
                wormholes = self.spread_wormhole_resonance(seeds, specs, adj, scores, engine=engine)
                active_n = sum(1 for v in scores.values() if float(v) > cfg.activation_threshold)
                return {"seeds": len(seeds), "active_n": active_n, "wormholes": len(wormholes)}

            stats = self._state.mutate(apply)

        self._hooks.append_runtime_log(
            (
                f"潜意识扩散 · seeds={stats['seeds']} active>{cfg.activation_threshold}={stats['active_n']} "
                f"wormholes={stats['wormholes']}"
            ),
            category="cognition",
            trace_id=trace_id,
        )
        self._hooks.schedule_persist()

    def schedule_post_turn(self, user_text: str, reply: str, trace_id: str) -> None:
        threading.Thread(
            target=self.post_turn,
            args=(user_text, reply, trace_id),
            daemon=True,
            name="cnexus-activation-spread",
        ).start()
        self._hooks.background_cognitive_update()

    def seed_projection_wormhole(self, node_ids: List[str]) -> None:
        if not node_ids:
            return
        cfg = self._config
        with self._lock:

            def apply(engine: Dict[str, Any]) -> None:
                specs = self._collect_from_engine(engine)
                scores = engine.setdefault("activation", {}).setdefault("scores", {})
                for spec in specs:
                    scores.setdefault(spec["id"], 0.0)
                for nid in node_ids:
                    scores[nid] = cfg.max_score
                adj = self.build_adjacency(specs, engine)
                self.spread_wormhole_resonance(set(node_ids), specs, adj, scores, engine=engine)

            self._state.mutate(apply)
        self._hooks.schedule_persist()

    def schedule_projection_wormhole(self, node_ids: List[str]) -> None:
        if not node_ids:
            return
        threading.Thread(
            target=self.seed_projection_wormhole,
            args=(list(node_ids),),
            daemon=True,
            name="cnexus-projection-wormhole",
        ).start()

    def _collect_from_engine(self, engine: Dict[str, Any]) -> List[Dict[str, Any]]:
        hooks = self._hooks
        cfg = self._config
        items: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        normalize = hooks.normalize_memory_tag

        def push(
            item_id,
            title,
            tag,
            desc="",
            meta="recent",
            cluster=None,
            parent_id=None,
            node_type=None,
            *,
            provenance=None,
            source_peer="",
            memory_level="long_term",
            memory_version: int | None = None,
            project_id: str = "",
            lifecycle_id: str = "",
        ):
            title_s = str(title or "").strip()[:120]
            tag_norm = normalize(tag)
            dedupe_key = (
                item_id
                if tag_norm in ("code_class", "code_function", "vision_component", "term")
                else title_s
            )
            if not title_s or dedupe_key in seen:
                return
            seen.add(dedupe_key)
            cluster_key = str(cluster or parent_id or meta or item_id)
            item = {
                "id": item_id,
                "title": title_s,
                "tag": tag_norm,
                "desc": str(desc or "")[:160],
                "meta": meta,
                "cluster": cluster_key,
                "parent_id": str(parent_id or ""),
            }
            if provenance:
                item["provenance"] = provenance
            if source_peer:
                item["source_peer"] = source_peer
            if memory_level:
                item["memory_level"] = memory_level
            if memory_version is not None:
                item["memory_version"] = memory_version
            if project_id:
                item["project_id"] = project_id
            if lifecycle_id:
                item["lifecycle_id"] = lifecycle_id
            if node_type:
                item["node_type"] = node_type
            items.append(item)

        st = engine["state"]
        goal = (st.goal or {}).get("current", "探索")
        push(
            "goal-current",
            goal,
            "goal",
            f"progress={(st.goal or {}).get('progress', 0):.0%}",
            "L0",
            cluster="core",
            parent_id=None,
        )

        memory_store = engine["memory_store"]
        blocks = memory_store.blocks
        recent_slice = blocks[-cfg.recent_blocks :]
        prov_mod = self._provenance

        try:
            from .protection import block_memory_level, level_priority
            from .project import block_visible_for_active_project, normalize_active_project
        except ImportError:
            block_memory_level = lambda _block: "long_term"  # type: ignore[assignment,misc]
            level_priority = lambda _lvl: 0  # type: ignore[assignment,misc]
            normalize_active_project = lambda _raw=None: {}  # type: ignore[assignment,misc]
            block_visible_for_active_project = lambda _block, _active=None: True  # type: ignore[assignment,misc]

        active_project = normalize_active_project(engine.get("active_project"))

        for block in blocks:
            if not block_visible_for_active_project(block, active_project):
                continue
            data = block.get("data") or {}
            block_id = block.get("block_id", f"mem-{len(items)}")
            label = str(block.get("label", "episodic"))
            memory_level = block_memory_level(block)
            is_semantic = label == "semantic" or str(block_id).startswith("sem-rem-")
            is_projection = label in ("code_class", "code_function", "vision_component") or str(block_id).startswith(
                ("class:", "func:", "vision:")
            )
            is_protected = level_priority(memory_level) >= level_priority("project")
            if not is_semantic and not is_projection and not is_protected and block not in recent_slice:
                continue
            if is_semantic:
                title = (data.get("content") or data.get("label") or "REM fact")[:120]
            else:
                title = data.get("filename") or data.get("label") or block.get("label", "memory")
            if is_projection:
                title = (data.get("label") or title)[:120]
            content = str(data.get("content") or data.get("response_text") or "")
            tag = label if is_projection else ("semantic" if is_semantic else label)
            meta = "long-term" if is_semantic else ("projection" if is_projection else "upload")
            if is_protected:
                meta = "foundation" if level_priority(memory_level) >= level_priority("foundation") else (
                    "project" if memory_level == "project" else "core"
                )
            cluster = data.get("cluster") or ("long-term" if is_semantic else block_id)
            parent_id = data.get("parent_id") or ("" if not is_projection else data.get("parent_id", ""))
            provenance = prov_mod.from_block(block) if prov_mod else "local-full"
            desc = content[:160]
            if prov_mod and prov_mod.is_preview(provenance):
                desc = f"{prov_mod.preview_tag(provenance)}{content[:120]}"
            push(
                block_id,
                title,
                tag,
                desc,
                meta,
                cluster=cluster,
                parent_id=parent_id,
                node_type=tag if is_projection else None,
                provenance=provenance,
                source_peer=str(data.get("source_peer") or ""),
                memory_level=memory_level,
                memory_version=int(data.get("memory_version") or 1) if is_protected and level_priority(memory_level) >= level_priority("foundation") else None,
                project_id=str(data.get("project_id") or ""),
                lifecycle_id=str(data.get("lifecycle_id") or ""),
            )
            for kw in data.get("keywords") or hooks.extract_keywords(content, 5):
                push(
                    f"kw-{block_id}-{kw}",
                    kw,
                    "term",
                    content[:80],
                    "keyword",
                    cluster=cluster,
                    parent_id=block_id,
                    memory_level=memory_level,
                )

        for entry in engine.get("trace", [])[-cfg.recent_trace :]:
            inp = str(entry.get("input") or "").strip()
            if not inp:
                continue
            trace_id = entry.get("trace_id", f"v2-trace-{entry.get('iteration', 0)}")
            speech = entry.get("speech") or {}
            reply = speech_text(speech)
            push(trace_id, inp[:100], "episode", f"trace {trace_id}", "dialogue", cluster=trace_id, parent_id=None)
            intent = decision_intent(entry.get("decision"))
            push(
                f"{trace_id}-intent",
                f"意图 · {intent}",
                "insight",
                inp[:80],
                trace_id,
                cluster=trace_id,
                parent_id=trace_id,
            )
            for kw in hooks.extract_keywords(inp, 4):
                push(
                    f"{trace_id}-kw-{kw}",
                    kw,
                    "term",
                    inp[:80],
                    "concept",
                    cluster=trace_id,
                    parent_id=trace_id,
                )
            if reply:
                for kw in hooks.extract_keywords(reply, 5):
                    push(
                        f"{trace_id}-rk-{kw}",
                        kw,
                        "insight",
                        reply[:80],
                        "reply_concept",
                        cluster=trace_id,
                        parent_id=trace_id,
                    )

        projection = engine.setdefault("projection", {"nodes": {}, "links": []})
        for node in projection.get("nodes", {}).values():
            push(
                node["id"],
                node.get("title") or node["id"],
                node.get("tag") or node.get("node_type") or "term",
                node.get("desc", ""),
                node.get("meta", "projection"),
                cluster=node.get("cluster"),
                parent_id=node.get("parent_id"),
                node_type=node.get("node_type") or node.get("tag"),
            )

        return items[: cfg.max_items]
