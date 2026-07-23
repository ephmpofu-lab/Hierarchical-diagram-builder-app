from typing import Optional

from fastapi import HTTPException

from .models import Project


def find_root_id(project: Project) -> str:
    for node in project.nodes.values():
        if node.parent_id is None:
            return node.id
    raise HTTPException(status_code=500, detail="Project has no root node")


def compute_level(project: Project, node_id: str) -> int:
    """Depth from root, root = level 1. Walks parent_id chain."""
    level = 1
    seen = set()
    current = project.nodes.get(node_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Node not found")
    while current.parent_id is not None:
        if current.id in seen:
            raise HTTPException(status_code=500, detail="Cycle detected in tree")
        seen.add(current.id)
        current = project.nodes.get(current.parent_id)
        if current is None:
            raise HTTPException(status_code=500, detail="Broken parent reference")
        level += 1
    return level


def get_node_or_404(project: Project, node_id: str):
    node = project.nodes.get(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


def add_node(
    project: Project,
    parent_id: str,
    label: str,
    node_id: str,
    insert_after: Optional[str] = None,
) -> None:
    from .models import Node

    parent = get_node_or_404(project, parent_id)
    new_node = Node(id=node_id, label=label, parent_id=parent_id, canvas_x=0, canvas_y=0)
    project.nodes[node_id] = new_node
    if insert_after is not None:
        if insert_after not in parent.children:
            raise HTTPException(status_code=400, detail="insert_after is not a child of parent_id")
        index = parent.children.index(insert_after)
        parent.children.insert(index + 1, node_id)
    else:
        parent.children.append(node_id)


def _is_ancestor(project: Project, candidate_id: str, of_node_id: str) -> bool:
    """True if candidate_id is an ancestor of of_node_id (or equal)."""
    current: Optional[str] = of_node_id
    seen = set()
    while current is not None:
        if current == candidate_id:
            return True
        if current in seen:
            break
        seen.add(current)
        current = project.nodes[current].parent_id
    return False


def delete_node(project: Project, node_id: str, promote_children: bool) -> None:
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot delete the root node")
    parent = project.nodes[node.parent_id]
    index = parent.children.index(node_id)

    if promote_children:
        for child_id in node.children:
            project.nodes[child_id].parent_id = node.parent_id
        parent.children[index:index + 1] = node.children
        del project.nodes[node_id]
    else:
        # delete entire subtree
        to_delete = []
        stack = [node_id]
        while stack:
            current_id = stack.pop()
            to_delete.append(current_id)
            stack.extend(project.nodes[current_id].children)
        parent.children.remove(node_id)
        for nid in to_delete:
            del project.nodes[nid]


def rename_node(
    project: Project,
    node_id: str,
    label: Optional[str],
    notes: Optional[str],
    collapsed: Optional[bool] = None,
) -> None:
    node = get_node_or_404(project, node_id)
    if label is not None:
        node.label = label
    if notes is not None:
        node.notes = notes
    if collapsed is not None:
        node.collapsed = collapsed


def move_node_position(project: Project, node_id: str, canvas_x: float, canvas_y: float) -> None:
    node = get_node_or_404(project, node_id)
    node.canvas_x = canvas_x
    node.canvas_y = canvas_y


def indent_node(project: Project, node_id: str) -> None:
    """Make node a child of its immediately preceding sibling (appended last)."""
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot indent the root node")
    parent = project.nodes[node.parent_id]
    index = parent.children.index(node_id)
    if index == 0:
        raise HTTPException(status_code=400, detail="No preceding sibling to indent under")
    new_parent_id = parent.children[index - 1]
    parent.children.pop(index)
    node.parent_id = new_parent_id
    project.nodes[new_parent_id].children.append(node_id)


def outdent_node(project: Project, node_id: str) -> None:
    """Move node up one level: becomes sibling of its current parent, placed right after it."""
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot outdent the root node")
    old_parent = project.nodes[node.parent_id]
    if old_parent.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot outdent a top-level node past the root")
    grandparent = project.nodes[old_parent.parent_id]

    old_parent.children.remove(node_id)
    node.parent_id = grandparent.id
    parent_index = grandparent.children.index(old_parent.id)
    grandparent.children.insert(parent_index + 1, node_id)
