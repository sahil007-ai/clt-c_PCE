"""LangSmith observability and tracing integration for VoltAI.

Automatically configures environment variables (LANGSMITH_TRACING,
LANGSMITH_API_KEY, LANGSMITH_PROJECT, LANGSMITH_ENDPOINT, and LANGCHAIN_*)
from project .env, and provides a safe @traceable decorator for all agent
nodes, coordinator workflows, and engine tool invocations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable


def setup_tracing() -> bool:
    """Ensure LangSmith tracing environment variables are populated from .env."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and val and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            pass

    # Synchronize dual LangSmith and LangChain environment variables
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if api_key:
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"

    project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")
    if project:
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGCHAIN_PROJECT"] = project

    endpoint = os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT")
    if endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    return bool(api_key)


# Initialize environment on module load
tracing_active = setup_tracing()

# Safe export of traceable decorator with graceful offline / missing-package fallback
try:
    from langsmith import traceable as _ls_traceable

    def traceable(*args: Any, **kwargs: Any) -> Any:
        return _ls_traceable(*args, **kwargs)

except ImportError:

    def traceable(*args: Any, **kwargs: Any) -> Any:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
