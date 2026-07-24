"""Thin facade over a ProjectRepository/TemplateRepository (see backend/repository.py).
Every public function here keeps its exact pre-migration name and signature -- api.py calls
these exactly as it always has and needs zero changes. The concrete backing implementation
(Postgres via Supabase today) lives in backend/db/ and is swappable without touching this
file's callers."""

from typing import List

from .db.postgres_project_repository import PostgresProjectRepository
from .db.postgres_template_repository import PostgresTemplateRepository
from .models import Project, ProjectSummary, Template, TemplateNode, TemplateSummary
from .repository import ProjectRepository, TemplateRepository

_project_repo: ProjectRepository = PostgresProjectRepository()
_template_repo: TemplateRepository = PostgresTemplateRepository()


def list_projects() -> List[ProjectSummary]:
    return _project_repo.list_summaries()


def load_project(project_id: str) -> Project:
    return _project_repo.load(project_id)


def save_project(project: Project) -> None:
    _project_repo.save(project)


def create_project(name: str) -> Project:
    return _project_repo.create(name)


def delete_project(project_id: str) -> None:
    _project_repo.delete(project_id)


def rename_project(project_id: str, name: str) -> Project:
    return _project_repo.rename(project_id, name)


def list_templates() -> List[TemplateSummary]:
    return _template_repo.list_summaries()


def load_template(template_id: str) -> Template:
    return _template_repo.load(template_id)


def save_new_template(name: str, root: TemplateNode) -> Template:
    return _template_repo.save_new(name, root)


def delete_template(template_id: str) -> None:
    _template_repo.delete(template_id)
