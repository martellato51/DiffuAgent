from __future__ import annotations

import argparse
import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

    from src.bfcl_data import (
        load_ids_from_file,
        load_multiturn_episodes,
        replay_gold_observations,
    )
    from src.llada_backend import load_traceable_llada_backend
    from src.parse_plan import parse_llmcompiler_plan
    from src.prompt_builder import SUPPORTED_MODES, build_prompt, normalize_mode
    from src.state_view import (
        StateViewConfig,
        build_turn_state_views,
        normalize_state_view_mode,
    )
else:
    from .bfcl_data import (
        load_ids_from_file,
        load_multiturn_episodes,
        replay_gold_observations,
    )
    from .llada_backend import load_traceable_llada_backend
    from .parse_plan import parse_llmcompiler_plan
    from .prompt_builder import SUPPORTED_MODES, build_prompt, normalize_mode
    from .state_view import (
        StateViewConfig,
        build_turn_state_views,
        normalize_state_view_mode,
    )


DEFAULT_BFCL_ROOT = (
    "/home/ilju/research/DiffuAgent/unified_envs/gorilla_bfcl_v3/"
    "berkeley-function-call-leaderboard"
)
DEFAULT_GRAPHS_PATH = (
    "/home/ilju/research/ParallelAgent/data/annotations/"
    "bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl"
)


def split_ids(value: str | None) -> list[str] | None:
    if value is None or value.strip() == "":
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def write_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


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


def _selected_ids(args: argparse.Namespace) -> tuple[set[str] | None, Path | None]:
    ids = split_ids(args.ids)
    ids_file = Path(args.ids_file).resolve() if args.ids_file else None
    if ids is None and ids_file is not None:
        ids = load_ids_from_file(ids_file, args.category)
    return set(ids) if ids is not None else None, ids_file


def _filter_prompt_rows_by_ids(
    rows: list[dict[str, Any]],
    selected_ids: set[str] | None,
) -> list[dict[str, Any]]:
    if selected_ids is None:
        return rows
    return [row for row in rows if row.get("question_id") in selected_ids]


