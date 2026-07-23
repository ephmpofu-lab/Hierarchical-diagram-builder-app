import uuid

from fastapi import APIRouter, HTTPException, Query

from . import storage, tree
from .models import (
    NodeCreate,
    NodePosition,
    NodeUpdate,
    NodeWithLevel,
    Project,
    ProjectCreate,
    ProjectRename,
    ProjectSummary,
    Reference,
    ReferenceCreate,
    Template,
    TemplateCreate,
    TemplateSummary,
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


@router.get("/projects/{project_id}")
def api_get_project(project_id: str):
    project = storage.load_project(project_id)
    return _project_with_levels(project)


@router.get("/projects/{project_id}/raw", response_model=Project)
def api_get_project_raw(project_id: str):
    """Exact on-disk file format, no computed fields — used for JSON export."""
    return storage.load_project(project_id)


@router.put("/projects/{project_id}", response_model=Project)
def api_rename_project(project_id: str, body: ProjectRename):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return storage.rename_project(project_id, body.name.strip())


@router.delete("/projects/{project_id}", status_code=204)
def api_delete_project(project_id: str):
    storage.delete_project(project_id)


@router.post("/projects/{project_id}/nodes", response_model=NodeWithLevel, status_code=201)
def api_add_node(project_id: str, body: NodeCreate):
    project = storage.load_project(project_id)
    node_id = str(uuid.uuid4())
    tree.add_node(project, body.parent_id, body.label, node_id, body.insert_after)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.put("/projects/{project_id}/nodes/{node_id}", response_model=NodeWithLevel)
def api_update_node(project_id: str, node_id: str, body: NodeUpdate):
    project = storage.load_project(project_id)
    tree.rename_node(project, node_id, body.label, body.notes, body.collapsed)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.delete("/projects/{project_id}/nodes/{node_id}", status_code=204)
def api_delete_node(project_id: str, node_id: str, promote_children: bool = Query(False)):
    project = storage.load_project(project_id)
    tree.delete_node(project, node_id, promote_children)
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
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


@router.post("/projects/{project_id}/nodes/{node_id}/outdent", response_model=NodeWithLevel)
def api_outdent_node(project_id: str, node_id: str):
    project = storage.load_project(project_id)
    tree.outdent_node(project, node_id)
    storage.save_project(project)
    node = project.nodes[node_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, node_id))


# ---------- References ----------


@router.post("/projects/{project_id}/references", response_model=Reference, status_code=201)
def api_add_reference(project_id: str, body: ReferenceCreate):
    project = storage.load_project(project_id)
    ref = tree.add_reference(project, body.from_, body.to, body.label)
    storage.save_project(project)
    return ref


@router.delete("/projects/{project_id}/references/{reference_id}", status_code=204)
def api_delete_reference(project_id: str, reference_id: str):
    project = storage.load_project(project_id)
    tree.delete_reference(project, reference_id)
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
    storage.save_project(project)
    node = project.nodes[new_id]
    return NodeWithLevel(**node.model_dump(), level=tree.compute_level(project, new_id))
