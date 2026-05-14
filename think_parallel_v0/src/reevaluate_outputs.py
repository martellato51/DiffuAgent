from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

    from src.bfcl_data import load_bfcl_records, load_edges, load_graphs
    from src.match_gold import function_tool_names, match_units_to_gold
    from src.metrics import (
        find_unit_span,
        render_summary,
        summarize_metrics,
        token_stats_for_span,
    )
else:
    from .bfcl_data import load_bfcl_records, load_edges, load_graphs
    from .match_gold import function_tool_names, match_units_to_gold
    from .metrics import (
        find_unit_span,
        render_summary,
        summarize_metrics,
        token_stats_for_span,
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-run BFCL think_parallel matching/metrics for an output dir"
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--graphs", default=None)
    parser.add_argument("--edges", default=None)
    parser.add_argument("--bfcl-root", default=None)
    parser.add_argument("--category", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    metrics_path = output_dir / "metrics.json"
    summary_path = output_dir / "summary.md"
    units_path = output_dir / "think_units.jsonl"
    conf_path = output_dir / "token_confidence.jsonl"
    matched_path = output_dir / "matched_units.jsonl"

    old_metrics = (
        json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics_path.exists()
        else {}
    )
    run_meta = dict(old_metrics.get("run", {}))
    category = args.category or run_meta.get("category") or "multi_turn_base"
    graphs_path = Path(args.graphs or run_meta["graphs"]).resolve()
    edges_path = Path(args.edges or run_meta["edges"]).resolve()
    bfcl_root = Path(args.bfcl_root or run_meta["bfcl_root"]).resolve()

    if str(bfcl_root) not in sys.path:
        sys.path.insert(0, str(bfcl_root))

    unit_records = read_jsonl(units_path)
    trace_records = read_jsonl(conf_path) if conf_path.exists() else []
    traces: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for token in trace_records:
        key = (token["question_id"], token["mode"])
        traces.setdefault(key, []).append(token)

    ids = list(dict.fromkeys(record["question_id"] for record in unit_records))
    samples = load_bfcl_records(bfcl_root, category, ids)
    sample_by_id = {sample["id"]: sample for sample in samples}
    graphs = load_graphs(graphs_path)
    edges = load_edges(edges_path)

    matched_path.unlink(missing_ok=True)
    all_matched_rows: list[dict[str, Any]] = []
    parse_records: list[dict[str, Any]] = []
    eval_records: list[dict[str, Any]] = []

    for record in unit_records:
        sample_id = record["question_id"]
        mode = record["mode"]
        sample = sample_by_id.get(sample_id, {})
        graph = graphs.get(sample_id)
        sample_edges = edges.get(sample_id, [])
        trace_tokens = traces.get((sample_id, mode), [])
        raw_response = record.get("raw_response", "")

        units = record.get("units", [])
        matched = match_units_to_gold(
            units,
            graph,
            sample_edges,
            available_tools=function_tool_names(sample.get("function", [])),
        )
        matched_hop_ids = {
            hop_id
            for unit in matched
            for hop_id in (unit.get("matched_hop_ids") or [])
        }
        n_gold_hops = len(graph.get("hops", [])) if graph else None
        parse_records.append(
            {
                "question_id": sample_id,
                "mode": mode,
                "parse_mode": record.get("parse_mode"),
                "parse_error": record.get("parse_error"),
                "n_units": len(units),
            }
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
                "n_compound_actions": sum(
                    1 for unit in matched if unit.get("compound_action")
                ),
            }
        )

        enriched_rows = []
        for unit in matched:
            start, end = find_unit_span(raw_response, unit.get("think", ""))
            stats = token_stats_for_span(trace_tokens, start, end)
            action_start, action_end = find_unit_span(
                raw_response,
                unit.get("raw_action") or unit.get("action_hint") or "",
            )
            action_stats = {
                f"action_{key}": value
                for key, value in token_stats_for_span(
                    trace_tokens, action_start, action_end
                ).items()
            }
            gold_label = unit.get("gold_edge_label_summary")
            row = {
                "question_id": sample_id,
                "mode": mode,
                **unit,
                "parse_mode": record.get("parse_mode"),
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

    metrics = summarize_metrics(
        all_matched_rows,
        parse_records=parse_records,
        eval_records=eval_records,
    )
    run_meta.update(
        {
            "category": category,
            "ids": ids,
            "graphs": str(graphs_path),
            "edges": str(edges_path),
            "bfcl_root": str(bfcl_root),
            "reevaluated_at": datetime.now().isoformat(timespec="seconds"),
            "matcher": "lenient_tool_coverage_with_compound_action_diagnostic",
        }
    )
    metrics["run"] = run_meta
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(render_summary(metrics), encoding="utf-8")
    print(f"Reevaluated outputs in {output_dir}")


if __name__ == "__main__":
    main()
