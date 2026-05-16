from __future__ import annotations

import json
import re
from typing import Any


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "none",
    "of",
    "on",
    "or",
    "result",
    "the",
    "to",
    "tool",
    "use",
    "with",
}


def normalize_tool_name(name: Any) -> str:
    text = str(name or "").strip()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return re.sub(r"[^a-z0-9_]", "", text.lower())


def hop_tool_name(hop: dict[str, Any]) -> str:
    question = hop.get("question_raw") or hop.get("question") or ""
    return question.split("(", 1)[0].strip()


def hop_args_text(hop: dict[str, Any]) -> str:
    question = hop.get("question_raw") or hop.get("question") or ""
    match = re.search(r"\((.*)\)\s*$", question)
    return match.group(1).strip() if match else ""


def hop_args_obj(hop: dict[str, Any]) -> Any:
    args = hop_args_text(hop)
    if not args:
        return {}
    try:
        return json.loads(args)
    except json.JSONDecodeError:
        return args


def _tokens(text: Any) -> set[str]:
    raw = str(text or "").lower()
    pieces = set(re.findall(r"[a-z0-9_.$@/-]+", raw))
    quoted = set(re.findall(r"['\"]([^'\"]+)['\"]", raw))
    tokens = {
        token.strip().lower()
        for token in pieces | quoted
        if len(token.strip()) > 1 and token.strip().lower() not in STOPWORDS
    }
    return tokens


def _contains_tool(raw_action: str, tool_name: str) -> bool:
    tool = re.escape(tool_name)
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9_]){tool}(?![A-Za-z0-9_])",
            raw_action,
            flags=re.IGNORECASE,
        )
    )


def _candidate_payload(
    hop: dict[str, Any],
    score: int,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "hop_id": hop.get("id"),
        "function_name": hop_tool_name(hop),
        "gold_call": hop.get("question_raw") or hop.get("question"),
        "arguments": hop_args_obj(hop),
        "argument_text": hop_args_text(hop),
        "turn": hop.get("turn"),
        "score": score,
        "candidate_reason": reasons,
    }


def candidate_rows_for_units(
    question_id: str,
    mode: str,
    units: list[dict[str, Any]],
    graph: dict[str, Any] | None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    if not graph:
        return [
            {
                "question_id": question_id,
                "mode": mode,
                "unit_id": unit.get("unit_id"),
                "unit": unit,
                "candidate_hops": [],
            }
            for unit in units
        ]

    hops = graph.get("hops", [])
    rows: list[dict[str, Any]] = []
    for unit in units:
        raw_action = unit.get("raw_action") or unit.get("action_hint") or ""
        unit_tool = normalize_tool_name(unit.get("tool_name"))
        known_tokens = _tokens(unit.get("known_inputs")) | _tokens(unit.get("intent"))
        scored: list[tuple[int, int, dict[str, Any], list[str]]] = []
        for order, hop in enumerate(hops):
            hop_tool = normalize_tool_name(hop_tool_name(hop))
            hop_tokens = _tokens(hop_args_text(hop)) | _tokens(hop.get("question_raw") or hop.get("question"))
            reasons: list[str] = []
            score = 0
            same_tool = bool(unit_tool and hop_tool and unit_tool == hop_tool)
            if same_tool:
                score += 100
                reasons.append(f"tool_name:{unit.get('tool_name')}")
            elif hop_tool and _contains_tool(raw_action, hop_tool_name(hop)):
                score += 90
                reasons.append(f"function_mention:{hop_tool_name(hop)}")

            overlap = sorted(known_tokens & hop_tokens)
            if overlap:
                score += min(50, 10 * len(overlap))
                reasons.append("known_input_overlap:" + ",".join(overlap[:8]))

            if not reasons:
                reasons.append("all_hops:no_anchor")
            scored.append((score, order, hop, reasons))

        # Judge every gold hop for each generated unit. The score only controls
        # prompt ordering and diagnostics; it no longer filters candidates.
        selected = sorted(scored, key=lambda item: (item[0], -item[1]), reverse=True)

        rows.append(
            {
                "question_id": question_id,
                "mode": mode,
                "unit_id": unit.get("unit_id"),
                "unit": unit,
                "candidate_hops": [
                    _candidate_payload(hop, score, reasons)
                    for score, _order, hop, reasons in selected
                ],
            }
        )
    return rows
