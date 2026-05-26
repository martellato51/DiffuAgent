from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

    from src.bfcl_data import load_graphs
    from src.match_v2_outputs import (
        DEFAULT_GRAPHS_PATH,
        PLACEHOLDER_PATTERN,
        REF_PATTERN,
        build_dependency_alignment,
        graph_hops_for_record,
        hop_payload,
        read_jsonl,
        summarize_metrics,
        write_jsonl,
    )
else:
    from .bfcl_data import load_graphs
    from .match_v2_outputs import (
        DEFAULT_GRAPHS_PATH,
        PLACEHOLDER_PATTERN,
        REF_PATTERN,
        build_dependency_alignment,
        graph_hops_for_record,
        hop_payload,
        read_jsonl,
        summarize_metrics,
        write_jsonl,
    )


JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "unit_id",
        "candidate_hop_id",
        "q1_action_relation",
        "q2_input_relation",
        "q3_extra_distinct_action",
        "q4_hallucinated_argument",
        "candidate_action_covered",
        "single_hop_match",
        "match_strength",
        "confidence",
        "better_hop_hint",
        "reason",
    ],
    "properties": {
        "unit_id": {"type": "string"},
        "candidate_hop_id": {"type": "string"},
        "q1_action_relation": {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "rationale"],
            "properties": {
                "answer": {
                    "type": "string",
                    "enum": ["exact", "semantic", "partial", "no", "unclear"],
                },
                "rationale": {"type": "string"},
            },
        },
        "q2_input_relation": {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "rationale"],
            "properties": {
                "answer": {
                    "type": "string",
                    "enum": [
                        "compatible",
                        "partially_compatible",
                        "incompatible",
                        "unresolved_ok",
                        "not_applicable",
                    ],
                },
                "rationale": {"type": "string"},
            },
        },
        "q3_extra_distinct_action": {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "rationale"],
            "properties": {
                "answer": {"type": "string", "enum": ["yes", "no", "unclear"]},
                "rationale": {"type": "string"},
            },
        },
        "q4_hallucinated_argument": {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "rationale"],
            "properties": {
                "answer": {"type": "string", "enum": ["yes", "no", "unclear"]},
                "rationale": {"type": "string"},
            },
        },
        "candidate_action_covered": {"type": "boolean"},
        "single_hop_match": {"type": "boolean"},
        "match_strength": {
            "type": "string",
            "enum": ["exact", "semantic", "partial", "wrong", "not_enough_information"],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "better_hop_hint": {"type": ["string", "null"]},
        "reason": {"type": "string"},
    },
}


JUDGE_SYSTEM = """\
You judge whether ONE generated current-turn tool-plan action corresponds to ONE candidate BFCL gold hop.

Do NOT judge the whole generated plan.
Do NOT classify parallelism or dependency structure.
Only compare the generated action with the candidate gold hop.

You may use the current turn context, previous completed-turn context, and current-turn gold hops for grounding.
Do not choose a different hop. If the generated action better matches another hop, set better_hop_hint,
but judge this candidate pair only.

Decision procedure:
1. q1_action_relation:
   exact    = same exact function behavior and same primary intent.
   semantic = syntax/tool name may differ, but the operation clearly matches.
   partial  = related but misses important intent or target detail.
   no       = different operation.
   unclear  = too ambiguous.

2. q2_input_relation:
   compatible             = known inputs/entities are compatible with the gold arguments.
   partially_compatible   = some important inputs match but others are missing/vague.
   incompatible           = a known input conflicts with the gold arguments.
   unresolved_ok          = missing concrete values are explicitly $id references or placeholders.
   not_applicable         = the gold hop has no meaningful arguments to compare.

3. q3_extra_distinct_action:
   yes if this single generated action includes another distinct tool/action besides this candidate hop.

4. q4_hallucinated_argument:
   yes if the generated action invents a concrete value that is not in the current/previous context
   and should require a prior tool result.

Rules:
- Do not require executable BFCL function-call formatting.
- Do not mark exact only because the function name matches; key intent and inputs must also be compatible.
- Treat $1.field and <placeholder> values as unresolved inputs, not concrete hallucinations.
- If a known concrete input conflicts with the gold argument, mark q2 incompatible and usually wrong.
- If one generated action covers multiple gold hops, candidate_action_covered may be true, but single_hop_match must be false.
- Be conservative with exact.
- Return JSON matching the schema. Keep rationales short.
"""


FEWSHOT = """\
Examples.

[Example 1 - schema surface error, semantically right]
CURRENT TURN:
Unlock all doors and turn on the headlights.
GENERATED ACTION:
1. lockDoors(arg={"unlock": True, "door": ["driver", "passenger"]})
CANDIDATE GOLD HOP:
h1: lockDoors({"unlock": true, "door": ["driver", "passenger"]})
EXPECTED:
candidate_action_covered=true, single_hop_match=true, match_strength=partial.
Reason: arg wrapper is not executable schema, but action intent and inputs match.

[Example 2 - same tool, wrong value]
CURRENT TURN:
Make sure all doors are securely locked.
GENERATED ACTION:
1. lockDoors(unlock=True, door=["driver", "passenger"])
CANDIDATE GOLD HOP:
h1: lockDoors({"unlock": false, "door": ["driver", "passenger"]})
EXPECTED:
candidate_action_covered=false, match_strength=wrong.
Reason: unlock=True conflicts with the requested/gold locked state.

[Example 3 - unresolved result is acceptable]
CURRENT TURN:
Get zipcodes for Rivermist and Stonebrook, then estimate the distance.
GENERATED ACTION:
3. estimate_distance(cityA=$1.zipcode, cityB=$2.zipcode)
CANDIDATE GOLD HOP:
h3: estimate_distance({"cityA": "83214", "cityB": "74532"})
EXPECTED:
candidate_action_covered=true, single_hop_match=true, match_strength=exact,
q2_input_relation=unresolved_ok.
Reason: concrete zipcodes are correctly represented as current-plan dependencies.

[Example 4 - synonym tool]
CURRENT TURN:
Estimate the distance between two cities.
GENERATED ACTION:
3. calculate_distance(city1=$1.zipcode, city2=$2.zipcode)
CANDIDATE GOLD HOP:
h3: estimate_distance({"cityA": "83214", "cityB": "74532"})
EXPECTED:
candidate_action_covered=true, single_hop_match=true, match_strength=semantic or partial.
Reason: the tool name is not exact, but the distance-estimation operation may correspond.
"""


