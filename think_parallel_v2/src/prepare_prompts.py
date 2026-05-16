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

    from src.prompt_builder import SUPPORTED_MODES, normalize_mode
    from src.run_discovery import (
        DEFAULT_BFCL_ROOT,
        DEFAULT_GRAPHS_PATH,
        _prepare_prompt_rows,
        log_progress,
        write_jsonl,
    )
else:
    from .prompt_builder import SUPPORTED_MODES, normalize_mode
    from .run_discovery import (
        DEFAULT_BFCL_ROOT,
        DEFAULT_GRAPHS_PATH,
        _prepare_prompt_rows,
        log_progress,
        write_jsonl,
    )


DEFAULT_PREPARED_PROMPTS = (
    "/home/ilju/research/DiffuAgent/think_parallel_v2/prepared/"
    "multi_turn_base_intra_turn_parallel_prompts.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare static BFCL multi-turn prompts for think_parallel_v2"
    )
    parser.add_argument("--category", default="multi_turn_base")
    parser.add_argument("--mode", default="llmcompiler_plan", choices=sorted(SUPPORTED_MODES))
    parser.add_argument("--ids", default=None, help="Comma-separated BFCL ids")
    parser.add_argument("--ids-file", default=None, help="JSON list or object keyed by category")
    parser.add_argument("--graphs-path", default=DEFAULT_GRAPHS_PATH)
    parser.add_argument(
        "--episode-filter",
        default="intra_turn_parallel",
        choices=["all", "graph_available", "intra_turn_parallel", "multi_hop"],
    )
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument("--bfcl-root", default=os.getenv("BFCL_ROOT", DEFAULT_BFCL_ROOT))
    parser.add_argument(
        "--prepared-prompts-path",
        default=DEFAULT_PREPARED_PROMPTS,
        help="Output JSONL containing one prepared prompt row per episode turn",
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Output episode manifest JSONL. Defaults to <prepared-prompts-stem>_manifest.jsonl",
    )
    parser.add_argument(
        "--metrics-path",
        default=None,
        help="Output preparation metrics JSON. Defaults to <prepared-prompts-stem>_metrics.json",
    )
    parser.add_argument(
        "--allow-gold-replay-errors",
        action="store_true",
        help="Write replay-error observations instead of failing when BFCL gold tool replay raises",
    )
    return parser.parse_args()


def _default_sibling(path: Path, suffix: str) -> Path:
    return path.with_name(path.stem + suffix)


def main() -> None:
    args = parse_args()
    mode = normalize_mode(args.mode)
    bfcl_root = Path(args.bfcl_root).resolve()
    prepared_path = Path(args.prepared_prompts_path).resolve()
    manifest_path = (
        Path(args.manifest_path).resolve()
        if args.manifest_path
        else _default_sibling(prepared_path, "_manifest.jsonl")
    )
    metrics_path = (
        Path(args.metrics_path).resolve()
        if args.metrics_path
        else _default_sibling(prepared_path, "_metrics.json")
    )
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    prepared_path.unlink(missing_ok=True)
    manifest_path.unlink(missing_ok=True)

    rows, manifests, graphs_path, ids_file = _prepare_prompt_rows(args, bfcl_root)
    config: dict[str, Any] = {
        "_config": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "category": args.category,
            "mode": mode,
            "bfcl_root": str(bfcl_root),
            "graphs_path": str(graphs_path) if graphs_path else None,
            "episode_filter": args.episode_filter,
            "ids_file": str(ids_file) if ids_file else None,
            "max_episodes": args.max_episodes,
            "allow_gold_replay_errors": args.allow_gold_replay_errors,
            "note": "Static prompts only. Current-turn gold calls are metadata, not model input.",
        }
    }
    write_jsonl(prepared_path, config)
    for row in rows:
        write_jsonl(prepared_path, row)
    write_jsonl(manifest_path, config)
    for manifest in manifests:
        write_jsonl(manifest_path, manifest)

    metrics = {
        "prepared_prompts_path": str(prepared_path),
        "manifest_path": str(manifest_path),
        "category": args.category,
        "mode": mode,
        "graphs_path": str(graphs_path) if graphs_path else None,
        "episode_filter": args.episode_filter,
        "n_episodes": len({row["question_id"] for row in rows}),
        "n_turn_prompts": len(rows),
        "n_gold_calls": sum(len(row.get("gold_calls", [])) for row in rows),
        "has_replay_error_observation": any(
            "Error during gold replay:" in str(obs)
            for row in rows
            for obs in row.get("gold_observations", [])
        ),
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    log_progress(
        f"Wrote {len(rows)} prepared turn prompts for "
        f"{metrics['n_episodes']} episodes to {prepared_path}"
    )


if __name__ == "__main__":
    main()
