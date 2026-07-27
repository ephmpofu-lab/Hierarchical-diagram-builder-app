"""Background execution for Cycles (Phase 11 sections 5-6) -- WP10, the async
counterpart to the existing synchronous reasoning (WP5/WP7) and decomposition (WP8)
endpoints. Runs the exact same, already-tested Orchestrator calls off the request
thread -- nothing about the reasoning, governance, or commit logic is duplicated or
reimplemented here, only sequenced and translated into CycleEvents. Matches the
sequence diagram's shape (CycleStarted -> per-stage progress -> Compliant/Violation ->
Committed) without inventing streaming/push infrastructure this stack doesn't have --
see api.py's polling endpoint for how a client observes progress instead."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from .. import storage
from ..agents.orchestrator import Orchestrator
from ..db import postgres_cycle_repository as cycle_repo
from ..decomposition.commit import commit_children
from ..models import CycleEvent


def _event(event_type: str, detail: str = "") -> CycleEvent:
    return CycleEvent(
        id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc).isoformat(), event_type=event_type, detail=detail
    )


def run_reasoning_cycle(cycle_id: str, objective: str) -> None:
    cycle_repo.append_event(cycle_id, _event("CycleStarted", objective))
    try:
        orchestrator = Orchestrator()
        result = orchestrator.run_pipeline(objective)
        for stage in result.stages:
            cycle_repo.append_event(
                cycle_id, _event("StageCompleted", f"{stage.stage} ({stage.agent}): {stage.summary[:200]}")
            )
        review = orchestrator.review_proposal(result)
        cycle_repo.append_event(
            cycle_id, _event("Compliant" if review.outcome == "approved" else "Violation", review.rationale)
        )
        cycle_repo.complete_cycle(cycle_id, {"reasoning": result.model_dump(), "review": review.model_dump()})
    except Exception as exc:  # noqa: BLE001 -- a background task has no caller to raise to;
        # translating any failure into a Failed cycle status is the only way it's ever seen.
        cycle_repo.append_event(cycle_id, _event("CycleFailed", str(exc)))
        cycle_repo.fail_cycle(cycle_id, str(exc))


def run_decomposition_cycle(
    cycle_id: str, project_id: str, node_id: str, strategy_override: Optional[str], actor: str
) -> None:
    cycle_repo.append_event(cycle_id, _event("CycleStarted"))
    try:
        project = storage.load_project(project_id)
        node = project.nodes[node_id]
        orchestrator = Orchestrator()
        result = orchestrator.decompose_node(project, node, strategy_override)
        cycle_repo.append_event(
            cycle_id, _event("StageCompleted", f"{result.strategy}: {len(result.proposed_nodes)} candidate child(ren)")
        )

        if result.review is not None:
            cycle_repo.append_event(
                cycle_id,
                _event("Compliant" if result.review.outcome == "approved" else "Violation", result.review.rationale),
            )
        if result.parallel_review is not None:
            cycle_repo.append_event(
                cycle_id,
                _event(
                    "Compliant" if result.parallel_review.outcome == "approved" else "Violation",
                    f"[{result.parallel_strategy}] {result.parallel_review.rationale}",
                ),
            )

        # Reload right before committing -- the AI calls above may have taken a while; this
        # keeps the load-mutate-save window as short as possible rather than holding one
        # long-lived snapshot across the whole cycle (see postgres_cycle_repository's docstring).
        needs_commit = (result.review is not None and result.review.outcome == "approved") or (
            result.parallel_review is not None and result.parallel_review.outcome == "approved"
        )
        if needs_commit:
            project = storage.load_project(project_id)
            node = project.nodes[node_id]
            if result.review is not None and result.review.outcome == "approved":
                result.committed_node_ids = commit_children(project, node, result.proposed_nodes, result.strategy, actor)
            if result.parallel_review is not None and result.parallel_review.outcome == "approved":
                result.parallel_committed_node_ids = commit_children(
                    project, node, result.parallel_proposed_nodes, result.parallel_strategy, actor
                )
            storage.save_project(project)
            total = len(result.committed_node_ids) + len(result.parallel_committed_node_ids)
            cycle_repo.append_event(cycle_id, _event("Committed", f"{total} node(s)"))

        cycle_repo.complete_cycle(cycle_id, result.model_dump())
    except Exception as exc:  # noqa: BLE001
        cycle_repo.append_event(cycle_id, _event("CycleFailed", str(exc)))
        cycle_repo.fail_cycle(cycle_id, str(exc))