STRENGTH_PRIORITY = {
    "wrong": 0,
    "not_enough_information": 0,
    "partial": 1,
    "semantic": 2,
    "exact": 3,
}
CONFLICT_WORDS = [
    ("true", "false"),
    ("false", "true"),
    ("start", "stop"),
    ("stop", "start"),
    ("on", "off"),
    ("off", "on"),
]


def load_codex_runner(parallel_agent_root: Path):
    runner_path = parallel_agent_root / "src" / "codex_runner.py"
    if not runner_path.exists():
        raise FileNotFoundError(f"CodexRunner not found: {runner_path}")
    spec = importlib.util.spec_from_file_location("parallelagent_codex_runner", runner_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load CodexRunner from {runner_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CodexRunner


def sanitize_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def parse_float(value: Any, default: float = -1.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def schema_error_for_unit(plan_record: dict[str, Any], unit_id: str | None) -> str | None:
    for error in (plan_record.get("quality_metrics") or {}).get("schema_errors") or []:
        if error.get("unit_id") == unit_id:
            return error.get("error") or "schema_error"
    return None


def unit_schema_valid(plan_record: dict[str, Any], unit_id: str | None) -> bool | None:
    quality = plan_record.get("quality_metrics") or {}
    if not quality.get("schema_checked"):
        return None
    return schema_error_for_unit(plan_record, unit_id) is None


def p0_key(row: dict[str, Any]) -> tuple[str, int, str, str]:
    return (
        row["question_id"],
        int(row["turn_index"]),
        row["mode"],
        str(row["unit_id"]),
    )


def candidate_key(row: dict[str, Any], hop_id: str) -> tuple[str, int, str, str, str]:
    return (
        row["question_id"],
        int(row["turn_index"]),
        row["mode"],
        str(row["unit_id"]),
        str(hop_id),
    )


def load_p0_inputs(
    output_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[tuple[str, int, str], dict[str, Any]],
    dict[tuple[str, int, str], dict[str, Any]],
]:
    required = [
        "plan_units.jsonl",
        "prompts.jsonl",
        "v2_match_candidates.jsonl",
        "v2_matches.jsonl",
        "v2_dependency_alignment.jsonl",
    ]
    missing = [name for name in required if not (output_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing P0 artifacts in {output_dir}: {', '.join(missing)}. "
            "Run scripts/run_v2_matching.sh first."
        )
    plan_rows = read_jsonl(output_dir / "plan_units.jsonl")
    prompt_rows = read_jsonl(output_dir / "prompts.jsonl")
    candidate_rows = read_jsonl(output_dir / "v2_match_candidates.jsonl")
    match_rows = read_jsonl(output_dir / "v2_matches.jsonl")
    alignment_rows = read_jsonl(output_dir / "v2_dependency_alignment.jsonl")
    prompt_by_turn = {
        (row["question_id"], int(row.get("turn_index", 0)), row.get("mode", "")): row
        for row in prompt_rows
    }
    plan_by_turn = {
        (row["question_id"], int(row.get("turn_index", 0)), row.get("mode", "")): row
        for row in plan_rows
    }
    return plan_rows, candidate_rows, match_rows, alignment_rows, prompt_by_turn, plan_by_turn


def best_candidate(candidate_row: dict[str, Any]) -> dict[str, Any] | None:
    candidates = candidate_row.get("candidate_hops") or []
    return candidates[0] if candidates else None


def candidate_by_hop(candidate_row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(candidate.get("hop_id")): candidate for candidate in candidate_row.get("candidate_hops") or []}


def has_argument_conflict(generated_action: str, gold_call: str) -> tuple[bool, str | None]:
    gen = re.sub(r"^\s*\d+\.\s*", "", generated_action or "").lower()
    gen = REF_PATTERN.sub(" ", gen)
    gen = PLACEHOLDER_PATTERN.sub(" ", gen)
    gold = (gold_call or "").lower()
    for left, right in CONFLICT_WORDS:
        if re.search(rf"(?<![a-z0-9_]){left}(?![a-z0-9_])", gen) and re.search(
            rf"(?<![a-z0-9_]){right}(?![a-z0-9_])", gold
        ):
            return True, f"{left}_vs_{right}"
    gen_nums = set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", gen))
    gold_nums = set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", gold))
    if gen_nums and gold_nums and gen_nums.isdisjoint(gold_nums):
        return True, "numeric_disjoint"
    return False, None


def add_case(
    cases: dict[tuple[str, int, str, str, str], dict[str, Any]],
    *,
    category: str,
    reason: str,
    priority: int,
    candidate_row: dict[str, Any],
    p0_match: dict[str, Any] | None,
    candidate: dict[str, Any],
    plan_record: dict[str, Any] | None,
    dependency_impact: bool = False,
) -> None:
    key = candidate_key(candidate_row, str(candidate.get("hop_id")))
    unit = candidate_row.get("unit") or {}
    schema_valid = unit_schema_valid(plan_record or {}, str(candidate_row.get("unit_id")))
    schema_error = schema_error_for_unit(plan_record or {}, str(candidate_row.get("unit_id")))
    existing = cases.get(key)
    if existing:
        existing["categories"] = sorted(set(existing["categories"] + [category]))
        existing["reasons"] = sorted(set(existing["reasons"] + [reason]))
        existing["priority"] = min(int(existing["priority"]), priority)
        existing["dependency_impact"] = bool(existing["dependency_impact"] or dependency_impact)
        return
    cases[key] = {
        "priority": priority,
        "categories": [category],
        "reasons": [reason],
        "question_id": candidate_row["question_id"],
        "turn_index": int(candidate_row["turn_index"]),
        "mode": candidate_row["mode"],
        "unit_id": candidate_row["unit_id"],
        "node_id": candidate_row.get("node_id"),
        "unit": unit,
        "candidate_hop_id": str(candidate.get("hop_id")),
        "candidate": candidate,
        "p0_match_strength": (p0_match or {}).get("match_strength"),
        "p0_primary_hop_id": (p0_match or {}).get("primary_hop_id"),
        "p0_primary_score": (p0_match or {}).get("primary_score"),
        "p0_best_candidate_hop_id": (p0_match or {}).get("best_candidate_hop_id"),
        "p0_best_candidate_score": (p0_match or {}).get("best_candidate_score"),
        "unit_schema_valid": schema_valid,
        "unit_schema_error": schema_error,
        "dependency_impact": dependency_impact,
    }


def select_judge_cases(
    candidate_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    alignment_rows: list[dict[str, Any]],
    plan_by_turn: dict[tuple[str, int, str], dict[str, Any]],
    high_score_threshold: int,
    semantic_score_threshold: int,
) -> list[dict[str, Any]]:
    candidates_by_unit = {p0_key(row): row for row in candidate_rows}
    matches_by_unit = {p0_key(row): row for row in match_rows}
    cases: dict[tuple[str, int, str, str, str], dict[str, Any]] = {}

    for candidate_row in candidate_rows:
        key = p0_key(candidate_row)
        p0_match = matches_by_unit.get(key)
        if not p0_match:
            continue
        plan_record = plan_by_turn.get(key[:3])
        unit = candidate_row.get("unit") or {}
        primary_hop = p0_match.get("primary_hop_id")
        best = best_candidate(candidate_row)
        by_hop = candidate_by_hop(candidate_row)
        primary_candidate = by_hop.get(str(primary_hop)) if primary_hop else None
        match_strength = p0_match.get("match_strength")
        schema_valid = unit_schema_valid(plan_record or {}, str(candidate_row.get("unit_id")))
        generated_action = unit.get("raw_action") or ""

        if match_strength == "wrong" and best and int(best.get("score") or 0) >= high_score_threshold:
            add_case(
                cases,
                category="high_score_unmatched",
                reason="P0 wrong but best candidate score is high",
                priority=1,
                candidate_row=candidate_row,
                p0_match=p0_match,
                candidate=best,
                plan_record=plan_record,
            )

        if match_strength == "partial" and schema_valid is False and primary_candidate:
            add_case(
                cases,
                category="schema_invalid_partial",
                reason="P0 partial match is schema-invalid and may be a surface-form error",
                priority=2,
                candidate_row=candidate_row,
                p0_match=p0_match,
                candidate=primary_candidate,
                plan_record=plan_record,
            )

        if match_strength in {"exact", "partial"} and primary_candidate:
            conflict, conflict_type = has_argument_conflict(
                generated_action,
                primary_candidate.get("gold_call") or "",
            )
            if conflict:
                add_case(
                    cases,
                    category="argument_value_conflict",
                    reason=f"P0 matched pair has possible argument conflict: {conflict_type}",
                    priority=1,
                    candidate_row=candidate_row,
                    p0_match=p0_match,
                    candidate=primary_candidate,
                    plan_record=plan_record,
                )

        if unit.get("is_valid_tool") is False and best:
            best_score = int(best.get("score") or 0)
            has_overlap = bool(best.get("argument_overlap") or best.get("parameter_overlap"))
            if best_score >= semantic_score_threshold or has_overlap:
                add_case(
                    cases,
                    category="semantic_tool_synonym_or_decomposition",
                    reason="Invalid/synonym tool may semantically correspond to a gold hop",
                    priority=1,
                    candidate_row=candidate_row,
                    p0_match=p0_match,
                    candidate=best,
                    plan_record=plan_record,
                )

        if p0_match.get("duplicate_primary_match") and primary_candidate:
            add_case(
                cases,
                category="duplicate_primary_match",
                reason="P0 marked this unit as duplicate coverage of a gold hop",
                priority=2,
                candidate_row=candidate_row,
                p0_match=p0_match,
                candidate=primary_candidate,
                plan_record=plan_record,
            )

    for row in alignment_rows:
        if row.get("edge_kind") != "generated_dependency":
            continue
        if row.get("alignment") not in {"unmatched_both_endpoints", "unmatched_source", "unmatched_target"}:
            continue
        for endpoint in ["source_unit_id", "target_unit_id"]:
            unit_id = row.get(endpoint)
            if not unit_id:
                continue
            key = (row["question_id"], int(row["turn_index"]), row["mode"], str(unit_id))
            candidate_row = candidates_by_unit.get(key)
            p0_match = matches_by_unit.get(key)
            if not candidate_row or not p0_match:
                continue
            best = best_candidate(candidate_row)
            if not best:
                continue
            if int(best.get("score") or 0) < semantic_score_threshold and not (
                best.get("argument_overlap") or best.get("parameter_overlap")
            ):
                continue
            add_case(
                cases,
                category="dependency_endpoint_unmatched",
                reason="Generated dependency edge endpoint is unmatched but has a plausible candidate",
                priority=1,
                candidate_row=candidate_row,
                p0_match=p0_match,
                candidate=best,
                plan_record=plan_by_turn.get(key[:3]),
                dependency_impact=True,
            )

    return sorted(
        cases.values(),
        key=lambda item: (
            int(item["priority"]),
            item["question_id"],
            int(item["turn_index"]),
            str(item["unit_id"]),
            str(item["candidate_hop_id"]),
        ),
    )


def current_turn_context(prompt_record: dict[str, Any] | None) -> str:
    if not prompt_record:
        return ""
    messages = prompt_record.get("prompt") or []
    user_content = ""
    for message in messages:
        if message.get("role") == "user":
            user_content = message.get("content") or ""
    if "Current Plan:" in user_content:
        return user_content.split("Current Plan:", 1)[0].strip()
    return user_content.strip()


def render_current_gold_hops(
    plan_record: dict[str, Any] | None,
    prompt_record: dict[str, Any] | None,
    graph: dict[str, Any] | None,
    candidate_hop_id: str,
) -> str:
    if not plan_record:
        return ""
    hops = graph_hops_for_record(plan_record, prompt_record, graph)
    lines: list[str] = []
    for hop in hops:
        payload = hop_payload(hop)
        marker = "  <-- candidate" if str(payload["hop_id"]) == str(candidate_hop_id) else ""
        deps = ",".join(payload.get("depends_on") or [])
        dep_text = f" depends_on=[{deps}]" if deps else ""
        lines.append(f"  {payload['hop_id']}: {payload['gold_call']}{dep_text}{marker}")
    return "\n".join(lines)


def unresolved_inputs(args_text: str) -> list[str]:
    return sorted(set(REF_PATTERN.findall(args_text or "")) | set(PLACEHOLDER_PATTERN.findall(args_text or "")))


def render_prompt(
    case: dict[str, Any],
    prompt_record: dict[str, Any] | None,
    plan_record: dict[str, Any] | None,
    graph: dict[str, Any] | None,
) -> str:
    unit = case.get("unit") or {}
    candidate = case.get("candidate") or {}
    args_text = unit.get("args_text") or ""
    return "\n".join(
        [
            JUDGE_SYSTEM,
            "",
            FEWSHOT,
            "",
            "=== NOW YOUR TURN ===",
            "",
            "CURRENT TURN CONTEXT:",
            current_turn_context(prompt_record),
            "",
            "CURRENT TURN GOLD HOPS:",
            render_current_gold_hops(plan_record, prompt_record, graph, str(case["candidate_hop_id"])),
            "",
            "GENERATED ACTION:",
            f"- unit_id: {case.get('unit_id')}",
            f"- numbered_action: {unit.get('raw_action')}",
            f"- tool_name: {unit.get('tool_name')}",
            f"- args_text: {args_text}",
            f"- thought: {unit.get('thought') or ''}",
            f"- current_plan_dependencies: {unit.get('dependencies') or []}",
            f"- unresolved_inputs: {unresolved_inputs(args_text)}",
            f"- schema_valid: {case.get('unit_schema_valid')}",
            f"- schema_error: {case.get('unit_schema_error')}",
            f"- p0_categories: {case.get('categories')}",
            f"- p0_reasons: {case.get('reasons')}",
            "",
            "CANDIDATE GOLD HOP:",
            f"- hop_id: {case.get('candidate_hop_id')}",
            f"- function: {candidate.get('function_name')}",
            f"- call: {candidate.get('gold_call')}",
            f"- arguments: {json.dumps(candidate.get('arguments'), ensure_ascii=False)}",
            f"- depends_on: {candidate.get('depends_on')}",
            f"- deterministic_score: {candidate.get('score')}",
            f"- deterministic_reason: {candidate.get('candidate_reason')}",
            "",
            "Return the JSON judgment for this candidate pair.",
        ]
    )


async def judge_cases_async(
    cases: list[dict[str, Any]],
    output_path: Path,
    prompt_by_turn: dict[tuple[str, int, str], dict[str, Any]],
    plan_by_turn: dict[tuple[str, int, str], dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
    parallel_agent_root: Path,
    max_concurrent: int,
    timeout: int,
    max_retries: int,
    codex_binary: str,
    model: str | None,
    sandbox: str,
    cache_dir: Path,
) -> list[dict[str, Any]]:
    CodexRunner = load_codex_runner(parallel_agent_root)
    runner = CodexRunner(
        max_concurrent=max_concurrent,
        timeout=timeout,
        max_retries=max_retries,
        sandbox=sandbox,
        model=model,
        codex_binary=codex_binary,
        cache_dir=cache_dir,
    )

    async def judge_one(case: dict[str, Any]) -> dict[str, Any]:
        turn_key = (case["question_id"], int(case["turn_index"]), case["mode"])
        prompt = render_prompt(
            case,
            prompt_by_turn.get(turn_key),
            plan_by_turn.get(turn_key),
            graphs.get(case["question_id"]),
        )
        label = sanitize_label(
            f"tpv2_{case['question_id']}_t{case['turn_index']}_{case['mode']}_{case['unit_id']}_{case['candidate_hop_id']}"
        )
        base = {
            "question_id": case["question_id"],
            "turn_index": int(case["turn_index"]),
            "mode": case["mode"],
            "unit_id": case["unit_id"],
            "candidate_hop_id": str(case["candidate_hop_id"]),
            "unit": case.get("unit"),
            "candidate": case.get("candidate"),
            "case_categories": case.get("categories") or [],
            "case_reasons": case.get("reasons") or [],
            "dependency_impact": bool(case.get("dependency_impact")),
        }
        try:
            result = await runner.run(prompt, JUDGE_SCHEMA, label=label)
        except Exception as exc:
            return {
                **base,
                "error": str(exc),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        return {
            **result,
            **base,
            "judge_unit_id": result.get("unit_id"),
            "judge_candidate_hop_id": result.get("candidate_hop_id"),
            "error": None,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    results: list[dict[str, Any]] = []
    completed = 0
    for future in asyncio.as_completed([judge_one(case) for case in cases]):
        result = await future
        results.append(result)
        write_jsonl(output_path, result)
        completed += 1
        if completed == 1 or completed % 10 == 0 or completed == len(cases):
            print(f"[judge_v2] completed {completed}/{len(cases)}", flush=True)
    return results


def judged_covered(row: dict[str, Any], confidence_threshold: float) -> bool:
    if row.get("error"):
        return False
    if parse_float(row.get("confidence"), 0.0) < confidence_threshold:
        return False
    return bool(row.get("candidate_action_covered")) and row.get("match_strength") in {
        "exact",
        "semantic",
        "partial",
    }


def judged_downgrade(row: dict[str, Any], confidence_threshold: float) -> bool:
    if row.get("error"):
        return False
    if parse_float(row.get("confidence"), 0.0) < confidence_threshold:
        return False
    q2 = row.get("q2_input_relation") or {}
    return row.get("match_strength") in {"wrong", "not_enough_information"} or q2.get("answer") == "incompatible"


def judge_sort_key(row: dict[str, Any]) -> tuple[int, int, float, int]:
    strength = STRENGTH_PRIORITY.get(row.get("match_strength"), 0)
    single = 1 if row.get("single_hop_match") else 0
    confidence = parse_float(row.get("confidence"), 0.0)
    candidate_score = int((row.get("candidate") or {}).get("score") or 0)
    return strength, single, confidence, candidate_score


def p0_sort_key(row: dict[str, Any]) -> tuple[int, int, float, int]:
    strength = STRENGTH_PRIORITY.get(row.get("match_strength"), 0)
    single = 1 if row.get("single_hop_match") else 0
    score = int(row.get("primary_score") or 0)
    return strength, single, 0.0, score


def apply_judge_to_match(
    p0_row: dict[str, Any],
    judgments: list[dict[str, Any]],
    confidence_threshold: float,
) -> dict[str, Any]:
    row = dict(p0_row)
    row["p0_primary_hop_id"] = p0_row.get("primary_hop_id")
    row["p0_match_strength"] = p0_row.get("match_strength")
    row["p0_primary_score"] = p0_row.get("primary_score")
    row["p0_match_method"] = p0_row.get("match_method")
    row["judge_considered_count"] = len(judgments)
    row["judge_error_count"] = sum(1 for item in judgments if item.get("error"))
    row["judge_confidence"] = p0_row.get("judge_confidence")
    row["judge_reason"] = p0_row.get("judge_reason")
    row["match_method"] = "hybrid_p0"
    row["override_reason"] = None
    row["judge_match_strength"] = None
    row["judge_primary_hop_id"] = None
    row["schema_surface_error_only"] = False
    row["argument_conflict_downgrade"] = False

    high_conf = [item for item in judgments if not item.get("error") and parse_float(item.get("confidence"), 0.0) >= confidence_threshold]
    covered = [item for item in high_conf if judged_covered(item, confidence_threshold)]
    covered.sort(key=judge_sort_key, reverse=True)

    primary_hop = str(p0_row.get("primary_hop_id")) if p0_row.get("primary_hop_id") else None
    primary_judgments = [
        item for item in high_conf if primary_hop and str(item.get("candidate_hop_id")) == primary_hop
    ]
    primary_downgraded = any(judged_downgrade(item, confidence_threshold) for item in primary_judgments)

    best_judge = covered[0] if covered else None
    if best_judge and (
        not primary_hop
        or primary_downgraded
        or judge_sort_key(best_judge) > p0_sort_key(p0_row)
        or str(best_judge.get("candidate_hop_id")) != primary_hop
    ):
        candidate = best_judge.get("candidate") or {}
        row.update(
            {
                "primary_hop_id": str(best_judge.get("candidate_hop_id")),
                "primary_gold_call": candidate.get("gold_call"),
                "primary_score": candidate.get("score"),
                "matched_hop_ids": [
                    str(item.get("candidate_hop_id")) for item in covered if item.get("candidate_hop_id")
                ],
                "candidate_action_covered": True,
                "single_hop_match": bool(best_judge.get("single_hop_match")),
                "match_strength": best_judge.get("match_strength"),
                "compound_action": not bool(best_judge.get("single_hop_match")),
                "hallucinated_argument": (best_judge.get("q4_hallucinated_argument") or {}).get("answer") == "yes",
                "judge_confidence": best_judge.get("confidence"),
                "judge_reason": best_judge.get("reason"),
                "judge_match_strength": best_judge.get("match_strength"),
                "judge_primary_hop_id": str(best_judge.get("candidate_hop_id")),
                "match_method": "hybrid_judge_rescue" if not primary_hop else "hybrid_judge_override",
                "override_reason": "judge_rescue_or_better_match",
            }
        )
        if p0_row.get("match_strength") == "partial" and best_judge.get("match_strength") in {"exact", "semantic", "partial"}:
            row["schema_surface_error_only"] = True
        return row

    if primary_downgraded and not covered:
        downgrade = primary_judgments[0]
        row.update(
            {
                "primary_hop_id": None,
                "primary_gold_call": None,
                "primary_score": None,
                "matched_hop_ids": [],
                "candidate_action_covered": False,
                "single_hop_match": False,
                "match_strength": "wrong",
                "compound_action": False,
                "hallucinated_argument": (downgrade.get("q4_hallucinated_argument") or {}).get("answer") == "yes",
                "judge_confidence": downgrade.get("confidence"),
                "judge_reason": downgrade.get("reason"),
                "judge_match_strength": downgrade.get("match_strength"),
                "judge_primary_hop_id": str(downgrade.get("candidate_hop_id")),
                "match_method": "hybrid_judge_downgrade",
                "override_reason": "judge_wrong_or_input_incompatible",
                "argument_conflict_downgrade": True,
            }
        )
        return row

    if primary_judgments:
        confirm = primary_judgments[0]
        row["match_method"] = "hybrid_judge_confirm"
        row["judge_confidence"] = confirm.get("confidence")
        row["judge_reason"] = confirm.get("reason")
        row["judge_match_strength"] = confirm.get("match_strength")
        row["judge_primary_hop_id"] = str(confirm.get("candidate_hop_id"))
        if row.get("match_strength") == "partial" and confirm.get("match_strength") in {"exact", "semantic", "partial"}:
            row["schema_surface_error_only"] = True
    return row


def mark_duplicate_primary_matches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_hop: dict[tuple[str, int, str, str], tuple[tuple[int, int, float, int], str]] = {}
    for row in rows:
        hop_id = row.get("primary_hop_id")
        if not hop_id:
            continue
        key = (row["question_id"], int(row["turn_index"]), row["mode"], str(hop_id))
        score = p0_sort_key(row)
        if key not in best_by_hop or score > best_by_hop[key][0]:
            best_by_hop[key] = (score, str(row["unit_id"]))
    for row in rows:
        hop_id = row.get("primary_hop_id")
        if not hop_id:
            row["duplicate_primary_match"] = False
            continue
        key = (row["question_id"], int(row["turn_index"]), row["mode"], str(hop_id))
        row["duplicate_primary_match"] = best_by_hop.get(key, (None, None))[1] != str(row["unit_id"])
    return rows


def resolve_hybrid_matches(
    p0_matches: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    confidence_threshold: float,
) -> list[dict[str, Any]]:
    judgments_by_unit: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in pairwise_rows:
        judgments_by_unit[p0_key(row)].append(row)
    hybrid = [
        apply_judge_to_match(row, judgments_by_unit.get(p0_key(row), []), confidence_threshold)
        for row in p0_matches
    ]
    return mark_duplicate_primary_matches(hybrid)


def gold_keys_for_rows(
    plan_rows: list[dict[str, Any]],
    prompt_by_turn: dict[tuple[str, int, str], dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
) -> set[tuple[str, int, str, str]]:
    keys: set[tuple[str, int, str, str]] = set()
    for record in plan_rows:
        question_id = record["question_id"]
        turn_index = int(record.get("turn_index", 0))
        mode = record.get("mode", "")
        graph = graphs.get(question_id)
        prompt_record = prompt_by_turn.get((question_id, turn_index, mode))
        for hop in graph_hops_for_record(record, prompt_record, graph):
            keys.add((question_id, turn_index, mode, str(hop.get("id"))))
    return keys


def summarize_hybrid_metrics(
    plan_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    hybrid_matches: list[dict[str, Any]],
    alignment_rows: list[dict[str, Any]],
    prompt_by_turn: dict[tuple[str, int, str], dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
    output_dir: Path,
    p0_metrics: dict[str, Any] | None,
    selected_cases: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    confidence_threshold: float,
    q2_confidence_threshold: float,
) -> dict[str, Any]:
    p0_like = summarize_metrics(
        plan_rows,
        candidate_rows,
        hybrid_matches,
        alignment_rows,
        prompt_by_turn,
        graphs,
        output_dir,
        score_threshold=-1,
    )
    gold_keys = gold_keys_for_rows(plan_rows, prompt_by_turn, graphs)
    q2_strict_keys = {
        (row["question_id"], int(row["turn_index"]), row["mode"], str(row["primary_hop_id"]))
        for row in hybrid_matches
        if row.get("primary_hop_id")
        and not row.get("duplicate_primary_match")
        and not row.get("compound_action")
        and not row.get("argument_conflict_downgrade")
        and (
            (
                row.get("match_strength") == "exact"
                and (row.get("unit") or {}).get("is_valid_tool") is True
            )
            or (
                row.get("match_strength") == "semantic"
                and parse_float(row.get("judge_confidence"), 0.0) >= q2_confidence_threshold
            )
        )
    }
    selected_by_category = Counter(
        category for case in selected_cases for category in case.get("categories") or []
    )
    judged_by_category = Counter(
        category for row in pairwise_rows if not row.get("error") for category in row.get("case_categories") or []
    )
    semantic_rescues = [
        row
        for row in hybrid_matches
        if row.get("match_method") in {"hybrid_judge_rescue", "hybrid_judge_override"}
        and row.get("p0_match_strength") in {None, "wrong"}
        and row.get("match_strength") in {"exact", "semantic", "partial"}
    ]
    downgrades = [row for row in hybrid_matches if row.get("match_method") == "hybrid_judge_downgrade"]
    schema_surface = [row for row in hybrid_matches if row.get("schema_surface_error_only")]
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

    total_units = len(hybrid_matches)
    hybrid_action = p0_like["action_matching"]
    hybrid_dep = p0_like["dependency_alignment"]
    return {
        "run": {
            "output_dir": str(output_dir),
            "n_turn_generations": len(plan_rows),
            "total_units": total_units,
            "total_gold_hops": len(gold_keys),
            "selected_judge_cases": len(selected_cases),
            "judged_pairs": len(pairwise_rows),
            "judge_errors": sum(1 for row in pairwise_rows if row.get("error")),
            "judge_confidence_threshold": confidence_threshold,
            "q2_confidence_threshold": q2_confidence_threshold,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "note": "Hybrid v2 matcher: deterministic P0 plus selective LLM-as-judge overrides.",
        },
        "p0_reference": p0_metrics,
        "hybrid_action_matching": {
            "hybrid_matched_gold_hop_recall": hybrid_action["matched_gold_hop_recall"],
            "hybrid_strict_single_action_recall": hybrid_action["strict_single_action_recall"],
            "hybrid_partial_or_better_recall": hybrid_action["partial_or_better_recall"],
            "hybrid_matched_unit_rate": hybrid_action["matched_unit_rate"],
            "hybrid_unmatched_action_rate": hybrid_action["unmatched_action_rate"],
            "hybrid_duplicate_primary_match_rate": hybrid_action["duplicate_primary_match_rate"],
            "hybrid_compound_action_rate": hybrid_action["compound_action_rate"],
            "hybrid_match_strength_counts": hybrid_action["match_strength_counts"],
            "q2_strict_matched_gold_hop_recall": ratio(len(q2_strict_keys & gold_keys), len(gold_keys)),
            "semantic_rescue_rate": ratio(len(semantic_rescues), max(1, len(selected_cases))),
            "conflict_downgrade_rate": ratio(len(downgrades), max(1, len(selected_cases))),
            "schema_surface_error_rate": ratio(len(schema_surface), max(1, len(pairwise_rows))),
        },
        "hybrid_dependency_alignment": {
            **hybrid_dep,
            "hybrid_false_serialization_count": generated_alignment_counts.get("false_serialization", 0),
            "hybrid_missing_dependency_count": gold_missing_counts.get("missing_dependency", 0),
            "alignment_counts": dict(alignment_counts),
        },
        "judge_selection": {
            "selected_by_category": dict(selected_by_category),
            "judged_by_category": dict(judged_by_category),
        },
    }


def render_audit(
    selected_cases: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    hybrid_matches: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> str:
    pairwise_by_key = {
        (
            row["question_id"],
            int(row["turn_index"]),
            row["mode"],
            str(row["unit_id"]),
            str(row["candidate_hop_id"]),
        ): row
        for row in pairwise_rows
    }
    hybrid_by_unit = {p0_key(row): row for row in hybrid_matches}
    lines = [
        "# think_parallel_v2 hybrid matcher audit",
        "",
        "## Summary",
        "",
        f"- selected_judge_cases: `{metrics['run']['selected_judge_cases']}`",
        f"- judged_pairs: `{metrics['run']['judged_pairs']}`",
        f"- judge_errors: `{metrics['run']['judge_errors']}`",
        "",
        "## Selection counts",
        "",
        "| category | selected | judged |",
        "|---|---:|---:|",
    ]
    selected_counts = Counter(category for case in selected_cases for category in case.get("categories") or [])
    judged_counts = Counter(
        category for row in pairwise_rows if not row.get("error") for category in row.get("case_categories") or []
    )
    for category in sorted(set(selected_counts) | set(judged_counts)):
        lines.append(f"| `{category}` | {selected_counts.get(category, 0)} | {judged_counts.get(category, 0)} |")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| case | categories | generated | candidate | judge | hybrid primary |",
            "|---|---|---|---|---|---|",
        ]
    )
    for case in selected_cases[:200]:
        key = (
            case["question_id"],
            int(case["turn_index"]),
            case["mode"],
            str(case["unit_id"]),
            str(case["candidate_hop_id"]),
        )
        judge = pairwise_by_key.get(key)
        hybrid = hybrid_by_unit.get(key[:4])
        unit = case.get("unit") or {}
        candidate = case.get("candidate") or {}
        judge_text = "not_run"
        if judge:
            if judge.get("error"):
                judge_text = "error"
            else:
                judge_text = f"{judge.get('match_strength')} c={parse_float(judge.get('confidence'), 0.0):.2f}"
        hybrid_text = "-"
        if hybrid:
            hybrid_text = f"{hybrid.get('primary_hop_id')} / {hybrid.get('match_strength')} / {hybrid.get('match_method')}"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{case['question_id']} t{case['turn_index']} {case['unit_id']}",
                    ",".join(case.get("categories") or []),
                    f"`{one_line(unit.get('raw_action'), 90)}`",
                    f"{case['candidate_hop_id']}: `{one_line(candidate.get('gold_call'), 90)}`",
                    judge_text,
                    hybrid_text,
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def one_line(value: Any, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def load_p0_metrics(output_dir: Path) -> dict[str, Any] | None:
    path = output_dir / "v2_match_metrics.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Selective LLM-as-judge hybrid matcher for think_parallel_v2 outputs."
    )
    parser.add_argument("--output-dir", required=True, help="think_parallel_v2 output directory")
    parser.add_argument(
        "--graphs-path",
        default=DEFAULT_GRAPHS_PATH,
        help="BFCL gold DAG graph annotation JSONL",
    )
    parser.add_argument(
        "--parallel-agent-root",
        default=os.getenv("PARALLEL_AGENT_ROOT", "/home/ilju/research/ParallelAgent"),
        help="ParallelAgent root containing src/codex_runner.py",
    )
    parser.add_argument("--dry-run-candidates", action="store_true")
    parser.add_argument("--limit-pairs", type=int, default=None)
    parser.add_argument("--high-score-threshold", type=int, default=80)
    parser.add_argument("--semantic-score-threshold", type=int, default=30)
    parser.add_argument("--confidence-threshold", type=float, default=0.65)
    parser.add_argument("--q2-confidence-threshold", type=float, default=0.75)
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=int(os.getenv("JUDGE_MAX_CONCURRENT", "4")),
    )
    parser.add_argument("--timeout", type=int, default=int(os.getenv("JUDGE_TIMEOUT", "180")))
    parser.add_argument(
        "--max-retries",
        type=int,
        default=int(os.getenv("JUDGE_MAX_RETRIES", "2")),
    )
    parser.add_argument("--codex-binary", default=os.getenv("CODEX_BINARY", "codex"))
    parser.add_argument("--model", default=os.getenv("JUDGE_MODEL") or None)
    parser.add_argument("--sandbox", default=os.getenv("JUDGE_SANDBOX", "read-only"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    graphs = load_graphs(Path(args.graphs_path).resolve() if args.graphs_path else None)
    (
        plan_rows,
        candidate_rows,
        p0_match_rows,
        p0_alignment_rows,
        prompt_by_turn,
        plan_by_turn,
    ) = load_p0_inputs(output_dir)

    cases_path = output_dir / "v2_judge_candidate_cases.jsonl"
    pairwise_path = output_dir / "v2_judge_pairwise.jsonl"
    hybrid_matches_path = output_dir / "v2_hybrid_matches.jsonl"
    hybrid_alignment_path = output_dir / "v2_hybrid_dependency_alignment.jsonl"
    hybrid_metrics_path = output_dir / "v2_hybrid_metrics.json"
    hybrid_audit_path = output_dir / "v2_hybrid_audit.md"

    for path in [
        cases_path,
        pairwise_path,
        hybrid_matches_path,
        hybrid_alignment_path,
    ]:
        path.unlink(missing_ok=True)

    selected_cases = select_judge_cases(
        candidate_rows,
        p0_match_rows,
        p0_alignment_rows,
        plan_by_turn,
        high_score_threshold=args.high_score_threshold,
        semantic_score_threshold=args.semantic_score_threshold,
    )
    for case in selected_cases:
        write_jsonl(cases_path, case)
    print(f"[judge_v2] wrote candidate cases: {cases_path} ({len(selected_cases)})", flush=True)

    if args.dry_run_candidates:
        print("[judge_v2] dry run, skipping judge and hybrid resolution", flush=True)
        return

    judge_cases = selected_cases
    if args.limit_pairs is not None:
        judge_cases = judge_cases[: args.limit_pairs]

    pairwise_rows = asyncio.run(
        judge_cases_async(
            judge_cases,
            pairwise_path,
            prompt_by_turn,
            plan_by_turn,
            graphs,
            Path(args.parallel_agent_root).resolve(),
            max_concurrent=args.max_concurrent,
            timeout=args.timeout,
            max_retries=args.max_retries,
            codex_binary=args.codex_binary,
            model=args.model,
            sandbox=args.sandbox,
            cache_dir=output_dir / ".codex_judge_cache_v2",
        )
    )

    hybrid_matches = resolve_hybrid_matches(
        p0_match_rows,
        pairwise_rows,
        confidence_threshold=args.confidence_threshold,
    )
    hybrid_alignment = build_dependency_alignment(plan_rows, hybrid_matches, graphs)
    metrics = summarize_hybrid_metrics(
        plan_rows,
        candidate_rows,
        hybrid_matches,
        hybrid_alignment,
        prompt_by_turn,
        graphs,
        output_dir,
        load_p0_metrics(output_dir),
        selected_cases,
        pairwise_rows,
        confidence_threshold=args.confidence_threshold,
        q2_confidence_threshold=args.q2_confidence_threshold,
    )

    for row in hybrid_matches:
        write_jsonl(hybrid_matches_path, row)
    for row in hybrid_alignment:
        write_jsonl(hybrid_alignment_path, row)
    hybrid_metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    hybrid_audit_path.write_text(
        render_audit(selected_cases, pairwise_rows, hybrid_matches, metrics),
        encoding="utf-8",
    )
    print(f"[judge_v2] wrote pairwise: {pairwise_path}", flush=True)
    print(f"[judge_v2] wrote hybrid matches: {hybrid_matches_path}", flush=True)
    print(f"[judge_v2] wrote hybrid alignment: {hybrid_alignment_path}", flush=True)
    print(f"[judge_v2] wrote hybrid metrics: {hybrid_metrics_path}", flush=True)
    print(f"[judge_v2] wrote audit: {hybrid_audit_path}", flush=True)


if __name__ == "__main__":
    main()
