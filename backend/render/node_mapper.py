"""Node Mapper (doc section 4.8) -- maps each atomic step in a frozen task tree to a real
n8n node type + pre-filled parameters, using a small, hand-curated, vendored catalog of
common n8n core nodes (rules/n8n_node_schemas.json). This exists instead of a live n8n API
call or a mechanically-scraped full catalog because neither is actually available: n8n's
public REST API has no node-schema endpoint, and its full node catalog only exists as
TypeScript source (packages/nodes-base/**/*.node.ts) with no downloadable JSON -- both
confirmed against n8n's own docs/community forum before this was written. Every atomic step
with no clean keyword match falls back to the Code node (the doc's own mandatory fallback),
embedding the step's own requires/produces/variables as a JS stub. Positions and connections
are computed once here, reused identically by the JSON exporter (n8n_exporter.py) and the
frontend SVG renderer -- never computed twice."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..models import DomainTaskTree, N8nNode, TaskTreeNode
from .python_renderer import _topological_order

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCHEMA_PATH = _REPO_ROOT / "rules" / "n8n_node_schemas.json"

_HORIZONTAL_SPACING = 280.0


def load_schemas() -> dict:
    """Public -- also reused by backend/validator/principles.py's Atomicity Test
    criterion 5 (spec's own instruction: check against the implementation schema already
    loaded here, not a separate judgment call)."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def match_schema(step: TaskTreeNode, schemas: dict) -> dict:
    """Public -- also reused by backend/decompose/engine.py's Stage 4 (Variable
    Exhaustion), which grounds each atomic step's variables in this same real schema."""
    text = f"{step.label} {step.notes}".lower()
    for schema in schemas["nodes"]:
        if any(keyword in text for keyword in schema["match_keywords"]):
            return schema
    return schemas["fallback"]


def _build_parameters(step: TaskTreeNode, schema: dict) -> Dict[str, Any]:
    params: Dict[str, Any] = dict(schema.get("default_parameters", {}))
    declared = {v.name: v.default for v in step.variables if v.default is not None}
    # Overlay any variable whose name matches a real parameter key on this node type.
    for key in list(params.keys()):
        if key in declared:
            params[key] = declared[key]
    if schema["type"] == "n8n-nodes-base.code":
        # P3 (Variable Exhaustion) applies here too -- no declared variable is silently
        # dropped just because it didn't match a known node's parameter name.
        var_lines = "\n".join(f"// {v.name} = {v.default!r}  -- {v.description}" for v in step.variables)
        params["jsCode"] = (
            f"// {step.label}\n// requires: {step.requires}\n// produces: {step.produces}\n"
            f"{var_lines}\n// TODO: implement\nreturn items;"
        )
    return params


def map_tree(tree: DomainTaskTree) -> Tuple[List[N8nNode], Dict[str, Any]]:
    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    ordered = _topological_order(atomic_steps)
    schemas = load_schemas()

    id_to_name: Dict[str, str] = {}
    used_names: set = set()
    nodes: List[N8nNode] = []
    for index, step in enumerate(ordered):
        schema = match_schema(step, schemas)
        base_name = step.label[:60] or f"Step {index + 1}"
        name = base_name
        suffix = 2
        while name in used_names:  # n8n names must be unique on a canvas
            name = f"{base_name} ({suffix})"
            suffix += 1
        used_names.add(name)
        id_to_name[step.id] = name
        nodes.append(N8nNode(
            step_id=step.id, name=name, type=schema["type"], type_version=schema["type_version"],
            position=[index * _HORIZONTAL_SPACING, 0.0], parameters=_build_parameters(step, schema),
        ))

    connections: Dict[str, Any] = {}
    for step in ordered:
        target_name = id_to_name[step.id]
        for dep_id in step.requires:
            source_name = id_to_name.get(dep_id)
            if source_name is None:
                continue
            connections.setdefault(source_name, {}).setdefault("main", [[]])
            connections[source_name]["main"][0].append({"node": target_name, "type": "main", "index": 0})
    return nodes, connections
