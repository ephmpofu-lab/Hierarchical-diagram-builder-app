"""Generates the next level of candidate children for one node, using the selected
domain strategy's guidance (Phase 5 section 4) -- WP8. Reuses WP5's own AI-calling
helpers (`intelligence.stages._ask_json`/`_build`) rather than inventing a second JSON-
completion path -- Phase 4 section 7's "recursion re-enters the same pipeline" continuity
holds here too, even though this is a new, node-scoped prompt rather than the 8-stage
objective pipeline."""

from typing import List

from ..intelligence.stages import _ask_json, _build
from ..models import Node, ProposedNode
from .strategies import STRATEGIES


def generate_children(node: Node, strategy_name: str, reasoning_context: str) -> List[ProposedNode]:
    strategy = STRATEGIES[strategy_name]
    data = _ask_json(
        system=(
            f"You are the {strategy_name} decomposition strategy of an enterprise-"
            f"architecture recursive decomposition engine. {strategy.child_guidance} "
            "Propose at most 5 candidate children -- the most essential ones, not an "
            'exhaustive list. Respond with strict JSON only: {"children": [{"label": str, '
            '"node_type": str or null, "notes": str}]}'
        ),
        prompt=(
            f"Reasoning context:\n{reasoning_context}\n\nNode being decomposed:\n"
            f"{node.label}\n{node.notes}"
        ),
        max_tokens=1500,
    )
    children = _build(ProposedNode, data.get("children", []))
    for child in children:
        child.parent_hint = node.label
    return children
