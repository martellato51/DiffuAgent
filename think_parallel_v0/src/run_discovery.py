from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

    from src.bfcl_data import load_bfcl_records, load_edges, load_graphs
    from src.llada_trace import TraceableLLaDABackend
    from src.match_gold import function_tool_names, match_units_to_gold
    from src.metrics import (
        find_unit_span,
        render_summary,
        summarize_metrics,
        token_stats_for_span,
    )
    from src.parse_units import parse_think_units
    from src.prompt_builder import build_prompt
else:
    from .bfcl_data import load_bfcl_records, load_edges, load_graphs
    from .llada_trace import TraceableLLaDABackend
    from .match_gold import function_tool_names, match_units_to_gold
    from .metrics import (
        find_unit_span,
        render_summary,
        summarize_metrics,
        token_stats_for_span,
    )
    from .parse_units import parse_think_units
    from .prompt_builder import build_prompt


def split_ids(value: str | None) -> list[str] | None:
    if value is None or value.strip() == "":
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def load_ids_from_file(path: Path, category: str) -> list[str]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected id file to contain a JSON object: {path}")
    ids = data.get(category)
    if ids is None:
        available = ", ".join(sorted(data))
        raise ValueError(
            f"Category {category!r} is not present in {path}. "
            f"Available categories: {available}"
        )
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise ValueError(f"Expected {category!r} in {path} to be a list of strings")
    return ids


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


