"""Python Renderer (doc section 4.7) -- turns a frozen task tree into ordered code blocks,
sequenced by the requires/produces dependency graph (P4). Atomic-step variables become
function arguments, never hardcoded values."""

from typing import List

from ..models import DomainTaskTree, RenderedCodeBlock, TaskTreeNode


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
