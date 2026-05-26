from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

    from src.bfcl_data import load_graphs, read_jsonl
    from src.candidate_generator import candidate_rows_for_units
    from src.parse_units import parse_think_units
else:
    from .bfcl_data import load_graphs, read_jsonl
    from .candidate_generator import candidate_rows_for_units
    from .parse_units import parse_think_units


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
You judge whether ONE generated action-plan line corresponds to ONE candidate BFCL gold hop.

This is NOT a dependency-classification task.
Do NOT decide whether the action is precomputable.
Do NOT judge the whole generated plan.
Only compare the generated action with the candidate gold hop.

You may use the full user goal and full gold trajectory as context.
Do not choose a different hop. If the generated action better matches another hop, set
better_hop_hint, but judge this candidate pair only.

Decision procedure:
1. q1_action_relation:
   exact    = the generated action uses the same exact function behavior and same primary intent.
   semantic = it does not rely on exact syntax/name, but the natural-language operation clearly matches.
   partial  = it is related but misses important intent or target detail.
   no       = it is a different operation.
   unclear  = the text is too ambiguous.

2. q2_input_relation:
   compatible             = known inputs/entities are compatible with the gold arguments.
   partially_compatible   = some important inputs match but others are missing/vague.
   incompatible           = a known input conflicts with the gold arguments.
   unresolved_ok          = missing concrete values are explicitly marked as unresolved from prior results.
   not_applicable         = the gold hop has no meaningful arguments to compare.

3. q3_extra_distinct_action:
   yes if this single generated [A] includes another distinct tool/action besides this candidate hop.

4. q4_hallucinated_argument:
   yes if the generated [A] invents a concrete value that is not in the user goal and should require a prior tool result.

Rules:
- Do not require executable BFCL function-call formatting.
- Do not mark exact only because the function name matches; key intent and inputs must also be compatible.
- If an input is explicitly marked unresolved, do not penalize it for not giving the value.
- If one generated action covers multiple gold hops, candidate_action_covered may be true, but single_hop_match must be false.
- Be conservative with exact.
- Return JSON matching the schema. Keep rationales short.
"""


FEWSHOT = """\
Examples. Use the same decision procedure and output schema.

[Example 1 - exact single-hop match]
FULL USER GOAL:
Move log.txt into archive.

GOLD TRAJECTORY:
  h1: mv({"source": "log.txt", "destination": "archive"})  <-- candidate

GENERATED ACTION:
[A1] Use mv: move log.txt into archive. Known inputs: log.txt, archive. Unresolved inputs: none.

EXPECTED JUDGMENT:
{
  "unit_id": "u1",
  "candidate_hop_id": "h1",
  "q1_action_relation": {"answer": "exact", "rationale": "The action is to move log.txt into archive."},
  "q2_input_relation": {"answer": "compatible", "rationale": "The source and destination match the gold arguments."},
  "q3_extra_distinct_action": {"answer": "no", "rationale": "No other tool action is included."},
  "q4_hallucinated_argument": {"answer": "no", "rationale": "All concrete inputs are given by the goal."},
  "candidate_action_covered": true,
  "single_hop_match": true,
  "match_strength": "exact",
  "confidence": 0.95,
  "better_hop_hint": null,
  "reason": "The generated action exactly matches the mv hop."
}

[Example 2 - semantic match without exact function name]
FULL USER GOAL:
Show the contents of goals.txt.

GOLD TRAJECTORY:
  h1: cat({"file_name": "goals.txt"})  <-- candidate

GENERATED ACTION:
[A1] Display the contents of goals.txt. Known inputs: goals.txt. Unresolved inputs: none.

