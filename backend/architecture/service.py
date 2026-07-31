"""TOGAF Architecture Generation (Journey 5, WP21) -- the only architecture framework
Architeq generates. `build_architecture_view` is a pure, deterministic grouping of a
project's already-real nodes by their own `classification` field (set by real engineering
steps -- Discovery Session's commit, or Recursive Decomposition's strategy assignment,
see decomposition/commit.py::commit_children's own `committed.classification = strategy_name`)
into the four TOGAF domains. No AI call, no invented content -- every id returned is a real
Node id already in the project, so every element is traceable back to whatever engineering
step produced it, by construction rather than by convention."""

from ..models import ArchitectureView, Project

TOGAF_DOMAINS = ("Business", "Data", "Application", "Technology")


def build_architecture_view(project: Project) -> ArchitectureView:
    buckets = {domain: [] for domain in TOGAF_DOMAINS}
    governance_node_ids = []
    unclassified_node_ids = []

    for node in project.nodes.values():
        if node.classification in buckets:
            buckets[node.classification].append(node.id)
        elif node.classification == "Governance":
            governance_node_ids.append(node.id)
        else:
            unclassified_node_ids.append(node.id)

    return ArchitectureView(
        business=buckets["Business"],
        data=buckets["Data"],
        application=buckets["Application"],
        technology=buckets["Technology"],
        governance_node_ids=governance_node_ids,
        unclassified_node_ids=unclassified_node_ids,
    )
