import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from . import concept, storage, tree
from .models import (
    AddParentRequest,
    Comment,
    CommentCreate,
    ConceptObject,
    ConceptObjectCreate,
    ConceptObjectUpdate,
    ConvertToNodeRequest,
    MoveSiblingRequest,
    NodeCreate,
    NodePosition,
    NodeUpdate,
    NodeWithLevel,
    OutlineImport,
    PasteSubtreeRequest,
    Project,
    ProjectCreate,
    ProjectRename,
    ProjectSummary,
    Reference,
    ReferenceCreate,
    ReferenceUpdate,
    ReparentRequest,
    Template,
    TemplateCreate,
    TemplateNode,
    TemplateSummary,
    ValidationReport,
)

router = APIRouter(prefix="/api")


def _project_with_levels(project: Project) -> dict:
    data = project.model_dump(by_alias=True)
    for node_id, node_data in data["nodes"].items():
        node_data["level"] = tree.compute_level(project, node_id)
    return data


@router.get("/projects", response_model=list[ProjectSummary])
def api_list_projects():
    return storage.list_projects()


@router.post("/projects", response_model=Project, status_code=201)
def api_create_project(body: ProjectCreate):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return storage.create_project(body.name.strip())


@router.post("/projects/from-outline", response_model=Project, status_code=201)
def api_create_project_from_outline(body: OutlineImport, name: Optional[str] = Query(None)):
    root_template = tree.parse_outline_text(body.text)
    project_name = name.strip() if name and name.strip() else root_template.label
    project = storage.create_project(project_name)
    root_id = next(iter(project.nodes))
    project.nodes[root_id].label = root_template.label
    project.nodes[root_id].notes = root_template.notes
    for child_template in root_template.children:
        tree.apply_template(project, root_id, child_template)
    tree.log_activity(project, f"Created project from imported outline ({len(project.nodes)} nodes)")
    storage.save_project(project)
    return project


@router.get("/projects/{project_id}")
def api_get_project(project_id: str):
    project = storage.load_project(project_id)
    return _project_with_levels(project)


@router.get("/projects/{project_id}/raw", response_model=Project)
def api_get_project_raw(project_id: str):
    """Exact on-disk file format, no computed fields — used for JSON export."""
    return storage.load_project(project_id)


@router.get("/projects/{project_id}/validation", response_model=ValidationReport)
def api_get_validation(project_id: str):
    project = storage.load_project(project_id)
    return tree.build_validation_report(project)


@router.put("/projects/{project_id}", response_model=Project)
def api_rename_project(project_id: str, body: ProjectRename):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return storage.rename_project(project_id, body.name.strip())


@router.delete("/projects/{project_id}", status_code=204)
def api_delete_project(project_id: str):
    storage.delete_project(project_id)


@router.put("/projects/{project_id}/restore", response_model=Project)
def api_restore_project(project_id: str, body: Project):
    """Overwrites the whole project with a client-supplied snapshot. Used by the editor's
    Undo/Redo, which keeps prior project states in memory and replays them wholesale
    rather than trying to compute a structural inverse for every possible edit."""
    storage.load_project(project_id)  # 404s if the project doesn't exist
    body.id = project_id
    storage.save_project(body)
    return body