EXPECTED JUDGMENT:
{
  "unit_id": "u1",
  "candidate_hop_id": "h1",
  "q1_action_relation": {"answer": "semantic", "rationale": "Displaying file contents corresponds to reading the file with cat."},
  "q2_input_relation": {"answer": "compatible", "rationale": "The target file is goals.txt."},
  "q3_extra_distinct_action": {"answer": "no", "rationale": "The action only describes reading one file."},
  "q4_hallucinated_argument": {"answer": "no", "rationale": "The file name is given by the goal."},
  "candidate_action_covered": true,
  "single_hop_match": true,
  "match_strength": "semantic",
  "confidence": 0.88,
  "better_hop_hint": null,
  "reason": "The generated action semantically matches the cat hop."
}

[Example 3 - unresolved input is acceptable]
FULL USER GOAL:
Place an order, then retrieve the details for the order that was just placed.

GOLD TRAJECTORY:
  h1: place_order({"symbol": "NVDA", "amount": 50})
  h2: get_order_details({"order_id": 12446})  <-- candidate

GENERATED ACTION:
[A2] Use get_order_details: retrieve details for the order just placed. Known inputs: none. Unresolved inputs: order_id from place_order result.

EXPECTED JUDGMENT:
{
  "unit_id": "u2",
  "candidate_hop_id": "h2",
  "q1_action_relation": {"answer": "exact", "rationale": "The function and intent are to get details for the placed order."},
  "q2_input_relation": {"answer": "unresolved_ok", "rationale": "The missing order_id is correctly marked as coming from a prior result."},
  "q3_extra_distinct_action": {"answer": "no", "rationale": "No additional tool action is included."},
  "q4_hallucinated_argument": {"answer": "no", "rationale": "It does not invent the order_id."},
  "candidate_action_covered": true,
  "single_hop_match": true,
  "match_strength": "exact",
  "confidence": 0.9,
  "better_hop_hint": null,
  "reason": "The generated action matches the get_order_details hop with an unresolved order_id."
}

[Example 4 - compound action]
FULL USER GOAL:
Go to workspace and search log.txt for Error.

GOLD TRAJECTORY:
  h1: cd({"folder": "workspace"})  <-- candidate
  h2: grep({"file_name": "log.txt", "pattern": "Error"})

GENERATED ACTION:
[A1] Use cd: enter workspace and search log.txt for Error. Known inputs: workspace, log.txt, Error. Unresolved inputs: none.

EXPECTED JUDGMENT:
{
  "unit_id": "u1",
  "candidate_hop_id": "h1",
  "q1_action_relation": {"answer": "exact", "rationale": "The action includes entering workspace."},
  "q2_input_relation": {"answer": "compatible", "rationale": "The workspace folder matches the candidate hop."},
  "q3_extra_distinct_action": {"answer": "yes", "rationale": "It also includes searching log.txt, which is another gold hop."},
  "q4_hallucinated_argument": {"answer": "no", "rationale": "The concrete inputs are given by the goal."},
  "candidate_action_covered": true,
  "single_hop_match": false,
  "match_strength": "exact",
  "confidence": 0.9,
  "better_hop_hint": null,
  "reason": "The candidate hop is covered, but the generated action is compound."
}

[Example 5 - hallucinated argument / wrong target]
FULL USER GOAL:
Cancel the order that was just placed.

GOLD TRAJECTORY:
  h1: place_order({"symbol": "NVDA", "amount": 50})
  h2: cancel_order({"order_id": 12446})  <-- candidate

GENERATED ACTION:
[A2] Use cancel_order: cancel order 99999. Known inputs: order 99999. Unresolved inputs: none.

