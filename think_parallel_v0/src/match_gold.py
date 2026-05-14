from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any


LABEL_PRIORITY = {"Strong": 4, "Weak-D": 3, "Weak-A": 2, "Independent": 1}


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
    return match.group(1) if match else ""


def function_tool_names(functions: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    for function in functions or []:
        name = function.get("name")
        if not name and isinstance(function.get("function"), dict):
            name = function["function"].get("name")
        if name:
            names.append(str(name))
    return names


def _tool_match_candidates(name: str) -> set[str]:
    candidates = {name}
    if "." in name:
        candidates.add(name.rsplit(".", 1)[-1])
    normalized = normalize_tool_name(name)
    if normalized:
        candidates.add(normalized)
    return {candidate for candidate in candidates if candidate}


def extract_tool_mentions(text: Any, tool_names: list[str]) -> list[str]:
    action_text = str(text or "")
    if not action_text.strip():
        return []

    normalized_to_name: dict[str, str] = {}
    matches: list[tuple[int, str]] = []
    for tool_name in tool_names:
        normalized = normalize_tool_name(tool_name)
        if not normalized:
            continue
        normalized_to_name.setdefault(normalized, tool_name.rsplit(".", 1)[-1])
        for candidate in _tool_match_candidates(tool_name):
            pattern = re.compile(
                rf"(?<![A-Za-z0-9_]){re.escape(candidate)}(?![A-Za-z0-9_])",
                re.IGNORECASE,
            )
            for match in pattern.finditer(action_text):
                matches.append((match.start(), normalized))

    ordered: list[str] = []
    seen: set[str] = set()
    for _, normalized in sorted(matches, key=lambda item: item[0]):
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized_to_name[normalized])
    return ordered


def edge_labels_by_dst(edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    labels: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        dst = edge.get("dst")
        if dst:
            labels[dst].append(edge.get("tier2") or edge.get("tier1") or "Strong")
    return labels


def summarize_labels(labels: list[str]) -> str:
    if not labels:
        return "Independent"
    return max(labels, key=lambda label: LABEL_PRIORITY.get(label, 0))


def _args_overlap(unit_args: Any, args_text: str) -> int:
    if not unit_args:
        return 0
    try:
        unit_text = json.dumps(unit_args, ensure_ascii=False).lower()
    except TypeError:
        unit_text = str(unit_args).lower()
    tokens = {
        token
        for token in re.findall(r"[a-zA-Z0-9_]+", unit_text)
        if len(token) > 1
    }
    gold = args_text.lower()
    return sum(1 for token in tokens if token in gold)


def match_units_to_gold(
    units: list[dict[str, Any]],
    graph: dict[str, Any] | None,
    edges: list[dict[str, Any]],
    available_tools: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not graph:
        return [
            {
                **unit,
                "mentioned_tools": extract_tool_mentions(
                    unit.get("raw_action") or unit.get("action_hint"), available_tools or []
                ),
                "matched_hop_ids": [],
                "matched_tools": [],
                "matched_hop_id": None,
                "matched_tool": None,
                "gold_questions": [],
                "gold_edge_labels": [],
                "gold_edge_label_summary": None,
                "gold_edge_label_summaries": [],
                "match_score": 0,
                "compound_action": False,
                "n_tool_mentions": 0,
            }
            for unit in units
        ]

    hops = graph.get("hops", [])
    gold_tool_names = [hop_tool_name(hop) for hop in hops]
    gold_norm_tools = {normalize_tool_name(name) for name in gold_tool_names}
    mention_tool_names = list(dict.fromkeys((available_tools or []) + gold_tool_names))
    labels_by_dst = edge_labels_by_dst(edges)
    used: set[str] = set()
    matched: list[dict[str, Any]] = []

    for unit in units:
        action_text = unit.get("raw_action") or unit.get("action_hint") or ""
        mentioned_tools = extract_tool_mentions(action_text, mention_tool_names)
        mentioned_gold_tools = {
            normalize_tool_name(tool)
            for tool in mentioned_tools
            if normalize_tool_name(tool) in gold_norm_tools
        }
        matched_hops: list[dict[str, Any]] = []
        scores: list[int] = []
        for mentioned_tool in mentioned_tools:
            normalized_mention = normalize_tool_name(mentioned_tool)
            for hop in hops:
                hop_id = hop.get("id")
                if hop_id in used:
                    continue
                if normalize_tool_name(hop_tool_name(hop)) != normalized_mention:
                    continue
                matched_hops.append(hop)
                used.add(hop_id)
                scores.append(100)
                break

        unit_tool = normalize_tool_name(action_text)
        best: tuple[int, dict[str, Any] | None] = (0, None)
        if not matched_hops:
            for hop in hops:
                hop_id = hop.get("id")
                if hop_id in used:
                    continue
                hop_tool = normalize_tool_name(hop_tool_name(hop))
                score = 0
                if unit_tool and hop_tool and unit_tool == hop_tool:
                    score += 100
                elif unit_tool and hop_tool and (unit_tool in hop_tool or hop_tool in unit_tool):
                    score += 60
                score += min(20, _args_overlap(unit.get("arguments_hint"), hop_args_text(hop)))
                if score > best[0]:
                    best = (score, hop)

            score, hop = best
            if hop is not None and score >= 60:
                matched_hops.append(hop)
                used.add(hop["id"])
                scores.append(score)

        if not matched_hops:
            matched.append(
                {
                    **unit,
                    "mentioned_tools": mentioned_tools,
                    "matched_hop_ids": [],
                    "matched_tools": [],
                    "matched_hop_id": None,
                    "matched_tool": None,
                    "gold_questions": [],
                    "gold_edge_labels": [],
                    "gold_edge_label_summary": None,
                    "gold_edge_label_summaries": [],
                    "match_score": best[0],
                    "match_scores": [],
                    "compound_action": len(mentioned_tools) > 1 or len(mentioned_gold_tools) > 1,
                    "n_tool_mentions": len(mentioned_tools),
                    "n_matched_hops": 0,
                }
            )
            continue

        primary_hop = matched_hops[0]
        primary_hop_id = primary_hop["id"]
        primary_labels = labels_by_dst.get(primary_hop_id, [])
        matched_hop_ids = [hop["id"] for hop in matched_hops]
        matched_tools = [hop_tool_name(hop) for hop in matched_hops]
        gold_questions = [
            hop.get("question_raw") or hop.get("question")
            for hop in matched_hops
        ]
        label_summaries = [
            summarize_labels(labels_by_dst.get(hop["id"], []))
            for hop in matched_hops
        ]
        matched.append(
            {
                **unit,
                "mentioned_tools": mentioned_tools,
                "matched_hop_ids": matched_hop_ids,
                "matched_tools": matched_tools,
                "matched_hop_id": primary_hop_id,
                "matched_tool": hop_tool_name(primary_hop),
                "gold_question": primary_hop.get("question_raw") or primary_hop.get("question"),
                "gold_questions": gold_questions,
                "gold_edge_labels": primary_labels,
                "gold_edge_label_summary": summarize_labels(primary_labels),
                "gold_edge_label_summaries": label_summaries,
                "match_score": max(scores) if scores else 0,
                "match_scores": scores,
                "compound_action": len(mentioned_tools) > 1 or len(matched_hops) > 1,
                "n_tool_mentions": len(mentioned_tools),
                "n_matched_hops": len(matched_hops),
            }
        )
    return matched
