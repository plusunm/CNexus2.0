"""CNexus v1.5 — Event Ontology + Timeline Builder + State Transition Engine."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

EVENT_ONTOLOGY_VERSION = "1.0"
TIMELINE_SCHEMA_VERSION = "1.0"

SILENCE_THRESHOLD_SEC = 86400
IGNORE_THRESHOLD_SEC = 7200
DAY_SEC = 86400
SEGMENT_MAX_SEC = 7 * DAY_SEC

COLD_KEYWORDS = re.compile(r"嗯|哦|好|行|忙|稍后|再说")

OPTION_TEXT = {
    "A": "等待观察 — 暂不行动，收集更多互动信号后再判断",
    "B": "主动沟通验证 — 用低压力方式确认对方状态与意图",
    "C": "降低投入 — 减少情绪消耗，保留边界与自我价值",
    "D": "明确决策 — 在信息足够时做出继续或结束的清晰选择",
}


def _parse_timestamp(raw: Any) -> int:
    if isinstance(raw, (int, float)):
        v = int(raw)
        return v // 1000 if v > 1_000_000_000_000 else v
    text = str(raw or "").strip().replace(" ", "T")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return int(datetime.now(timezone.utc).timestamp())


def _infer_entities(turns: List[Dict[str, Any]]) -> Tuple[str, str]:
    speakers = []
    seen = set()
    for row in turns:
        sp = str(row.get("speaker") or "").strip()
        if sp and sp not in seen:
            seen.add(sp)
            speakers.append(sp)
    if len(speakers) >= 2:
        return speakers[0], speakers[1]
    if len(speakers) == 1:
        return speakers[0], "B" if speakers[0] == "A" else "A"
    return "A", "B"


def _emotion_direction(text: str, prev_len: int) -> Optional[str]:
    t = text.strip()
    if len(t) <= 3 and COLD_KEYWORDS.search(t):
        return "cold"
    if prev_len > 0 and len(t) < prev_len * 0.4 and len(t) < 8:
        return "cold"
    if len(t) > 20:
        return "warm"
    return None


def extract_events_from_conversation(
    conversation: List[Dict[str, Any]],
    entities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    sorted_turns = []
    for row in conversation:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        sorted_turns.append({
            "speaker": str(row.get("speaker") or "").strip(),
            "text": text,
            "ts": _parse_timestamp(row.get("timestamp")),
        })
    sorted_turns.sort(key=lambda r: r["ts"])

    if entities and len(entities) >= 2:
        entity_a, entity_b = entities[0], entities[1]
    else:
        entity_a, entity_b = _infer_entities(conversation)

    events: List[Dict[str, Any]] = []
    last_speaker: Optional[str] = None
    last_ts = 0
    last_text_len = 0
    last_initiative: Dict[str, int] = {}

    for turn in sorted_turns:
        target = entity_b if turn["speaker"] == entity_a else entity_a
        ts = turn["ts"]

        if last_ts > 0:
            gap = ts - last_ts
            if gap >= SILENCE_THRESHOLD_SEC:
                events.append({
                    "type": "silence",
                    "duration": gap,
                    "timestamp": last_ts + gap // 2,
                })

        if last_speaker != turn["speaker"]:
            prev = last_initiative.get(turn["speaker"])
            if not prev or ts - prev > 3600:
                events.append({"type": "initiative", "actor": turn["speaker"], "timestamp": ts})
                last_initiative[turn["speaker"]] = ts

        if last_speaker and last_speaker != turn["speaker"] and last_ts > 0:
            delay = ts - last_ts
            events.append({
                "type": "reply_delay",
                "actor": turn["speaker"],
                "target": last_speaker,
                "value": delay,
                "timestamp": ts,
            })
            if delay >= IGNORE_THRESHOLD_SEC:
                events.append({
                    "type": "ignore",
                    "actor": turn["speaker"],
                    "target": last_speaker,
                    "value": delay,
                    "timestamp": ts,
                })

        shift = _emotion_direction(turn["text"], last_text_len)
        if shift:
            events.append({
                "type": "emotion_shift",
                "actor": turn["speaker"],
                "direction": shift,
                "timestamp": ts,
            })

        events.append({
            "type": "message",
            "actor": turn["speaker"],
            "target": target,
            "text": turn["text"],
            "timestamp": ts,
        })

        last_speaker = turn["speaker"]
        last_ts = ts
        last_text_len = len(turn["text"])

    delays = [e["value"] for e in events if e.get("type") == "reply_delay"]
    if len(sorted_turns) >= 2 and delays:
        avg = sum(delays) / len(delays)
        delta = -0.2 if avg > 3600 else (0.1 if avg < 600 else 0)
        if delta:
            events.append({"type": "intensity", "delta": delta, "timestamp": sorted_turns[-1]["ts"]})

    events.sort(key=lambda e: e["timestamp"])
    return {"version": EVENT_ONTOLOGY_VERSION, "entities": [entity_a, entity_b], "events": events}


def _empty_metrics() -> Dict[str, Any]:
    return {
        "replyLatencyAvg": 0,
        "initiativeRatio": 0,
        "silenceRatio": 0,
        "messageCount": 0,
        "ignoreCount": 0,
        "emotionColdCount": 0,
    }


def _compute_metrics(events: List[Dict[str, Any]], start: int, end: int) -> Dict[str, Any]:
    slice_ev = [e for e in events if start <= e.get("timestamp", 0) <= end]
    m = _empty_metrics()
    delays: List[float] = []
    initiative = 0
    silence_dur = 0

    for e in slice_ev:
        t = e.get("type")
        if t == "message":
            m["messageCount"] += 1
        elif t == "reply_delay":
            delays.append(float(e.get("value") or 0))
        elif t == "initiative":
            initiative += 1
        elif t == "silence":
            silence_dur += int(e.get("duration") or 0)
        elif t == "ignore":
            m["ignoreCount"] += 1
        elif t == "emotion_shift" and e.get("direction") == "cold":
            m["emotionColdCount"] += 1

    m["replyLatencyAvg"] = sum(delays) / len(delays) if delays else 0
    m["initiativeRatio"] = initiative / m["messageCount"] if m["messageCount"] else 0
    span = max(end - start, 1)
    m["silenceRatio"] = silence_dur / span
    return m


def _initial_state(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "neutral"
    warmish = any(e.get("type") == "message" and len(str(e.get("text") or "")) > 15 for e in events)
    return "warm" if warmish else "neutral"


def _is_cooling(m: Dict[str, Any]) -> bool:
    return m["replyLatencyAvg"] > 1800 and m["initiativeRatio"] < 0.45


def _is_cold(m: Dict[str, Any]) -> bool:
    return m["silenceRatio"] > 0.25 or (m["initiativeRatio"] < 0.3 and m["replyLatencyAvg"] > 3600)


def _is_breaking(m: Dict[str, Any], seg_events: List[Dict[str, Any]]) -> bool:
    long_silence = any(e.get("type") == "silence" and int(e.get("duration") or 0) >= 2 * DAY_SEC for e in seg_events)
    return m["ignoreCount"] >= 2 or (m["emotionColdCount"] >= 2 and m["initiativeRatio"] < 0.2) or long_silence


def _is_dead(m: Dict[str, Any], seg_events: List[Dict[str, Any]]) -> bool:
    week = any(e.get("type") == "silence" and int(e.get("duration") or 0) >= 7 * DAY_SEC for e in seg_events)
    return week or (m["messageCount"] == 0 and m["silenceRatio"] > 0.5)


def transition_state(state: str, metrics: Dict[str, Any], seg_events: List[Dict[str, Any]]) -> str:
    if state == "warm" and _is_cooling(metrics):
        return "neutral"
    if state == "neutral" and _is_cold(metrics):
        return "cold"
    if state == "cold" and _is_breaking(metrics, seg_events):
        return "breaking"
    if state == "breaking" and _is_dead(metrics, seg_events):
        return "broken"
    if state == "warm" and _is_cold(metrics):
        return "cold"
    if state == "neutral" and _is_breaking(metrics, seg_events):
        return "breaking"
    if state == "cold" and _is_dead(metrics, seg_events):
        return "broken"
    return state


def dynamics_to_canonical_stage(state: str) -> str:
    return {
        "warm": "stable",
        "neutral": "uncertain",
        "cold": "cold",
        "breaking": "cold",
        "broken": "broken",
    }.get(state, "uncertain")


def metrics_to_level_bands(metrics: Dict[str, Any]) -> Dict[str, str]:
    ir = metrics["initiativeRatio"]
    mc = metrics["messageCount"]
    ec = metrics["emotionColdCount"]
    return {
        "emotionConnection": "low" if ec >= 2 else ("high" if ec == 0 and mc >= 5 else "medium"),
        "initiativeLevel": "high" if ir >= 0.5 else ("medium" if ir >= 0.25 else "low"),
        "interactionFrequency": "high" if mc >= 10 else ("medium" if mc >= 3 else "low"),
    }


def _segment_boundaries(events: List[Dict[str, Any]]) -> List[int]:
    if not events:
        return []
    timestamps = [e["timestamp"] for e in events]
    min_ts, max_ts = timestamps[0], timestamps[-1]
    bounds = [min_ts]
    for e in events:
        if e.get("type") == "silence" and int(e.get("duration") or 0) >= DAY_SEC:
            mid = e["timestamp"]
            if mid > bounds[-1] + 3600:
                bounds.append(mid)
    cursor = bounds[-1]
    while cursor + SEGMENT_MAX_SEC < max_ts:
        cursor += SEGMENT_MAX_SEC
        bounds.append(cursor)
    bounds.append(max_ts)
    return sorted(set(bounds))


def build_timeline(stream: Dict[str, Any]) -> Dict[str, Any]:
    entities = stream.get("entities") or []
    events = sorted(stream.get("events") or [], key=lambda e: e.get("timestamp", 0))

    if not events:
        return {
            "version": TIMELINE_SCHEMA_VERSION,
            "entities": entities,
            "events": [],
            "segments": [],
            "currentState": "neutral",
            "stateHistory": [],
        }

    bounds = _segment_boundaries(events)
    segments: List[Dict[str, Any]] = []
    state = _initial_state(events)
    history: List[Dict[str, Any]] = []

    for i in range(len(bounds) - 1):
        start, end = bounds[i], bounds[i + 1]
        seg_events = [e for e in events if start <= e.get("timestamp", 0) <= end]
        metrics = _compute_metrics(events, start, end)
        prev = state
        state = transition_state(state, metrics, seg_events)
        if state != prev:
            history.append({"segmentIndex": i, "from": prev, "to": state})
        segments.append({"start": start, "end": end, "stateSnapshot": state, "metrics": metrics})

    return {
        "version": TIMELINE_SCHEMA_VERSION,
        "entities": entities,
        "events": events,
        "segments": segments,
        "currentState": state,
        "stateHistory": history,
    }


def _signals_from_timeline(timeline: Dict[str, Any]) -> Dict[str, List[str]]:
    segments = timeline.get("segments") or []
    if not segments:
        return {"positive": [], "negative": []}
    m = segments[-1]["metrics"]
    positive, negative = [], []
    if m["initiativeRatio"] >= 0.4:
        positive.append("段内仍保持一定主动性")
    if m["replyLatencyAvg"] < 1800 and m["messageCount"] >= 3:
        positive.append("回复延迟处于可接受范围")
    if m["silenceRatio"] > 0.3:
        negative.append("沉默窗口占比偏高")
    if m["replyLatencyAvg"] > 3600:
        negative.append("平均回复延迟显著增加")
    if m["ignoreCount"] > 0:
        negative.append("存在未回应/长延迟互动")
    if m["emotionColdCount"] > 0:
        negative.append("语气趋冷信号出现")
    if not positive:
        positive.append("时间轴已结构化，可继续观察")
    return {"positive": positive, "negative": negative}


def _decision_from_state(state: str) -> Dict[str, str]:
    mapping = {
        "warm": ("A", "互动稳定，优先观察并收集更多信号"),
        "neutral": ("B", "局面不确定，优先低压力沟通验证"),
        "cold": ("B", "降温信号出现，宜验证而非猜测"),
        "breaking": ("C", "崩解信号累积，宜降低投入并设边界"),
        "broken": ("D", "长期低互动/无修复，宜做明确决策"),
    }
    rec, reason = mapping.get(state, ("B", "优先验证"))
    return {"recommended": rec, "reason": reason}


def timeline_to_analysis(
    timeline: Dict[str, Any],
    *,
    analysis_id: str,
    source_input: str,
) -> Dict[str, Any]:
    segments = timeline.get("segments") or []
    last_metrics = segments[-1]["metrics"] if segments else _empty_metrics()
    bands = metrics_to_level_bands(last_metrics)
    current = timeline.get("currentState") or "neutral"
    sig = _signals_from_timeline(timeline)
    dec = _decision_from_state(current)
    rec = dec["recommended"]

    return {
        "meta": {
            "id": analysis_id,
            "sourceInput": source_input,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "schemaVersion": "1.0",
        },
        "state": {
            **bands,
            "relationshipStage": dynamics_to_canonical_stage(current),
        },
        "signals": sig,
        "uncertainty": {
            "missingInfo": ["时间轴段数较少，趋势判断有限"] if len(segments) < 2 else [],
            "risk": (
                "关系动力学显示衰退趋势，宜避免情绪驱动决策"
                if current in ("breaking", "broken")
                else "基于行为时间轴推断，仍需结合线下事实验证"
            ),
        },
        "decision": {
            "options": dict(OPTION_TEXT),
            "recommended": rec,
            "reason": dec["reason"],
        },
        "actions": [
            f"优先执行：{OPTION_TEXT[rec].split(' — ')[0]}",
            "对照时间轴分段指标，记录后续 1–2 个窗口变化",
            "若沉默/ignore 信号持续，避免做不可逆决定",
        ],
    }


def run_cognitive_pipeline(
    conversation: List[Dict[str, Any]],
    *,
    entities: Optional[List[str]] = None,
    analysis_id: Optional[str] = None,
    source_input: Optional[str] = None,
) -> Dict[str, Any]:
    event_stream = extract_events_from_conversation(conversation, entities)
    timeline = build_timeline(event_stream)

    if not source_input:
        last = conversation[-1] if conversation else {}
        text = str(last.get("text") or "关系聊天记录分析")
        source_input = f"聊天记录分析：{text[:40]}{'…' if len(text) > 40 else ''}"

    analysis = timeline_to_analysis(
        timeline,
        analysis_id=analysis_id or f"tl-{int(datetime.now(timezone.utc).timestamp())}",
        source_input=source_input,
    )

    return {
        "eventStream": event_stream,
        "timeline": timeline,
        "analysis": analysis,
        "relationshipState": timeline.get("currentState"),
        "sourceInput": source_input,
    }
