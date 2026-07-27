"""Migration runner (Phase 11 section 12, WP13a). Replaces the hand-run-SQL-in-Supabase's-
editor workflow this project used through WP1-WP11b -- every migration_*.sql file in this
directory is tracked in a `schema_migrations` table (filename + applied_at) and applied
in filename order exactly once, instead of relying on the developer to remember which
migrations have already run against a given database.

Usage:
    .venv\\Scripts\\python.exe scripts\\run_migrations.py           # apply any pending migrations
    .venv\\Scripts\\python.exe scripts\\run_migrations.py --check   # list pending without applying

Bootstrapping: five migrations (WP1, WP3, WP8/9, WP10, WP11b) were already applied by hand
before this runner existed. migration_wp1_governance_knowledge.sql in particular is NOT
idempotent (plain `create table`, no `if not exists`) -- re-executing it against a database
that already has these tables would fail outright. So on first run, if the tracking table
is empty, these five are recorded as already-applied (their real history) rather than
re-executed, and only migrations added after WP13a go through the actual apply path.
"""

import argparse
import sys
from pathlib import Path

# Only needed so `from backend...` resolves when this file is run directly as a script
# (python scripts/run_migrations.py) -- Python auto-adds the script's own directory to
# sys.path, not its parent. Harmless (and a no-op) when this module is imported instead,
# e.g. from tests, since the importer already has the project root on sys.path by then.
# Run from the project root, same as every other script in this project (see the module
# docstring's usage line) -- python-dotenv's load_dotenv() (backend/db/connection.py)
# resolves .env relative to the caller's own working directory, not this file's location.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.db.connection import get_pool  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent

# Applied by hand, before this runner existed (see module docstring) -- recorded as history,
# never re-executed. Anything not in this set is applied for real the first time it's seen.
PRE_RUNNER_MIGRATIONS = {
    "migration_wp1_governance_knowledge.sql",
    "migration_wp3_knowledge_lifecycle.sql",
    "migration_wp8_wp9_node_columns.sql",
    "migration_wp10_cycles.sql",
    "migration_wp11b_node_temporal.sql",
}


def ensure_tracking_table() -> None:
    with get_pool().connection() as conn:
        conn.execute(
            """
            create table if not exists schema_migrations (
                filename text primary key,
                applied_at timestamptz not null default now(),
                bootstrapped boolean not null default false
            )
            """
        )


def applied_filenames() -> set:
    with get_pool().connection() as conn:
        rows = conn.execute("select filename from schema_migrations").fetchall()
    return {r[0] for r in rows}


def bootstrap_pre_runner_migrations(already_applied: set) -> list:
    to_seed = [f for f in sorted(PRE_RUNNER_MIGRATIONS) if f not in already_applied]
    if not to_seed:
        return []
    with get_pool().connection() as conn:
        for filename in to_seed:
            conn.execute(
                "insert into schema_migrations (filename, bootstrapped) values (%s, true) "
                "on conflict (filename) do nothing",
                (filename,),
            )
    return to_seed


def pending_migrations(already_applied: set) -> list:
    all_files = sorted(p.name for p in MIGRATIONS_DIR.glob("migration_*.sql"))
    return [f for f in all_files if f not in already_applied]


def apply_migration(filename: str) -> None:
    sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    with get_pool().connection() as conn:
        conn.execute(sql)
        conn.execute("insert into schema_migrations (filename) values (%s)", (filename,))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="List pending migrations without applying them")
    args = parser.parse_args()

    ensure_tracking_table()
    already = applied_filenames()

    seeded = bootstrap_pre_runner_migrations(already)
    if seeded:
        print(f"Bootstrapped {len(seeded)} pre-runner migration(s) as already-applied history:")
        for f in seeded:
            print(f"  - {f}")
        already |= set(seeded)

    pending = pending_migrations(already)
    if not pending:
        print("No pending migrations. Database is up to date.")
        return

    if args.check:
        print(f"{len(pending)} pending migration(s):")
        for f in pending:
            print(f"  - {f}")
        return

    print(f"Applying {len(pending)} pending migration(s):")
    for filename in pending:
        print(f"  - {filename} ... ", end="")
        apply_migration(filename)
        print("done")
    print("All pending migrations applied.")


if __name__ == "__main__":
    main()
