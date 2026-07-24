import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException

from .models import Comment, Project, Reference, TemplateNode, ValidationIssue, ValidationReport


def find_root_id(project: Project) -> str:
    for node in project.nodes.values():
        if node.parent_id is None:
            return node.id
    raise HTTPException(status_code=500, detail="Project has no root node")


def compute_level(project: Project, node_id: str) -> int:
    """Depth from root, root = level 1. Walks parent_id chain. Group nodes (is_group=True)
    are level-transparent: organizing a node's children into a group never changes the
    level number its real descendants show, since a group isn't a real architecture layer,
    just a display-time grouping of items that already belong to the same level."""
    level = 1
    seen = set()
    current = project.nodes.get(node_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Node not found")
    while current.parent_id is not None:
        if current.id in seen:
            raise HTTPException(status_code=500, detail="Cycle detected in tree")
        seen.add(current.id)
        parent = project.nodes.get(current.parent_id)
        if parent is None:
            raise HTTPException(status_code=500, detail="Broken parent reference")
        if not parent.is_group:
            level += 1
        current = parent
    return level


def get_node_or_404(project: Project, node_id: str):
    node = project.nodes.get(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


def get_canvas_object_or_404(project: Project, object_id: str):
    """Anything a reference/connector can point at: an architecture node OR a free (concept)
    object — connectors are not exclusive to the hierarchy."""
    node = project.nodes.get(object_id)
    if node is not None:
        return node
    for obj in project.concept_objects:
        if obj.id == object_id:
            return obj
    raise HTTPException(status_code=404, detail="Node or object not found")


def canvas_object_label(project: Project, object_id: str) -> str:
    node = project.nodes.get(object_id)
    if node is not None:
        return node.label
    for obj in project.concept_objects:
        if obj.id == object_id:
            return obj.text or obj.type
    return "?"


def add_node(
    project: Project,
    parent_id: str,
    label: str,
    node_id: str,
    insert_after: Optional[str] = None,
    is_group: bool = False,
) -> None:
    from .models import Node

    parent = get_node_or_404(project, parent_id)
    max_per_row = 5
    index = len(parent.children)
    row, col = divmod(index, max_per_row)
    default_x = parent.canvas_x + col * 170
    default_y = parent.canvas_y + 150 + row * 130
    new_node = Node(
        id=node_id, label=label, parent_id=parent_id, canvas_x=default_x, canvas_y=default_y, is_group=is_group
    )
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
    if node.locked:
        raise HTTPException(status_code=400, detail="This component is locked — unlock it before deleting")
    parent = project.nodes[node.parent_id]
    index = parent.children.index(node_id)

    if promote_children:
        for child_id in node.children:
            project.nodes[child_id].parent_id = node.parent_id
        parent.children[index:index + 1] = node.children
        del project.nodes[node_id]
        removed_ids = {node_id}
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
        removed_ids = set(to_delete)

    project.references = [
        r for r in project.references if r.from_ not in removed_ids and r.to not in removed_ids
    ]


def rename_node(
    project: Project,
    node_id: str,
    label: Optional[str],
    notes: Optional[str],
    collapsed: Optional[bool] = None,
    node_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    complexity: Optional[str] = None,
    risk_level: Optional[str] = None,
    tags: Optional[List[str]] = None,
    owner: Optional[str] = None,
    shape: Optional[str] = None,
    group_children: Optional[bool] = None,
    is_group: Optional[bool] = None,
    classification: Optional[str] = None,
    custom_color: Optional[str] = None,
    planning_status: Optional[str] = None,
    locked: Optional[bool] = None,
) -> None:
    node = get_node_or_404(project, node_id)
    is_editing = any(
        v is not None
        for v in (label, notes, node_type, status, priority, complexity, risk_level, tags, owner, classification, custom_color, planning_status)
    )
    if node.locked and is_editing and locked is None:
        raise HTTPException(status_code=400, detail="This component is locked")
    if label is not None:
        node.label = label
    if notes is not None:
        node.notes = notes
    if collapsed is not None:
        node.collapsed = collapsed
    if node_type is not None:
        node.node_type = node_type
    if status is not None:
        node.status = status
    if priority is not None:
        node.priority = priority
    if complexity is not None:
        node.complexity = complexity
    if risk_level is not None:
        node.risk_level = risk_level
    if tags is not None:
        node.tags = tags
    if owner is not None:
        node.owner = owner
    if shape is not None:
        node.shape = shape
    if group_children is not None:
        node.group_children = group_children
    if is_group is not None:
        node.is_group = is_group
    if classification is not None:
        node.classification = classification
    if custom_color is not None:
        node.custom_color = custom_color
    if planning_status is not None:
        node.planning_status = planning_status
    if locked is not None:
        node.locked = locked


def move_sibling(project: Project, node_id: str, direction: str) -> None:
    """Reorder node_id one position earlier ("up") or later ("down") among its siblings."""
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot reorder the root node")
    parent = project.nodes[node.parent_id]
    idx = parent.children.index(node_id)
    if direction == "up":
        if idx == 0:
            raise HTTPException(status_code=400, detail="Already first among its siblings")
        parent.children[idx - 1], parent.children[idx] = parent.children[idx], parent.children[idx - 1]
    elif direction == "down":
        if idx == len(parent.children) - 1:
            raise HTTPException(status_code=400, detail="Already last among its siblings")
        parent.children[idx + 1], parent.children[idx] = parent.children[idx], parent.children[idx + 1]
    else:
        raise HTTPException(status_code=400, detail="direction must be 'up' or 'down'")


def move_node_position(project: Project, node_id: str, canvas_x: float, canvas_y: float) -> None:
    node = get_node_or_404(project, node_id)
    if node.locked:
        raise HTTPException(status_code=400, detail="This component is locked")
    node.canvas_x = canvas_x
    node.canvas_y = canvas_y


def arrange_children(project: Project, node_id: str) -> None:
    """Re-lay-out a node's direct children into a wrapped grid centered under it,
    instead of whatever scattered positions they've accumulated (e.g. from a bulk import
    or a lot of manual dragging). Does not touch grandchildren."""
    node = get_node_or_404(project, node_id)
    max_per_row = 5
    count = len(node.children)
    if count == 0:
        return
    rows = (count + max_per_row - 1) // max_per_row
    for index, child_id in enumerate(node.children):
        row, col = divmod(index, max_per_row)
        cols_in_this_row = min(max_per_row, count - row * max_per_row)
        row_offset_x = -(cols_in_this_row - 1) * 170 / 2
        child = project.nodes[child_id]
        child.canvas_x = node.canvas_x + row_offset_x + col * 170
        child.canvas_y = node.canvas_y + 150 + row * 130


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


def reparent_node(project: Project, node_id: str, new_parent_id: str) -> None:
    """Move node_id to become a child of new_parent_id (e.g. dragging its tree edge onto
    a different node). Root can't be reparented this way — use promote_to_root instead."""
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot reparent the root node this way")
    if node.locked:
        raise HTTPException(status_code=400, detail="This component is locked")
    new_parent = get_node_or_404(project, new_parent_id)
    if new_parent_id == node_id:
        raise HTTPException(status_code=400, detail="A node cannot be its own parent")
    if node.parent_id == new_parent_id:
        return
    if _is_ancestor(project, node_id, new_parent_id):
        raise HTTPException(status_code=400, detail="Cannot move a node under its own descendant")

    old_parent = project.nodes[node.parent_id]
    old_parent.children.remove(node_id)
    new_parent.children.append(node_id)
    node.parent_id = new_parent_id


def promote_to_root(project: Project, node_id: str) -> None:
    """Re-root the tree at node_id. Reverses the chain of parent links from node_id up to
    the current root; every other subtree stays attached exactly where it was."""
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="This node is already the root")

    path = []
    current = node_id
    while project.nodes[current].parent_id is not None:
        path.append(current)
        current = project.nodes[current].parent_id
    path.append(current)  # current is now the old root

    for i in range(len(path) - 1):
        child_id = path[i]
        old_parent_id = path[i + 1]
        child_node = project.nodes[child_id]
        old_parent_node = project.nodes[old_parent_id]
        if child_id in old_parent_node.children:
            old_parent_node.children.remove(child_id)
        child_node.children.append(old_parent_id)
        old_parent_node.parent_id = child_id

    node.parent_id = None


def add_reference(
    project: Project, from_id: str, to_id: str, label: Optional[str], reference_type: Optional[str] = None
) -> Reference:
    get_canvas_object_or_404(project, from_id)
    get_canvas_object_or_404(project, to_id)
    if from_id == to_id:
        raise HTTPException(status_code=400, detail="Cannot reference a node to itself")
    ref = Reference(id=str(uuid.uuid4()), **{"from": from_id}, to=to_id, label=label, reference_type=reference_type)
    project.references.append(ref)
    return ref


def delete_reference(project: Project, reference_id: str) -> None:
    before = len(project.references)
    project.references = [r for r in project.references if r.id != reference_id]
    if len(project.references) == before:
        raise HTTPException(status_code=404, detail="Reference not found")


def update_reference(
    project: Project,
    reference_id: str,
    from_id: Optional[str],
    to_id: Optional[str],
    label: Optional[str],
    reference_type: Optional[str] = None,
    custom_color: Optional[str] = None,
    thickness: Optional[str] = None,
    direction: Optional[str] = None,
    animated: Optional[bool] = None,
    connector_hidden: Optional[bool] = None,
    line_style: Optional[str] = None,
    opacity: Optional[float] = None,
    show_arrowhead: Optional[bool] = None,
    curve_style: Optional[str] = None,
    animation_speed: Optional[float] = None,
) -> Reference:
    ref = next((r for r in project.references if r.id == reference_id), None)
    if ref is None:
        raise HTTPException(status_code=404, detail="Reference not found")
    new_from = from_id if from_id is not None else ref.from_
    new_to = to_id if to_id is not None else ref.to
    get_canvas_object_or_404(project, new_from)
    get_canvas_object_or_404(project, new_to)
    if new_from == new_to:
        raise HTTPException(status_code=400, detail="Cannot reference a node to itself")
    ref.from_ = new_from
    ref.to = new_to
    if label is not None:
        ref.label = label
    if custom_color is not None:
        ref.custom_color = custom_color or None
    if thickness is not None:
        ref.thickness = thickness or None
    if direction is not None:
        ref.direction = direction or None
    if animated is not None:
        ref.animated = animated
    if connector_hidden is not None:
        ref.connector_hidden = connector_hidden
    if reference_type is not None:
        ref.reference_type = reference_type or None
    if line_style is not None:
        ref.line_style = line_style or None
    if opacity is not None:
        ref.opacity = opacity
    if show_arrowhead is not None:
        ref.show_arrowhead = show_arrowhead
    if curve_style is not None:
        ref.curve_style = curve_style or None
    if animation_speed is not None:
        ref.animation_speed = animation_speed
    return ref


def add_comment(project: Project, node_id: str, text: str) -> Comment:
    node = get_node_or_404(project, node_id)
    comment = Comment(id=str(uuid.uuid4()), text=text, created_at=datetime.now(timezone.utc).isoformat())
    node.comments.append(comment)
    return comment


def delete_comment(project: Project, node_id: str, comment_id: str) -> None:
    node = get_node_or_404(project, node_id)
    before = len(node.comments)
    node.comments = [c for c in node.comments if c.id != comment_id]
    if len(node.comments) == before:
        raise HTTPException(status_code=404, detail="Comment not found")


def log_activity(project: Project, message: str) -> None:
    from .models import ActivityEntry

    entry = ActivityEntry(id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc).isoformat(), message=message)
    project.activity_log.append(entry)
    project.activity_log = project.activity_log[-200:]


