"""Stopping criteria for recursive decomposition (Phase 5 section 5) -- WP8."""

from ..models import Node
from .strategies import STRATEGIES


def is_terminal(node: Node, strategy_name: str) -> bool:
    """A human override (section 5, HITL point 4) always wins. Otherwise a node stops
    decomposing once its `node_type` matches the leaf type its strategy's decomposition
    ladder ends at (section 4's table) -- the universal rule ("Full Specification" detail
    level, directly executable/assignable as a single unit of work) expressed concretely
    per domain rather than via a separate abstract detail-level model."""
    if node.decomposition_terminal is not None:
        return node.decomposition_terminal
    strategy = STRATEGIES.get(strategy_name)
    if strategy is None:
        return False
    return node.node_type in strategy.leaf_node_types