REF_PATTERN = re.compile(r"\$\{?\d+\}?(?:\.[A-Za-z_][A-Za-z0-9_]*)?")
GOLD_TOOL_PATTERN = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def _function_schema_map(functions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for function in functions:
        name = function.get("name")
        if not name:
            continue
        parameters = function.get("parameters") or {}
        response = function.get("response") or {}
        schemas[name] = {
            "parameters": parameters,
            "response": response,
        }
    return schemas


def _extract_call_keywords(args_text: str) -> tuple[set[str], int | None, str | None]:
    sanitized = REF_PATTERN.sub('"__CURRENT_PLAN_REF__"', args_text)
    try:
        parsed = ast.parse(f"_f({sanitized})", mode="eval")
    except SyntaxError as exc:
        return set(), None, f"syntax_error: {exc.msg}"
    if not isinstance(parsed.body, ast.Call):
        return set(), None, "not_call"
    keywords = {kw.arg for kw in parsed.body.keywords if kw.arg is not None}
    return keywords, len(parsed.body.args), None


def _schema_quality(
    units: list[dict[str, Any]],
    function_schemas: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if not function_schemas:
        return {
            "schema_checked": False,
            "schema_valid_units": None,
            "schema_invalid_units": None,
            "schema_errors": [],
        }

    valid = 0
    errors: list[dict[str, Any]] = []
    for unit in units:
        tool_name = unit.get("tool_name")
        schema = function_schemas.get(tool_name)
        if not schema:
            errors.append(
                {
                    "unit_id": unit.get("unit_id"),
                    "tool_name": tool_name,
                    "error": "missing_tool_schema",
                }
            )
            continue
        params = schema.get("parameters") or {}
        properties = params.get("properties") or {}
        allowed = set(properties.keys())
        required = set(params.get("required") or [])
        keywords, n_positional, parse_error = _extract_call_keywords(
            unit.get("args_text") or ""
        )
        unit_errors: list[str] = []
        if parse_error:
            unit_errors.append(parse_error)
        if n_positional:
            unit_errors.append("positional_args_not_schema_checked")
        missing = sorted(required - keywords)
        unknown = sorted(keywords - allowed)
        if missing:
            unit_errors.append("missing_required: " + ", ".join(missing))
        if unknown:
            unit_errors.append("unknown_parameters: " + ", ".join(unknown))
        if unit_errors:
            errors.append(
                {
                    "unit_id": unit.get("unit_id"),
                    "tool_name": tool_name,
                    "error": "; ".join(unit_errors),
                }
            )
        else:
            valid += 1

    return {
        "schema_checked": True,
        "schema_valid_units": valid,
        "schema_invalid_units": len(units) - valid,
        "schema_errors": errors,
    }


def _tool_name(call: str) -> str | None:
    match = GOLD_TOOL_PATTERN.match(call)
    return match.group(1) if match else None


def _quality_metrics(
    units: list[dict[str, Any]],
    prompt_record: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    mode = normalize_mode(mode)
    action_texts = [
        (unit.get("raw_action") or "").split(".", 1)[-1].strip() for unit in units
    ]
    duplicate_actions = len(action_texts) - len(set(action_texts))
    gold_calls = prompt_record.get("gold_calls", [])
    gold_tools = [_tool_name(call) for call in gold_calls]
    generated_tools = [unit.get("tool_name") for unit in units]
    valid_tool_name_units = sum(1 for unit in units if unit.get("is_valid_tool"))
    invalid_tool_name_units = sum(
        1 for unit in units if not unit.get("is_valid_tool")
    )
    invalid_tool_names = sorted(
        {
            unit.get("tool_name")
            for unit in units
            if not unit.get("is_valid_tool") and unit.get("tool_name")
        }
    )
    schema_quality = _schema_quality(
        units, prompt_record.get("function_schemas")
    )
    dependency_edge_count = sum(
        len(unit.get("dependencies") or []) for unit in units
    )
    flat_reference_violation_count = (
        dependency_edge_count if mode == "llmcompiler_flat_plan" else 0
    )
    return {
        "valid_tool_name_units": valid_tool_name_units,
        "invalid_tool_name_units": invalid_tool_name_units,
        "invalid_tool_names": invalid_tool_names,
        "duplicate_action_count": duplicate_actions,
        "has_duplicate_actions": duplicate_actions > 0,
        "generated_gold_call_delta": len(units) - len(gold_calls),
        "is_over_generated_vs_gold": len(units) > len(gold_calls),
        "gold_tool_names": gold_tools,
        "generated_tool_names": generated_tools,
        "dependency_edge_count": dependency_edge_count,
        "flat_reference_violation_count": flat_reference_violation_count,
        "has_flat_reference_violation": flat_reference_violation_count > 0,
        **schema_quality,
        "note": "valid_tool_name_units only checks whether the tool name is provided; it is not gold correctness.",
    }


def _aggregate_quality(parse_records: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [record.get("quality_metrics") or {} for record in parse_records]
    schema_checked = [item for item in metrics if item.get("schema_checked")]
    return {
        "valid_tool_name_units": sum(
            int(item.get("valid_tool_name_units") or 0) for item in metrics
        ),
        "invalid_tool_name_units": sum(
            int(item.get("invalid_tool_name_units") or 0) for item in metrics
        ),
        "schema_checked_generations": len(schema_checked),
        "schema_valid_units": sum(
            int(item.get("schema_valid_units") or 0) for item in schema_checked
        ),
        "schema_invalid_units": sum(
            int(item.get("schema_invalid_units") or 0) for item in schema_checked
        ),
        "duplicate_action_generations": sum(
            1 for item in metrics if item.get("has_duplicate_actions")
        ),
        "duplicate_action_count": sum(
            int(item.get("duplicate_action_count") or 0) for item in metrics
        ),
        "over_generated_vs_gold_generations": sum(
            1 for item in metrics if item.get("is_over_generated_vs_gold")
        ),
        "dependency_edge_count": sum(
            int(item.get("dependency_edge_count") or 0) for item in metrics
        ),
        "flat_reference_violation_generations": sum(
            1 for item in metrics if item.get("has_flat_reference_violation")
        ),
        "flat_reference_violation_count": sum(
            int(item.get("flat_reference_violation_count") or 0)
            for item in metrics
        ),
        "note": (
            "These are post-hoc diagnostics. Tool-name validity, schema validity, "
            "compactness, and gold/DAG alignment should be interpreted separately."
        ),
    }


def log_progress(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"[progress {timestamp}] {message}", flush=True)


def render_summary(metrics: dict[str, Any]) -> str:
    run = metrics["run"]
    parse = metrics["parse"]
    quality = metrics.get("quality", {})
    return "\n".join(
        [
            "# think_parallel_v2 generation summary",
            "",
            "## Run",
            "",
            f"- category: `{run['category']}`",
            f"- mode: `{run['mode']}`",
            f"- n_episodes: `{run['n_episodes']}`",
            f"- n_turn_generations: `{run['n_turn_generations']}`",
            f"- episode_filter: `{run['episode_filter']}`",
            f"- dry_run: `{run['dry_run']}`",
            f"- output_dir: `{run['output_dir']}`",
            "",
            "## Parse",
            "",
            f"- total_generations: `{parse['total_generations']}`",
            f"- parsed_generations: `{parse['parsed_generations']}`",
            f"- format_parse_rate: `{parse['format_parse_rate']:.3f}`",
            f"- total_units: `{parse['total_units']}`",
            f"- mean_units_per_generation: `{parse['mean_units_per_generation']:.2f}`",
            "",
            "## Quality Diagnostics",
            "",
            "- `valid_tool_name_units` checks provided tool names only; it is not gold correctness.",
            f"- valid_tool_name_units: `{quality.get('valid_tool_name_units', 0)}`",
            f"- invalid_tool_name_units: `{quality.get('invalid_tool_name_units', 0)}`",
            f"- schema_checked_generations: `{quality.get('schema_checked_generations', 0)}`",
            f"- schema_valid_units: `{quality.get('schema_valid_units', 0)}`",
            f"- duplicate_action_generations: `{quality.get('duplicate_action_generations', 0)}`",
            f"- over_generated_vs_gold_generations: `{quality.get('over_generated_vs_gold_generations', 0)}`",
            f"- dependency_edge_count: `{quality.get('dependency_edge_count', 0)}`",
            f"- flat_reference_violation_generations: `{quality.get('flat_reference_violation_generations', 0)}`",
            f"- flat_reference_violation_count: `{quality.get('flat_reference_violation_count', 0)}`",
            "",
            "Gold graph matching and denoising analyses are post-hoc steps.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BFCL multi_turn_base LLMCompiler-style DLM planning diagnostic"
    )
    parser.add_argument("--category", default="multi_turn_base")
    parser.add_argument("--mode", default="llmcompiler_plan", choices=sorted(SUPPORTED_MODES))
    parser.add_argument("--ids", default=None, help="Comma-separated BFCL ids")
    parser.add_argument("--ids-file", default=None, help="JSON list or object keyed by category")
    parser.add_argument("--graphs-path", default=DEFAULT_GRAPHS_PATH)
    parser.add_argument("--episode-filter", default="all", choices=["all", "graph_available", "intra_turn_parallel", "multi_hop"])
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument(
        "--prepared-prompts-path",
        default=None,
        help="Read already prepared turn prompts and skip BFCL/graph/gold-observation preprocessing",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bfcl-root", default=os.getenv("BFCL_ROOT", DEFAULT_BFCL_ROOT))
    parser.add_argument("--dtype", default=os.getenv("LLADA_DTYPE", "bfloat16"))
    parser.add_argument("--dry-run", action="store_true", help="Build prompts and gold context without loading LLaDA")
    parser.add_argument(
        "--state-view",
        default=os.getenv("THINK_PARALLEL_STATE_VIEW", "tree"),
        choices=["none", "tree", "raw"],
        help="Deterministic current-environment state view inserted before the current turn",
    )
    parser.add_argument(
        "--state-view-include-file-content",
        action="store_true",
        help="Include truncated file content in the deterministic state view",
    )
    parser.add_argument("--state-view-max-depth", type=int, default=6)
    parser.add_argument("--state-view-max-entries", type=int, default=200)
    parser.add_argument("--state-view-max-chars", type=int, default=6000)
    parser.add_argument("--state-view-max-file-chars", type=int, default=300)
    parser.add_argument(
        "--allow-gold-replay-errors",
        action="store_true",
        help="Write replay-error observations instead of failing when BFCL gold tool replay raises",
    )
    return parser.parse_args()


def _manifest_from_prompt_rows(rows: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["question_id"], []).append(row)
    manifests: list[dict[str, Any]] = []
    for question_id, group in grouped.items():
        group = sorted(group, key=lambda item: item.get("turn_index", 0))
        graph_stats = [row.get("graph_stats") or {} for row in group]
        manifests.append(
            {
                "question_id": question_id,
                "category": category,
                "n_turns": len(group),
                "n_gold_calls": sum(len(row.get("gold_calls", [])) for row in group),
                "has_graph": any(stats.get("has_graph") for stats in graph_stats),
                "prepared_prompt_source": True,
            }
        )
    return manifests


def _prepare_prompt_rows(args: argparse.Namespace, bfcl_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Path | None, Path | None]:
    mode = normalize_mode(args.mode)
    state_view_mode = normalize_state_view_mode(getattr(args, "state_view", "tree"))
    state_view_config = StateViewConfig(
        mode=state_view_mode,
        include_file_content=bool(getattr(args, "state_view_include_file_content", False)),
        max_depth=int(getattr(args, "state_view_max_depth", 6)),
        max_entries=int(getattr(args, "state_view_max_entries", 200)),
        max_chars=int(getattr(args, "state_view_max_chars", 6000)),
        max_file_chars=int(getattr(args, "state_view_max_file_chars", 300)),
    )
    selected_ids, ids_file = _selected_ids(args)

    graphs_path = Path(args.graphs_path).resolve() if args.graphs_path else None
    episodes = load_multiturn_episodes(
        bfcl_root,
        args.category,
        ids=sorted(selected_ids) if selected_ids is not None else None,
        graphs_path=graphs_path,
        episode_filter=args.episode_filter,
        max_episodes=args.max_episodes,
    )
    if not episodes:
        raise ValueError("No episodes selected")

    run_label = datetime.now().strftime("%Y%m%d_%H%M%S")
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for episode in episodes:
        replay_gold_observations(
            bfcl_root,
            episode,
            run_label=run_label,
            strict=not args.allow_gold_replay_errors,
        )
        state_views = build_turn_state_views(
            bfcl_root,
            episode,
            run_label=run_label,
            config=state_view_config,
            strict=not args.allow_gold_replay_errors,
        )
        graph = episode.get("graph")
        manifests.append(
            {
                "question_id": episode["id"],
                "category": args.category,
                "n_turns": len(episode["turns"]),
                "n_gold_calls": sum(len(turn["gold_calls"]) for turn in episode["turns"]),
                "has_graph": graph is not None,
                "graph_summary": {
                    key: graph.get(key)
                    for key in [
                        "n_hops",
                        "critical_path",
                        "parallel_width",
                        "turn_bound_max_width",
                        "n_intra_turn_antichain_pairs",
                    ]
                }
                if graph
                else None,
            }
        )
        for turn, state_view in zip(episode["turns"], state_views, strict=True):
            messages, functions, current_goal = build_prompt(
                bfcl_root,
                episode,
                turn,
                mode,
                args.category,
                state_view=state_view,
            )
            rows.append(
                {
                    "question_id": episode["id"],
                    "turn_index": turn["turn_index"],
                    "mode": mode,
                    "current_goal": current_goal,
                    "prompt": messages,
                    "state_view_mode": state_view_mode,
                    "state_view": state_view,
                    "state_view_config": {
                        "include_file_content": state_view_config.include_file_content,
                        "max_depth": state_view_config.max_depth,
                        "max_entries": state_view_config.max_entries,
                        "max_chars": state_view_config.max_chars,
                        "max_file_chars": state_view_config.max_file_chars,
                    },
                    "state_view_replay_turn_index": turn["turn_index"],
                    "state_view_replay_uses_gold_previous_turns": True,
                    "n_functions": len(functions),
                    "function_names": [
                        func.get("name") for func in functions if func.get("name")
                    ],
                    "function_schemas": _function_schema_map(functions),
                    "gold_calls": turn["gold_calls"],
                    "gold_observations": turn.get("gold_observations", []),
                    "graph_stats": turn["graph_stats"],
                }
            )
    return rows, manifests, graphs_path, ids_file


def main() -> None:
    args = parse_args()
    run_mode = normalize_mode(args.mode)
    bfcl_root = Path(args.bfcl_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "raw_generations.jsonl"
    units_path = output_dir / "plan_units.jsonl"
    conf_path = output_dir / "token_confidence.jsonl"
    prompts_path = output_dir / "prompts.jsonl"
    manifest_path = output_dir / "episode_manifest.jsonl"
    metrics_path = output_dir / "generation_metrics.json"
    summary_path = output_dir / "summary.md"
    for path in [raw_path, units_path, conf_path, prompts_path, manifest_path]:
        path.unlink(missing_ok=True)

    prepared_prompts_path = (
        Path(args.prepared_prompts_path).resolve()
        if args.prepared_prompts_path
        else None
    )
    if prepared_prompts_path:
        prompt_rows = read_jsonl(prepared_prompts_path)
        selected_ids, ids_file = _selected_ids(args)
        before_filter = len(prompt_rows)
        prompt_rows = _filter_prompt_rows_by_ids(prompt_rows, selected_ids)
        if not prompt_rows:
            suffix = (
                f" after ids filter: {sorted(selected_ids)}"
                if selected_ids is not None
                else ""
            )
            raise ValueError(f"No prompt rows in {prepared_prompts_path}{suffix}")
        manifests = _manifest_from_prompt_rows(prompt_rows, args.category)
        graphs_path = None
        if selected_ids is None:
            log_progress(
                f"Loaded {len(prompt_rows)} prepared turn prompts from {prepared_prompts_path}"
            )
        else:
            log_progress(
                f"Loaded {len(prompt_rows)}/{before_filter} prepared turn prompts "
                f"from {prepared_prompts_path} after ids filter"
            )
    else:
        prompt_rows, manifests, graphs_path, ids_file = _prepare_prompt_rows(args, bfcl_root)
        log_progress(
            f"Prepared {len(prompt_rows)} turn prompts from BFCL/graph inputs; "
            f"filter={args.episode_filter}"
        )

    total_turns = len(prompt_rows)
    n_episodes = len({row["question_id"] for row in prompt_rows})
    row_modes = {
        normalize_mode(row.get("mode") or args.mode)
        for row in prompt_rows
    }
    if len(row_modes) == 1:
        run_mode = next(iter(row_modes))
    for manifest in manifests:
        write_jsonl(manifest_path, manifest)

    backend = None
    if not args.dry_run:
        log_progress("Loading LLaDA backend")
        backend_cls = load_traceable_llada_backend()
        backend = backend_cls(dtype=args.dtype)
        log_progress("LLaDA backend loaded")

    parse_records: list[dict[str, Any]] = []
    completed = 0
    for prompt_record in prompt_rows:
        sample_id = prompt_record["question_id"]
        turn_index = int(prompt_record.get("turn_index", 0))
        mode = normalize_mode(prompt_record.get("mode") or args.mode)
        generation_index = completed + 1
        log_progress(
            f"Start turn generation {generation_index}/{total_turns}: "
            f"{sample_id} turn={turn_index + 1}"
        )
        messages = prompt_record["prompt"]
        current_goal = prompt_record.get("current_goal", "")
        valid_tools = set(prompt_record.get("function_names") or [])
        write_jsonl(prompts_path, prompt_record)

        if args.dry_run:
            raw_response = ""
            result_payload = {
                "latency": None,
                "input_tokens": None,
                "output_tokens": None,
                "generation_config": None,
                "trace_tokens": [],
            }
        else:
            assert backend is not None
            result = backend.generate(messages)
            raw_response = result.text
            result_payload = {
                "latency": result.latency,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "generation_config": result.generation_config,
                "trace_tokens": result.trace_tokens,
            }
            log_progress(
                f"Generated {sample_id} turn={turn_index + 1}: "
                f"latency={result.latency:.2f}s, "
                f"input_tokens={result.input_tokens}, output_tokens={result.output_tokens}"
            )

        raw_record = {
            "question_id": sample_id,
            "turn_index": turn_index,
            "mode": mode,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "current_goal": current_goal,
            "state_view_mode": prompt_record.get("state_view_mode", "unknown"),
            "state_view": prompt_record.get("state_view", ""),
            "state_view_config": prompt_record.get("state_view_config"),
            "gold_calls": prompt_record.get("gold_calls", []),
            "gold_observations": prompt_record.get("gold_observations", []),
            "graph_stats": prompt_record.get("graph_stats"),
            "prompt": messages,
            "n_functions": prompt_record.get("n_functions"),
            "bfcl_function_doc_serialization": os.getenv("BFCL_FUNCTION_DOC_SERIALIZATION"),
            "raw_response": raw_response,
            **{k: v for k, v in result_payload.items() if k != "trace_tokens"},
        }
        write_jsonl(raw_path, raw_record)

        if args.dry_run:
            units, parse_error, parse_mode = [], None, "dry_run"
        else:
            units, parse_error, parse_mode = parse_llmcompiler_plan(
                raw_response, valid_tools=valid_tools or None
            )
        parse_record = {
            "question_id": sample_id,
            "turn_index": turn_index,
            "mode": mode,
            "parse_mode": parse_mode,
            "parse_error": parse_error,
            "n_units": len(units),
            "gold_n_calls": len(prompt_record.get("gold_calls", [])),
            "graph_stats": prompt_record.get("graph_stats"),
        }
        quality_metrics = _quality_metrics(units, prompt_record, mode)
        parse_record["quality_metrics"] = quality_metrics
        parse_records.append(parse_record)
        write_jsonl(
            units_path,
            {
                **parse_record,
                "units": units,
                "raw_response": raw_response,
            },
        )
        for token in result_payload["trace_tokens"]:
            write_jsonl(
                conf_path,
                {
                    "question_id": sample_id,
                    "turn_index": turn_index,
                    "mode": mode,
                    **token,
                },
            )
        completed += 1
        log_progress(
            f"Parsed {sample_id} turn={turn_index + 1}: "
            f"parse_mode={parse_mode}, units={len(units)}, "
            f"parse_error={parse_error or 'none'}"
        )

    parsed_generations = sum(1 for row in parse_records if row["parse_mode"] != "failed")
    total_units = sum(row["n_units"] for row in parse_records)
    metrics = {
        "run": {
            "category": args.category,
            "mode": run_mode,
            "ids": sorted({row["question_id"] for row in prompt_rows}),
            "prepared_prompts_path": str(prepared_prompts_path) if prepared_prompts_path else None,
            "ids_file": str(ids_file) if ids_file else None,
            "graphs_path": str(graphs_path) if graphs_path else None,
            "episode_filter": "prepared" if prepared_prompts_path else args.episode_filter,
            "bfcl_root": str(bfcl_root),
            "output_dir": str(output_dir),
            "dry_run": args.dry_run,
            "allow_gold_replay_errors": args.allow_gold_replay_errors,
            "state_view_modes": sorted(
                {
                    str(row.get("state_view_mode", "missing"))
                    for row in prompt_rows
                }
            ),
            "n_episodes": n_episodes,
            "n_turn_generations": len(parse_records),
            "note": "Gold graph hops are not used during generation. Graph data is for post-hoc analysis.",
        },
        "parse": {
            "total_generations": len(parse_records),
            "parsed_generations": parsed_generations,
            "format_parse_rate": parsed_generations / len(parse_records)
            if parse_records
            else 0.0,
            "total_units": total_units,
            "mean_units_per_generation": total_units / len(parse_records)
            if parse_records
            else 0.0,
            "records": parse_records,
        },
        "quality": _aggregate_quality(parse_records),
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(render_summary(metrics), encoding="utf-8")
    log_progress(f"Wrote outputs to {output_dir}")


if __name__ == "__main__":
    main()