EXPECTED JUDGMENT:
{
  "unit_id": "u2",
  "candidate_hop_id": "h2",
  "q1_action_relation": {"answer": "exact", "rationale": "The operation type is cancellation."},
  "q2_input_relation": {"answer": "incompatible", "rationale": "The generated order_id conflicts with the candidate order_id."},
  "q3_extra_distinct_action": {"answer": "no", "rationale": "It contains only one action."},
  "q4_hallucinated_argument": {"answer": "yes", "rationale": "The concrete order_id should come from the prior placement result."},
  "candidate_action_covered": false,
  "single_hop_match": false,
  "match_strength": "wrong",
  "confidence": 0.93,
  "better_hop_hint": null,
  "reason": "The action invents an incompatible order id."
}
"""


STRENGTH_PRIORITY = {
    "exact": 3,
    "semantic": 2,
    "partial": 1,
    "wrong": 0,
    "not_enough_information": 0,
}


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


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


def render_gold_trajectory(graph: dict[str, Any], candidate_hop_id: str) -> str:
    lines: list[str] = []
    for hop in graph.get("hops", []):
        marker = "  <-- candidate" if hop.get("id") == candidate_hop_id else ""
        turn = hop.get("turn")
        turn_text = f" [turn={turn}]" if turn is not None else ""
        lines.append(
            f"  {hop.get('id')}: {hop.get('question_raw') or hop.get('question')}{turn_text}{marker}"
        )
    return "\n".join(lines)


def render_prompt(
    goal: str,
    graph: dict[str, Any],
    unit: dict[str, Any],
    candidate: dict[str, Any],
) -> str:
    candidate_hop_id = str(candidate["hop_id"])
    action = unit.get("raw_action") or unit.get("action_hint") or ""
    label = f"A{unit.get('source_step')}" if unit.get("source_step") else unit.get("unit_id")
    return "\n".join(
        [
            JUDGE_SYSTEM,
            "",
            FEWSHOT,
            "",
            "=== NOW YOUR TURN ===",
            "",
            "FULL USER GOAL:",
            goal,
            "",
            "GOLD TRAJECTORY:",
            render_gold_trajectory(graph, candidate_hop_id),
            "",
            "GENERATED ACTION:",
            f"- unit_id: {unit.get('unit_id')}",
            f"- text: [{label}] {action}",
            "",
            "CANDIDATE GOLD HOP:",
            f"- hop_id: {candidate_hop_id}",
            f"- function: {candidate.get('function_name')}",
            f"- call: {candidate.get('gold_call')}",
            f"- arguments: {json.dumps(candidate.get('arguments'), ensure_ascii=False)}",
            f"- turn: {candidate.get('turn')}",
            f"- candidate_reason: {candidate.get('candidate_reason')}",
            "",
            "Return the JSON judgment for this candidate pair.",
        ]
    )


def build_candidate_rows(
    output_dir: Path,
    graphs: dict[str, dict[str, Any]],
    top_k: int,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    # Re-parse raw generations at judge time so matcher improvements are not
    # blocked by stale think_units.jsonl from an earlier parser version.
    raw_rows = read_jsonl(output_dir / "raw_generations.jsonl")
    candidate_rows: list[dict[str, Any]] = []
    generation_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in raw_rows:
        units, parse_error, parse_mode = parse_think_units(raw.get("raw_response", ""))
        key = (raw["question_id"], raw["mode"])
        generation_meta[key] = {
            "question_id": raw["question_id"],
            "mode": raw["mode"],
            "goal": raw.get("goal", ""),
            "parse_mode": parse_mode,
            "parse_error": parse_error,
            "n_units": len(units),
        }
        candidate_rows.extend(
            candidate_rows_for_units(
                raw["question_id"],
                raw["mode"],
                units,
                graphs.get(raw["question_id"]),
                top_k=top_k,
            )
        )
    return candidate_rows, generation_meta


def iter_pairs(
    candidate_rows: list[dict[str, Any]],
    graphs: dict[str, dict[str, Any]],
    generation_meta: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for row in candidate_rows:
        key = (row["question_id"], row["mode"])
        graph = graphs.get(row["question_id"])
        if not graph:
            continue
        goal = generation_meta.get(key, {}).get("goal", graph.get("goal", ""))
        for candidate in row.get("candidate_hops", []):
            pairs.append(
                {
                    "question_id": row["question_id"],
                    "mode": row["mode"],
                    "unit_id": row["unit_id"],
                    "unit": row["unit"],
                    "candidate": candidate,
                    "goal": goal,
                    "graph": graph,
                }
            )
    return pairs


async def judge_pairs_async(
    pairs: list[dict[str, Any]],
    output_path: Path,
    parallel_agent_root: Path,
    max_concurrent: int,
    timeout: int,
    max_retries: int,
    codex_binary: str,
    model: str | None,
    sandbox: str,
    cache_dir: Path | None,
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

    async def judge_one(pair: dict[str, Any]) -> dict[str, Any]:
        candidate = pair["candidate"]
        prompt = render_prompt(pair["goal"], pair["graph"], pair["unit"], candidate)
        label = sanitize_label(
            f"tpv1_{pair['question_id']}_{pair['mode']}_{pair['unit_id']}_{candidate['hop_id']}"
        )
        base = {
            "question_id": pair["question_id"],
            "mode": pair["mode"],
            "unit_id": pair["unit_id"],
            "candidate_hop_id": str(candidate["hop_id"]),
            "unit": pair["unit"],
            "candidate": candidate,
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

    tasks = [judge_one(pair) for pair in pairs]
    results: list[dict[str, Any]] = []
    completed = 0
    for future in asyncio.as_completed(tasks):
        result = await future
        results.append(result)
        write_jsonl(output_path, result)
        completed += 1
        if completed == 1 or completed % 25 == 0 or completed == len(tasks):
            print(f"[judge] completed {completed}/{len(tasks)}", flush=True)
    return results


def is_covered(record: dict[str, Any]) -> bool:
    if record.get("error"):
        return False
    if not record.get("candidate_action_covered"):
        return False
    return record.get("match_strength") in {"exact", "semantic", "partial"}


def has_hallucinated_arg(record: dict[str, Any]) -> bool:
    q4 = record.get("q4_hallucinated_argument") or {}
    return q4.get("answer") == "yes"


def score_record(record: dict[str, Any]) -> tuple[int, int, float, int]:
    strength = STRENGTH_PRIORITY.get(record.get("match_strength"), 0)
    single = 1 if record.get("single_hop_match") else 0
    confidence = float(record.get("confidence") or 0.0)
    candidate_score = int((record.get("candidate") or {}).get("score") or 0)
    return strength, single, confidence, candidate_score


def resolve_matches(
    candidate_rows: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    generation_meta: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    pairwise_by_unit: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in pairwise_rows:
        pairwise_by_unit[(record["question_id"], record["mode"], record["unit_id"])].append(record)

    rows: list[dict[str, Any]] = []
    for candidate_row in candidate_rows:
        key = (
            candidate_row["question_id"],
            candidate_row["mode"],
            candidate_row["unit_id"],
        )
        judgments = pairwise_by_unit.get(key, [])
        covered = [record for record in judgments if is_covered(record)]
        covered.sort(key=score_record, reverse=True)
        primary = covered[0] if covered else None
        matched_hop_ids = [record["candidate_hop_id"] for record in covered]
        hallucinated = any(has_hallucinated_arg(record) for record in judgments)
        single_hop_match = bool(
            primary and primary.get("single_hop_match") and len(matched_hop_ids) <= 1
        )
        row = {
            "question_id": candidate_row["question_id"],
            "mode": candidate_row["mode"],
            "unit_id": candidate_row["unit_id"],
            "unit": candidate_row["unit"],
            "n_candidates": len(candidate_row.get("candidate_hops", [])),
            "matched_hop_ids": matched_hop_ids,
            "primary_hop_id": primary["candidate_hop_id"] if primary else None,
            "candidate_action_covered": bool(covered),
            "single_hop_match": single_hop_match,
            "match_strength": primary.get("match_strength") if primary else "wrong",
            "judge_confidence": primary.get("confidence") if primary else None,
            "hallucinated_argument": hallucinated,
            "compound_action": bool(primary and not single_hop_match),
            "judge_reason": primary.get("reason") if primary else None,
            "better_hop_hint": primary.get("better_hop_hint") if primary else None,
            "parse_mode": generation_meta.get(
                (candidate_row["question_id"], candidate_row["mode"]), {}
            ).get("parse_mode"),
        }
        rows.append(row)

    best_by_hop: dict[tuple[str, str, str], tuple[tuple[int, int, float, int], str]] = {}
    for row in rows:
        hop_id = row.get("primary_hop_id")
        if not hop_id:
            continue
        key = (row["question_id"], row["mode"], hop_id)
        score = (
            STRENGTH_PRIORITY.get(row.get("match_strength"), 0),
            1 if row.get("single_hop_match") else 0,
            float(row.get("judge_confidence") or 0.0),
            0,
        )
        if key not in best_by_hop or score > best_by_hop[key][0]:
            best_by_hop[key] = (score, row["unit_id"])

    for row in rows:
        hop_id = row.get("primary_hop_id")
        row["duplicate_primary_match"] = False
        if hop_id:
            best = best_by_hop.get((row["question_id"], row["mode"], hop_id))
            row["duplicate_primary_match"] = bool(best and best[1] != row["unit_id"])
    return rows


def _gold_keys(graphs: dict[str, dict[str, Any]], generation_keys: set[tuple[str, str]]) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for question_id, mode in generation_keys:
        graph = graphs.get(question_id)
        if not graph:
            continue
        for hop in graph.get("hops", []):
            keys.add((question_id, mode, str(hop.get("id"))))
    return keys


def summarize_judge_metrics(
    graphs: dict[str, dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    match_rows: list[dict[str, Any]],
    generation_meta: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    generation_keys = set(generation_meta)
    gold_keys = _gold_keys(graphs, generation_keys)
    total_gold = len(gold_keys)
    total_units = len(match_rows)
    parsed_generations = sum(
        1 for meta in generation_meta.values() if meta.get("parse_mode") != "failed"
    )
    candidate_gold_keys = {
        (row["question_id"], row["mode"], str(candidate["hop_id"]))
        for row in candidate_rows
        for candidate in row.get("candidate_hops", [])
    }
    strict_keys = {
        (row["question_id"], row["mode"], row["primary_hop_id"])
        for row in match_rows
        if row.get("primary_hop_id")
        and row.get("single_hop_match")
        and row.get("match_strength") == "exact"
        and not row.get("duplicate_primary_match")
    }
    semantic_keys = {
        (row["question_id"], row["mode"], row["primary_hop_id"])
        for row in match_rows
        if row.get("primary_hop_id")
        and row.get("single_hop_match")
        and row.get("match_strength") in {"exact", "semantic"}
        and not row.get("duplicate_primary_match")
    }
    partial_keys = {
        (row["question_id"], row["mode"], row["primary_hop_id"])
        for row in match_rows
        if row.get("primary_hop_id")
        and row.get("single_hop_match")
        and row.get("match_strength") in {"exact", "semantic", "partial"}
        and not row.get("duplicate_primary_match")
    }
    including_compound_keys = {
        (row["question_id"], row["mode"], hop_id)
        for row in match_rows
        for hop_id in row.get("matched_hop_ids", [])
    }

    def ratio(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    return {
        "run": {
            "total_generations": len(generation_meta),
            "parsed_generations": parsed_generations,
            "total_units": total_units,
            "total_gold_hops": total_gold,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
        "metrics": {
            "format_parse_rate": ratio(parsed_generations, len(generation_meta)),
            "candidate_gold_coverage": ratio(len(candidate_gold_keys & gold_keys), total_gold),
            "strict_single_action_recall": ratio(len(strict_keys & gold_keys), total_gold),
            "semantic_single_action_recall": ratio(len(semantic_keys & gold_keys), total_gold),
            "partial_or_better_recall": ratio(len(partial_keys & gold_keys), total_gold),
            "recall_including_compound": ratio(
                len(including_compound_keys & gold_keys), total_gold
            ),
            "compound_action_rate": ratio(
                sum(1 for row in match_rows if row.get("compound_action")), total_units
            ),
            "hallucinated_argument_rate": ratio(
                sum(1 for row in match_rows if row.get("hallucinated_argument")), total_units
            ),
            "unmatched_action_rate": ratio(
                sum(1 for row in match_rows if not row.get("candidate_action_covered")),
                total_units,
            ),
            "duplicate_action_rate": ratio(
                sum(1 for row in match_rows if row.get("duplicate_primary_match")),
                total_units,
            ),
        },
    }


def render_summary(metrics: dict[str, Any]) -> str:
    values = metrics["metrics"]
    run = metrics["run"]
    lines = [
        "# think_parallel_v1 judge summary",
        "",
        "## Run",
        "",
        f"- total_generations: `{run['total_generations']}`",
        f"- parsed_generations: `{run['parsed_generations']}`",
        f"- total_units: `{run['total_units']}`",
        f"- total_gold_hops: `{run['total_gold_hops']}`",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key in [
        "format_parse_rate",
        "candidate_gold_coverage",
        "strict_single_action_recall",
        "semantic_single_action_recall",
        "partial_or_better_recall",
        "recall_including_compound",
        "compound_action_rate",
        "hallucinated_argument_rate",
        "unmatched_action_rate",
        "duplicate_action_rate",
    ]:
        lines.append(f"| `{key}` | {values.get(key, 0.0):.3f} |")
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- `strict_single_action_recall`: exact match and one generated action maps to one gold hop.",
            "- `semantic_single_action_recall`: exact or semantic match, still one generated action per gold hop.",
            "- `recall_including_compound`: coverage upper bound; compound actions are included.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Codex judge matching for think_parallel_v1 outputs")
    parser.add_argument("output_dir")
    parser.add_argument("--graphs", required=True)
    parser.add_argument("--parallel-agent-root", required=True)
    parser.add_argument("--top-k", type=int, default=int(os.getenv("JUDGE_TOP_K", "5")))
    parser.add_argument("--limit-pairs", type=int, default=None)
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
    parser.add_argument("--dry-run-candidates", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    graphs = load_graphs(Path(args.graphs).resolve())
    candidates_path = output_dir / "judge_candidates.jsonl"
    pairwise_path = output_dir / "judge_pairwise.jsonl"
    matches_path = output_dir / "judge_matches.jsonl"
    metrics_path = output_dir / "judge_metrics.json"
    summary_path = output_dir / "summary.md"

    for path in [candidates_path, pairwise_path, matches_path]:
        path.unlink(missing_ok=True)

    candidate_rows, generation_meta = build_candidate_rows(output_dir, graphs, args.top_k)
    for row in candidate_rows:
        write_jsonl(candidates_path, row)
    print(f"[judge] wrote candidates: {candidates_path}", flush=True)

    pairs = iter_pairs(candidate_rows, graphs, generation_meta)
    if args.limit_pairs is not None:
        pairs = pairs[: args.limit_pairs]
    if args.dry_run_candidates:
        print(f"[judge] dry run, candidate pairs={len(pairs)}", flush=True)
        return

    pairwise_rows = asyncio.run(
        judge_pairs_async(
            pairs,
            pairwise_path,
            Path(args.parallel_agent_root).resolve(),
            max_concurrent=args.max_concurrent,
            timeout=args.timeout,
            max_retries=args.max_retries,
            codex_binary=args.codex_binary,
            model=args.model,
            sandbox=args.sandbox,
            cache_dir=output_dir / ".codex_judge_cache",
        )
    )
    match_rows = resolve_matches(candidate_rows, pairwise_rows, generation_meta)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in match_rows:
        grouped[(row["question_id"], row["mode"])].append(row)
    for (question_id, mode), rows in sorted(grouped.items()):
        write_jsonl(matches_path, {"question_id": question_id, "mode": mode, "rows": rows})

    metrics = summarize_judge_metrics(graphs, candidate_rows, match_rows, generation_meta)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(render_summary(metrics), encoding="utf-8")
    print(f"[judge] wrote matches: {matches_path}", flush=True)
    print(f"[judge] wrote metrics: {metrics_path}", flush=True)


if __name__ == "__main__":
    main()
