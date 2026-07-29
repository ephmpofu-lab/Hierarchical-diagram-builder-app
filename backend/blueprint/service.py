"""Generates an Implementation Blueprint for an already-decomposed subtree (Journey 3,
WP19): milestone grouping, schedule, and build-order dependencies for existing Task
nodes, plus advisory testing/CI-CD guidance. Reuses WP5's own AI-calling helpers
(`intelligence.stages._ask_json`/`_build`) rather than inventing a second JSON-completion
path -- same cross-module reuse decomposition/service.py already established. One call
reasons over every leaf at once (not per-leaf): cross-task build-order/dependency
reasoning is only possible if the model sees the whole leaf set together."""

from typing import List

from ..intelligence.stages import _ask_json, _build
from ..models import BlueprintResult, Node, ProposedDependency, ProposedWorkPackage


def generate_blueprint(root: Node, leaves: List[Node], reasoning_context: str) -> BlueprintResult:
    valid_ids = {leaf.id for leaf in leaves}
    leaf_lines = "\n".join(f"{leaf.id}: {leaf.label} -- {leaf.notes}" for leaf in leaves)
    data = _ask_json(
        system=(
            "You are the Implementation Blueprint stage of an enterprise-architecture "
            "planning engine. Given a set of already-decomposed, directly-executable Task "
            "nodes (identified by their real ids), propose: a milestone grouping label for "
            "each task, a rough target_date (ISO YYYY-MM-DD) and duration_days, a short "
            "testing_notes sentence, the build-order dependencies between tasks (which must "
            "finish before which), and overall testing_strategy/ci_cd_strategy prose (2-4 "
            "sentences each). Only reference the given task ids -- never invent new ones. "
            'Respond with strict JSON only: {"work_packages": [{"node_id": str, '
            '"milestone": str, "target_date": str or null, "duration_days": int or null, '
            '"testing_notes": str}], "dependencies": [{"from_node_id": str, "to_node_id": '
            'str, "label": str or null}], "testing_strategy": str, "ci_cd_strategy": str}'
        ),
        prompt=f"Reasoning context:\n{reasoning_context}\n\nTasks:\n{leaf_lines}",
        max_tokens=3000,
    )

    # Any id the model returns outside the real leaf-id set is silently dropped, not
    # errored -- mirrors commit_reasoning_proposal's own "skip unresolvable reference,
    # don't error" precedent, just keyed by id instead of label.
    work_packages = [
        wp for wp in _build(ProposedWorkPackage, data.get("work_packages", [])) if wp.node_id in valid_ids
    ]
    dependencies = [
        dep
        for dep in _build(ProposedDependency, data.get("dependencies", []))
        if dep.from_node_id in valid_ids and dep.to_node_id in valid_ids
    ]

    return BlueprintResult(
        root_node_id=root.id,
        proposed_work_packages=work_packages,
        proposed_dependencies=dependencies,
        testing_strategy=str(data.get("testing_strategy", "")),
        ci_cd_strategy=str(data.get("ci_cd_strategy", "")),
    )
