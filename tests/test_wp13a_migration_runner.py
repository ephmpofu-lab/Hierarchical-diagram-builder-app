"""WP13a (Migration runner formalization, Phase 11 section 12) tests.

Replaces the hand-run-SQL-in-Supabase's-editor workflow this project used through
WP1-WP11b with a real, tracked migration runner. Tests exercise the real live database
(no separate test DB exists in this project, matching every prior WP's convention) using
a throwaway isolated migrations directory (monkeypatched) so these tests never touch the
real scripts/migration_*.sql files or their already-applied tracking rows.
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_migrations  # noqa: E402
from backend.db.connection import get_pool  # noqa: E402

TEST_PREFIX = "__WP13A_TEST__"


@pytest.fixture
def isolated_migrations_dir(tmp_path, monkeypatch):
    """Redirects the runner at a throwaway directory instead of the real scripts/ folder --
    these tests must never apply or bootstrap-seed the project's real migration history."""
    monkeypatch.setattr(run_migrations, "MIGRATIONS_DIR", tmp_path)
    monkeypatch.setattr(run_migrations, "PRE_RUNNER_MIGRATIONS", set())
    yield tmp_path


@pytest.fixture
def cleanup_tracking_rows():
    applied_this_test = []
    yield applied_this_test
    if applied_this_test:
        with get_pool().connection() as conn:
            for filename in applied_this_test:
                conn.execute("delete from schema_migrations where filename = %s", (filename,))


def test_ensure_tracking_table_is_idempotent():
    run_migrations.ensure_tracking_table()
    run_migrations.ensure_tracking_table()  # must not raise on the second call


def test_pending_migrations_excludes_already_tracked(isolated_migrations_dir, cleanup_tracking_rows):
    run_migrations.ensure_tracking_table()
    filename = f"migration_{TEST_PREFIX}_a.sql"
    (isolated_migrations_dir / filename).write_text("select 1;", encoding="utf-8")

    assert run_migrations.pending_migrations(set()) == [filename]
    assert run_migrations.pending_migrations({filename}) == []


def test_apply_migration_executes_sql_and_is_queryable(isolated_migrations_dir, cleanup_tracking_rows):
    run_migrations.ensure_tracking_table()
    table_name = f"__wp13a_test_{uuid.uuid4().hex[:8]}"
    filename = f"migration_{TEST_PREFIX}_apply.sql"
    cleanup_tracking_rows.append(filename)
    (isolated_migrations_dir / filename).write_text(f"create table {table_name} (id int);", encoding="utf-8")

    try:
        run_migrations.apply_migration(filename)
        with get_pool().connection() as conn:
            exists = conn.execute("select to_regclass(%s)", (table_name,)).fetchone()[0]
            assert exists == table_name
    finally:
        with get_pool().connection() as conn:
            conn.execute(f"drop table if exists {table_name}")


def test_apply_migration_records_filename_in_tracking_table(isolated_migrations_dir, cleanup_tracking_rows):
    run_migrations.ensure_tracking_table()
    filename = f"migration_{TEST_PREFIX}_recorded.sql"
    cleanup_tracking_rows.append(filename)
    (isolated_migrations_dir / filename).write_text("select 1;", encoding="utf-8")

    run_migrations.apply_migration(filename)
    assert filename in run_migrations.applied_filenames()


def test_bootstrap_pre_runner_migrations_seeds_without_executing(isolated_migrations_dir, cleanup_tracking_rows, monkeypatch):
    run_migrations.ensure_tracking_table()
    fake_historical = f"migration_{TEST_PREFIX}_historical.sql"
    cleanup_tracking_rows.append(fake_historical)
    monkeypatch.setattr(run_migrations, "PRE_RUNNER_MIGRATIONS", {fake_historical})
    # Deliberately no file on disk for fake_historical -- bootstrapping must never try to
    # read/execute it, only record it, exactly like the real WP1-WP11b history it mirrors.

    seeded = run_migrations.bootstrap_pre_runner_migrations(already_applied=set())
    assert seeded == [fake_historical]

    with get_pool().connection() as conn:
        row = conn.execute(
            "select bootstrapped from schema_migrations where filename = %s", (fake_historical,)
        ).fetchone()
    assert row == (True,)


def test_bootstrap_is_a_noop_when_already_applied(isolated_migrations_dir, monkeypatch):
    run_migrations.ensure_tracking_table()
    fake_historical = f"migration_{TEST_PREFIX}_already_there.sql"
    monkeypatch.setattr(run_migrations, "PRE_RUNNER_MIGRATIONS", {fake_historical})

    seeded = run_migrations.bootstrap_pre_runner_migrations(already_applied={fake_historical})
    assert seeded == []


def test_real_project_migrations_are_all_already_tracked():
    """The 5 real migrations applied by hand before this runner existed (WP1, WP3,
    WP8/WP9, WP10, WP11b) must already be reflected in the real tracking table -- this
    confirms the live bootstrap this WP performed against the real database actually
    took effect, without re-running against the real scripts/ directory."""
    run_migrations.ensure_tracking_table()
    already = run_migrations.applied_filenames()
    for filename in run_migrations.PRE_RUNNER_MIGRATIONS:
        assert filename in already, f"{filename} should already be tracked from this WP's live bootstrap"
