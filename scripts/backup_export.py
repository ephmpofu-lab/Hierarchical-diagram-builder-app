"""Disaster recovery: application-level project backup/export (AFDF Phase 11 section 14,
WP14).

Per the approved Technical Architecture, backup strategy relies on the managed
Postgres/Supabase platform's own backup mechanism -- this script does not replace that,
and enabling/verifying Supabase's own backup and point-in-time recovery settings for this
project is a dashboard setting, not something this script or this codebase can configure.
This is a secondary, defense-in-depth export at the application level: e.g. to recover a
single accidentally-deleted or corrupted project without a full platform-level restore,
or to hold a portable copy of the data independent of the hosting provider.

Restore is deliberately scoped to ONE named project at a time via the existing,
already-tested save_project() path -- never a blind bulk overwrite of every project in a
backup file. A backup file can contain many projects; restoring all of them in one motion
would be exactly the kind of destructive, hard-to-reverse action this project's own
standing discipline treats with extra care.

Targets (the decision the original Phase 11 spec deferred, now set): RPO 24 hours (daily
backup cadence -- matches Supabase's default backup tier), RTO same business day (a few
hours, achievable via Supabase's own restore plus this script's restore_project() for
narrower incidents, without needing on-call/failover infrastructure this project doesn't
otherwise need yet).

Usage:
    .venv\\Scripts\\python.exe scripts\\backup_export.py                       # export all projects
    .venv\\Scripts\\python.exe scripts\\backup_export.py --list <backup.json>  # inspect a backup file
    .venv\\Scripts\\python.exe scripts\\backup_export.py --restore <backup.json> --project-id <id>
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# See scripts/run_migrations.py's own comment for why this is needed and why it's a no-op
# when imported (e.g. from tests) rather than run directly.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend import storage  # noqa: E402
from backend.models import Project  # noqa: E402

BACKUPS_DIR = Path(__file__).resolve().parent.parent / "backups"


def export_all_projects(output_dir: Path = BACKUPS_DIR) -> Path:
    output_dir.mkdir(exist_ok=True)
    summaries = storage.list_projects()
    projects = [storage.load_project(s.id).model_dump(mode="json") for s in summaries]
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_count": len(projects),
        "projects": projects,
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"backup_{timestamp}.json"
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output_path


def load_backup(backup_path: Path) -> dict:
    return json.loads(backup_path.read_text(encoding="utf-8"))


def list_backup_contents(backup_path: Path) -> list:
    manifest = load_backup(backup_path)
    return [(p["id"], p["name"]) for p in manifest["projects"]]


def restore_project(backup_path: Path, project_id: str) -> Project:
    """Restore exactly one project from a backup file via the existing save_project()
    path. Raises ValueError if the id isn't in the backup -- never silently restores a
    different project or falls back to restoring everything."""
    manifest = load_backup(backup_path)
    matches = [p for p in manifest["projects"] if p["id"] == project_id]
    if not matches:
        raise ValueError(f"Project {project_id!r} not found in backup {backup_path}")
    project = Project.model_validate(matches[0])
    storage.save_project(project)
    return project


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", metavar="BACKUP_FILE", help="List projects in a backup file")
    parser.add_argument("--restore", metavar="BACKUP_FILE", help="Restore one project from a backup file")
    parser.add_argument("--project-id", help="Project id to restore (required with --restore)")
    args = parser.parse_args()

    if args.list:
        for project_id, name in list_backup_contents(Path(args.list)):
            print(f"  {project_id}  {name}")
        return

    if args.restore:
        if not args.project_id:
            parser.error("--restore requires --project-id")
        restore_project(Path(args.restore), args.project_id)
        print(f"Restored project {args.project_id} from {args.restore}")
        return

    output_path = export_all_projects()
    manifest = load_backup(output_path)
    print(f"Exported {manifest['project_count']} project(s) to {output_path}")


if __name__ == "__main__":
    main()
