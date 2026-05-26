from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

    from src.bfcl_data import load_graphs
else:
    from .bfcl_data import load_graphs


DEFAULT_GRAPHS_PATH = (
    "/home/ilju/research/ParallelAgent/data/annotations/"
    "bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl"
)

GOLD_TOOL_PATTERN = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
CALL_ARGS_PATTERN = re.compile(r"\s*[A-Za-z_][A-Za-z0-9_]*\s*\((.*)\)\s*$")
REF_PATTERN = re.compile(r"\$\{?\d+\}?(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]+\])?)*")
PLACEHOLDER_PATTERN = re.compile(r"<[^>\n]+>")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.$@/-]+")
QUOTED_PATTERN = re.compile(r"['\"]([^'\"]+)['\"]")

STOPWORDS = {
    "a",
    "an",
    "and",
    "arg",
    "args",
    "by",
    "current",
    "false",
    "for",
    "from",
    "in",
    "is",
    "none",
    "null",
    "of",
    "on",
    "or",
    "result",
    "the",
    "to",
    "true",
    "with",
}

STRENGTH_PRIORITY = {"wrong": 0, "partial": 1, "semantic": 2, "exact": 3}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_config" not in obj:
                rows.append(obj)
    return rows


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


def normalize_tool_name(name: Any) -> str:
    text = str(name or "").strip()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return re.sub(r"[^a-z0-9_]", "", text.lower())


def tool_name_from_call(call: str) -> str | None:
    match = GOLD_TOOL_PATTERN.match(call or "")
    return match.group(1) if match else None


def call_args_text(call: str) -> str:
    match = CALL_ARGS_PATTERN.match(call or "")
    return match.group(1).strip() if match else ""


def parse_gold_args(call: str) -> Any:
    args = call_args_text(call)
    if not args:
        return {}
    try:
        return json.loads(args)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(args)
    except Exception:
        return args


def sanitize_generated_args(args_text: str) -> str:
    text = REF_PATTERN.sub('"__CURRENT_PLAN_REF__"', args_text or "")
    text = PLACEHOLDER_PATTERN.sub('"__PLACEHOLDER__"', text)
    return text


def generated_keywords(args_text: str) -> set[str]:
    sanitized = sanitize_generated_args(args_text)
    try:
        parsed = ast.parse(f"_f({sanitized})", mode="eval")
    except SyntaxError:
        return set()
    if not isinstance(parsed.body, ast.Call):
        return set()
    return {kw.arg for kw in parsed.body.keywords if kw.arg is not None}


def schema_error_for_unit(record: dict[str, Any], unit_id: str | None) -> str | None:
    for error in (record.get("quality_metrics") or {}).get("schema_errors") or []:
        if error.get("unit_id") == unit_id:
            return error.get("error") or "schema_error"
    return None


def is_schema_valid(record: dict[str, Any], unit: dict[str, Any]) -> bool | None:
    quality = record.get("quality_metrics") or {}
    if not quality.get("schema_checked"):
        return None
    return schema_error_for_unit(record, unit.get("unit_id")) is None


def text_tokens(value: Any) -> set[str]:
    raw = str(value or "").lower()
    raw = REF_PATTERN.sub(" ", raw)
    raw = PLACEHOLDER_PATTERN.sub(" ", raw)
    pieces = set(TOKEN_PATTERN.findall(raw)) | set(QUOTED_PATTERN.findall(raw))
    tokens: set[str] = set()
    for token in pieces:
        token = token.strip().strip("'\"").lower()
        if len(token) <= 1:
            continue
        if token in STOPWORDS or token.startswith("__"):
            continue
        tokens.add(token)
    return tokens


def hop_tool_name(hop: dict[str, Any]) -> str | None:
    return tool_name_from_call(hop.get("question_raw") or hop.get("question") or "")


def hop_payload(hop: dict[str, Any]) -> dict[str, Any]:
    call = hop.get("question_raw") or hop.get("question") or ""
    return {
        "hop_id": str(hop.get("id")),
        "function_name": hop_tool_name(hop),
        "gold_call": call,
        "arguments": parse_gold_args(call),
        "argument_text": call_args_text(call),
        "turn": hop.get("turn"),
        "depends_on": [str(item) for item in hop.get("depends_on") or []],
    }


