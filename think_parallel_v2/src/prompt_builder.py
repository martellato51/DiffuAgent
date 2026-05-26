from __future__ import annotations

import copy
import json
import os
from typing import Any

from .bfcl_data import ensure_bfcl_on_path


SUPPORTED_MODES = {
    "llmcompiler_plan",
    "llmcompiler_explicit_dag",
    "llmcompiler_flat_plan",
}
END_PLAN = "<END_PLAN>"


def normalize_mode(mode: str) -> str:
    if mode == "llmcompiler_plan":
        return "llmcompiler_explicit_dag"
    if mode in SUPPORTED_MODES:
        return mode
    raise ValueError(f"Unsupported think_parallel_v2 mode: {mode}")


def _render_previous_turns(episode: dict[str, Any], current_turn_index: int) -> str:
    if current_turn_index == 0:
        return "Completed Previous Turns (read-only context):\nNone."

    lines: list[str] = [
        "Completed Previous Turns (read-only context):",
        "Their Observations may be used as concrete input values.",
        "Do not output Observation lines in the Current Plan.",
    ]
    for turn in episode["turns"][:current_turn_index]:
        lines.extend(
            [
                "",
                f"Turn {turn['turn_index'] + 1} User:",
                turn.get("user_text") or "",
                "Previous Plan:",
            ]
        )
        gold_calls = turn.get("gold_calls", [])
        observations = turn.get("gold_observations", [])
        if not gold_calls:
            lines.append(f"{END_PLAN}")
            continue
        for i, call in enumerate(gold_calls, start=1):
            lines.append(f"{i}. {call}")
            if i - 1 < len(observations):
                lines.append(f"Observation: {observations[i - 1]}")
        lines.append(f"{END_PLAN}")
    return "\n".join(lines)


def _planner_user_content(
    episode: dict[str, Any],
    turn: dict[str, Any],
    state_view: str = "",
) -> str:
    previous = _render_previous_turns(episode, turn["turn_index"])
    current_user = turn.get("user_text") or ""
    parts = [
        previous,
        "",
    ]
    if state_view.strip():
        parts.extend(
            [
                state_view.strip(),
                "",
            ]
        )
    parts.extend(
        [
            "Current Turn User:",
            current_user,
            "",
            "Current Plan:",
        ]
    )
    return "\n".join(parts)


def _local_function_doc_preprocessing(
    functions: list[dict[str, Any]],
    category: str,
) -> list[dict[str, Any]]:
    if category == "java":
        hint = " Note that the provided function is in Java 8 SDK syntax."
    elif category == "javascript":
        hint = " Note that the provided function is in JavaScript syntax."
    else:
        hint = " Note that the provided function is in Python 3 syntax."
    processed = copy.deepcopy(functions)
    for item in processed:
        if isinstance(item, dict) and isinstance(item.get("description"), str):
            item["description"] = item["description"] + hint
    return processed


def _render_function_docs(functions: list[dict[str, Any]]) -> str:
    serialization = os.getenv("BFCL_FUNCTION_DOC_SERIALIZATION", "json").lower()
    if serialization == "legacy":
        return str(functions)
    if serialization == "json":
        return json.dumps(functions, ensure_ascii=False, indent=2)
    raise ValueError(
        "Unsupported BFCL_FUNCTION_DOC_SERIALIZATION="
        f"{serialization!r}; expected 'legacy' or 'json'"
    )


def _planner_system_content(
    functions: list[dict[str, Any]],
    mode: str,
) -> str:
    rendered = _render_function_docs(functions)
    common_header = [
        "You are an expert planner for API function-call plans.",
        "Given the current user turn, create the minimal sufficient tool-use plan to solve it.",
        "Use only necessary actions. Among those actions, maximize parallelizability.",
        "",
        "Each action described below contains input/output types and description.",
        "You must strictly adhere to the input and output types for each action.",
        "The action descriptions contain the guidelines. You MUST strictly follow those guidelines when you use the actions.",
        "",
        "Available functions:",
        "",
        rendered,
        "",
    ]

    common_contract = [
        f"- Output only Thought, numbered actions, and {END_PLAN}; no observations, answers, comments, JSON, or list-style answer wrappers.",
        "- Each action must be one provided function using exact schema parameter names.",
        "- Do not wrap arguments in arg= unless the function schema contains a parameter named arg.",
        "- IDs start at 1 and strictly increase within the Current Plan.",
        "- Do not repeat previous-turn actions unless the current user explicitly asks to perform them again.",
        "- Use functions at their documented granularity; do not add helper actions unless their outputs are needed for the current turn.",
        "- Do not call join().",
    ]

    if mode == "llmcompiler_explicit_dag":
        mode_specific = [
            "Add dependencies only when an input truly requires a current-plan result.",
            "",
            "Output format:",
            "Thought: <optional one-line strategy>",
            "1. tool_name(param=value)",
            "2. tool_name(param=$1.field)",
            END_PLAN,
            "",
            "Output contract:",
            *common_contract,
            "- Inputs may be constants, concrete values from Previous Turns/Observations, or current-plan references like $1 or $1.field.",
            "- If an action requires the output of an earlier Current Plan action, use $id or $id.field to express that dependency.",
            "- If using $id.field, field must appear in that tool's response schema.",
            "- Independent actions must not reference each other.",
        ]
    elif mode == "llmcompiler_flat_plan":
        mode_specific = [
            "Do not express dependencies inside action arguments; keep the plan as a flat numbered list.",
            "",
            "Output format:",
            "Thought: <optional one-line strategy>",
            "1. tool_name(param=value)",
            END_PLAN,
            "",
            "Output contract:",
            *common_contract,
            "- Inputs may be constants, concrete values from Previous Turns/Observations, or short angle-bracket placeholder strings.",
            "- Do not refer to numbered actions inside arguments.",
            "- If an argument requires a value produced by another Current Plan action, use a short angle-bracket placeholder string instead, such as \"<zipcode for Rivermist>\".",
            "- Keep all necessary action nodes visible even when using placeholders.",
        ]
    else:
        raise ValueError(f"Unsupported think_parallel_v2 mode: {mode}")

    return "\n".join([*common_header, *mode_specific])


def build_prompt(
    bfcl_root,
    episode: dict[str, Any],
    turn: dict[str, Any],
    mode: str,
    category: str,
    state_view: str = "",
) -> tuple[list[dict[str, str]], list[dict[str, Any]], str]:
    mode = normalize_mode(mode)

    ensure_bfcl_on_path(bfcl_root)
    try:
        from bfcl_eval.model_handler.utils import (
            func_doc_language_specific_pre_processing,
        )
        functions = func_doc_language_specific_pre_processing(
            copy.deepcopy(episode["function"]), category
        )
    except Exception:
        functions = _local_function_doc_preprocessing(episode["function"], category)
    messages = [
        {
            "role": "system",
            "content": _planner_system_content(functions, mode),
        },
        {
            "role": "user",
            "content": _planner_user_content(episode, turn, state_view=state_view),
        },
    ]
    return messages, functions, turn.get("user_text") or ""
