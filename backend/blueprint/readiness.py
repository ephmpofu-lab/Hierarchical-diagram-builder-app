"""Readiness check for Implementation Blueprint generation (Journey 3, WP19): is a
subtree's leaf Task nodes actually fully decomposed yet? Never blocks generation --
informs only, the same "warn, don't block" posture the Health dashboard and Decompose's
own active-risk hint already use in this app."""

from typing import List, Tuple

from ..decomposition.stopping import is_terminal
from ..models import Node, Project


def collect_leaf_nodes(project: Project, root_id: str) -> List[Node]:
    """Every childless node in root_id's own subtree, root included if it has no
    children itself -- the same recursive walk pattern as tree.subtree_depth."""
    root = project.nodes[root_id]
    if not root.children:
        return [root]
    leaves: List[Node] = []
    for child_id in root.children:
        leaves.extend(collect_leaf_nodes(project, child_id))
    return leaves


def check_readiness(project: Project, root_id: str) -> Tuple[bool, List[str]]:
    """Returns (ready, non_terminal_leaf_labels). A leaf counts as terminal per
    decomposition.stopping.is_terminal, using its own classification when set and
    defaulting to Technology (Blueprint's natural home -- the one strategy whose leaf
    type, Task, is "directly executable, single owner") when unclassified. Never blocks
    generation -- only informs (see this module's own docstring)."""
    leaves = collect_leaf_nodes(project, root_id)
    non_terminal = [
        leaf.label for leaf in leaves if not is_terminal(leaf, leaf.classification or "Technology")
    ]
    return not non_terminal, non_terminal
