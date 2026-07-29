"""WP14 (Disaster recovery: application-level backup/export, AFDF Phase 11 section 14)
tests.

Backup strategy relies primarily on the managed Postgres/Supabase platform's own
mechanism (unchanged, not something this codebase configures) -- this covers the
secondary, defense-in-depth export/restore-one-project script
(scripts/backup_export.py). Real throwaway projects against the live DB, self-cleaning
via try/finally; export files are written to pytest's tmp_path, never the real backups/
directory.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import backup_export  # noqa: E402

from backend import storage  # noqa: E402

TEST_PREFIX = "__WP14_TEST__"


@pytest.fixture
def throwaway_project():
    project = storage.create_project(f"{TEST_PREFIX}project")
    try:
        yield project
    finally:
        try:
            storage.delete_project(project.id)
        except Exception:
            pass


# ---------- Unit tests: export ----------


def test_export_includes_a_real_throwaway_project(throwaway_project, tmp_path):
    output_path = backup_export.export_all_projects(output_dir=tmp_path)
    manifest = backup_export.load_backup(output_path)
    ids = {p["id"] for p in manifest["projects"]}
    assert throwaway_project.id in ids
    assert manifest["project_count"] == len(manifest["projects"])


def test_export_manifest_has_expected_top_level_keys(throwaway_project, tmp_path):
    output_path = backup_export.export_all_projects(output_dir=tmp_path)
    manifest = backup_export.load_backup(output_path)
    assert "exported_at" in manifest
    assert "project_count" in manifest
    assert "projects" in manifest


def test_list_backup_contents_returns_id_name_pairs(throwaway_project, tmp_path):
    output_path = backup_export.export_all_projects(output_dir=tmp_path)
    contents = backup_export.list_backup_contents(output_path)
    assert (throwaway_project.id, throwaway_project.name) in contents


# ---------- Unit tests: restore ----------


def test_restore_recreates_a_deleted_project(throwaway_project, tmp_path):
    project_id = throwaway_project.id
    project_name = throwaway_project.name

    output_path = backup_export.export_all_projects(output_dir=tmp_path)
    storage.delete_project(project_id)  # simulate the disaster

    restored = backup_export.restore_project(output_path, project_id)
    assert restored.id == project_id
    assert restored.name == project_name

    reloaded = storage.load_project(project_id)
    assert reloaded.name == project_name


def test_restore_raises_for_project_id_not_in_backup(throwaway_project, tmp_path):
    output_path = backup_export.export_all_projects(output_dir=tmp_path)
    with pytest.raises(ValueError):
        backup_export.restore_project(output_path, "nonexistent-id-xyz")
