"""The Engineering Cycle (Journey 5, WP21): the one genuinely new piece of infrastructure
this journey needs. Every existing Cycle (backend/cycles/service.py) wraps exactly ONE
bounded background call -- nothing in this codebase chains multiple decompose calls into
one tracked job. This loops Recursive Decomposition across an entire subtree, hidden from
the user, until every leaf is terminal (Business/Data/Application/Technology architecture
has fully emerged) or a safety cap is hit -- reusing Orchestrator.decompose_node and
decomposition.commit.commit_children entirely unchanged; only the loop is new. A branch
that holds for human review is skipped on later passes (never silently retried forever)
so the rest of the tree can keep progressing -- "warn, don't block", the same posture
Blueprint's own readiness check already established.

WP21 Amendment 2: TOGAF architecture is generated per-Task, not assigned from the top of
the tree. A node's Operations decomposition (Workspace -> Activity -> Task) always shows
up terminal to `decompose_node` once it reaches a real Task -- `generate_task_architecture`
is the separate AI call the pipeline runs at exactly that point, proposing only the
Business/Data/Application/Technology components this specific task genuinely needs (never
forcing all four). It lives here, not in backend/architecture/service.py, which stays
100% deterministic/zero-AI grouping over whatever this call (once approved and committed)
produces."""

import uuid
from datetime import datetime, timezone
from typing import List

from .. import storage
from ..agents.orchestrator import Orchestrator
from ..blueprint.readiness import collect_leaf_nodes
from ..db import postgres_cycle_repository as cycle_repo
from ..decomposition.commit import commit_children
from ..intelligence.stages import _ask_json, _build
from ..models import CycleEvent, Node, ProposedNode

# A small fixed constant, not adaptive -- same posture as MAX_GOVERNANCE_LOOPS
# (intelligence/pipeline.py) and MAX_DISCOVERY_TURNS (discovery/service.py). Revisited
# only if it proves limiting in practice.
MAX_ENGINEERING_ITERATIONS = 40

# The only architecture this call is allowed to propose -- matches
# backend/architecture/service.py's own TOGAF_DOMAINS exactly. Governance is deliberately
# not offered here: a Task is operational, not a compliance rule, so nothing at this step
# should ever propose a Governance-classified component.
TOGAF_DOMAINS = ("Business", "Data", "Application", "Technology")


def _event(event_type: str, detail: str) -> CycleEvent:
    return CycleEvent(id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc).isoformat(), event_type=event_type, detail=detail)


def generate_task_architecture(node: Node, reasoning_context: str) -> List[ProposedNode]:
    """One AI call (Journey 5, WP21 Amendment 2) proposing the minimal real TOGAF
    components a single, real, atomic Task needs -- reuses WP5/WP8's own AI-calling
    helpers, same convention as decomposition/service.py::generate_children. Each proposed
    component sets its own `classification`; a task that only needs 1-3 domains gets only
    those -- forcing all four would itself be inventing content the task doesn't need."""
    data = _ask_json(
        system=(
            "You are proposing the minimal enterprise architecture components a single, "
            "real, atomic engineering Task needs in order to be realized, using ONLY "
            "TOGAF's four architecture domains. Only propose a component for a domain if "
            "this task genuinely needs one there -- never force all four, and never "
            "invent components the task doesn't need. For each component: label, "
            "node_type, classification, notes -- classification must be exactly one of "
            f"{', '.join(TOGAF_DOMAINS)}. "
            'Respond with strict JSON only: {"components": [{"label": str, "node_type": '
            'str or null, "classification": str, "notes": str}]}'
        ),
        prompt=f"Reasoning context:\n{reasoning_context}\n\nTask:\n{node.label}\n{node.notes}",
        max_tokens=1200,
    )
    children = _build(ProposedNode, data.get("components", []))
    for child in children:
        child.parent_hint = node.label
        if child.classification not in TOGAF_DOMAINS:
            child.classification = None
    return children


def run_engineering_pipeline(cycle_id: str, project_id: str, root_id: str, actor: str) -> None:
    held_node_ids = set()
    try:
        for _ in range(MAX_ENGINEERING_ITERATIONS):
            project = storage.load_project(project_id)
            leaves = collect_leaf_nodes(project, root_id)
            pending = [n for n in leaves if n.id not in held_node_ids]
            if not pending:
                break

            progressed = False
            for node in pending:
                result = Orchestrator().decompose_node(project, node)
                if result.terminal:
                    # A node's Operations decomposition (Workspace -> Activity -> Task)
                    # always looks terminal here once it reaches a real Task -- that's
                    # exactly the point TOGAF architecture generation begins (Amendment 2),
                    # not a signal to skip the node. Anything else terminal (a real
                    # Sub-process/Attribute/Interface/Control/already-architected Task) is
                    # genuinely finished.
                    if result.strategy != "Operations":
                        continue
                    result = Orchestrator().generate_task_architecture(project, node)
                progressed = True
                if result.review and result.review.outcome == "approved":
                    commit_children(project, node, result.proposed_nodes, result.strategy, actor)
                    domains = sorted({c.classification for c in result.proposed_nodes if c.classification}) or [result.strategy]
                    cycle_repo.append_event(cycle_id, _event("DomainProgress", f"{','.join(domains)}:{node.label}"))
                else:
                    held_node_ids.add(node.id)
                    cycle_repo.append_event(cycle_id, _event("BranchHeld", node.label))
                storage.save_project(project)

            if not progressed:
                break
        cycle_repo.complete_cycle(cycle_id, {"root_id": root_id})
    except Exception as exc:  # pragma: no cover - mirrors cycles/service.py's own fail_cycle posture
        cycle_repo.fail_cycle(cycle_id, str(exc))
