"""Deterministic per-domain planning artifacts for Module 12 (R38-R40).

The functions here only project already-frozen domain artifacts.  They never use this
repository's ARCHITEQ-*.md files as end-user content and never ask an LLM to fill gaps.
"""

from typing import Any, Optional

from .models import ComponentTree, DataArchitecture, DomainTaskTree
from .render.python_renderer import render_workflow_tree_roadmap


_META = [
    ("prd", "PRD", "PRD.md", "document"),
    ("tdd", "Tech Design Document", "TDD.md", "blueprint"),
    ("app_flow", "App Flow", "AppFlow.md", "route"),
    ("design_brief", "Design Brief", "DesignBrief.md", "palette"),
    ("backend_schema", "Backend Schema", "BackendSchema.md", "database"),
    ("engineering_plan", "Engineering Plan", "EngineeringPlan.md", "roadmap"),
]


def _artifact(artifact_id: str, title: str, filename: str, icon: str, description: str, sections: list[tuple[str, list[str]]], markdown: str, unavailable: Optional[str] = None) -> dict[str, Any]:
    return {"id": artifact_id, "title": title, "file": filename, "icon": icon,
            "description": description, "sections": [{"title": name, "items": items} for name, items in sections],
            "markdown": markdown, "status": "missing" if unavailable else "built", "blocked_reason": unavailable}


def build_artifacts(domain: str, workflow: DomainTaskTree, component: Optional[ComponentTree], data: Optional[DataArchitecture]) -> list[dict[str, Any]]:
    layers = [workflow.nodes[node_id] for node_id in workflow.root_ids if node_id in workflow.nodes]
    atomic = [node for node in workflow.nodes.values() if node.level == "Atomic step"]
    layer_lines = [f"{layer.label}: {len(layer.children)} sub-task(s)" for layer in layers]
    step_lines = [node.label for node in atomic]
    requirements = [f"{r.prd_requirement_id}: {r.text}" for r in component.requirements] if component else step_lines
    prd_markdown = "# " + domain + " PRD\n\n## Requirements\n" + "\n".join(f"- {item}" for item in requirements)
    tdd_sections = [("Workflow architecture", layer_lines), ("Implementation units", step_lines)]
    tdd_markdown = "# " + domain + " Tech Design Document\n\n## Workflow architecture\n" + "\n".join(f"- {item}" for item in layer_lines) + "\n\n## Implementation units\n" + "\n".join(f"- {item}" for item in step_lines)
    artifacts = [
        _artifact("prd", "PRD", "PRD.md", "document", f"{domain} requirements derived from its frozen architecture.", [("Requirements", requirements)], prd_markdown),
        _artifact("tdd", "Tech Design Document", "TDD.md", "blueprint", f"{domain} workflow and implementation structure.", tdd_sections, tdd_markdown),
    ]
    if component is None:
        reason = "Requires a frozen Component Tree to determine whether this domain contains a UI component."
        artifacts += [_artifact("app_flow", "App Flow", "AppFlow.md", "route", "User interaction flow for this domain.", [], "", reason), _artifact("design_brief", "Design Brief", "DesignBrief.md", "palette", "Visual system for this domain.", [], "", reason)]
    else:
        ui_components = [c.label for c in component.components if c.is_ui_tagged]
        applicable = ui_components or ["Not applicable: the frozen Component Tree has no UI-tagged component."]
        artifacts += [_artifact("app_flow", "App Flow", "AppFlow.md", "route", f"UI flow recorded for {domain}.", [("UI components", applicable)], "# " + domain + " App Flow\n\n" + "\n".join(f"- {item}" for item in applicable)), _artifact("design_brief", "Design Brief", "DesignBrief.md", "palette", f"UI design scope recorded for {domain}.", [("UI components", applicable)], "# " + domain + " Design Brief\n\n" + "\n".join(f"- {item}" for item in applicable))]
    if data is None:
        artifacts.append(_artifact("backend_schema", "Backend Schema", "BackendSchema.md", "database", "Persistent data model for this domain.", [], "", "Requires a frozen Data Architecture for this domain."))
    else:
        entities = [f"{e.id} {e.name}" for e in data.entities]
        artifacts.append(_artifact("backend_schema", "Backend Schema", "BackendSchema.md", "database", f"{domain} canonical persistent entities.", [("Entities", entities)], "# " + domain + " Backend Schema\n\n" + "\n".join(f"- {item}" for item in entities)))
    roadmap = render_workflow_tree_roadmap(workflow)
    artifacts.append(_artifact("engineering_plan", "Engineering Plan", "EngineeringPlan.md", "roadmap", f"{domain} build order derived from the frozen Workflow Tree.", [("Layers", layer_lines), ("Atomic steps", step_lines)], "# " + domain + " Engineering Plan\n\n" + roadmap))
    return artifacts
