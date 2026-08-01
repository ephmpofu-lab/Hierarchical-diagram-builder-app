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
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..models import DomainTaskTree, N8nNode, N8nStageZone, TaskTreeNode
from .python_renderer import _topological_order

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCHEMA_PATH = _REPO_ROOT / "rules" / "n8n_node_schemas.json"

_HORIZONTAL_SPACING = 280.0
_ROW_HEIGHT = 160.0  # CR6 -- includes whitespace reserved for cross-row routing lanes
_ZONE_HEADER_HEIGHT = 60.0
_ZONE_PADDING = 40.0
_MAX_NODES_PER_ROW = 10  # CR4's own "~9-10 nodes" cap


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


def _atomic_steps_by_layer(tree: DomainTaskTree) -> Dict[str, List[TaskTreeNode]]:
    """Groups the tree's Atomic steps by their owning Layer (via the Atomic step ->
    Sub-task -> Layer parent chain), preserving the global R10 topological order within
    each layer's own list."""
    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    global_order = _topological_order(atomic_steps)

    layer_of_atomic: Dict[str, str] = {}
    for layer_id in tree.root_ids:
        layer = tree.nodes.get(layer_id)
        if layer is None:
            continue
        for sub_task_id in layer.children:
            sub_task = tree.nodes.get(sub_task_id)
            if sub_task is None:
                continue
            for atomic_id in sub_task.children:
                layer_of_atomic[atomic_id] = layer_id

    by_layer: Dict[str, List[TaskTreeNode]] = {layer_id: [] for layer_id in tree.root_ids}
    for node in global_order:
        layer_id = layer_of_atomic.get(node.id)
        if layer_id is not None:
            by_layer[layer_id].append(node)
    return by_layer


def compute_stage_zones(tree: DomainTaskTree) -> Tuple[List[N8nStageZone], Dict[str, List[float]]]:
    """CR3/CR4/CR15 -- allocates each Layer's non-overlapping vertical zone first (stacked
    via a running cursor, never derived from wherever nodes happen to land), then positions
    that layer's own Atomic steps within it: row-wrapped at _MAX_NODES_PER_ROW (CR4),
    left to right in dependency order within a row (CR3, subordinate to CR15)."""
    by_layer = _atomic_steps_by_layer(tree)

    zones: List[N8nStageZone] = []
    positions: Dict[str, List[float]] = {}
    cursor_y = 0.0
    for layer_id in tree.root_ids:
        layer = tree.nodes.get(layer_id)
        steps = by_layer.get(layer_id, [])
        if layer is None or not steps:
            continue

        num_rows = max(1, math.ceil(len(steps) / _MAX_NODES_PER_ROW))
        zone_height = _ZONE_HEADER_HEIGHT + num_rows * _ROW_HEIGHT + _ZONE_PADDING
        zone_width = min(len(steps), _MAX_NODES_PER_ROW) * _HORIZONTAL_SPACING
        zones.append(N8nStageZone(
            layer_id=layer_id, label=layer.label, x=0.0, y=cursor_y,
            width=zone_width, height=zone_height,
        ))

        for index, step in enumerate(steps):
            row, col = divmod(index, _MAX_NODES_PER_ROW)
            positions[step.id] = [col * _HORIZONTAL_SPACING, cursor_y + _ZONE_HEADER_HEIGHT + row * _ROW_HEIGHT]

        cursor_y += zone_height

    return zones, positions


def _classify_one(
    source_id: str,
    target_id: str,
    positions: Dict[str, List[float]],
    node_to_zone: Dict[str, str],
    zone_index: Dict[str, int],
) -> str:
    """CR18's own mechanical predicate (see 10a-ii's plan file for the exact category
    definitions this codifies -- CR18's text itself doesn't give a numeric boundary between
    "row transition" and "cross-row," or between "cross-stage" and "long-distance"; this is
    a concrete, defensible rule for those, not a fuzzy judgment call)."""
    zone_source = node_to_zone.get(source_id)
    zone_target = node_to_zone.get(target_id)
    x_source, y_source = positions[source_id]
    x_target, y_target = positions[target_id]

    if zone_source == zone_target:
        if y_source == y_target:
            col_diff = round((x_target - x_source) / _HORIZONTAL_SPACING)
            return "adjacent" if col_diff == 1 else "local_branch"
        row_diff = round((y_target - y_source) / _ROW_HEIGHT)
        return "row_transition" if row_diff == 1 else "cross_row"

    zi_source = zone_index.get(zone_source)
    zi_target = zone_index.get(zone_target)
    if zi_source is not None and zi_target is not None and abs(zi_target - zi_source) == 1:
        return "cross_stage"
    return "long_distance"


def classify_connections(tree: DomainTaskTree) -> Dict[Tuple[str, str], str]:
    """CR18 -- classifies every real (dependency_id, dependent_id) connection drawn from
    each Atomic step's own `requires` list, before any path geometry is generated. Reuses
    10a-i's compute_stage_zones for positions/zone membership -- never a second, separate
    layout computation."""
    zones, positions = compute_stage_zones(tree)
    zone_index = {zone.layer_id: index for index, zone in enumerate(zones)}
    by_layer = _atomic_steps_by_layer(tree)
    node_to_zone: Dict[str, str] = {
        step.id: layer_id for layer_id, steps in by_layer.items() for step in steps
    }

    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    classifications: Dict[Tuple[str, str], str] = {}
    for step in atomic_steps:
        for dep_id in step.requires:
            if dep_id not in positions or step.id not in positions:
                continue
            classifications[(dep_id, step.id)] = _classify_one(
                dep_id, step.id, positions, node_to_zone, zone_index
            )
    return classifications


def map_tree(tree: DomainTaskTree) -> Tuple[List[N8nNode], Dict[str, Any]]:
    atomic_steps = [n for n in tree.nodes.values() if n.level == "Atomic step"]
    ordered = _topological_order(atomic_steps)
    schemas = load_schemas()
    _, positions = compute_stage_zones(tree)

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
        # A step whose Layer can't be resolved (shouldn't happen in a well-formed tree)
        # falls back to the old flat single-row formula rather than crashing.
        position = positions.get(step.id, [index * _HORIZONTAL_SPACING, 0.0])
        nodes.append(N8nNode(
            step_id=step.id, name=name, type=schema["type"], type_version=schema["type_version"],
            position=position, parameters=_build_parameters(step, schema),
            parameter_options=schema.get("parameter_options", {}),
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
