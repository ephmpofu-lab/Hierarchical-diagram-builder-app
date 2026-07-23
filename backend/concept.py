import uuid
from typing import Optional

from fastapi import HTTPException

from . import tree
from .models import ConceptObject, Node, Project

DEFAULT_SIZES = {
    "rectangle": (180, 100),
    "rounded-rectangle": (180, 100),
    "circle": (120, 120),
    "diamond": (160, 120),
    "sticky-note": (160, 140),
    "text": (160, 40),
    "divider": (240, 4),
    "arrow": (160, 4),
    "icon": (64, 64),
}


def get_object_or_404(project: Project, object_id: str) -> ConceptObject:
    for obj in project.concept_objects:
        if obj.id == object_id:
            return obj
    raise HTTPException(status_code=404, detail="Planning object not found")


def add_object(
    project: Project,
    obj_type: str,
    x: float,
    y: float,
    width: Optional[float],
    height: Optional[float],
    text: str,
    color: Optional[str],
) -> ConceptObject:
    default_w, default_h = DEFAULT_SIZES.get(obj_type, (160, 90))
    max_z = max((o.z_index for o in project.concept_objects), default=-1)
    obj = ConceptObject(
        id=str(uuid.uuid4()),
        type=obj_type,
        x=x,
        y=y,
        width=width if width is not None else default_w,
        height=height if height is not None else default_h,
        text=text,
        color=color,
        z_index=max_z + 1,
    )
    project.concept_objects.append(obj)
    return obj


def update_object(
    project: Project,
    object_id: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    width: Optional[float] = None,
    height: Optional[float] = None,
    rotation: Optional[float] = None,
    text: Optional[str] = None,
    color: Optional[str] = None,
    border_style: Optional[str] = None,
    z_index: Optional[int] = None,
) -> ConceptObject:
    obj = get_object_or_404(project, object_id)
    if x is not None:
        obj.x = x
    if y is not None:
        obj.y = y
    if width is not None:
        obj.width = width
    if height is not None:
        obj.height = height
    if rotation is not None:
        obj.rotation = rotation
    if text is not None:
        obj.text = text
    if color is not None:
        obj.color = color or None
    if border_style is not None:
        obj.border_style = border_style
    if z_index is not None:
        obj.z_index = z_index
    return obj


def delete_object(project: Project, object_id: str) -> None:
    before = len(project.concept_objects)
    project.concept_objects = [o for o in project.concept_objects if o.id != object_id]
    if len(project.concept_objects) == before:
        raise HTTPException(status_code=404, detail="Planning object not found")


def duplicate_object(project: Project, object_id: str) -> ConceptObject:
    obj = get_object_or_404(project, object_id)
    max_z = max((o.z_index for o in project.concept_objects), default=-1)
    new_obj = obj.model_copy(update={"id": str(uuid.uuid4()), "x": obj.x + 24, "y": obj.y + 24, "z_index": max_z + 1})
    project.concept_objects.append(new_obj)
    return new_obj


def bring_to_front(project: Project, object_id: str) -> ConceptObject:
    obj = get_object_or_404(project, object_id)
    max_z = max((o.z_index for o in project.concept_objects), default=0)
    obj.z_index = max_z + 1
    return obj


def send_to_back(project: Project, object_id: str) -> ConceptObject:
    obj = get_object_or_404(project, object_id)
    min_z = min((o.z_index for o in project.concept_objects), default=0)
    obj.z_index = min_z - 1
    return obj


def convert_object_to_node(project: Project, object_id: str, parent_id: str) -> Node:
    """Creates an architecture node from a planning object's text — additive, does not
    remove the planning object, so nothing about the freeform sketch is lost."""
    obj = get_object_or_404(project, object_id)
    new_id = str(uuid.uuid4())
    tree.add_node(project, parent_id, obj.text.strip() or obj.type.replace("-", " ").title(), new_id)
    return project.nodes[new_id]


def convert_node_to_object(project: Project, node_id: str) -> ConceptObject:
    """Creates a sticky-note planning object from a node's label — additive, does not
    remove the node."""
    node = tree.get_node_or_404(project, node_id)
    return add_object(project, "sticky-note", 240, 160, None, None, node.label, node.custom_color)
