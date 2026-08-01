"""Python Renderer (doc section 4.7) -- turns a frozen task tree into ordered code blocks,
sequenced by the requires/produces dependency graph (P4). Atomic-step variables become
function arguments, never hardcoded values."""

import re
from typing import List, Tuple

from ..models import (
    Attribute,
    Capability,
    Component,
    DomainTaskTree,
    ExtractedRequirement,
    RenderedCodeBlock,
    RenderedComponentModule,
    TaskTreeNode,
)


def _format_default(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in ("true", "false"):
        return lowered.capitalize()
    try:
        int(value)
        return value
    except ValueError:
        pass
    try:
        float(value)
        return value
    except ValueError:
        pass
    return repr(value)


def _function_name(label: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in label.lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "step"


def _topological_order(atomic_steps: List[TaskTreeNode]) -> List[TaskTreeNode]:
    by_id = {n.id: n for n in atomic_steps}
    in_degree = {n.id: 0 for n in atomic_steps}
    dependents = {n.id: [] for n in atomic_steps}
    for node in atomic_steps:
        for dep_id in node.requires:
            if dep_id in by_id:
                in_degree[node.id] += 1
                dependents[dep_id].append(node.id)

    # Parallel-safe steps (no dependency relationship) sort by step id -- arbitrary but
    # deterministic, so identical re-runs never shuffle output (spec section 6, point 5).
    ready = sorted(nid for nid, deg in in_degree.items() if deg == 0)
    ordered: List[TaskTreeNode] = []
    while ready:
        current_id = ready.pop(0)
        ordered.append(by_id[current_id])
        newly_ready = []
        for dependent_id in dependents[current_id]:
            in_degree[dependent_id] -= 1
            if in_degree[dependent_id] == 0:
                newly_ready.append(dependent_id)
        ready.extend(newly_ready)
        ready.sort()

    # A step never reached means a dependency cycle -- shouldn't happen if the Validator
    # ran first, but rendering never silently drops a step; append in id order instead.
    seen_ids = {n.id for n in ordered}
    ordered.extend(sorted((n for n in atomic_steps if n.id not in seen_ids), key=lambda n: n.id))
    return ordered


def render_python(tree: DomainTaskTree) -> List[RenderedCodeBlock]:
    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    ordered = _topological_order(atomic_steps)

    blocks = []
    for node in ordered:
        # Python requires every parameter without a default to precede every parameter
        # with one -- a stable sort on "has a default" preserves the tree's own variable
        # order within each group without producing invalid syntax.
        ordered_vars = sorted(node.variables, key=lambda v: v.default is not None)
        args = ", ".join(
            f"{v.name}={_format_default(v.default)}" if v.default is not None else v.name
            for v in ordered_vars
        )
        lines = [f"def {_function_name(node.label)}({args}):", f'    """{node.label}"""']
        if node.notes:
            lines.append(f"    # {node.notes}")
        if node.produces:
            lines.append(f"    {node.produces} = ...  # TODO: implement")
            lines.append(f"    return {node.produces}")
        else:
            lines.append("    ...  # TODO: implement")
        blocks.append(RenderedCodeBlock(step_id=node.id, label=node.label, code="\n".join(lines)))
    return blocks


# ============================================================================
# Component Tree rendering (Module 11, CD7/CD8, R30) -- a second entry point in this same
# file, not a separate module: R30's own text names "The Python Renderer" as one shared
# concern across both trees, the same way R11's mode selection is one choice covering both.
# ============================================================================

_PY_TYPE_MAP = {
    "integer": "int", "int": "int", "string": "str", "str": "str",
    "boolean": "bool", "bool": "bool", "list": "list", "float": "float",
    "number": "float", "dict": "dict",
}


def _python_type(type_name: str) -> str:
    # Unrecognized types default to str -- never invented further than that.
    return _PY_TYPE_MAP.get((type_name or "").strip().lower(), "str")


def _py_field_name(name: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in name.lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "field"


def _py_class_name(label: str) -> str:
    words = [w for w in re.split(r"[^a-zA-Z0-9]+", label) if w]
    return "".join(w.capitalize() for w in words) or "Component"


def render_component_tree(
    domain: str,
    requirements: List[ExtractedRequirement],
    capabilities: List[Capability],
    components: List[Component],
    attributes: List[Attribute],
) -> "Tuple[str, List[RenderedComponentModule]]":
    """CD7/CD8, R30 -- renders the Component Tree as a literal ASCII branching diagram
    retaining Requirements Engineering/Capability Identification/Functional Decomposition
    as visible provenance branches (CD7), plus one Python class per Component with one
    field per Attribute (CD8). Components and Attributes nest under Functional
    Decomposition, grouped by the Capability that realizes them -- that's where they're
    semantically produced; Requirements Engineering and Capability Identification are shown
    as flat provenance lists, not re-nested trees of their own."""
    lines = [domain]

    lines.append("├── Requirements Engineering")
    for i, req in enumerate(requirements):
        connector = "└──" if i == len(requirements) - 1 else "├──"
        lines.append(f"│   {connector} {req.prd_requirement_id}: {req.text}")

    lines.append("├── Capability Identification")
    for i, cap in enumerate(capabilities):
        connector = "└──" if i == len(capabilities) - 1 else "├──"
        traces = ", ".join(cap.traced_requirements)
        lines.append(f"│   {connector} {cap.label} (traces: {traces})")

    lines.append("└── Functional Decomposition")
    for ci, cap in enumerate(capabilities):
        cap_last = ci == len(capabilities) - 1
        cap_connector = "└──" if cap_last else "├──"
        lines.append(f"    {cap_connector} {cap.label}")
        cap_prefix = "        " if cap_last else "    │   "
        cap_components = [c for c in components if c.realizes_capability == cap.label]
        for coi, comp in enumerate(cap_components):
            comp_last = coi == len(cap_components) - 1
            comp_connector = "└──" if comp_last else "├──"
            lines.append(f"{cap_prefix}{comp_connector} {comp.label}")
            attr_prefix = f"{cap_prefix}    " if comp_last else f"{cap_prefix}│   "
            comp_attrs = [a for a in attributes if a.component_label == comp.label]
            for ai, attr in enumerate(comp_attrs):
                attr_last = ai == len(comp_attrs) - 1
                attr_connector = "└──" if attr_last else "├──"
                lines.append(f"{attr_prefix}{attr_connector} {attr.name}: {attr.type}")

    diagram = "\n".join(lines)

    modules = []
    for comp in components:
        comp_attrs = [a for a in attributes if a.component_label == comp.label]
        class_name = _py_class_name(comp.label)
        if comp_attrs:
            field_lines = [f"    {_py_field_name(a.name)}: {_python_type(a.type)}" for a in comp_attrs]
        else:
            field_lines = ["    pass"]
        code = f'class {class_name}:\n    """{comp.label}"""\n' + "\n".join(field_lines)
        modules.append(RenderedComponentModule(component_label=comp.label, code=code))

    return diagram, modules


# ============================================================================
# Roadmap + Checklist Render (Module 11, R37/CD11) -- one shared, mode-agnostic view reused
# by both the Python Renderer and the n8n Renderer (CD11's own "Applies to" line): nodes in
# topological build order, each showing its current [ ]/[-]/[x] status. Derived entirely
# from existing tree fields at render time, never a separately maintained document.
# ============================================================================


def render_roadmap_checklist(items: "List[Tuple[str, str, int]]") -> str:
    """The shared, tree-agnostic renderer. Each item is (label, status, depth); renders one
    markdown checklist line per item, indented 2 spaces per depth level."""
    return "\n".join(f"{'  ' * depth}- {status} {label}" for label, status, depth in items)


def render_workflow_tree_roadmap(tree: DomainTaskTree) -> str:
    """R37/CD11 for the Workflow Tree -- Layers/Sub-tasks in the tree's own root_ids/children
    build order (depth 0/1); Atomic steps (depth 2) ordered via the same R10
    _topological_order this file already computes for render_python, filtered per Sub-task
    while preserving that global order."""
    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    global_order = [n.id for n in _topological_order(atomic_steps)]

    items: List[Tuple[str, str, int]] = []
    for layer_id in tree.root_ids:
        layer = tree.nodes.get(layer_id)
        if layer is None:
            continue
        items.append((layer.label, layer.status, 0))
        for sub_task_id in layer.children:
            sub_task = tree.nodes.get(sub_task_id)
            if sub_task is None:
                continue
            items.append((sub_task.label, sub_task.status, 1))
            ordered_children = sorted(
                (cid for cid in sub_task.children if cid in tree.nodes),
                key=lambda cid: global_order.index(cid) if cid in global_order else len(global_order),
            )
            for atomic_id in ordered_children:
                atomic = tree.nodes[atomic_id]
                items.append((atomic.label, atomic.status, 2))

    return render_roadmap_checklist(items)


def render_component_tree_roadmap(
    capabilities: List[Capability], components: List[Component], attributes: List[Attribute]
) -> str:
    """R37/CD11 for the Component Tree -- Capabilities (depth 0), their Components via
    realizes_capability (depth 1), each Component's Attributes via component_label (depth 2),
    in the same breadth-first construction order render_component_tree (11f) already walks."""
    items: List[Tuple[str, str, int]] = []
    for capability in capabilities:
        items.append((capability.label, capability.status, 0))
        cap_components = [c for c in components if c.realizes_capability == capability.label]
        for component in cap_components:
            items.append((component.label, component.status, 1))
            comp_attrs = [a for a in attributes if a.component_label == component.label]
            for attribute in comp_attrs:
                items.append((attribute.name, attribute.status, 2))

    return render_roadmap_checklist(items)
