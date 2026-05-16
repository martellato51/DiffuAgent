from __future__ import annotations

import copy
from typing import Any

from bfcl_eval.model_handler.utils import system_prompt_pre_processing_chat_model

try:
    from bfcl_eval.model_handler.utils import func_doc_language_specific_pre_processing
except ImportError:
    from bfcl_eval.utils import (
        _func_doc_language_specific_pre_processing as func_doc_language_specific_pre_processing,
    )

from .bfcl_data import join_user_goal


SUPPORTED_MODES = {"exact_name_a"}


def _build_exact_name_a_user_content(sample: dict[str, Any]) -> list[str]:
    goal = join_user_goal(sample["question"])
    return [
        "You are an expert in planning tool use.",
        "",
        "You are given a user request and a set of available BFCL functions.",
        "Your task is not to call the functions.",
        "Your task is to write a concise action-only plan for tool use.",
        "",
        "Output format:",
        "[A1] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.",
        "[A2] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.",
        "",
        "Rules:",
        "- Use the exact labels [A1], [A2], [A3], ...",
        "- Each [A] must describe exactly one intended function/tool action.",
        "- Use the exact function name from the available function schema.",
        "- Do not output executable BFCL function-call syntax.",
        "- Do not output JSON.",
        "- Do not write thoughts, observations, or final summaries.",
        "- A user turn may require multiple tool actions; split them into separate [An] lines.",
        "- Keep the numbering global across the whole request; do not reset at each turn.",
        "- Include known file names, ids, dates, locations, entities, and literal values when they are stated in the user request.",
        "- If an input depends on an earlier result, describe that input naturally instead of guessing the concrete value.",
        "- Use only the available functions.",
        "- Include only actions needed to satisfy the user request.",
        "- Do not add verification, inspection, or cleanup actions unless the user explicitly asks for them.",
        "- Do not include extra text before or after the labeled actions.",
        "",
        "User request:",
        goal,
        "",
        "Output:",
    ]


def _system_override() -> list[str]:
    return [
        "",
        "Diagnostic override: this run is not BFCL action execution.",
        "Ignore any earlier instruction that says to return only executable function calls.",
        "Use the function documentation only as the available action schema.",
        "Return only labeled action-plan lines in the form [A1], [A2], [A3], ...",
        "Do not return thoughts, JSON, or executable BFCL function calls.",
    ]


def build_prompt(
    sample: dict[str, Any],
    mode: str,
    category: str,
) -> tuple[list[dict[str, str]], list[dict[str, Any]], str]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode for think_parallel_v1: {mode}")

    functions = func_doc_language_specific_pre_processing(
        copy.deepcopy(sample["function"]), category
    )
    goal = join_user_goal(sample["question"])
    messages = [
        {
            "role": "user",
            "content": "\n".join(_build_exact_name_a_user_content(sample)),
        }
    ]
    messages = system_prompt_pre_processing_chat_model(messages, functions, category)
    messages[0]["content"] += "\n".join(_system_override())
    return messages, functions, goal
