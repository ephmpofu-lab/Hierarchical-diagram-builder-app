"""AI decision logic for selecting a decomposition strategy (Phase 5 section 9) -- WP8."""

from typing import Optional, Tuple

from ..models import Node
from .strategies import STRATEGIES

_DEFAULT_STRATEGY = "Business"  # ARC-0002: Business cascades to the other three -- the
# same fallback WP5's domain selection uses when a node has no domain tag yet


def select_strategy(node: Node, has_active_risk: bool) -> Tuple[str, Optional[str]]:
    """Returns (primary_strategy_name, parallel_strategy_name_or_None). Domain
    (`node.classification`) is the primary signal; a Physical abstraction level overrides
    it to Technology regardless of the node's nominal domain tag (section 9's own
    diagram). Governance runs alongside the primary strategy, never instead of it,
    whenever the node has an active (unresolved) Risk against it."""
    primary = node.classification if node.classification in STRATEGIES else _DEFAULT_STRATEGY
    if node.abstraction_level == "Physical":
        primary = "Technology"
    parallel = "Governance" if has_active_risk else None
    return primary, parallel
