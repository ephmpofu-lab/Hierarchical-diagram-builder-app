"""JSON Exporter (doc section 4.9) -- turns the Node Mapper's shared node/connection output
into a valid, directly-importable n8n workflow JSON. Positions and connections are never
recomputed here; this only wraps backend/render/node_mapper.py::map_tree's output into the
final export shape n8n expects (nodes[], connections{}), plus the rendering-only stage-zone/
classification metadata (10a-i/10a-ii) the frontend SVG Renderer consumes -- never re-
computed there, and never part of the real downloaded workflow.json (see N8nWorkflow's own
field comments)."""

from ..models import DomainTaskTree, N8nConnectionClassification, N8nWorkflow
from .node_mapper import classify_connections, compute_stage_zones, map_tree


def export_workflow(tree: DomainTaskTree) -> N8nWorkflow:
    nodes, connections = map_tree(tree)
    zones, _ = compute_stage_zones(tree)
    classifications = classify_connections(tree)
    return N8nWorkflow(
        name=tree.domain,
        nodes=nodes,
        connections=connections,
        stage_zones=zones,
        connection_classifications=[
            N8nConnectionClassification(source_step_id=source_id, target_step_id=target_id, classification=tag)
            for (source_id, target_id), tag in classifications.items()
        ],
    )