@router.post("/projects/{project_id}/nodes", response_model=NodeWithLevel, status_code=201)
def api_add_node(project_id: str, body: NodeCreate):
    project = storage.load_project(project_id)
    node_id = str(uuid.uuid4())
    tree.add_node(project, body.parent_id, body.label, node_id, body.insert_after, body.is_group)
    tree.log_activity(project, f"Added {'group' if body.is_group else 'node'} '{body.label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.put("/projects/{project_id}/nodes/{node_id}", response_model=NodeWithLevel)
def api_update_node(project_id: str, node_id: str, body: NodeUpdate):
    project = storage.load_project(project_id)
    old_label = project.nodes[node_id].label
    tree.rename_node(
        project,
        node_id,
        body.label,
        body.notes,
        body.collapsed,
        body.node_type,
        body.status,
        body.priority,
        body.complexity,
        body.risk_level,
        body.tags,
        body.owner,
        body.shape,
        body.group_children,
        body.is_group,
        body.classification,
        body.custom_color,
        body.planning_status,
    )
    if body.label is not None and body.label != old_label:
        tree.log_activity(project, f"Renamed '{old_label}' to '{body.label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/move-sibling", response_model=NodeWithLevel)
def api_move_sibling(project_id: str, node_id: str, body: MoveSiblingRequest):
    project = storage.load_project(project_id)
    tree.move_sibling(project, node_id, body.direction)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.delete("/projects/{project_id}/nodes/{node_id}", status_code=204)
def api_delete_node(project_id: str, node_id: str, promote_children: bool = Query(False)):
    project = storage.load_project(project_id)
    label = project.nodes[node_id].label
    tree.delete_node(project, node_id, promote_children)
    tree.log_activity(project, f"Deleted node '{label}'")
    storage.save_project(project)


@router.put("/projects/{project_id}/nodes/{node_id}/position", response_model=NodeWithLevel)
def api_move_node(project_id: str, node_id: str, body: NodePosition):
    project = storage.load_project(project_id)
    tree.move_node_position(project, node_id, body.canvas_x, body.canvas_y)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/indent", response_model=NodeWithLevel)
def api_indent_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.indent_node(project, node_id)
    tree.log_activity(project, f"Indented '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/arrange-children", response_model=NodeWithLevel)
def api_arrange_children(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.arrange_children(project, node_id)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/reparent", response_model=NodeWithLevel)
def api_reparent_node(project_id: str, node_id: str, body: ReparentRequest):
    project = storage.load_project(project_id)
    old_parent_label = project.nodes[project.nodes[node_id].parent_id].label if project.nodes[node_id].parent_id else "?"
    tree.reparent_node(project, node_id, body.new_parent_id)
    new_parent_label = project.nodes[body.new_parent_id].label
    tree.log_activity(
        project, f"Moved '{project.nodes[node_id].label}' from '{old_parent_label}' to '{new_parent_label}'"
    )
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/promote-to-root", response_model=NodeWithLevel)
def api_promote_to_root(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    label = project.nodes[node_id].label
    tree.promote_to_root(project, node_id)
    tree.log_activity(project, f"Promoted '{label}' to be the new root")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/duplicate", response_model=NodeWithLevel, status_code=201)
def api_duplicate_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    label = project.nodes[node_id].label
    new_id = tree.duplicate_node(project, node_id)
    tree.log_activity(project, f"Duplicated '{label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


@router.post("/projects/{project_id}/nodes/{node_id}/add-parent", response_model=NodeWithLevel, status_code=201)
def api_add_parent(project_id: str, node_id: str, body: AddParentRequest):
    project = storage.load_project(project_id)
    child_label = project.nodes[node_id].label
    new_id = tree.add_parent_above(project, node_id, body.label)
    tree.log_activity(project, f"Inserted '{body.label}' as new parent of '{child_label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


@router.get("/projects/{project_id}/nodes/{node_id}/subtree", response_model=TemplateNode)
def api_get_subtree(project_id: str, node_id: str):
    """Serializes a node's subtree structure — used for both Copy (client holds it for a
    later Paste) and Export Subtree (client downloads it as JSON)."""
    project = storage.load_project(project_id)
    return tree.capture_template(project, node_id)


@router.post("/projects/{project_id}/nodes/{node_id}/paste-subtree", response_model=NodeWithLevel, status_code=201)
def api_paste_subtree(project_id: str, node_id: str, body: PasteSubtreeRequest):
    project = storage.load_project(project_id)
    new_id = tree.apply_template(project, node_id, body.root)
    tree.log_activity(project, f"Pasted '{body.root.label}' under '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


@router.post("/projects/{project_id}/nodes/{node_id}/outdent", response_model=NodeWithLevel)
def api_outdent_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.outdent_node(project, node_id)
    tree.log_activity(project, f"Outdented '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


# ---------- References ----------


@router.post("/projects/{project_id}/references", response_model=Reference, status_code=201)
def api_add_reference(project_id: str, body: ReferenceCreate):
    project = storage.load_project(project_id)
    ref = tree.add_reference(project, body.from_, body.to, body.label, body.reference_type)
    tree.log_activity(
        project, f"Linked '{project.nodes[body.from_].label}' -> '{project.nodes[body.to].label}'"
    )
    storage.save_project(project)
    return ref


@router.put("/projects/{project_id}/references/{reference_id}", response_model=Reference)
def api_update_reference(project_id: str, reference_id: str, body: ReferenceUpdate):
    project = storage.load_project(project_id)
    ref = tree.update_reference(
        project,
        reference_id,
        body.from_,
        body.to,
        body.label,
        body.reference_type,
        body.custom_color,
        body.thickness,
        body.direction,
        body.animated,
        body.connector_hidden,
    )
    tree.log_activity(
        project, f"Relinked reference to '{project.nodes[ref.from_].label}' -> '{project.nodes[ref.to].label}'"
    )
    storage.save_project(project)
    return ref


@router.delete("/projects/{project_id}/references/{reference_id}", status_code=204)
def api_delete_reference(project_id: str, reference_id: str):
    project = storage.load_project(project_id)
    tree.delete_reference(project, reference_id)
    storage.save_project(project)


# ---------- Comments ----------


@router.post("/projects/{project_id}/nodes/{node_id}/comments", response_model=Comment, status_code=201)
def api_add_comment(project_id: str, node_id: str, body: CommentCreate):
    project = storage.load_project(project_id)
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Comment text cannot be empty")
    comment = tree.add_comment(project, node_id, body.text.strip())
    storage.save_project(project)
    return comment


@router.delete("/projects/{project_id}/nodes/{node_id}/comments/{comment_id}", status_code=204)
def api_delete_comment(project_id: str, node_id: str, comment_id: str):
    project = storage.load_project(project_id)
    tree.delete_comment(project, node_id, comment_id)
    storage.save_project(project)


# ---------- Templates ----------


@router.get("/templates", response_model=list[TemplateSummary])
def api_list_templates():
    return storage.list_templates()


@router.post("/projects/{project_id}/nodes/{node_id}/save-as-template", response_model=Template, status_code=201)
def api_save_as_template(project_id: str, node_id: str, body: TemplateCreate):
    project = storage.load_project(project_id)
    root = tree.capture_template(project, node_id)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return storage.save_new_template(body.name.strip(), root)


@router.delete("/templates/{template_id}", status_code=204)
def api_delete_template(template_id: str):
    storage.delete_template(template_id)


@router.post("/projects/{project_id}/nodes/{node_id}/apply-template/{template_id}", response_model=NodeWithLevel, status_code=201)
def api_apply_template(project_id: str, node_id: str, template_id: str):
    project = storage.load_project(project_id)
    template = storage.load_template(template_id)
    new_id = tree.apply_template(project, node_id, template.root)
    tree.log_activity(project, f"Applied template '{template.name}' under '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


# ---------- Outline import ----------


@router.post("/projects/{project_id}/nodes/{node_id}/import-outline", response_model=NodeWithLevel, status_code=201)
def api_import_outline_under_node(project_id: str, node_id: str, body: OutlineImport):
    project = storage.load_project(project_id)
    root_template = tree.parse_outline_text(body.text)
    new_id = tree.apply_template(project, node_id, root_template)
    tree.log_activity(project, f"Imported outline under '{project.nodes[node_id].label}'")
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))


# ---------- Concept Mode: freeform planning objects ----------


@router.post("/projects/{project_id}/concept-objects", response_model=ConceptObject, status_code=201)
def api_add_concept_object(project_id: str, body: ConceptObjectCreate):
    project = storage.load_project(project_id)
    obj = concept.add_object(project, body.type, body.x, body.y, body.width, body.height, body.text, body.color)
    storage.save_project(project)
    return obj


@router.put("/projects/{project_id}/concept-objects/{object_id}", response_model=ConceptObject)
def api_update_concept_object(project_id: str, object_id: str, body: ConceptObjectUpdate):
    project = storage.load_project(project_id)
    obj = concept.update_object(
        project,
        object_id,
        body.x,
        body.y,
        body.width,
        body.height,
        body.rotation,
        body.text,
        body.color,
        body.border_style,
        body.z_index,
        body.locked,
    )
    storage.save_project(project)
    return obj


@router.delete("/projects/{project_id}/concept-objects/{object_id}", status_code=204)
def api_delete_concept_object(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    concept.delete_object(project, object_id)
    storage.save_project(project)


@router.post("/projects/{project_id}/concept-objects/{object_id}/duplicate", response_model=ConceptObject, status_code=201)
def api_duplicate_concept_object(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    obj = concept.duplicate_object(project, object_id)
    storage.save_project(project)
    return obj


@router.post("/projects/{project_id}/concept-objects/{object_id}/bring-to-front", response_model=ConceptObject)
def api_bring_concept_object_to_front(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    obj = concept.bring_to_front(project, object_id)
    storage.save_project(project)
    return obj


@router.post("/projects/{project_id}/concept-objects/{object_id}/send-to-back", response_model=ConceptObject)
def api_send_concept_object_to_back(project_id: str, object_id: str):
    project = storage.load_project(project_id)
    obj = concept.send_to_back(project, object_id)
    storage.save_project(project)
    return obj


@router.post("/projects/{project_id}/concept-objects/{object_id}/convert-to-node", response_model=NodeWithLevel, status_code=201)
def api_convert_object_to_node(project_id: str, object_id: str, body: ConvertToNodeRequest):
    project = storage.load_project(project_id)
    node = concept.convert_object_to_node(project, object_id, body.parent_id)
    tree.log_activity(project, f"Converted planning object '{node.label}' into an architecture component")
    storage.save_project(project)
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node.id))


@router.post("/projects/{project_id}/nodes/{node_id}/convert-to-object", response_model=ConceptObject, status_code=201)
def api_convert_node_to_object(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    obj = concept.convert_node_to_object(project, node_id)
    tree.log_activity(project, f"Converted '{project.nodes[node_id].label}' into a planning object")
    storage.save_project(project)
    return obj