def pseudo_hops_from_gold_calls(gold_calls: list[str], turn_index: int) -> list[dict[str, Any]]:
    hops: list[dict[str, Any]] = []
    for i, call in enumerate(gold_calls, start=1):
        hops.append(
            {
                "id": f"g{turn_index + 1}_{i}",
                "question": call,
                "question_raw": call,
                "answer": "",
                "depends_on": [],
                "turn": turn_index,
            }
        )
    return hops


def graph_hops_for_record(
    record: dict[str, Any],
    prompt_record: dict[str, Any] | None,
    graph: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    turn_index = int(record.get("turn_index", 0))
    gold_ids = list((record.get("graph_stats") or {}).get("gold_hop_ids") or [])
    if graph and gold_ids:
        by_id = {str(hop.get("id")): hop for hop in graph.get("hops", [])}
        return [by_id[hid] for hid in gold_ids if hid in by_id]
    if graph:
        return [
            hop
            for hop in graph.get("hops", [])
            if int(hop.get("turn", -1)) == turn_index
        ]
    return pseudo_hops_from_gold_calls(
        list((prompt_record or {}).get("gold_calls") or []), turn_index
    )


def score_candidate(
    unit: dict[str, Any],
    hop: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    unit_tool = normalize_tool_name(unit.get("tool_name"))
    hop_tool = normalize_tool_name(hop_tool_name(hop))
    raw_action = unit.get("raw_action") or ""
    args_text = unit.get("args_text") or ""
    hop_args = call_args_text(hop.get("question_raw") or hop.get("question") or "")
    unit_tokens = text_tokens(args_text) | text_tokens(unit.get("thought"))
    hop_tokens = text_tokens(hop_args) | text_tokens(hop.get("question_raw") or hop.get("question"))
    overlap = sorted(unit_tokens & hop_tokens)
    unit_keywords = generated_keywords(args_text)
    hop_arguments = parse_gold_args(hop.get("question_raw") or hop.get("question") or "")
    hop_keywords = set(hop_arguments.keys()) if isinstance(hop_arguments, dict) else set()
    keyword_overlap = sorted(unit_keywords & hop_keywords)
    unresolved_inputs = sorted(set(REF_PATTERN.findall(args_text)) | set(PLACEHOLDER_PATTERN.findall(args_text)))
    schema_valid = is_schema_valid(record, unit)

    score = 0
    reasons: list[str] = []
    same_tool = bool(unit_tool and hop_tool and unit_tool == hop_tool)
    if same_tool:
        score += 100
        reasons.append("exact_tool_name")
    elif hop_tool and re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(hop_tool)}(?![A-Za-z0-9_])",
        raw_action,
        flags=re.IGNORECASE,
    ):
        score += 80
        reasons.append("function_mention")

    if keyword_overlap:
        score += min(30, 10 * len(keyword_overlap))
        reasons.append("parameter_overlap:" + ",".join(keyword_overlap[:6]))
    if overlap:
        score += min(50, 10 * len(overlap))
        reasons.append("argument_overlap:" + ",".join(overlap[:8]))
    if schema_valid is True:
        score += 5
        reasons.append("schema_valid")
    elif schema_valid is False:
        reasons.append("schema_invalid")
    if unresolved_inputs:
        reasons.append("unresolved_input")
    if not reasons:
        reasons.append("no_anchor")

    return {
        **hop_payload(hop),
        "score": score,
        "candidate_reason": reasons,
        "same_tool": same_tool,
        "argument_overlap": overlap,
        "parameter_overlap": keyword_overlap,
        "unresolved_inputs": unresolved_inputs,
        "unit_schema_valid": schema_valid,
        "unit_schema_error": schema_error_for_unit(record, unit.get("unit_id")),
    }


