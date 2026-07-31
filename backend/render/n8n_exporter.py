"""JSON Exporter (doc section 4.9) -- turns the Node Mapper's shared node/connection output
into a valid, directly-importable n8n workflow JSON. Positions and connections are never
recomputed here; this only wraps backend/render/node_mapper.py::map_tree's output into the
final export shape n8n expects (nodes[], connections{})."""

from ..models import DomainTaskTree, N8nWorkflow
from .node_mapper import map_tree


def export_workflow(tree: DomainTaskTree) -> N8nWorkflow:
    nodes, connections = map_tree(tree)
    return N8nWorkflow(name=tree.domain, nodes=nodes, connections=connections)
