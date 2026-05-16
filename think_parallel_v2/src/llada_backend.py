from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def load_traceable_llada_backend() -> Any:
    """Load the v1 traceable LLaDA backend without importing its `src` package name."""
    v1_trace = Path(__file__).resolve().parents[2] / "think_parallel_v1" / "src" / "llada_trace.py"
    if not v1_trace.exists():
        raise FileNotFoundError(f"Missing v1 LLaDA trace backend: {v1_trace}")
    spec = importlib.util.spec_from_file_location("think_parallel_v1_llada_trace", v1_trace)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import {v1_trace}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TraceableLLaDABackend