def subtree_depth(project: Project, node_id: str) -> int:
    """Deepest level (absolute, root=1) reached anywhere in node_id's subtree."""
    node = project.nodes[node_id]
    deepest = compute_level(project, node_id)
    for child_id in node.children:
        deepest = max(deepest, subtree_depth(project, child_id))
    return deepest


def capture_template(project: Project, node_id: str) -> TemplateNode:
    node = get_node_or_404(project, node_id)
    return TemplateNode(
        label=node.label,
        notes=node.notes,
        children=[capture_template(project, child_id) for child_id in node.children],
    )


def apply_template(project: Project, parent_id: str, template_node: TemplateNode) -> str:
    """Instantiate a TemplateNode tree as new children under parent_id. Returns new root node id."""
    new_id = str(uuid.uuid4())
    add_node(project, parent_id, template_node.label, new_id)
    project.nodes[new_id].notes = template_node.notes
    for child_template in template_node.children:
        apply_template(project, new_id, child_template)
    return new_id


def duplicate_node(project: Project, node_id: str) -> str:
    """Copy node_id's whole subtree as a new sibling right after it. Returns the new node id."""
    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(status_code=400, detail="Cannot duplicate the root node")
    captured = capture_template(project, node_id)
    new_id = str(uuid.uuid4())
    add_node(project, node.parent_id, captured.label, new_id, insert_after=node_id)
    project.nodes[new_id].notes = captured.notes
    for child_template in captured.children:
        apply_template(project, new_id, child_template)
    return new_id


