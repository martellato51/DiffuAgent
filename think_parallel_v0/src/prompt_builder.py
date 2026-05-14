from __future__ import annotations

import copy
from typing import Any

from bfcl_eval.model_handler.utils import system_prompt_pre_processing_chat_model
from bfcl_eval.utils import (
    _func_doc_language_specific_pre_processing as func_doc_language_specific_pre_processing,
)

from .bfcl_data import join_user_goal, summarize_initial_config


SUPPORTED_MODES = {
    "goal_tools_a",
    "goal_init_tools_a",
    "goal_tools_ta",
    "goal_init_tools_ta",
}


def _uses_initial_config(mode: str) -> bool:
    return mode in {"goal_init_tools_a", "goal_init_tools_ta"}


def _is_a_only_mode(mode: str) -> bool:
    return mode.endswith("_a")


def _build_ta_user_content(sample: dict[str, Any], mode: str) -> list[str]:
    goal = join_user_goal(sample["question"])
    user_content = [
        "You are an expert in planning tool use.",
        "",
        "You are given a user request and a set of available functions.",
        "Your task is not to call the functions.",
        "Your task is to write a concise planning-only rationale for function use.",
        "",
        "Rules:",
        "- Use the exact labels [T1], [A1], [T2], [A2], ...",
        "- A user turn may require multiple tool actions.",
        "- Each [T] must be one short sentence about what needs to be known, decided, or done.",
        "- Each [A] must be one short sentence describing exactly one intended function/tool action.",
        "- If multiple tools are needed, split them into separate [Tn]/[An] pairs.",
        "- Keep the numbering global across the whole request; do not reset at each turn.",
        "- When an [A] uses an available function, start the sentence with that exact function name or with 'Use <function_name>'.",
        "- [A] may be natural language or a pseudo-call, but it does not need to match the exact BFCL function-call format.",
        "- Use only the available functions.",
        "- Do not output JSON.",
        "- Do not add a final summary step such as 'the user request is fully planned'.",
        "- Do not include extra text before or after the labeled steps.",
        "- Stop when the user request is fully planned.",
        "",
        "User request:",
        goal,
    ]
    if _uses_initial_config(mode):
        user_content.extend(
            [
                "",
                "Initial environment configuration summary:",
                summarize_initial_config(sample.get("initial_config", {})),
            ]
        )
    user_content.extend(["", "Output:"])
    return user_content


def _build_a_user_content(sample: dict[str, Any], mode: str) -> list[str]:
    goal = join_user_goal(sample["question"])
    user_content = [
        "You are an expert in planning tool use.",
        "",
        "You are given a user request and a set of available functions.",
        "Your task is not to call the functions.",
        "Your task is to write a concise action-only plan for tool use.",
        "",
        "Rules:",
        "- Use the exact labels [A1], [A2], [A3], ...",
        "- Do not write thoughts, explanations, observations, or final summaries.",
        "- A user turn may require multiple tool actions.",
        "- Each [A] must describe exactly one intended function/tool action.",
        "- If multiple tools are needed, split them into separate [An] lines.",
        "- Keep the numbering global across the whole request; do not reset at each turn.",
        "- When an [A] uses an available function, start the sentence with that exact function name or with 'Use <function_name>'.",
        "- [A] may be natural language or a pseudo-call, but it does not need to match the exact BFCL function-call format.",
        "- Use only the available functions.",
        "- Include only actions needed to satisfy the user request.",
        "- Do not add verification, inspection, or cleanup actions unless the user explicitly asks for them.",
        "- Do not output JSON.",
        "- Do not include extra text before or after the labeled actions.",
        "",
        "User request:",
        goal,
    ]
    if _uses_initial_config(mode):
        user_content.extend(
            [
                "",
                "Initial environment configuration summary:",
                summarize_initial_config(sample.get("initial_config", {})),
            ]
        )
    user_content.extend(["", "Output:"])
    return user_content


def _system_override(mode: str) -> list[str]:
    if _is_a_only_mode(mode):
        return [
            "",
            "Diagnostic override: this run is not BFCL action execution.",
            "Ignore any earlier instruction that says to return only executable function calls.",
            "Use the function documentation only as the available action schema.",
            "Return only labeled action-plan lines in the form [A1], [A2], [A3], ...",
            "Do not return thoughts, JSON, or executable BFCL function calls.",
        ]
    return [
        "",
        "Diagnostic override: this run is not BFCL action execution.",
        "Ignore any earlier instruction that says to return only executable function calls.",
        "Use the function documentation only as the available action schema.",
        "Return only labeled planning lines in the form [T1], [A1], [T2], [A2], ...",
        "Do not return JSON and do not return executable BFCL function calls.",
    ]


def build_prompt(
    sample: dict[str, Any],
    mode: str,
    category: str,
) -> tuple[list[dict[str, str]], list[dict[str, Any]], str]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    functions = func_doc_language_specific_pre_processing(
        copy.deepcopy(sample["function"]), category
    )
    goal = join_user_goal(sample["question"])
    if _is_a_only_mode(mode):
        user_content = _build_a_user_content(sample, mode)
    else:
        user_content = _build_ta_user_content(sample, mode)
    messages = [{"role": "user", "content": "\n".join(user_content)}]
    messages = system_prompt_pre_processing_chat_model(messages, functions, category)
    messages[0]["content"] += "\n".join(_system_override(mode))
    return messages, functions, goal
