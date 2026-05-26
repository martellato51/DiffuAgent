from __future__ import annotations

import copy
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bfcl_data import ensure_bfcl_on_path


SUPPORTED_STATE_VIEW_MODES = {"none", "tree", "raw"}


@dataclass(frozen=True)
class StateViewConfig:
    mode: str = "tree"
    include_file_content: bool = False
    max_depth: int = 6
    max_entries: int = 200
    max_chars: int = 6000
    max_file_chars: int = 300


def normalize_state_view_mode(mode: str | None) -> str:
    value = (mode or "tree").strip().lower()
    if value not in SUPPORTED_STATE_VIEW_MODES:
        expected = ", ".join(sorted(SUPPORTED_STATE_VIEW_MODES))
        raise ValueError(f"Unsupported state view mode: {mode!r}; expected one of {expected}")
    return value


def _safe_model_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    return value.strip("_") or "state_view"


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...<state_view_truncated>"


def _is_directory(value: Any) -> bool:
    return hasattr(value, "contents") and isinstance(getattr(value, "contents"), dict)


def _is_file(value: Any) -> bool:
    return hasattr(value, "content") and not _is_directory(value)


def _cwd_path(filesystem: Any) -> str:
    current = getattr(filesystem, "_current_dir", None)
    root = getattr(filesystem, "root", None)
    if current is None:
        return "<unknown>"
    names: list[str] = []
    cursor = current
    while cursor is not None:
        name = getattr(cursor, "name", None)
        if name:
            names.append(str(name))
        if cursor is root:
            break
        cursor = getattr(cursor, "parent", None)
    return "/" + "/".join(reversed(names))


def _render_directory_tree(
    directory: Any,
    *,
    depth: int,
    config: StateViewConfig,
    counter: list[int],
) -> list[str]:
    if depth >= config.max_depth:
        return ["  " * depth + "...<max_depth_reached>"]

    contents = getattr(directory, "contents", {}) or {}
    lines: list[str] = []
    for name in sorted(contents):
        if counter[0] >= config.max_entries:
            lines.append("  " * depth + "...<max_entries_reached>")
            break
        counter[0] += 1
        item = contents[name]
        prefix = "  " * depth
        if _is_directory(item):
            lines.append(f"{prefix}- {name}/")
            lines.extend(
                _render_directory_tree(
                    item,
                    depth=depth + 1,
                    config=config,
                    counter=counter,
                )
            )
        elif _is_file(item):
            if config.include_file_content:
                content = str(getattr(item, "content", ""))
                if len(content) > config.max_file_chars:
                    content = content[: config.max_file_chars] + "...<truncated>"
                lines.append(f"{prefix}- {name}: {json.dumps(content, ensure_ascii=False)}")
            else:
                lines.append(f"{prefix}- {name}")
        else:
            lines.append(f"{prefix}- {name}: {repr(item)}")
    if not lines:
        lines.append("  " * depth + "- <empty>")
    return lines


def _render_gorilla_filesystem(instance: Any, config: StateViewConfig) -> str:
    lines = [
        "GorillaFileSystem:",
        f"cwd: {_cwd_path(instance)}",
        "tree:",
    ]
    root = getattr(instance, "root", None)
    if root is None:
        lines.append("- <missing root>")
        return "\n".join(lines)
    root_name = getattr(root, "name", "root")
    lines.append(f"- {root_name}/")
    lines.extend(
        _render_directory_tree(
            root,
            depth=1,
            config=config,
            counter=[0],
        )
    )
    return "\n".join(lines)


def _jsonable(value: Any, *, max_depth: int = 5) -> Any:
    if max_depth <= 0:
        return repr(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(item, max_depth=max_depth - 1) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item, max_depth=max_depth - 1) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item, max_depth=max_depth - 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if _is_directory(value) or _is_file(value):
        return repr(value)
    attrs = {
        key: item
        for key, item in vars(value).items()
        if not key.startswith("_")
    } if hasattr(value, "__dict__") else {}
    if attrs:
        return _jsonable(attrs, max_depth=max_depth - 1)
    return repr(value)


def _render_generic_class(class_name: str, instance: Any) -> str:
    attrs = {
        key: value
        for key, value in vars(instance).items()
        if not key.startswith("_")
    } if hasattr(instance, "__dict__") else {}
    if not attrs:
        return f"{class_name}: <no public state>"
    payload = _jsonable(attrs)
    return f"{class_name}:\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def render_state_view(
    involved_instances: dict[str, Any],
    *,
    config: StateViewConfig,
) -> str:
    mode = normalize_state_view_mode(config.mode)
    if mode == "none":
        return ""

    sections = ["Current Environment State:"]
    for class_name in sorted(involved_instances):
        instance = involved_instances[class_name]
        if mode == "raw":
            sections.append(f"{class_name}:\n{repr(instance)}")
        elif class_name == "GorillaFileSystem":
            sections.append(_render_gorilla_filesystem(instance, config))
        else:
            sections.append(_render_generic_class(class_name, instance))
    return _truncate("\n\n".join(sections), config.max_chars)


def build_turn_state_views(
    bfcl_root: Path,
    episode: dict[str, Any],
    *,
    run_label: str,
    config: StateViewConfig,
    strict: bool = True,
) -> list[str]:
    mode = normalize_state_view_mode(config.mode)
    if mode == "none":
        return ["" for _turn in episode["turns"]]

    ensure_bfcl_on_path(bfcl_root)
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
        execute_multi_turn_func_call,
    )

    sample_id = episode["id"]
    model_name = _safe_model_name(
        f"think_parallel_v2_state_{run_label}_{sample_id}_{uuid.uuid4().hex[:8]}"
    )
    initial_config = episode["initial_config"]
    involved_classes = episode["involved_classes"]
    test_category = sample_id.rsplit("_", 1)[0]
    long_context = "long_context" in test_category or "composite" in test_category

    _observations, involved_instances = execute_multi_turn_func_call(
        [],
        initial_config,
        involved_classes,
        model_name,
        sample_id,
        long_context=long_context,
        is_evaL_run=False,
    )

    views: list[str] = []
    replay_error: str | None = None
    for turn in episode["turns"]:
        view = render_state_view(involved_instances, config=config)
        if replay_error:
            view = view + f"\n\nState Replay Note: {replay_error}"
        views.append(view)
        try:
            _observations, involved_instances = execute_multi_turn_func_call(
                copy.deepcopy(turn.get("gold_calls", [])),
                initial_config,
                involved_classes,
                model_name,
                sample_id,
                long_context=long_context,
                is_evaL_run=False,
            )
        except Exception as exc:
            if strict:
                raise
            replay_error = f"{type(exc).__name__}: {exc}"
    return views
