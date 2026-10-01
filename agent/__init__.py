"""Tool-mediated coordinator and LangGraph multi-agent copilot for deterministic fleet planning."""

from agent.tracing import setup_tracing, traceable

# Auto-initialize LangSmith environment variables on module import
setup_tracing()

__all__ = ["setup_tracing", "traceable"]
