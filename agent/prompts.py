"""Role instructions retained for a future optional LLM presenter.

The current coordinator is deterministic. If a language model is added, these
rules preserve the existing tool and numeric-grounding boundary.
"""

COORDINATOR_RULES = """Use only checked tool output. Do not calculate or invent
numbers. State infeasibility, data provenance, and the need for human approval.
Never send a schedule to real charging hardware."""
