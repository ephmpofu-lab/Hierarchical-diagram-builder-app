"""One-time (re-runnable) migration: reads the old projects/*.json files and templates.json
directly off disk -- bypassing backend/storage.py, which now points at Postgres -- validates
them through the existing Pydantic models, and writes them into the new Postgres schema via
the same repository classes the app uses at runtime. Safe to re-run: each project/template is
upserted by its existing id, not duplicated.

Usage: python scripts/migrate_json_to_postgres.py
Requires DATABASE_URL to be set (in a local .env file, or the environment already).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.postgres_project_repository import PostgresProjectRepository
from backend.db.postgres_template_repository import PostgresTemplateRepository
from backend.models import Project, Template

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
TEMPLATES_PATH = REPO_ROOT / "templates.json"


def migrate_projects() -> None:
    repo = PostgresProjectRepository()
    files = sorted(PROJECTS_DIR.glob("*.json"))
    if not files:
        print("No project files found in", PROJECTS_DIR)
        return
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        project = Project.model_validate(data)
        repo.save(project)
        reloaded = repo.load(project.id)
        assert len(reloaded.nodes) == len(project.nodes), (
            f"Node count mismatch for {project.name}: expected {len(project.nodes)}, got {len(reloaded.nodes)}"
        )
        assert len(reloaded.references) == len(project.references), "Reference count mismatch"
        assert len(reloaded.concept_objects) == len(project.concept_objects), "Concept object count mismatch"
        assert len(reloaded.activity_log) == len(project.activity_log), "Activity log count mismatch"
        print(
            f"Migrated project '{project.name}' ({project.id}): "
            f"{len(project.nodes)} nodes, {len(project.references)} references, "
            f"{len(project.concept_objects)} concept objects, {len(project.activity_log)} activity entries -- verified."
        )


def migrate_templates() -> None:
    if not TEMPLATES_PATH.exists():
        print("No templates.json found, skipping.")
        return
    raw = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    if not raw:
        print("templates.json is empty, nothing to migrate.")
        return
    repo = PostgresTemplateRepository()
    for entry in raw:
        template = Template.model_validate(entry)
        # save_new() always mints a fresh id -- insert directly with the ORIGINAL id instead,
        # so re-running this script upserts rather than duplicating templates.
        from psycopg.types.json import Jsonb

        from backend.db.connection import get_pool

        with get_pool().connection() as conn:
            conn.execute(
                """
                insert into templates (id, name, created_at, root) values (%s, %s, %s, %s)
                on conflict (id) do update set name = excluded.name, root = excluded.root
                """,
                (template.id, template.name, template.created_at, Jsonb(template.root.model_dump())),
            )
        reloaded = repo.load(template.id)
        assert reloaded.name == template.name
        print(f"Migrated template '{template.name}' ({template.id}) -- verified.")


if __name__ == "__main__":
    migrate_projects()
    migrate_templates()
    print("Done.")