def add_parent_above(project: Project, node_id: str, label: str) -> str:
    """Insert a new node between node_id and its current parent, so node_id becomes a
    child of this new node instead of its old parent. Returns the new parent's id."""
    from .models import Node

    node = get_node_or_404(project, node_id)
    if node.parent_id is None:
        raise HTTPException(
            status_code=400, detail="Cannot add a parent above the root — promote a different node to root instead"
        )
    old_parent = project.nodes[node.parent_id]
    idx = old_parent.children.index(node_id)
    new_id = str(uuid.uuid4())
    new_node = Node(
        id=new_id, label=label, parent_id=old_parent.id, canvas_x=node.canvas_x, canvas_y=node.canvas_y - 60,
        children=[node_id],
    )
    project.nodes[new_id] = new_node
    old_parent.children[idx] = new_id
    node.parent_id = new_id
    return new_id


# ---------- Validation / health ----------


def find_reference_cycles(project: Project) -> List[List[str]]:
    graph: dict = {}
    for r in project.references:
        graph.setdefault(r.from_, []).append(r.to)

    visited = set()
    in_stack = set()
    path: List[str] = []
    cycles: List[List[str]] = []

    def dfs(node_id: str) -> None:
        visited.add(node_id)
        in_stack.add(node_id)
        path.append(node_id)
        for neighbor in graph.get(node_id, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in in_stack:
                idx = path.index(neighbor)
                cycle_ids = path[idx:] + [neighbor]
                labels = [project.nodes[n].label for n in cycle_ids if n in project.nodes]
                cycles.append(labels)
        path.pop()
        in_stack.remove(node_id)

    for node_id in list(graph.keys()):
        if node_id not in visited:
            dfs(node_id)

    return cycles


def build_validation_report(project: Project) -> ValidationReport:
    label_counts: dict = {}
    single_child: list = []
    large_modules: list = []
    missing_notes: list = []
    missing_owners: list = []
    risk_distribution: dict = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0, "Unset": 0}
    depths: list = []

    root_id = find_root_id(project)
    reachable: set = set()
    stack = [root_id]
    while stack:
        current_id = stack.pop()
        if current_id in reachable or current_id not in project.nodes:
            continue
        reachable.add(current_id)
        stack.extend(project.nodes[current_id].children)
    orphan_nodes = [
        ValidationIssue(id=n.id, label=n.label) for n in project.nodes.values() if n.id not in reachable
    ]

    for node in project.nodes.values():
        label_counts[node.label] = label_counts.get(node.label, 0) + 1
        if len(node.children) == 1:
            single_child.append(ValidationIssue(id=node.id, label=node.label))
        if len(node.children) > 10:
            large_modules.append(ValidationIssue(id=node.id, label=node.label))
        if not node.notes.strip():
            missing_notes.append(ValidationIssue(id=node.id, label=node.label))
        if not node.is_group and not (node.owner or "").strip():
            missing_owners.append(ValidationIssue(id=node.id, label=node.label))
        risk_distribution[node.risk_level or "Unset"] = risk_distribution.get(node.risk_level or "Unset", 0) + 1
        if node.id in reachable:
            depths.append(compute_level(project, node.id))

    duplicate_labels = [
        ValidationIssue(id=n.id, label=n.label)
        for n in project.nodes.values()
        if label_counts[n.label] > 1
    ]
    circular_references = find_reference_cycles(project)

    node_ids = set(project.nodes.keys())
    canvas_object_ids = node_ids | {obj.id for obj in project.concept_objects}
    broken_references = [
        f"Reference '{r.label or r.id}' points to an object that no longer exists"
        for r in project.references
        if r.from_ not in canvas_object_ids or r.to not in canvas_object_ids
    ]

    avg_depth = round(sum(depths) / len(depths), 2) if depths else 0.0
    max_depth = max(depths) if depths else 0

    penalty = (
        5 * len(duplicate_labels)
        + 15 * len(circular_references)
        + 3 * len(large_modules)
        + 2 * len(single_child)
        + 1 * len(missing_notes)
        + 2 * len(missing_owners)
        + 10 * len(orphan_nodes)
        + 10 * len(broken_references)
    )
    score = max(0, min(100, 100 - penalty))
    if score >= 90:
        rating = "Excellent"
    elif score >= 75:
        rating = "Good"
    elif score >= 50:
        rating = "Fair"
    elif score >= 25:
        rating = "Poor"
    else:
        rating = "Critical"

    return ValidationReport(
        score=score,
        rating=rating,
        duplicate_labels=duplicate_labels,
        circular_references=circular_references,
        large_modules=large_modules,
        single_child_nodes=single_child,
        missing_notes=missing_notes,
        missing_owners=missing_owners,
        orphan_nodes=orphan_nodes,
        broken_references=broken_references,
        avg_depth=avg_depth,
        max_depth=max_depth,
        risk_distribution=risk_distribution,
    )


