import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import HTTPException

from .models import Node, Project, ProjectSummary, Template, TemplateSummary

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"
TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "templates.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.json"


def list_projects() -> List[ProjectSummary]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for path in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        summaries.append(
            ProjectSummary(
                id=data["id"],
                name=data["name"],
                updated_at=data["updated_at"],
                node_count=len(data.get("nodes", {})),
            )
        )
    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


def load_project(project_id: str) -> Project:
    path = _project_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Project.model_validate(data)


def save_project(project: Project) -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    project.updated_at = _now()
    path = _project_path(project.id)
    path.write_text(
        json.dumps(project.model_dump(by_alias=True), indent=2),
        encoding="utf-8",
    )


def create_project(name: str) -> Project:
    project_id = str(uuid.uuid4())
    root_id = str(uuid.uuid4())
    now = _now()
    root_node = Node(
        id=root_id,
        label=name,
        parent_id=None,
        children=[],
        canvas_x=400,
        canvas_y=100,
    )
    project = Project(
        id=project_id,
        name=name,
        created_at=now,
        updated_at=now,
        nodes={root_id: root_node},
        references=[],
    )
    save_project(project)
    return project


def delete_project(project_id: str) -> None:
    path = _project_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    path.unlink()


def rename_project(project_id: str, name: str) -> Project:
    project = load_project(project_id)
    project.name = name
    save_project(project)
    return project


def _count_template_nodes(node) -> int:
    return 1 + sum(_count_template_nodes(c) for c in node.children)


def _load_templates_raw() -> list:
    if not TEMPLATES_PATH.exists():
        return []
    try:
        return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_templates_raw(templates: list) -> None:
    TEMPLATES_PATH.write_text(json.dumps(templates, indent=2), encoding="utf-8")


def list_templates() -> List[TemplateSummary]:
    raw = _load_templates_raw()
    summaries = []
    for t in raw:
        template = Template.model_validate(t)
        summaries.append(
            TemplateSummary(
                id=template.id,
                name=template.name,
                created_at=template.created_at,
                node_count=_count_template_nodes(template.root),
            )
        )
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def load_template(template_id: str) -> Template:
    raw = _load_templates_raw()
    for t in raw:
        if t.get("id") == template_id:
            return Template.model_validate(t)
    raise HTTPException(status_code=404, detail="Template not found")


def save_new_template(name: str, root) -> Template:
    template = Template(id=str(uuid.uuid4()), name=name, created_at=_now(), root=root)
    raw = _load_templates_raw()
    raw.append(template.model_dump())
    _save_templates_raw(raw)
    return template


def delete_template(template_id: str) -> None:
    raw = _load_templates_raw()
    filtered = [t for t in raw if t.get("id") != template_id]
    if len(filtered) == len(raw):
        raise HTTPException(status_code=404, detail="Template not found")
    _save_templates_raw(filtered)
