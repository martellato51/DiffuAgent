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

    from src.bfcl_data import load_bfcl_records
    from src.llada_trace import TraceableLLaDABackend
    from src.parse_units import parse_think_units
    from src.prompt_builder import SUPPORTED_MODES, build_prompt
else:
    from .bfcl_data import load_bfcl_records
    from .llada_trace import TraceableLLaDABackend
    from .parse_units import parse_think_units
    from .prompt_builder import SUPPORTED_MODES, build_prompt


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


def render_summary(metrics: dict[str, Any]) -> str:
    parse = metrics["parse"]
    run = metrics["run"]
    return "\n".join(
        [
            "# think_parallel_v1 generation summary",
            "",
            "## Run",
            "",
            f"- category: `{run['category']}`",
            f"- modes: `{', '.join(run['modes'])}`",
            f"- n_samples: `{run['n_samples']}`",
            f"- output_dir: `{run['output_dir']}`",
            f"- bfcl_function_doc_serialization: `{run.get('bfcl_function_doc_serialization')}`",
            "",
            "## Parse",
            "",
            f"- total_generations: `{parse['total_generations']}`",
            f"- parsed_generations: `{parse['parsed_generations']}`",
            f"- format_parse_rate: `{parse['format_parse_rate']:.3f}`",
            f"- total_units: `{parse['total_units']}`",
            f"- mean_units_per_generation: `{parse['mean_units_per_generation']:.2f}`",
            "",
            "Judge matching has not been run yet. Run:",
            "",
            "```bash",
            f"bash think_parallel_v1/scripts/run_judge_matching.sh {run['output_dir']}",
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BFCL LLaDA exact-name A-only discovery")
    parser.add_argument("--ids", default=None, help="Comma-separated BFCL ids")
    parser.add_argument(
        "--ids-file",
        default=None,
        help="JSON object mapping BFCL categories to id lists. Ignored when --ids is set.",
    )
    parser.add_argument("--category", default="multi_turn_base")
    parser.add_argument("--mode", default="exact_name_a", choices=sorted(SUPPORTED_MODES))
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
    metrics_path = output_dir / "generation_metrics.json"
    summary_path = output_dir / "summary.md"
    for path in [raw_path, units_path, conf_path]:
        path.unlink(missing_ok=True)

    ids = split_ids(args.ids)
    ids_file = Path(args.ids_file).resolve() if args.ids_file else None
    if ids is None and ids_file is not None:
        ids = load_ids_from_file(ids_file, args.category)

    records = load_bfcl_records(bfcl_root, args.category, ids)
    modes = [args.mode]
    total_generations = len(records) * len(modes)

    log_progress(
        f"Loading LLaDA backend for {len(records)} samples, "
        f"modes={modes}, total_generations={total_generations}"
    )
    backend = TraceableLLaDABackend(dtype=args.dtype)
    log_progress("LLaDA backend loaded")

    parse_records: list[dict[str, Any]] = []
    completed_generations = 0
    for sample_index, sample in enumerate(records, start=1):
        sample_id = sample["id"]
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
            log_progress(
                f"Parsed {sample_id} mode={mode}: "
                f"parse_mode={parse_mode}, units={len(units)}, "
                f"parse_error={parse_error or 'none'}"
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

            completed_generations += 1
            pct = completed_generations / total_generations * 100 if total_generations else 100.0
            log_progress(
                f"Completed generation {completed_generations}/{total_generations} "
                f"({pct:.1f}% complete)"
            )

    parsed_generations = sum(1 for row in parse_records if row["parse_mode"] != "failed")
    total_units = sum(row["n_units"] for row in parse_records)
    metrics = {
        "run": {
            "category": args.category,
            "ids": [record["id"] for record in records],
            "ids_file": str(ids_file) if ids_file else None,
            "modes": modes,
            "bfcl_root": str(bfcl_root),
            "bfcl_data_sources": sorted(
                {
                    str(record.get("_bfcl_data_source"))
                    for record in records
                    if record.get("_bfcl_data_source")
                }
            ),
            "bfcl_function_doc_sources": sorted(
                {
                    source
                    for record in records
                    for source in record.get("_bfcl_function_doc_sources", [])
                }
            ),
            "output_dir": str(output_dir),
            "bfcl_function_doc_serialization": os.getenv("BFCL_FUNCTION_DOC_SERIALIZATION"),
            "offline_full_trajectory_planning": True,
            "n_samples": len(records),
            "note": "Gold graph hops are not used during generation. Judge matching is post-hoc.",
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
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(render_summary(metrics), encoding="utf-8")
    log_progress(f"Wrote outputs to {output_dir}")


if __name__ == "__main__":
    main()