# ---------- Outline text import ----------

_BULLET_STRIP_RE = re.compile(r"^[\s│├└─\-•*|]+")
_LEVEL_TAG_RE = re.compile(r"\(\s*level\s*(\d+)\s*\)", re.IGNORECASE)
_LONE_LEVEL_TAG_RE = re.compile(r"^[\s│├└─\-•*|]*\(\s*level\s*\d+\s*\)[\s│├└─\-•*|]*$", re.IGNORECASE)


def _merge_orphan_level_tags(lines: list) -> list:
    """If a '(Level N)' tag lands alone on its own line (e.g. from a copy-pasted
    multi-column ASCII diagram), merge it onto the previous line instead of dropping it."""
    merged: list = []
    for line in lines:
        if _LONE_LEVEL_TAG_RE.match(line) and merged:
            merged[-1] = merged[-1].rstrip() + " " + line.strip()
        else:
            merged.append(line)
    return merged


def parse_outline_text(text: str) -> TemplateNode:
    """Parse an indented outline (optionally with explicit '(Level N)' tags, matching
    this app's own Markdown export format or a level-annotated tree like ASCII art) into
    a TemplateNode tree."""
    raw_lines = [line for line in text.splitlines() if line.strip()]
    if not raw_lines:
        raise HTTPException(status_code=400, detail="No parseable lines found in outline text")
    raw_lines = _merge_orphan_level_tags(raw_lines)

    entries = []  # list of (level, label)
    # Dynamic indentation stack: (raw_indent, level) pairs for the currently-open path.
    # Lines with an explicit '(Level N)' tag are authoritative anchors; lines without one
    # are placed relative to the nearest open ancestor by raw indentation. This handles a
    # mix of tagged and untagged lines (e.g. pasted ASCII trees that only annotate some
    # nodes), not just an all-tagged or all-untagged file.
    indent_stack: list = []

    for line in raw_lines:
        tag_match = _LEVEL_TAG_RE.search(line)
        working = _LEVEL_TAG_RE.sub("", line) if tag_match else line
        # Count the *entire* leading run of whitespace/box-drawing/bullet characters as
        # indent width, not just literal spaces — ASCII tree art ("│   ├── Item") signals
        # depth through repeated fixed-width prefixes made of "│", "─", "├", "└", etc.,
        # and treating those as plain non-indent characters flattens the whole structure.
        bullet_match = _BULLET_STRIP_RE.match(working)
        raw_indent = len(bullet_match.group(0)) if bullet_match else 0
        label = _BULLET_STRIP_RE.sub("", working).strip()
        if not label:
            continue

        if tag_match:
            level = int(tag_match.group(1))
            indent_stack = [(i, lv) for (i, lv) in indent_stack if lv < level]
        else:
            while indent_stack and raw_indent <= indent_stack[-1][0]:
                indent_stack.pop()
            level = indent_stack[-1][1] + 1 if indent_stack else 1
        indent_stack.append((raw_indent, level))
        entries.append((level, label))

    if not entries:
        raise HTTPException(status_code=400, detail="No parseable lines found in outline text")

    root_template: Optional[TemplateNode] = None
    stack: dict = {}

    for level, label in entries:
        node = TemplateNode(label=label, notes="", children=[])
        if root_template is None:
            root_template = node
            stack[max(level, 1)] = node
            continue

        parent_level = level - 1
        parent = stack.get(parent_level)
        if parent is None:
            candidates = [lv for lv in stack if lv < level]
            parent = stack[max(candidates)] if candidates else root_template
        parent.children.append(node)
        stack[level] = node
        for lv in list(stack.keys()):
            if lv > level:
                del stack[lv]

    return root_template