def log_progress(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"[progress {timestamp}] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BFCL LLaDA think-unit discovery")
    parser.add_argument("--ids", default=None, help="Comma-separated BFCL ids")
    parser.add_argument(
        "--ids-file",
        default=None,
        help="JSON object mapping BFCL categories to id lists. Ignored when --ids is set.",
    )
    parser.add_argument("--category", default="multi_turn_base")
    parser.add_argument(
        "--mode",
        default="both_ta",
        choices=[
            "goal_tools_a",
            "goal_init_tools_a",
            "both_a",
            "goal_tools_ta",
            "goal_init_tools_ta",
            "both_ta",
        ],
    )
    parser.add_argument("--graphs", required=True)
    parser.add_argument("--edges", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bfcl-root", default=os.getcwd())
    parser.add_argument("--dtype", default=os.getenv("LLADA_DTYPE", "bfloat16"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bfcl_root = Path(args.bfcl_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "raw_generations.jsonl"
    units_path = output_dir / "think_units.jsonl"
    conf_path = output_dir / "token_confidence.jsonl"
    matched_path = output_dir / "matched_units.jsonl"
    metrics_path = output_dir / "metrics.json"
    summary_path = output_dir / "summary.md"
    for path in [raw_path, units_path, conf_path, matched_path]:
        path.unlink(missing_ok=True)

    ids = split_ids(args.ids)
    ids_file = Path(args.ids_file).resolve() if args.ids_file else None
    if ids is None and ids_file is not None:
        ids = load_ids_from_file(ids_file, args.category)

    if args.mode == "both_ta":
        modes = ["goal_tools_ta", "goal_init_tools_ta"]
    elif args.mode == "both_a":
        modes = ["goal_tools_a", "goal_init_tools_a"]
    else:
        modes = [args.mode]
    records = load_bfcl_records(bfcl_root, args.category, ids)
    graphs = load_graphs(Path(args.graphs))
    edges = load_edges(Path(args.edges))
    total_generations = len(records) * len(modes)

    log_progress(
        f"Loading LLaDA backend for {len(records)} samples, "
        f"modes={modes}, total_generations={total_generations}"
    )
    backend = TraceableLLaDABackend(dtype=args.dtype)
    log_progress("LLaDA backend loaded")
    all_matched_rows: list[dict[str, Any]] = []
    parse_records: list[dict[str, Any]] = []
    eval_records: list[dict[str, Any]] = []

    completed_generations = 0
    for sample_index, sample in enumerate(records, start=1):
        sample_id = sample["id"]
        graph = graphs.get(sample_id)
        sample_edges = edges.get(sample_id, [])
        for mode_index, mode in enumerate(modes, start=1):
            generation_index = completed_generations + 1
            pct = (generation_index - 1) / total_generations * 100 if total_generations else 0.0
            log_progress(
                f"Start generation {generation_index}/{total_generations} "
                f"({pct:.1f}% complete): sample {sample_index}/{len(records)} "
                f"{sample_id}, mode {mode_index}/{len(modes)} {mode}"
            )
            messages, functions, goal = build_prompt(sample, mode, args.category)
            result = backend.generate(messages)
            log_progress(
                f"Generated {sample_id} mode={mode}: "
                f"latency={result.latency:.2f}s, "
                f"input_tokens={result.input_tokens}, "
                f"output_tokens={result.output_tokens}"
            )
            raw_record = {
                "question_id": sample_id,
                "mode": mode,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "goal": goal,
                "prompt": messages,
                "n_functions": len(functions),
                "bfcl_function_doc_serialization": os.getenv(
                    "BFCL_FUNCTION_DOC_SERIALIZATION"
                ),
                "raw_response": result.text,
                "latency": result.latency,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "generation_config": result.generation_config,
            }
            write_jsonl(raw_path, raw_record)

            units, parse_error, parse_mode = parse_think_units(result.text)
            log_progress(
                f"Parsed {sample_id} mode={mode}: "
                f"parse_mode={parse_mode}, units={len(units)}, "
                f"parse_error={parse_error or 'none'}"
            )
            parse_record = {
                "question_id": sample_id,
                "mode": mode,
                "parse_mode": parse_mode,
                "parse_error": parse_error,
                "n_units": len(units),
            }
            parse_records.append(parse_record)
            write_jsonl(
                units_path,
                {
                    "question_id": sample_id,
                    "mode": mode,
                    "parse_mode": parse_mode,
                    "parse_error": parse_error,
                    "units": units,
                    "raw_response": result.text,
                },
            )

            for token in result.trace_tokens:
                write_jsonl(
                    conf_path,
                    {
                        "question_id": sample_id,
                        "mode": mode,
                        **token,
                    },
                )

            matched = match_units_to_gold(
                units,
                graph,
                sample_edges,
                available_tools=function_tool_names(functions),
            )
            matched_hop_ids = {
                hop_id
                for unit in matched
                for hop_id in (unit.get("matched_hop_ids") or [])
            }
            n_gold_hops = len(graph.get("hops", [])) if graph else None
            n_compound_actions = sum(
                1 for unit in matched if unit.get("compound_action")
            )
            eval_records.append(
                {
                    "question_id": sample_id,
                    "mode": mode,
                    "n_gold_hops": n_gold_hops,
                    "n_matched_hops": len(matched_hop_ids),
                    "n_units": len(matched),
                    "n_unmatched_units": sum(
                        1 for unit in matched if not (unit.get("matched_hop_ids") or [])
                    ),
                    "n_compound_actions": n_compound_actions,
                }
            )
            log_progress(
                f"Matched {sample_id} mode={mode}: "
                f"matched_hops={len(matched_hop_ids)}/{n_gold_hops}, "
                f"matched_units={sum(1 for unit in matched if unit.get('matched_hop_ids'))}/{len(matched)}, "
                f"compound_actions={n_compound_actions}"
            )
            enriched_rows = []
            for unit in matched:
                start, end = find_unit_span(result.text, unit.get("think", ""))
                stats = token_stats_for_span(result.trace_tokens, start, end)
                action_start, action_end = find_unit_span(
                    result.text, unit.get("raw_action") or unit.get("action_hint") or ""
                )
                action_stats = {
                    f"action_{key}": value
                    for key, value in token_stats_for_span(
                        result.trace_tokens, action_start, action_end
                    ).items()
                }
                gold_label = unit.get("gold_edge_label_summary")
                row = {
                    "question_id": sample_id,
                    "mode": mode,
                    **unit,
                    "parse_mode": parse_mode,
                    "gold_dependency_label": gold_label,
                    "think_char_start": start,
                    "think_char_end": end,
                    "action_char_start": action_start,
                    "action_char_end": action_end,
                    **stats,
                    **action_stats,
                }
                enriched_rows.append(row)
                all_matched_rows.append(row)
            write_jsonl(
                matched_path,
                {
                    "question_id": sample_id,
                    "mode": mode,
                    "rows": enriched_rows,
                },
            )
            completed_generations += 1
            pct = completed_generations / total_generations * 100 if total_generations else 100.0
            log_progress(
                f"Completed generation {completed_generations}/{total_generations} "
                f"({pct:.1f}% complete)"
            )

    metrics = summarize_metrics(
        all_matched_rows,
        parse_records=parse_records,
        eval_records=eval_records,
    )
    metrics["run"] = {
        "category": args.category,
        "ids": [record["id"] for record in records],
        "ids_file": str(ids_file) if ids_file else None,
        "modes": modes,
        "graphs": str(Path(args.graphs).resolve()),
        "edges": str(Path(args.edges).resolve()),
        "bfcl_root": str(bfcl_root),
        "bfcl_function_doc_serialization": os.getenv("BFCL_FUNCTION_DOC_SERIALIZATION"),
        "offline_full_trajectory_planning": True,
        "note": "Graph hops and edges were used only for post-hoc matching/evaluation, not prompt input.",
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(render_summary(metrics), encoding="utf-8")
    log_progress(f"Wrote outputs to {output_dir}")


if __name__ == "__main__":
    main()