def build_candidate_rows(
    plan_rows: list[dict[str, Any]],
    prompt_by_key: dict[tuple[str, int, str], dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in plan_rows:
        question_id = record["question_id"]
        turn_index = int(record.get("turn_index", 0))
        mode = record.get("mode", "")
        prompt_record = prompt_by_key.get((question_id, turn_index, mode))
        graph = graphs.get(question_id)
        candidate_hops = graph_hops_for_record(record, prompt_record, graph)
        for unit in record.get("units") or []:
            candidates = [
                score_candidate(unit, hop, record)
                for hop in candidate_hops
            ]
            candidates.sort(key=lambda item: item["score"], reverse=True)
            rows.append(
                {
                    "question_id": question_id,
                    "turn_index": turn_index,
                    "mode": mode,
                    "unit_id": unit.get("unit_id"),
                    "node_id": unit.get("node_id"),
                    "unit": unit,
                    "n_current_turn_gold_hops": len(candidate_hops),
                    "candidate_hops": candidates,
                }
            )
    return rows


def match_strength(candidate: dict[str, Any], score_threshold: int) -> str:
    if candidate.get("score", 0) < score_threshold:
        return "wrong"
    if candidate.get("same_tool"):
        if candidate.get("unit_schema_valid") is True and candidate.get("argument_overlap"):
            return "exact"
        return "partial"
    return "semantic"


def resolve_matches(
    candidate_rows: list[dict[str, Any]],
    score_threshold: int,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        grouped[(row["question_id"], row["turn_index"], row["mode"])].append(row)

    match_rows: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        pairs: list[tuple[int, str, str, dict[str, Any], dict[str, Any]]] = []
        for row in rows:
            for candidate in row.get("candidate_hops") or []:
                pairs.append(
                    (
                        int(candidate.get("score") or 0),
                        str(row.get("unit_id")),
                        str(candidate.get("hop_id")),
                        row,
                        candidate,
                    )
                )
        pairs.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        selected_units: set[str] = set()
        selected_hops: set[str] = set()
        primary_by_unit: dict[str, dict[str, Any]] = {}
        all_above_threshold: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for score, unit_id, hop_id, row, candidate in pairs:
            if score >= score_threshold:
                all_above_threshold[unit_id].append(candidate)
            if score < score_threshold:
                continue
            if unit_id in selected_units or hop_id in selected_hops:
                continue
            selected_units.add(unit_id)
            selected_hops.add(hop_id)
            primary_by_unit[unit_id] = candidate

        for row in rows:
            unit_id = str(row.get("unit_id"))
            primary = primary_by_unit.get(unit_id)
            best_candidate = (row.get("candidate_hops") or [None])[0]
            strength = match_strength(primary, score_threshold) if primary else "wrong"
            matched_hop_ids = [
                str(candidate.get("hop_id"))
                for candidate in all_above_threshold.get(unit_id, [])
            ]
            match_rows.append(
                {
                    "question_id": row["question_id"],
                    "turn_index": row["turn_index"],
                    "mode": row["mode"],
                    "unit_id": row["unit_id"],
                    "node_id": row.get("node_id"),
                    "unit": row.get("unit"),
                    "primary_hop_id": primary.get("hop_id") if primary else None,
                    "primary_gold_call": primary.get("gold_call") if primary else None,
                    "primary_score": primary.get("score") if primary else None,
                    "best_candidate_hop_id": best_candidate.get("hop_id") if best_candidate else None,
                    "best_candidate_score": best_candidate.get("score") if best_candidate else None,
                    "matched_hop_ids": matched_hop_ids,
                    "candidate_action_covered": primary is not None,
                    "single_hop_match": primary is not None,
                    "match_strength": strength,
                    "match_method": "deterministic_v2",
                    "duplicate_primary_match": False,
                    "compound_action": len(matched_hop_ids) > 1,
                    "hallucinated_argument": None,
                    "judge_confidence": None,
                    "judge_reason": None,
                    "unmatched_reason": None
                    if primary
                    else "no_candidate_above_threshold",
                }
            )

    return mark_duplicate_primary_matches(match_rows)


def mark_duplicate_primary_matches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_hop: dict[tuple[str, int, str, str, str], tuple[int, str]] = {}
    for row in rows:
        hop_id = row.get("primary_hop_id")
        if not hop_id:
            continue
        key = (
            row["question_id"],
            int(row["turn_index"]),
            row["mode"],
            str(hop_id),
        )
        score = int(row.get("primary_score") or 0)
        unit_id = str(row.get("unit_id"))
        if key not in best_by_hop or score > best_by_hop[key][0]:
            best_by_hop[key] = (score, unit_id)
    for row in rows:
        hop_id = row.get("primary_hop_id")
        if not hop_id:
            row["duplicate_primary_match"] = False
            continue
        key = (
            row["question_id"],
            int(row["turn_index"]),
            row["mode"],
            str(hop_id),
        )
        row["duplicate_primary_match"] = best_by_hop.get(key, (None, None))[1] != row.get("unit_id")
    return rows


def graph_relations(graph: dict[str, Any] | None) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    if not graph:
        return {}, {}
    hop_ids = [str(hop.get("id")) for hop in graph.get("hops") or []]
    children: dict[str, set[str]] = {hid: set() for hid in hop_ids}
    parents: dict[str, set[str]] = {hid: set() for hid in hop_ids}
    for hop in graph.get("hops") or []:
        hid = str(hop.get("id"))
        for dep in hop.get("depends_on") or []:
            dep = str(dep)
            if dep in children:
                children[dep].add(hid)
                parents[hid].add(dep)

    descendants: dict[str, set[str]] = {hid: set() for hid in hop_ids}
    ancestors: dict[str, set[str]] = {hid: set() for hid in hop_ids}
    for hid in hop_ids:
        queue = deque(children.get(hid, set()))
        while queue:
            nxt = queue.popleft()
            if nxt in descendants[hid]:
                continue
            descendants[hid].add(nxt)
            queue.extend(children.get(nxt, set()))
        queue = deque(parents.get(hid, set()))
        while queue:
            prev = queue.popleft()
            if prev in ancestors[hid]:
                continue
            ancestors[hid].add(prev)
            queue.extend(parents.get(prev, set()))
    return descendants, ancestors


def classify_generated_edge(
    source_hop: str | None,
    target_hop: str | None,
    graph: dict[str, Any] | None,
    descendants: dict[str, set[str]],
) -> str:
    if not source_hop and not target_hop:
        return "unmatched_both_endpoints"
    if not source_hop:
        return "unmatched_source"
    if not target_hop:
        return "unmatched_target"
    if source_hop == target_hop:
        return "same_gold_hop"
    if not graph:
        return "no_gold_graph"
    target = next(
        (hop for hop in graph.get("hops") or [] if str(hop.get("id")) == target_hop),
        None,
    )
    if target and source_hop in {str(dep) for dep in target.get("depends_on") or []}:
        return "gold_direct_edge"
    if target_hop in descendants.get(source_hop, set()):
        return "gold_ancestor_edge"
    if source_hop in descendants.get(target_hop, set()):
        return "reverse_gold_dependency"
    return "false_serialization"


def generated_path_exists(
    source_unit: str,
    target_unit: str,
    generated_edges: dict[str, set[str]],
) -> bool:
    queue = deque(generated_edges.get(source_unit, set()))
    seen: set[str] = set()
    while queue:
        nxt = queue.popleft()
        if nxt == target_unit:
            return True
        if nxt in seen:
            continue
        seen.add(nxt)
        queue.extend(generated_edges.get(nxt, set()))
    return False


def build_dependency_alignment(
    plan_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    matches_by_key_unit = {
        (
            row["question_id"],
            int(row["turn_index"]),
            row["mode"],
            str(row["unit_id"]),
        ): row
        for row in match_rows
    }
    rows: list[dict[str, Any]] = []

    for record in plan_rows:
        question_id = record["question_id"]
        turn_index = int(record.get("turn_index", 0))
        mode = record.get("mode", "")
        graph = graphs.get(question_id)
        descendants, _ancestors = graph_relations(graph)
        units = record.get("units") or []
        unit_by_node = {int(unit.get("node_id")): unit for unit in units if unit.get("node_id") is not None}
        unit_by_id = {str(unit.get("unit_id")): unit for unit in units}
        generated_edges: dict[str, set[str]] = defaultdict(set)

        for target in units:
            target_unit_id = str(target.get("unit_id"))
            target_match = matches_by_key_unit.get((question_id, turn_index, mode, target_unit_id))
            target_hop = target_match.get("primary_hop_id") if target_match else None
            for dep_node in target.get("dependencies") or []:
                source = unit_by_node.get(int(dep_node))
                source_unit_id = str(source.get("unit_id")) if source else None
                source_match = (
                    matches_by_key_unit.get((question_id, turn_index, mode, source_unit_id))
                    if source_unit_id
                    else None
                )
                source_hop = source_match.get("primary_hop_id") if source_match else None
                if source_unit_id:
                    generated_edges[source_unit_id].add(target_unit_id)
                label = classify_generated_edge(source_hop, target_hop, graph, descendants)
                rows.append(
                    {
                        "question_id": question_id,
                        "turn_index": turn_index,
                        "mode": mode,
                        "edge_kind": "generated_dependency",
                        "source_node_id": dep_node,
                        "target_node_id": target.get("node_id"),
                        "source_unit_id": source_unit_id,
                        "target_unit_id": target_unit_id,
                        "source_hop_id": source_hop,
                        "target_hop_id": target_hop,
                        "alignment": label,
                    }
                )

        current_hops = set((record.get("graph_stats") or {}).get("gold_hop_ids") or [])
        if graph and current_hops:
            matched_unit_by_hop: dict[str, str] = {}
            for unit_id in unit_by_id:
                match = matches_by_key_unit.get((question_id, turn_index, mode, unit_id))
                hop_id = str(match.get("primary_hop_id")) if match and match.get("primary_hop_id") else None
                if hop_id and hop_id not in matched_unit_by_hop:
                    matched_unit_by_hop[hop_id] = unit_id
            for hop in graph.get("hops") or []:
                target_hop = str(hop.get("id"))
                if target_hop not in current_hops:
                    continue
                for source_hop in [str(dep) for dep in hop.get("depends_on") or []]:
                    if source_hop not in current_hops:
                        continue
                    source_unit = matched_unit_by_hop.get(source_hop)
                    target_unit = matched_unit_by_hop.get(target_hop)
                    if not source_unit or not target_unit:
                        rows.append(
                            {
                                "question_id": question_id,
                                "turn_index": turn_index,
                                "mode": mode,
                                "edge_kind": "gold_dependency",
                                "source_hop_id": source_hop,
                                "target_hop_id": target_hop,
                                "source_unit_id": source_unit,
                                "target_unit_id": target_unit,
                                "alignment": "missing_dependency_unmatched_endpoint",
                            }
                        )
                    elif not generated_path_exists(source_unit, target_unit, generated_edges):
                        rows.append(
                            {
                                "question_id": question_id,
                                "turn_index": turn_index,
                                "mode": mode,
                                "edge_kind": "gold_dependency",
                                "source_hop_id": source_hop,
                                "target_hop_id": target_hop,
                                "source_unit_id": source_unit,
                                "target_unit_id": target_unit,
                                "alignment": "missing_dependency",
                            }
                        )
    return rows


def gold_keys_for_rows(
    plan_rows: list[dict[str, Any]],
    prompt_by_key: dict[tuple[str, int, str], dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
) -> set[tuple[str, int, str, str]]:
    keys: set[tuple[str, int, str, str]] = set()
    for record in plan_rows:
        question_id = record["question_id"]
        turn_index = int(record.get("turn_index", 0))
        mode = record.get("mode", "")
        graph = graphs.get(question_id)
        prompt_record = prompt_by_key.get((question_id, turn_index, mode))
        for hop in graph_hops_for_record(record, prompt_record, graph):
            keys.add((question_id, turn_index, mode, str(hop.get("id"))))
    return keys


def summarize_metrics(
    plan_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    alignment_rows: list[dict[str, Any]],
    prompt_by_key: dict[tuple[str, int, str], dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
    output_dir: Path,
    score_threshold: int,
) -> dict[str, Any]:
    gold_keys = gold_keys_for_rows(plan_rows, prompt_by_key, graphs)
    total_gold = len(gold_keys)
    total_units = len(match_rows)
    matched_keys = {
        (row["question_id"], int(row["turn_index"]), row["mode"], str(row["primary_hop_id"]))
        for row in match_rows
        if row.get("primary_hop_id") and not row.get("duplicate_primary_match")
    }
    strict_keys = {
        (row["question_id"], int(row["turn_index"]), row["mode"], str(row["primary_hop_id"]))
        for row in match_rows
        if row.get("primary_hop_id")
        and row.get("match_strength") == "exact"
        and not row.get("duplicate_primary_match")
    }
    partial_keys = {
        (row["question_id"], int(row["turn_index"]), row["mode"], str(row["primary_hop_id"]))
        for row in match_rows
        if row.get("primary_hop_id")
        and row.get("match_strength") in {"exact", "semantic", "partial"}
        and not row.get("duplicate_primary_match")
    }
    candidate_gold_keys = {
        (row["question_id"], int(row["turn_index"]), row["mode"], str(candidate["hop_id"]))
        for row in candidate_rows
        for candidate in row.get("candidate_hops") or []
    }
    alignment_counts = Counter(row.get("alignment") for row in alignment_rows)
    generated_alignment_counts = Counter(
        row.get("alignment")
        for row in alignment_rows
        if row.get("edge_kind") == "generated_dependency"
    )
    gold_missing_counts = Counter(
        row.get("alignment")
        for row in alignment_rows
        if row.get("edge_kind") == "gold_dependency"
    )

    def ratio(num: int, denom: int) -> float:
        return num / denom if denom else 0.0

    return {
        "run": {
            "output_dir": str(output_dir),
            "score_threshold": score_threshold,
            "n_turn_generations": len(plan_rows),
            "total_units": total_units,
            "total_gold_hops": total_gold,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "note": "Deterministic v2 matcher; LLM-as-judge is not run in this MVP.",
        },
        "action_matching": {
            "candidate_gold_coverage": ratio(len(candidate_gold_keys & gold_keys), total_gold),
            "matched_gold_hop_recall": ratio(len(matched_keys & gold_keys), total_gold),
            "strict_single_action_recall": ratio(len(strict_keys & gold_keys), total_gold),
            "partial_or_better_recall": ratio(len(partial_keys & gold_keys), total_gold),
            "matched_unit_rate": ratio(
                sum(1 for row in match_rows if row.get("candidate_action_covered")),
                total_units,
            ),
            "unmatched_action_rate": ratio(
                sum(1 for row in match_rows if not row.get("candidate_action_covered")),
                total_units,
            ),
            "duplicate_primary_match_rate": ratio(
                sum(1 for row in match_rows if row.get("duplicate_primary_match")),
                total_units,
            ),
            "compound_action_rate": ratio(
                sum(1 for row in match_rows if row.get("compound_action")),
                total_units,
            ),
            "match_strength_counts": dict(Counter(row.get("match_strength") for row in match_rows)),
        },
        "dependency_alignment": {
            "generated_dependency_edges": sum(
                1 for row in alignment_rows if row.get("edge_kind") == "generated_dependency"
            ),
            "gold_dependency_checks": sum(
                1 for row in alignment_rows if row.get("edge_kind") == "gold_dependency"
            ),
            "alignment_counts": dict(alignment_counts),
            "generated_edge_alignment_counts": dict(generated_alignment_counts),
            "gold_missing_dependency_counts": dict(gold_missing_counts),
            "false_serialization_count": generated_alignment_counts.get("false_serialization", 0),
            "missing_dependency_count": gold_missing_counts.get("missing_dependency", 0),
            "missing_dependency_unmatched_endpoint_count": gold_missing_counts.get(
                "missing_dependency_unmatched_endpoint", 0
            ),
        },
    }


def load_inputs(output_dir: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, int, str], dict[str, Any]]]:
    plan_path = output_dir / "plan_units.jsonl"
    prompts_path = output_dir / "prompts.jsonl"
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing {plan_path}")
    if not prompts_path.exists():
        raise FileNotFoundError(f"Missing {prompts_path}")
    plan_rows = read_jsonl(plan_path)
    prompt_rows = read_jsonl(prompts_path)
    prompt_by_key = {
        (row["question_id"], int(row.get("turn_index", 0)), row.get("mode", "")): row
        for row in prompt_rows
    }
    return plan_rows, prompt_by_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post-hoc deterministic matcher for think_parallel_v2 outputs."
    )
    parser.add_argument("--output-dir", required=True, help="think_parallel_v2 output directory")
    parser.add_argument(
        "--graphs-path",
        default=DEFAULT_GRAPHS_PATH,
        help="BFCL gold DAG graph annotation JSONL",
    )
    parser.add_argument(
        "--score-threshold",
        type=int,
        default=100,
        help="Minimum deterministic candidate score for a resolved match",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    graphs = load_graphs(Path(args.graphs_path).resolve() if args.graphs_path else None)
    plan_rows, prompt_by_key = load_inputs(output_dir)

    candidates_path = output_dir / "v2_match_candidates.jsonl"
    matches_path = output_dir / "v2_matches.jsonl"
    alignment_path = output_dir / "v2_dependency_alignment.jsonl"
    metrics_path = output_dir / "v2_match_metrics.json"
    for path in [candidates_path, matches_path, alignment_path]:
        path.unlink(missing_ok=True)

    candidate_rows = build_candidate_rows(plan_rows, prompt_by_key, graphs)
    match_rows = resolve_matches(candidate_rows, args.score_threshold)
    alignment_rows = build_dependency_alignment(plan_rows, match_rows, graphs)
    metrics = summarize_metrics(
        plan_rows,
        candidate_rows,
        match_rows,
        alignment_rows,
        prompt_by_key,
        graphs,
        output_dir,
        args.score_threshold,
    )

    for row in candidate_rows:
        write_jsonl(candidates_path, row)
    for row in match_rows:
        write_jsonl(matches_path, row)
    for row in alignment_rows:
        write_jsonl(alignment_path, row)
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[match_v2] wrote {candidates_path}")
    print(f"[match_v2] wrote {matches_path}")
    print(f"[match_v2] wrote {alignment_path}")
    print(f"[match_v2] wrote {metrics_path}")


if __name__ == "__main__":
    main()
